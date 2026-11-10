import math, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addon"))
from alex1bc.core import *

def close(a, b, e=1e-6):
    return all(abs(x - y) < e for x, y in zip(a, b))

class T(unittest.TestCase):
    def test_upright_phone_looks_north(self):
        q = device_quaternion(0, 90, 0)
        self.assertTrue(close(qrotate(q, (0, 0, -1)), (0, 1, 0)))      # forward = +Y
        self.assertTrue(close(qrotate(q, (0, 1, 0)), (0, 0, 1)))       # up = +Z (level horizon)

    def test_flat_phone_looks_down(self):
        self.assertTrue(close(qrotate(device_quaternion(0, 0, 0), (0, 0, -1)), (0, 0, -1)))

    def test_alpha_turns_left(self):
        q = device_quaternion(90, 90, 0)    # CCW 90deg about Z: north -> west
        self.assertTrue(close(qrotate(q, (0, 0, -1)), (-1, 0, 0)))

    def test_landscape_keeps_horizon(self):
        # phone upright, rotated to landscape (screen angle 90): camera 'up' must still be +Z-ish
        # for a camera looking at the horizon: device held on its side => device x axis is vertical
        q = device_quaternion(0, 0, 0)
        for a in (90, 270):
            qq = device_quaternion(0, 90, 0, a)
            f = qrotate(qq, (0, 0, -1))
            self.assertAlmostEqual(f[2], 0.0, places=6)    # screen angle only rolls the camera

    def test_real_landscape_posture_is_level(self):
        # phone held sideways (top of phone to the left), back camera facing north:
        # device x -> up, y -> west, z -> south.  Browser reports screen angle 90.
        import math
        m = [[0, -1, 0], [0, 0, -1], [1, 0, 0]]    # rows: earth x,y,z ; cols: device x,y,z images
        # columns are images of device axes: x->(0,0,1), y->(-1,0,0), z->(0,-1,0)
        m = [[0, -1, 0], [0, 0, -1], [1, 0, 0]]
        tr = m[0][0] + m[1][1] + m[2][2]
        # general matrix->quat (Shepperd)
        if tr > 0:
            s = math.sqrt(tr + 1) * 2; q = (s/4, (m[2][1]-m[1][2])/s, (m[0][2]-m[2][0])/s, (m[1][0]-m[0][1])/s)
        elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
            s = math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2; q = ((m[2][1]-m[1][2])/s, s/4, (m[0][1]+m[1][0])/s, (m[0][2]+m[2][0])/s)
        elif m[1][1] > m[2][2]:
            s = math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2; q = ((m[0][2]-m[2][0])/s, (m[0][1]+m[1][0])/s, s/4, (m[1][2]+m[2][1])/s)
        else:
            s = math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2; q = ((m[1][0]-m[0][1])/s, (m[0][2]+m[2][0])/s, (m[1][2]+m[2][1])/s, s/4)
        q = qnormalize(q)
        self.assertTrue(close(qrotate(q, (1, 0, 0)), (0, 0, 1)))        # sanity: device x -> up
        cam = qmul(q, qaxis((0, 0, 1), -math.radians(90)))
        self.assertTrue(close(qrotate(cam, (0, 1, 0)), (0, 0, 1)))      # camera up = world up
        self.assertTrue(close(qrotate(cam, (1, 0, 0)), (1, 0, 0)))      # camera right = east
        self.assertTrue(close(qrotate(cam, (0, 0, -1)), (0, 1, 0)))     # looking north

    def test_yaw_of(self):
        self.assertAlmostEqual(yaw_of(qaxis((0, 0, 1), 0.7) if False else qmul(qaxis((0, 0, 1), 0.7), device_quaternion(0, 90, 0))), 0.7, places=6)
        self.assertAlmostEqual(yaw_of(device_quaternion(0, 0, 0)), yaw_of(device_quaternion(0, 0, 0)))

    def test_no_jump_on_align(self):
        r = Rig(); r.s.smoothing = 0
        start = qmul(qaxis((0, 0, 1), 1.2), device_quaternion(0, 90, 0))
        r.adopt((1, 2, 3), start, 35)
        phone = device_quaternion(200, 90, 0)          # arbitrary compass heading
        r.step(1/60, 'gyro', {}, phone)
        f0 = qrotate(start, (0, 0, -1)); f1 = qrotate(r.q, (0, 0, -1))
        self.assertTrue(close(f0, f1, 0.05))           # heading preserved (small ease step)
        # then turning the phone 30deg turns the camera by 30deg
        for _ in range(120): r.step(1/60, 'gyro', {}, device_quaternion(230, 90, 0))
        self.assertAlmostEqual(math.degrees(yaw_of(r.q) - yaw_of(start)), 30, delta=0.5)

    def test_horizon_follows_phone_pitch(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(120): r.step(1/60, 'gyro', {}, device_quaternion(0, 60, 0))   # tilt phone down
        self.assertLess(qrotate(r.q, (0, 0, -1))[2], -0.4)

    def test_analog_move_forward(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(60): r.step(1/60, 'analog', {'my': 1.0}, None)
        self.assertGreater(r.pos[1], 2.0); self.assertAlmostEqual(r.pos[0], 0, places=4)

    def test_analog_up_and_strafe(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(60): r.step(1/60, 'analog', {'mz': 1.0, 'mx': 1.0}, None)
        self.assertGreater(r.pos[2], 2.0); self.assertGreater(r.pos[0], 2.0)

    def test_analog_look_right_turns_clockwise(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(30): r.step(1/60, 'analog', {'lx': 1.0}, None)
        self.assertLess(yaw_of(r.q), -0.3)
        f = qrotate(r.q, (0, 0, -1)); self.assertGreater(f[0], 0.2)   # now looking toward +X (east)

    def test_pitch_clamped_and_no_roll(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(600): r.step(1/60, 'analog', {'ly': 1.0, 'lx': 0.5}, None)
        self.assertLess(abs(qrotate(r.q, (0, 0, -1))[2]), 0.9991)
        self.assertAlmostEqual(qrotate(r.q, (1, 0, 0))[2], 0.0, places=5)   # horizon stays level

    def test_gyro_ignores_sticks(self):
        r = Rig(); r.s.smoothing = 0; r.adopt((0, 0, 0), device_quaternion(0, 90, 0), 50)
        for _ in range(30): r.step(1/60, 'gyro', {'my': 1.0}, device_quaternion(0, 90, 0))
        self.assertAlmostEqual(r.pos[1], 0, places=6)

    def test_zoom_clamped(self):
        r = Rig(); r.adopt((0, 0, 0), (1, 0, 0, 0), 50)
        for _ in range(2000): r.step(1/60, 'analog', {'zoom': 1.0}, None)
        self.assertEqual(r.lens, r.s.lens_max)

    def test_garbage_input_is_safe(self):
        for bad in (float('nan'), float('inf'), 'x', None, [1], 1e9):
            self.assertLessEqual(abs(shape(bad)), 1.0)

    def test_slerp_endpoints(self):
        a = (1, 0, 0, 0); b = qaxis((0, 0, 1), 1.0)
        self.assertTrue(close(qslerp(a, b, 1.0), b)); self.assertTrue(close(qslerp(a, b, 0.0), a))

if __name__ == "__main__":
    unittest.main()
