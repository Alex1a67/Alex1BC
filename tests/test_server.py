import asyncio, json, os, ssl, sys, tempfile, time, unittest, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addon"))
import websockets
from alex1bc.server import Hub, AlexServer

WEB = os.path.join(os.path.dirname(__file__), "..", "addon", "alex1bc", "web")
os.makedirs(WEB, exist_ok=True)
if not os.path.exists(os.path.join(WEB, "index.html")):
    open(os.path.join(WEB, "index.html"), "w").write("<html>ok</html>")

class S(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = Hub(); cls.port = 47900
        cls.srv = AlexServer(cls.hub, WEB, tempfile.mkdtemp(), cls.port, host="127.0.0.1")
        cls.srv.start()
        for _ in range(100):
            if cls.hub.status in ('waiting', 'error'): break
            time.sleep(0.1)
        assert cls.hub.status == 'waiting', cls.hub.error
        cls.ctx = ssl.create_default_context(); cls.ctx.check_hostname = False; cls.ctx.verify_mode = ssl.CERT_NONE
    @classmethod
    def tearDownClass(cls): cls.srv.stop()

    def run_async(self, coro): return asyncio.run(coro)
    def url(self): return f"wss://127.0.0.1:{self.port}/ws"

    def test_serves_https_and_loopback_http(self):
        r = urllib.request.urlopen(f"https://127.0.0.1:{self.port}/", context=self.ctx); self.assertEqual(r.status, 200)
        self.assertEqual(r.headers['X-Content-Type-Options'], 'nosniff')
        r = urllib.request.urlopen(f"http://127.0.0.1:{self.port+1}/"); self.assertEqual(r.status, 200)
        with self.assertRaises(urllib.error.HTTPError) as e: urllib.request.urlopen(f"http://127.0.0.1:{self.port+1}/../../etc/passwd")
        self.assertEqual(e.exception.code, 404)

    def test_full_pairing_input_and_reconnect(self):
        code = self.hub.new_code()
        async def go():
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send(json.dumps({'t': 'pair', 'code': code, 'name': 'Pixel'}))
                m = json.loads(await ws.recv()); self.assertEqual(m['t'], 'paired'); sess = m['session']
                self.assertEqual(self.hub.status, 'connected')
                await ws.send(json.dumps({'t': 'in', 'mode': 'hybrid', 'my': 1, 'o': [0, 90, 0, 0]}))
                await ws.send(json.dumps({'t': 'cmd', 'c': 'play'}))
                await ws.send(json.dumps({'t': 'cmd', 'c': 'os.system'}))
                self.hub.state = {'lens': 35}
                got = set()
                for _ in range(6):
                    try: got.add(json.loads(await asyncio.wait_for(ws.recv(), 1))['t'])
                    except asyncio.TimeoutError: break
                self.assertIn('state', got); self.assertIn('toast', got)
                inp, age = self.hub.get_input(); self.assertEqual(inp['my'], 1); self.assertIsNotNone(inp['q'])
            self.assertIsNone(self.hub.get_input()[0])        # input cleared on disconnect (safety)
            cmds = []
            while not self.hub.cmds.empty(): cmds.append(self.hub.cmds.get()['c'])
            self.assertIn('play', cmds); self.assertNotIn('os.system', cmds); self.assertIn('_connected', cmds)
            await asyncio.sleep(0.3); self.assertEqual(self.hub.status, 'waiting')   # disconnect noticed
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:           # resume with session
                await ws.send(json.dumps({'t': 'resume', 'session': sess}))
                self.assertEqual(json.loads(await ws.recv())['t'], 'paired')
        self.run_async(go())

    def test_code_is_single_use_and_rate_limited(self):
        code = self.hub.new_code()
        async def go():
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send(json.dumps({'t': 'pair', 'code': code, 'name': 'A'})); await ws.recv()
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send(json.dumps({'t': 'pair', 'code': code, 'name': 'B'}))
                self.assertEqual(json.loads(await ws.recv())['code'], 'bad_code')
            self.hub.new_code()
            for _ in range(5):
                async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                    await ws.send(json.dumps({'t': 'pair', 'code': '000000000'})); await ws.recv()
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send(json.dumps({'t': 'pair', 'code': self.hub.code}))      # even the right code is refused
                self.assertEqual(json.loads(await ws.recv())['code'], 'locked')
            self.hub.locked_until = 0
        self.run_async(go())

    def test_cross_site_origin_rejected_and_garbage_survives(self):
        async def go():
            with self.assertRaises(Exception):
                async with websockets.connect(self.url(), ssl=self.ctx, origin="https://evil.example") as ws: await ws.recv()
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send("not json{")
                with self.assertRaises(websockets.ConnectionClosed): await asyncio.wait_for(ws.recv(), 2)
            async with websockets.connect(self.url(), ssl=self.ctx) as ws:
                await ws.send(json.dumps({'t': 'in'}))                               # unauthenticated input ignored
                with self.assertRaises(websockets.ConnectionClosed): await asyncio.wait_for(ws.recv(), 2)
        self.run_async(go())

    def test_input_validation(self):
        h = Hub(); h.set_input({'mode': 'evil', 'mx': float('nan'), 'my': 99, 'o': [1, 2, 'x', 0], 'zoom': 'a'})
        d, _ = h.get_input(); self.assertEqual((d['mode'], d['mx'], d['my'], d['q'], d['zoom']), ('analog', 0.0, 1.0, None, 0.0))

    def test_native_quaternion_input_matches_browser_angles(self):
        from alex1bc.core import device_quaternion, qrotate
        h = Hub(); q = device_quaternion(30, 85, 3, 0)
        h.set_input({'q': list(q), 's': 90}); a, _ = h.get_input()
        h.set_input({'o': [30, 85, 3, 90]}); b, _ = h.get_input()
        self.assertTrue(all(abs(x - y) < 1e-9 for x, y in zip(a['q'], b['q'])))
        h.set_input({'q': [0, 0, 0, 0]}); self.assertIsNone(h.get_input()[0]['q'])
        h.set_input({'q': [float('nan'), 0, 0, 1]}); self.assertIsNone(h.get_input()[0]['q'])

    def test_fingerprint_exposed(self):
        self.assertEqual(len(self.hub.fingerprint), 64)

if __name__ == "__main__":
    unittest.main()
