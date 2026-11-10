"""Camera math and the control 'rig'. Pure Python - no bpy - so it is unit-tested.

Frames
------
Blender world: Z-up, right-handed. A Blender camera looks along its local -Z, local +Y is up.
Phone (W3C DeviceOrientation): Earth frame is X=east, Y=north, Z=up (also Z-up, right-handed).
Device frame (portrait): x=right, y=top of screen, z=out of the screen. The back camera looks
along -z, which is exactly the Blender camera convention. So the camera's world rotation is the
device-to-earth rotation  R = Rz(alpha) * Rx(beta) * Ry(gamma), times Rz(-screen_angle) for
landscape holds. Quaternions are (w, x, y, z).
"""
import math

# ---------------------------------------------------------------- quaternions
def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2)

def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])

def qnormalize(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)

def qaxis(axis, angle):
    s = math.sin(angle / 2.0)
    return (math.cos(angle / 2.0), axis[0] * s, axis[1] * s, axis[2] * s)

def qrotate(q, v):
    r = qmul(qmul(q, (0.0, v[0], v[1], v[2])), qconj(q))
    return (r[1], r[2], r[3])

def qslerp(a, b, t):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = tuple(-c for c in b)
        dot = -dot
    if dot > 0.9995:
        return qnormalize(tuple(x + (y - x) * t for x, y in zip(a, b)))
    th0 = math.acos(dot)
    th = th0 * t
    s0 = math.cos(th) - dot * math.sin(th) / math.sin(th0)
    s1 = math.sin(th) / math.sin(th0)
    return qnormalize(tuple(s0 * x + s1 * y for x, y in zip(a, b)))

def device_quaternion(alpha_deg, beta_deg, gamma_deg, screen_deg=0.0):
    """DeviceOrientation angles (degrees) -> camera world quaternion in Blender's Z-up world."""
    q = qaxis((0, 0, 1), math.radians(alpha_deg))
    q = qmul(q, qaxis((1, 0, 0), math.radians(beta_deg)))
    q = qmul(q, qaxis((0, 1, 0), math.radians(gamma_deg)))
    q = qmul(q, qaxis((0, 0, 1), -math.radians(screen_deg)))
    return qnormalize(q)

def yaw_of(q):
    """Heading (radians, CCW about +Z, 0 = looking along +Y) of a camera quaternion."""
    f = qrotate(q, (0, 0, -1))
    if math.hypot(f[0], f[1]) > 0.2:
        return math.atan2(-f[0], f[1])
    u = qrotate(q, (0, 1, 0))
    if f[2] < 0:                      # looking down: camera 'up' points forward
        return math.atan2(-u[0], u[1])
    return math.atan2(u[0], -u[1])    # looking up: camera 'up' points backward

# ---------------------------------------------------------------- rig
def shape(v):
    """Clamp, dead-zone and gentle expo curve for stick / slider values."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    v = max(-1.0, min(1.0, v))
    a = abs(v)
    if a < 0.06:
        return 0.0
    a = (a - 0.06) / 0.94
    return math.copysign(0.4 * a + 0.6 * a * a, v)


class Settings:
    move_speed = 3.0      # metres / second at full stick
    look_speed = 90.0     # degrees / second at full stick
    zoom_speed = 1.1      # e-folds / second at full zoom
    smoothing = 0.3       # 0 = raw .. 1 = very soft
    lens_min = 8.0
    lens_max = 400.0


class Rig:
    """Turns phone input into a camera pose, without ever jumping on (re)connect or recenter."""

    def __init__(self, settings=None):
        self.s = settings or Settings()
        self.pos = [0.0, 0.0, 0.0]
        self.q = (1.0, 0.0, 0.0, 0.0)
        self.target_q = self.q
        self.lens = 50.0
        self.vel = [0.0, 0.0, 0.0]
        self.yaw_off = 0.0
        self.needs_align = True
        self.easing = False
        self.mode = 'analog'

    def adopt(self, pos, q, lens):
        """Take over the camera's current pose (no jump)."""
        self.pos = [float(c) for c in pos]
        self.q = self.target_q = qnormalize(q)
        self.lens = float(lens)
        self.vel = [0.0, 0.0, 0.0]
        self.needs_align = True

    def realign(self):
        self.needs_align = True
        self.target_q = self.q

    def step(self, dt, mode, ax, phone_q):
        s = self.s
        if mode != self.mode:
            self.mode = mode
            self.realign()
        mx, my, mz, lx, ly, zm = (shape(ax.get(k, 0.0)) for k in ('mx', 'my', 'mz', 'lx', 'ly', 'zoom'))
        if mode == 'gyro':
            mx = my = mz = lx = ly = 0.0
        use_phone = mode in ('gyro', 'hybrid') and phone_q is not None

        if use_phone:
            if self.needs_align:
                self.yaw_off = yaw_of(self.q) - yaw_of(phone_q)
                self.needs_align = False
                self.easing = True
            self.yaw_off -= math.radians(lx * s.look_speed) * dt
            self.target_q = qnormalize(qmul(qaxis((0, 0, 1), self.yaw_off), phone_q))
        elif mode == 'analog' or mode == 'hybrid':
            yaw = -math.radians(lx * s.look_speed) * dt
            pitch = math.radians(ly * s.look_speed) * dt
            t = qmul(qaxis((0, 0, 1), yaw), self.target_q)
            cand = qmul(t, qaxis((1, 0, 0), pitch))
            if abs(qrotate(cand, (0, 0, -1))[2]) < 0.999:    # don't flip over the poles
                t = cand
            self.target_q = qnormalize(t)
            self.needs_align = False

        tau = s.smoothing * 0.25
        ang = 2.0 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(self.q, self.target_q)))))
        if self.easing:                      # re-engaging: glide to the phone's pose, never snap
            tau = max(tau, 0.12)
            if ang < math.radians(0.5):
                self.easing = False
        a = 1.0 if tau <= 0 else 1.0 - math.exp(-dt / tau)
        if self.easing and ang > 1e-6:
            a = min(a, math.radians(150.0) * dt / ang)     # max 150 deg/s while easing
        self.q = qslerp(self.q, self.target_q, a)

        sp = s.move_speed
        local = (mx * sp, 0.0, -my * sp)
        w = qrotate(self.q, local)
        tv = (w[0], w[1], w[2] + mz * sp)
        av = 1.0 - math.exp(-dt / (0.04 + s.smoothing * 0.3))
        self.vel = [v + (t - v) * av for v, t in zip(self.vel, tv)]
        self.pos = [p + v * dt for p, v in zip(self.pos, self.vel)]

        if zm:
            self.lens = max(s.lens_min, min(s.lens_max, self.lens * math.exp(zm * s.zoom_speed * dt)))

    def set_lens(self, mm):
        self.lens = max(self.s.lens_min, min(self.s.lens_max, float(mm)))

    def stop(self):
        self.vel = [0.0, 0.0, 0.0]
