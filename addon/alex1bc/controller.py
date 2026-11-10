"""Blender side: applies phone input to the camera on Blender's MAIN thread (timer), records takes,
owns operators and settings. The network thread (server.py) never touches bpy data."""
import math, os, queue, shutil, subprocess, time
import bpy
from bpy.props import FloatProperty, IntProperty
from mathutils import Euler, Matrix, Quaternion
from . import core
from .server import AlexServer, Hub

TAKE_PREFIX = "A1BC_Take_"
HERE = os.path.dirname(__file__)


class Runtime:
    def __init__(self):
        self.hub = None
        self.server = None
        self.running = False
        self.rig = core.Rig()
        self.last = time.monotonic()
        self.cam_name = None
        self.last_sig = None
        self.was_stale = True
        self.playing = False
        self.t_start = 0.0
        self.f_start = 0.0
        self.rec = None
        self.last_take = None          # (camera, take, previous action or None)
        self.note = ""                 # status line shown in the panel
        self.qr_for = None
        self.qr_icon = 0
        self.pcoll = None
        self.ui_gen = -1
        self.ui_time = 0.0
        self.state_time = 0.0
        self.err_time = 0.0
RT = Runtime()


# ------------------------------------------------------------------ settings
class ALEX1BC_Settings(bpy.types.PropertyGroup):
    port: IntProperty(name="Port", default=47800, min=1024, max=65000,
                      description="HTTPS port for the phone controller (port+1 is used for the USB route)")
    host: bpy.props.StringProperty(name="Bind address", default="",
                                   description="Leave empty to auto-detect your Wi-Fi/LAN address. Set it if you use a VPN or several network adapters")
    move_speed: FloatProperty(name="Move speed", default=3.0, min=0.1, max=50.0, description="Metres per second at full stick")
    look_speed: FloatProperty(name="Turn speed", default=90.0, min=10.0, max=360.0, description="Degrees per second at full stick")
    smoothing: FloatProperty(name="Smoothing", default=0.3, min=0.0, max=1.0, subtype='FACTOR',
                             description="0 = raw and instant, 1 = very soft cinematic damping")


def user_dir():
    try:
        return bpy.utils.extension_path_user(__package__, path="", create=True)
    except Exception:
        d = os.path.join(bpy.utils.user_resource('CONFIG'), "alex1bc")
        os.makedirs(d, exist_ok=True)
        return d


# ------------------------------------------------------------------ camera helpers
def _rot_path(cam):
    return 'rotation_quaternion' if cam.rotation_mode == 'QUATERNION' else 'rotation_euler'

def _signature(cam):
    rot = cam.rotation_quaternion if cam.rotation_mode == 'QUATERNION' else cam.rotation_euler
    return tuple(cam.location) + tuple(rot) + (cam.data.lens,)

def _same(a, b):
    return all(abs(x - y) <= 2e-4 + 1e-5 * abs(x) for x, y in zip(a, b))

def _adopt(cam):
    loc, rot, _ = cam.matrix_world.decompose()
    RT.rig.adopt(loc, (rot.w, rot.x, rot.y, rot.z), cam.data.lens)

def _set_pose(cam, pos, q, lens, euler_hint=None):
    M = Matrix.Translation(pos) @ Quaternion(q).to_matrix().to_4x4()
    if cam.parent:
        M = cam.matrix_parent_inverse.inverted() @ cam.parent.matrix_world.inverted() @ M
    loc, rq, _ = M.decompose()
    cam.location = loc
    if cam.rotation_mode == 'QUATERNION':
        cam.rotation_quaternion = rq
    else:
        if cam.rotation_mode == 'AXIS_ANGLE':
            cam.rotation_mode = 'XYZ'
        hint = euler_hint if euler_hint is not None else Euler(cam.rotation_euler, cam.rotation_mode)
        cam.rotation_euler = rq.to_euler(cam.rotation_mode, hint)
    if abs(cam.data.lens - lens) > 1e-4:
        cam.data.lens = lens

def _animated(cam):
    ad = cam.animation_data
    if not ad or not ad.action:
        return False
    try:
        return any(fc.data_path in ('location', 'rotation_euler', 'rotation_quaternion') for fc in ad.action.fcurves)
    except AttributeError:      # newer Blender action API
        return True

def _fps(scene):
    return scene.render.fps / (scene.render.fps_base or 1.0)

def cameras(scene):
    return sorted(o.name for o in scene.objects if o.type == 'CAMERA')[:24]


# ------------------------------------------------------------------ transport + recording
def _play(scene, now):
    RT.playing, RT.t_start, RT.f_start = True, now, float(scene.frame_current)

def _pause():
    RT.playing = False

def _float_frame(scene, now):
    return RT.f_start + (now - RT.t_start) * _fps(scene)

def _advance(scene, now):
    if not RT.playing:
        return
    f = _float_frame(scene, now)
    if f > scene.frame_end + 0.999:
        if RT.rec:
            RT.note = "Recording stopped at the end of the frame range"
            _rec_stop(scene, now)
            return
        RT.t_start, RT.f_start, f = now, float(scene.frame_start), float(scene.frame_start)
    if int(f) != scene.frame_current:
        scene.frame_set(int(f))

def _take_names():
    return sorted(a.name for a in bpy.data.actions if a.name.startswith(TAKE_PREFIX))

def _next_take_name():
    n = len(_take_names()) + 1
    while f"{TAKE_PREFIX}{n:03d}" in bpy.data.actions:
        n += 1
    return f"{TAKE_PREFIX}{n:03d}"

def _rec_start(scene, cam, now):
    if RT.rec:
        return
    if not cam:
        RT.hub.toast("No camera in the scene", 'error'); return
    prev = cam.animation_data.action if cam.animation_data else None
    if prev:                                   # keep existing animation safe; restorable via Undo take
        prev.use_fake_user = True
        cam.animation_data.action = None
    RT.rec = {'cam': cam.name, 'prev': prev.name if prev else None, 'f0': scene.frame_current, 'samples': [], 'paused': False}
    _play(scene, now)
    RT.note = "Recording"

def _rec_sample(scene, now, rig):
    if RT.rec and RT.playing:
        RT.rec['samples'].append((_float_frame(scene, now), tuple(rig.pos), rig.q, rig.lens))

def _pose_at(samples, f):
    lo, hi = 0, len(samples) - 1
    if f <= samples[0][0]:
        return samples[0][1:]
    if f >= samples[hi][0]:
        return samples[hi][1:]
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if samples[mid][0] <= f else (lo, mid)
    a, b = samples[lo], samples[hi]
    t = (f - a[0]) / ((b[0] - a[0]) or 1.0)
    return (tuple(x + (y - x) * t for x, y in zip(a[1], b[1])), core.qslerp(a[2], b[2], t), a[3] + (b[3] - a[3]) * t)

def _rec_stop(scene, now, cancel=False):
    rec = RT.rec
    if not rec:
        return
    _pause()
    RT.rec = None
    cam = bpy.data.objects.get(rec['cam'])
    prev = bpy.data.actions.get(rec['prev']) if rec['prev'] else None
    s = rec['samples']
    if cancel or not cam or len(s) < 2:
        if cam and prev:
            cam.animation_data_create(); cam.animation_data.action = prev
        RT.note = "Recording too short - nothing saved" if not cancel else "Recording cancelled"
        if RT.hub: RT.hub.toast(RT.note, 'error')
        scene.frame_set(rec['f0'])
        return
    name = _next_take_name()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    cam.animation_data_create()
    cam.animation_data.action = act
    path, lens_varies = _rot_path(cam), (max(x[3] for x in s) - min(x[3] for x in s)) > 0.01
    hint = Euler(cam.rotation_euler, cam.rotation_mode) if path == 'rotation_euler' else None
    first, last = int(math.floor(s[0][0])), int(math.floor(s[-1][0]))
    for f in range(first, last + 1):
        pos, q, lens = _pose_at(s, float(f))
        _set_pose(cam, pos, q, lens, hint)
        if hint is not None:
            hint = Euler(cam.rotation_euler, cam.rotation_mode)
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert(path, frame=f)
        if lens_varies:
            cam.data.keyframe_insert('lens', frame=f)
    RT.last_take = (cam.name, name, prev.name if prev else None)
    scene.frame_set(rec['f0'])
    _adopt_soon()
    RT.note = f"Saved {name}: frames {first}-{last}"
    if RT.hub: RT.hub.toast(f"Saved {name} ({last - first + 1} frames)", 'ok')

def _adopt_soon():
    RT.last_sig = None

def _undo_take(scene):
    if not RT.last_take:
        if RT.hub: RT.hub.toast("No take to undo", 'error')
        return
    cam_n, take_n, prev_n = RT.last_take
    cam, take, prev = bpy.data.objects.get(cam_n), bpy.data.actions.get(take_n), (bpy.data.actions.get(prev_n) if prev_n else None)
    if cam:
        cam.animation_data_create()
        cam.animation_data.action = prev
    if take:
        take.use_fake_user = False
        bpy.data.actions.remove(take)
    RT.last_take = None
    scene.frame_set(scene.frame_current)
    _adopt_soon()
    RT.note = f"Removed {take_n}" + (" and restored previous animation" if prev else "")
    if RT.hub: RT.hub.toast(RT.note, 'ok')

def _insert_key(scene, cam):
    if not cam:
        return
    cam.keyframe_insert('location'); cam.keyframe_insert(_rot_path(cam)); cam.data.keyframe_insert('lens')
    RT.hub.toast(f"Keyframe at frame {scene.frame_current}", 'ok')


# ------------------------------------------------------------------ commands from the phone
def _handle(cmd, scene, cam, now):
    c, v = cmd['c'], cmd.get('v')
    if c == '_connected':
        RT.rig.realign(); RT.was_stale = True
        if RT.rec: RT.note = "Phone reconnected - press play to resume recording"
    elif c == '_disconnected':
        RT.rig.stop()
        if RT.rec and RT.playing:
            _pause(); RT.note = "Phone disconnected - recording paused"
    elif c == 'recenter':
        RT.rig.realign(); RT.hub.toast("Recentered", 'ok')
    elif c == 'lens' and isinstance(v, (int, float)) and math.isfinite(v):
        RT.rig.set_lens(v)
    elif c == 'speed' and isinstance(v, (int, float)) and math.isfinite(v):
        bpy.context.window_manager.alex1bc.move_speed = max(0.1, min(50.0, float(v)))
    elif c == 'play':
        if RT.playing: _pause()
        else: _play(scene, now)
        if RT.rec: RT.rec['paused'] = not RT.playing
    elif c == 'rec':
        if RT.rec: _rec_stop(scene, now)
        else: _rec_start(scene, cam, now)
    elif c == 'rec_stop':
        _rec_stop(scene, now)
    elif c == 'key':
        _insert_key(scene, cam)
    elif c == 'undo_take':
        _undo_take(scene)
    elif c == 'camera' and isinstance(v, str):
        obj = scene.objects.get(v)
        if obj and obj.type == 'CAMERA':
            if RT.rec: RT.hub.toast("Stop recording before switching camera", 'error')
            else: scene.camera = obj


# ------------------------------------------------------------------ QR / UI refresh
def _update_qr():
    hub = RT.hub
    base = hub.urls.get('lan') or hub.urls.get('usb')
    if not base or not hub.code:
        return
    key = (base, hub.code)
    if key == RT.qr_for:
        return
    from .vendor import segno
    path = os.path.join(user_dir(), "pairing_qr.png")
    fp = f"&fp={hub.fingerprint}" if hub.fingerprint and base.startswith("https") else ""
    segno.make(f"{base}/#t={hub.code}{fp}", error='m').save(path, scale=8, border=2, dark='#090D17', light='#FFFFFF')
    try:
        import bpy.utils.previews as previews
        if RT.pcoll:
            previews.remove(RT.pcoll)
        RT.pcoll = previews.new()
        RT.qr_icon = RT.pcoll.load(f"qr{abs(hash(key))}", path, 'IMAGE').icon_id
    except Exception:
        RT.qr_icon = 0
    RT.qr_for = key

def _redraw(wm):
    for win in wm.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for r in area.regions:
                    if r.type == 'UI':
                        r.tag_redraw()


# ------------------------------------------------------------------ main-thread tick
def tick():
    if not RT.running:
        return None
    try:
        _tick()
    except Exception as e:                                   # report once per 5 s, keep running
        import traceback; traceback.print_exc()
        if time.monotonic() - RT.err_time > 5 and RT.hub:
            RT.err_time = time.monotonic(); RT.hub.toast(f"Blender error: {e}", 'error')
    return 1.0 / 60.0

def _tick():
    hub, rig = RT.hub, RT.rig
    now = time.monotonic()
    dt = max(1e-3, min(0.1, now - RT.last)); RT.last = now
    scene, wm = bpy.context.scene, bpy.context.window_manager
    st = wm.alex1bc
    rig.s.move_speed, rig.s.look_speed, rig.s.smoothing = st.move_speed, st.look_speed, st.smoothing
    cam = scene.camera

    while True:
        try: cmd = hub.cmds.get_nowait()
        except queue.Empty: break
        _handle(cmd, scene, cam, now)
        cam = scene.camera
    _advance(scene, now)
    if hub.status in ('waiting', 'connected'):
        _update_qr()

    if cam and cam.type == 'CAMERA':
        sig = _signature(cam)
        if RT.cam_name != cam.name or RT.last_sig is None or not _same(sig, RT.last_sig):
            if RT.last_sig is not None and RT.rec is None:
                bpy.context.view_layer.update()
            _adopt(cam); RT.cam_name = cam.name
        inp, age = hub.get_input()
        live = (hub.status == 'connected' and inp is not None and age < 0.6 and not inp['freeze'])
        playing_anim = RT.playing and RT.rec is None and _animated(cam)
        if live and not playing_anim:
            if RT.was_stale:
                rig.realign(); RT.was_stale = False
            rig.step(dt, inp['mode'], inp, inp['q'])
            _set_pose(cam, rig.pos, rig.q, rig.lens)
            _rec_sample(scene, now, rig)
        else:
            RT.was_stale = True
            rig.stop()
            if RT.rec and RT.playing and hub.status == 'connected' and inp is not None and inp['freeze']:
                _rec_sample(scene, now, rig)
        RT.last_sig = _signature(cam)

    if now - RT.state_time > 0.1:
        RT.state_time = now
        hub.state = {
            'cam': cam.name if cam else None, 'cams': cameras(scene), 'lens': round(rig.lens, 1),
            'frame': scene.frame_current, 'fps': round(_fps(scene), 2), 'playing': RT.playing,
            'rec': 'off' if not RT.rec else ('rec' if RT.playing else 'pause'),
            'rec_s': round(len(RT.rec['samples']) / 60.0, 1) if RT.rec else 0.0,
            'takes': len(_take_names()), 'speed': round(st.move_speed, 2), 'blender': bpy.app.version_string,
        }
    if hub.generation != RT.ui_gen or now - RT.ui_time > 0.5:
        RT.ui_gen, RT.ui_time = hub.generation, now
        _redraw(wm)


# ------------------------------------------------------------------ start / stop
def start(context):
    if RT.running:
        return
    st = context.window_manager.alex1bc
    RT.hub = Hub()
    RT.hub.new_code()
    RT.server = AlexServer(RT.hub, os.path.join(HERE, "web"), user_dir(), st.port, st.host.strip() or None)
    RT.server.start()
    RT.running, RT.qr_for, RT.last_sig, RT.was_stale, RT.note = True, None, None, True, ""
    RT.last = time.monotonic()
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=0.05, persistent=True)

def stop():
    if RT.rec:
        try: _rec_stop(bpy.context.scene, time.monotonic(), cancel=True)
        except Exception: pass
    RT.running, RT.playing = False, False
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if RT.server:
        RT.server.stop()
    RT.server = None
    if RT.pcoll:
        import bpy.utils.previews as previews
        previews.remove(RT.pcoll); RT.pcoll = None
    RT.qr_icon, RT.qr_for = 0, None


# ------------------------------------------------------------------ operators
class ALEX1BC_OT_start(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.start", "Start Alex1BC", "Start the local server and show the pairing QR code"
    def execute(self, context):
        start(context); return {'FINISHED'}

class ALEX1BC_OT_stop(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.stop", "Stop", "Stop the server and disconnect the phone"
    def execute(self, context):
        stop(); return {'FINISHED'}

class ALEX1BC_OT_new_code(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.new_code", "New code", "Create a fresh pairing code and QR"
    def execute(self, context):
        if RT.hub: RT.hub.new_code()
        return {'FINISHED'}

class ALEX1BC_OT_disconnect(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.disconnect", "Disconnect phone", "Disconnect and forget the paired phone"
    def execute(self, context):
        if RT.hub and RT.server:
            RT.hub.forget(); RT.server.kick(); RT.hub.new_code()
        return {'FINISHED'}

class ALEX1BC_OT_copy_url(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.copy_url", "Copy link", "Copy the phone link to the clipboard"
    def execute(self, context):
        if RT.hub and RT.hub.code:
            base = RT.hub.urls.get('lan') or RT.hub.urls.get('usb')
            context.window_manager.clipboard = f"{base}/#t={RT.hub.code}"        # browsers need no fingerprint
        return {'FINISHED'}

class ALEX1BC_OT_adb(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.adb_reverse", "Enable USB route", "Run 'adb reverse' so the phone reaches Blender over the USB cable"
    def execute(self, context):
        adb = shutil.which("adb")
        if not adb:
            for p in (os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"), os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"), os.path.expanduser("~/Android/Sdk/platform-tools/adb")):
                if os.path.exists(p): adb = p; break
        if not adb:
            self.report({'ERROR'}, "adb not found. Install Android platform-tools and add it to PATH."); return {'CANCELLED'}
        port = context.window_manager.alex1bc.port + 1
        try:
            r = subprocess.run([adb, "reverse", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=15)
        except Exception as e:
            self.report({'ERROR'}, f"adb failed: {e}"); return {'CANCELLED'}
        if r.returncode:
            self.report({'ERROR'}, (r.stderr or r.stdout).strip() or "adb failed (is USB debugging on and the phone authorised?)"); return {'CANCELLED'}
        self.report({'INFO'}, f"USB route ready. On the phone open http://localhost:{port}")
        return {'FINISHED'}

class ALEX1BC_OT_add_camera(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.add_camera", "Add camera", "Create a camera and make it the active scene camera"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        data = bpy.data.cameras.new("Alex1BC Camera"); obj = bpy.data.objects.new("Alex1BC Camera", data)
        context.scene.collection.objects.link(obj)
        obj.location, obj.rotation_euler = (0, -6, 1.6), (math.radians(88), 0, 0)
        context.scene.camera = obj
        return {'FINISHED'}

class ALEX1BC_OT_recenter(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.recenter", "Recenter", "Make the phone's current direction the camera's current direction"
    def execute(self, context):
        RT.rig.realign(); return {'FINISHED'}

class _TakeOp:
    name: bpy.props.StringProperty()

class ALEX1BC_OT_take_apply(bpy.types.Operator, _TakeOp):
    bl_idname, bl_label, bl_description = "alex1bc.take_apply", "Use take", "Assign this take to the active camera"
    def execute(self, context):
        cam, act = context.scene.camera, bpy.data.actions.get(self.name)
        if not cam or not act: return {'CANCELLED'}
        cam.animation_data_create(); cam.animation_data.action = act
        context.scene.frame_set(context.scene.frame_current); _adopt_soon(); return {'FINISHED'}

class ALEX1BC_OT_take_delete(bpy.types.Operator, _TakeOp):
    bl_idname, bl_label, bl_description = "alex1bc.take_delete", "Delete take", "Delete this take"
    def execute(self, context):
        act = bpy.data.actions.get(self.name)
        if act: act.use_fake_user = False; bpy.data.actions.remove(act)
        return {'FINISHED'}

class ALEX1BC_OT_take_undo(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "alex1bc.take_undo", "Undo last take", "Remove the last take and restore the animation the camera had before it"
    def execute(self, context):
        _undo_take(context.scene); return {'FINISHED'}


CLASSES = (ALEX1BC_Settings, ALEX1BC_OT_start, ALEX1BC_OT_stop, ALEX1BC_OT_new_code, ALEX1BC_OT_disconnect,
           ALEX1BC_OT_copy_url, ALEX1BC_OT_adb, ALEX1BC_OT_add_camera, ALEX1BC_OT_recenter,
           ALEX1BC_OT_take_apply, ALEX1BC_OT_take_delete, ALEX1BC_OT_take_undo)

def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.WindowManager.alex1bc = bpy.props.PointerProperty(type=ALEX1BC_Settings)

def unregister():
    stop()
    del bpy.types.WindowManager.alex1bc
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
