import bpy
from . import __version__
from .controller import RT, _take_names, TAKE_PREFIX


class _P:
    bl_space_type, bl_region_type, bl_category = 'VIEW_3D', 'UI', "Alex1BC"


class ALEX1BC_PT_main(_P, bpy.types.Panel):
    bl_label = "Alex1BC"
    bl_idname = "ALEX1BC_PT_main"

    def draw_header(self, context):
        self.layout.label(text=f"v{__version__}")

    def draw(self, context):
        hub, col = RT.hub, self.layout.column(align=True)
        if not RT.running:
            col.label(text="Your camera. Your movement.")
            col.scale_y = 1.6
            col.operator("alex1bc.start", icon='PLAY')
            return
        status = hub.status
        if status == 'error':
            col.label(text=hub.error or "Server error", icon='ERROR')
            col.operator("alex1bc.stop", icon='CANCEL')
            return
        if status == 'connected':
            col.label(text=f"Connected: {hub.device}", icon='CHECKMARK')
            col.label(text=f"Latency {hub.rtt_ms:.0f} ms")
        elif status == 'starting':
            col.label(text="Starting...", icon='TIME')
        else:
            col.label(text="Waiting for phone", icon='TIME')
        if RT.note:
            col.label(text=RT.note, icon='INFO')


class ALEX1BC_PT_connection(_P, bpy.types.Panel):
    bl_label, bl_parent_id, bl_idname = "Connection", "ALEX1BC_PT_main", "ALEX1BC_PT_connection"

    @classmethod
    def poll(cls, context):
        return RT.running

    def draw(self, context):
        hub, lay = RT.hub, self.layout
        if hub.status == 'connected':
            lay.operator("alex1bc.disconnect", icon='X')
        elif hub.status == 'waiting':
            if RT.qr_icon:
                lay.template_icon(icon_value=RT.qr_icon, scale=11)
            c = hub.code or "---------"
            lay.label(text=f"Code  {c[:3]} {c[3:6]} {c[6:]}")
            lay.label(text="Scan with the phone camera, same Wi-Fi", icon='OUTLINER_OB_CAMERA')
            row = lay.row(align=True)
            row.operator("alex1bc.new_code", icon='FILE_REFRESH'); row.operator("alex1bc.copy_url", icon='COPYDOWN')
            box = lay.box(); box.label(text="USB cable (most stable)", icon='LINKED')
            box.label(text="1. Turn on USB debugging, plug in")
            box.operator("alex1bc.adb_reverse", icon='PLUGIN')
            box.label(text=f"2. Phone browser: {hub.urls.get('usb', '')}")
            box.label(text="3. Type the code above")
        lay.operator("alex1bc.stop", icon='CANCEL')


class ALEX1BC_PT_camera(_P, bpy.types.Panel):
    bl_label, bl_parent_id, bl_idname = "Camera", "ALEX1BC_PT_main", "ALEX1BC_PT_camera"

    def draw(self, context):
        lay, cam = self.layout, context.scene.camera
        if not cam:
            lay.label(text="No active camera", icon='ERROR'); lay.operator("alex1bc.add_camera", icon='ADD'); return
        lay.prop(context.scene, "camera", text="")
        lay.prop(cam.data, "lens", text="Focal length")
        lay.prop(cam.data.dof, "use_dof", text="Depth of field")
        if cam.data.dof.use_dof:
            lay.prop(cam.data.dof, "focus_distance"); lay.prop(cam.data.dof, "aperture_fstop")
        lay.operator("alex1bc.recenter", icon='ORIENTATION_GIMBAL')


class ALEX1BC_PT_control(_P, bpy.types.Panel):
    bl_label, bl_parent_id, bl_idname = "Control", "ALEX1BC_PT_main", "ALEX1BC_PT_control"

    def draw(self, context):
        s = context.window_manager.alex1bc
        for p in ("move_speed", "look_speed", "smoothing"):
            self.layout.prop(s, p)
        self.layout.label(text="Mode (Gyro / Analog / Hybrid) is chosen on the phone")


class ALEX1BC_PT_recording(_P, bpy.types.Panel):
    bl_label, bl_parent_id, bl_idname = "Recording", "ALEX1BC_PT_main", "ALEX1BC_PT_recording"

    def draw(self, context):
        lay = self.layout
        if RT.rec:
            lay.label(text="REC" if RT.playing else "PAUSED", icon='REC')
        lay.label(text="Record and play from the phone. Each take is a new action;")
        lay.label(text="existing animation is never overwritten.")
        takes = _take_names()
        for n in takes[-8:]:
            row = lay.row(align=True)
            row.label(text=n[len(TAKE_PREFIX):] and f"Take {n[len(TAKE_PREFIX):]}", icon='ACTION')
            o = row.operator("alex1bc.take_apply", text="Use"); o.name = n
            o = row.operator("alex1bc.take_delete", text="", icon='TRASH'); o.name = n
        if RT.last_take:
            lay.operator("alex1bc.take_undo", icon='LOOP_BACK')
        if not takes:
            lay.label(text="No takes yet")


class ALEX1BC_PT_advanced(_P, bpy.types.Panel):
    bl_label, bl_parent_id, bl_idname = "Advanced", "ALEX1BC_PT_main", "ALEX1BC_PT_advanced"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        row = self.layout.row(); row.enabled = not RT.running
        row.prop(context.window_manager.alex1bc, "port")
        row = self.layout.row(); row.enabled = not RT.running
        row.prop(context.window_manager.alex1bc, "host")
        self.layout.label(text="Allow this port in the Windows Firewall (Private networks).")


CLASSES = (ALEX1BC_PT_main, ALEX1BC_PT_connection, ALEX1BC_PT_camera, ALEX1BC_PT_control, ALEX1BC_PT_recording, ALEX1BC_PT_advanced)

def register():
    for c in CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(CLASSES): bpy.utils.unregister_class(c)
