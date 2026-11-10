"""Loads the real phone page (headless DOM) against the real server and checks what the server receives."""
import json, os, shutil, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addon"))
from alex1bc.server import Hub, AlexServer
WEB = os.path.join(os.path.dirname(__file__), "..", "addon", "alex1bc", "web")
NODE_DIR = os.environ.get("JSDOM_DIR", "/tmp/jt")

@unittest.skipUnless(shutil.which("node") and os.path.isdir(os.path.join(NODE_DIR, "node_modules", "jsdom")), "needs node + jsdom (npm i jsdom)")
class PhonePage(unittest.TestCase):
    def test_page_pairs_and_sends_controls(self):
        hub = Hub(); srv = AlexServer(hub, WEB, tempfile.mkdtemp(), 47960, host="127.0.0.1"); srv.start()
        for _ in range(100):
            if hub.status in ('waiting', 'error'): break
            time.sleep(0.1)
        self.assertEqual(hub.status, 'waiting', hub.error)
        code = hub.new_code()
        hub.state = {'cam': 'Camera', 'cams': ['Camera', 'B'], 'lens': 35.0, 'frame': 12, 'rec': 'rec', 'rec_s': 65.0, 'playing': True}
        p = subprocess.Popen(["node", os.path.join(NODE_DIR, "phone.js"), f"http://127.0.0.1:47961/#t={code}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=NODE_DIR)
        seen = {}
        t_end = time.time() + 6
        while time.time() < t_end and p.poll() is None:
            inp, age = hub.get_input()
            if inp and inp['my'] > 0.9 and inp['q'] and inp['mz'] > 0.9: seen = inp
            try: c = hub.cmds.get_nowait(); seen.setdefault('cmds', []).append((c['c'], c.get('v')))
            except Exception: pass
            time.sleep(0.01)
        out, err = p.communicate(timeout=10); srv.stop()
        self.assertEqual(p.returncode, 0, err)
        r = json.loads(out.strip().splitlines()[-1])
        self.assertTrue(r['gateHiddenAfter'] and not r['appHidden'], r)
        self.assertEqual(r['hashAfter'], '', "pairing code must be scrubbed from the address bar")
        self.assertEqual(r['session'], 'stored')
        self.assertEqual((r['camName'], r['lens'], r['recLbl']), ('Camera', '35', '01:05'))
        self.assertIn('on', r['recClass'].split()); self.assertIn('ok', r['dotOk'])
        self.assertEqual(seen.get('mode'), 'hybrid'); self.assertGreater(seen['my'], 0.9); self.assertGreater(seen['lx'], 0.9); self.assertGreater(seen['mz'], 0.9)
        self.assertIsNotNone(seen['q'])
        cmds = [c for c, _ in seen['cmds']]
        for need in ('rec', 'key', 'recenter', 'lens'): self.assertIn(need, cmds)
        self.assertIn(('lens', 35), seen['cmds'])
if __name__ == "__main__": unittest.main()
