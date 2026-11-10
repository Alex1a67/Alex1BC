"""Run with a Python that has the `bpy` module:  python tests/bpy_integration.py
Drives the REAL add-on inside real Blender with a simulated phone over real TLS WebSockets."""
import asyncio, json, math, os, site, ssl, sys, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "addon"))
sys.path.append(site.getusersitepackages())
import bpy, websockets
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
import alex1bc
alex1bc.register()
from alex1bc import controller as C
RT = C.RT
PORT = 47950
bpy.context.window_manager.alex1bc.port = PORT
bpy.context.window_manager.alex1bc.host = '127.0.0.1'
fails = []
def check(name, cond, info=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{info}]" if info else ""))
    if not cond: fails.append(name)

class Phone:
    def __init__(self):
        self.loop = asyncio.new_event_loop(); self.msgs = []; self.inp = None; self.ws = None; self.alive = False
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
    def run(self, coro): return asyncio.run_coroutine_threadsafe(coro, self.loop).result(10)
    async def _connect(self, first):
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        self.ws = await websockets.connect(f"wss://127.0.0.1:{PORT}/ws", ssl=ctx)
        await self.ws.send(json.dumps(first)); self.alive = True
        asyncio.ensure_future(self._reader()); asyncio.ensure_future(self._sender())
    async def _reader(self):
        try:
            async for m in self.ws: self.msgs.append(json.loads(m))
        except Exception: pass
        self.alive = False
    async def _sender(self):
        while self.alive:
            if self.inp is not None:
                try: await self.ws.send(json.dumps({'t': 'in', **self.inp}))
                except Exception: return
            await asyncio.sleep(1/60)
    def connect(self, first): self.run(self._connect(first))
    def cmd(self, c, v=None): self.run(self.ws.send(json.dumps({'t': 'cmd', 'c': c, 'v': v})))
    def close(self): self.run(self.ws.close()); self.alive = False
    def last(self, t):
        for m in reversed(self.msgs):
            if m['t'] == t: return m

def pump(sec):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        C._tick(); time.sleep(1/60)

def fcs(action):
    try: return list(action.fcurves)
    except AttributeError:      # Blender 5: layered actions
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: out += list(cb.fcurves)
        return out

def heading(v): return math.degrees(math.atan2(-v.x, v.y))

def pump_track(sec):
    """Pump ticks and return the largest per-tick turn (degrees) of the camera."""
    worst, prev = 0.0, forward(cam).copy()
    end = time.monotonic() + sec
    while time.monotonic() < end:
        C._tick(); time.sleep(1/60)
        cur = forward(cam); worst = max(worst, math.degrees(prev.angle(cur, 0.0))); prev = cur.copy()
    return worst

def forward(cam):
    bpy.context.view_layer.update()
    return cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))

scene = bpy.context.scene
scene.render.fps = 24; scene.frame_start, scene.frame_end = 1, 250
bpy.ops.alex1bc.add_camera()
cam = scene.camera
check("add_camera makes active camera", cam is not None and cam.type == 'CAMERA')

C.start(bpy.context)
for _ in range(100):
    if RT.hub.status == 'waiting': break
    time.sleep(0.1)
check("server starts inside Blender", RT.hub.status == 'waiting', RT.hub.error)
pump(0.3)
check("QR png generated", os.path.exists(os.path.join(C.user_dir(), "pairing_qr.png")))

ph = Phone(); code = RT.hub.code
ph.connect({'t': 'pair', 'code': code, 'name': 'Test Pixel'})
pump(0.5)
check("pairing -> connected", RT.hub.status == 'connected' and RT.hub.device == 'Test Pixel')
session = ph.last('paired')['session']
check("phone receives live state", ph.last('state') and ph.last('state')['cam'] == cam.name, str(ph.last('state')))

# --- no jump on connect: pose before == after, even with phone sending an arbitrary orientation
p0 = tuple(cam.location); f0 = forward(cam).copy()
ph.inp = {'mode': 'gyro', 'o': [123.0, 80.0, 5.0, 0.0]}
step = pump_track(1.2)
f1 = forward(cam)
check("connect: heading preserved, position untouched", abs(heading(f0) - heading(f1)) < 1.0 and tuple(cam.location) == p0, f"{heading(f0):.1f} vs {heading(f1):.1f}")
check("connect: tilt eases in smoothly (no snap)", step < 3.0, f"max {step:.2f} deg per tick")

# --- gyro: turn phone 40 deg left -> camera turns 40 deg left
ph.inp = {'mode': 'gyro', 'o': [163.0, 80.0, 5.0, 0.0]}
pump(1.5)
f2 = forward(cam)
ang = math.degrees(math.atan2(f1.x, f1.y) - math.atan2(f2.x, f2.y))
check("gyro: phone yaw +40 turns camera 40deg", abs(ang - 40) < 1.5, f"{ang:.2f}")
ph.inp = {'mode': 'gyro', 'o': [163.0, 50.0, 5.0, 0.0]}      # tilt phone down 30 deg
pump(1.5)
check("gyro: tilting phone down pitches camera down", forward(cam).z < f2.z - 0.3, f"{forward(cam).z:.2f}")

# --- analog movement + zoom
cam_before = cam.location.copy()
ph.inp = {'mode': 'analog', 'my': 1.0, 'zoom': 1.0}
lens0 = cam.data.lens; pump(1.0)
moved = (cam.location - cam_before).length
check("analog: forward stick moves camera", moved > 1.2, f"{moved:.2f} m")
check("analog: zoom increases focal length", cam.data.lens > lens0 * 1.5, f"{cam.data.lens:.1f}mm")
ph.inp = {'mode': 'analog', 'mz': 1.0}; z0 = cam.location.z; pump(0.7)
check("analog: rise slider raises camera", cam.location.z > z0 + 0.8)
ph.inp = {'mode': 'analog'}; pump(0.5)
ph.cmd('lens', 35); pump(0.3)
check("lens command sets 35mm", abs(cam.data.lens - 35) < 0.01, f"{cam.data.lens}")

# --- manual keyframe
ph.cmd('key'); pump(0.3)
check("KEY inserts keyframes", cam.animation_data and cam.animation_data.action and len(fcs(cam.animation_data.action)) >= 3)
orig_action = cam.animation_data.action.name

# --- freeze
ph.inp = {'mode': 'analog', 'my': 1.0, 'fr': 1}; p = cam.location.copy(); pump(0.4)
check("freeze stops camera input", (cam.location - p).length < 1e-4)

# --- record a take (existing animation must be preserved)
ph.inp = {'mode': 'analog', 'my': 0.8, 'lx': 0.4}
ph.cmd('rec'); pump(0.2)
check("REC starts, playback runs", RT.rec is not None and RT.playing)
pump(2.0)
check("frame advances in real time", scene.frame_current > 30, f"frame {scene.frame_current}")
ph.cmd('rec'); pump(0.4)
takes = C._take_names()
check("take created", len(takes) == 1, str(takes))
act = bpy.data.actions.get(takes[0]) if takes else None
check("take assigned to camera", cam.animation_data.action == act)
kp = [len(fc.keyframe_points) for fc in fcs(act)] if act else []
check("take has dense editable keyframes", kp and min(kp) >= 40, f"{kp}")
check("previous animation preserved (not overwritten)", bpy.data.actions.get(orig_action) is not None and bpy.data.actions[orig_action].use_fake_user)
locs = [fc for fc in fcs(act) if fc.data_path == 'location' and fc.array_index == 1]
check("recorded path moves forward over time", locs and locs[0].keyframe_points[-1].co[1] > locs[0].keyframe_points[0].co[1] + 1.0)
scene.frame_set(20); y20 = cam.location.y; scene.frame_set(40); y40 = cam.location.y
check("scrubbing plays back recorded motion", y40 > y20, f"{y20:.2f}->{y40:.2f}")

# --- undo take restores old animation
ph.cmd('undo_take'); pump(0.3)
check("undo take restores previous action", cam.animation_data.action and cam.animation_data.action.name == orig_action and not C._take_names())

# --- safe disconnect
ph.inp = {'mode': 'analog', 'my': 1.0}; pump(0.3)
ph.close(); pump(0.6)
check("disconnect -> waiting", RT.hub.status == 'waiting')
p = cam.location.copy(); pump(0.5)
check("camera holds still after disconnect", (cam.location - p).length < 1e-4)

# --- resume via session: no jump
f_pre = forward(cam).copy(); pos_pre = cam.location.copy()
ph2 = Phone(); ph2.connect({'t': 'resume', 'session': session}); pump(0.3)
ph2.inp = {'mode': 'hybrid', 'o': [10.0, 95.0, 0.0, 0.0]}; step2 = pump_track(1.2)
check("resume session reconnects", RT.hub.status == 'connected')
check("reconnect: heading + position preserved, no snap", abs(heading(f_pre) - heading(forward(cam))) < 1.0 and (cam.location - pos_pre).length < 1e-3 and step2 < 3.0, f"step {step2:.2f}")

# --- user moves camera manually in Blender: rig follows (no snap back)
ph2.inp = {'mode': 'analog'}; cam.location.x += 5; pump(0.5)
check("manual Blender move is adopted (no snap back)", abs(cam.location.x - (pos_pre.x + 5)) < 0.01, f"{cam.location.x}")

# --- camera switching + missing camera
data = bpy.data.cameras.new("B"); o2 = bpy.data.objects.new("CamB", data); scene.collection.objects.link(o2)
ph2.cmd('camera', 'CamB'); pump(0.4)
check("phone switches active camera", scene.camera == o2)

# --- stop
ph2.close(); C.stop(); time.sleep(0.2)
check("stop unregisters timer and server", not bpy.app.timers.is_registered(C.tick) and RT.hub.status == 'stopped')
alex1bc.unregister()
print("\nBlender", bpy.app.version_string, "-", "ALL PASSED" if not fails else f"FAILED: {fails}")
sys.exit(1 if fails else 0)
