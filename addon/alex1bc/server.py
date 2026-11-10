"""Alex1BC network layer - standard library only, no bpy.

* HTTPS (LAN) + plain HTTP on 127.0.0.1 (USB / adb reverse) serve the phone controller.
* One WebSocket endpoint (/ws) carries pairing, controls and state. Phones cannot send UDP from a
  browser; TCP with TCP_NODELAY on a LAN is fine because the hub only ever keeps the LATEST input
  (stale motion is overwritten, never queued) and the sender drops frames when the socket backs up.
* Nothing here touches Blender data. Blender's main thread polls the Hub.
"""
import asyncio, base64, collections, hashlib, hmac, json, math, os, queue, secrets, socket, ssl, struct, threading, time
from . import certgen
from .core import device_quaternion, qaxis, qmul, qnormalize

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 16384
CMD_ALLOW = {'recenter', 'lens', 'play', 'rec', 'key', 'camera', 'speed', 'undo_take', 'rec_stop'}
MODES = ('gyro', 'analog', 'hybrid')
CTYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
          '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml',
          '.webmanifest': 'application/manifest+json'}


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))     # no packet is sent; picks the outgoing interface
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def _num(v, lo, hi, default=0.0):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return max(lo, min(hi, float(v)))


class Hub:
    """Thread-safe mailbox between the network thread and Blender's main thread."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cmds = queue.Queue(maxsize=256)
        self.events = collections.deque(maxlen=64)       # toasts for the phone
        self.state = {}                                   # published by Blender, read by server
        self.status = 'stopped'                           # stopped|starting|waiting|connected|error
        self.error = ''
        self.device = ''
        self.rtt_ms = 0.0
        self.code = None
        self.code_expiry = 0.0
        self.session = None
        self.fails = 0
        self.locked_until = 0.0
        self.input = None
        self.input_time = 0.0
        self.conn = None
        self.urls = {}
        self.fingerprint = ''                             # SHA-256 of the TLS certificate (goes in the QR for pinning)
        self.generation = 0                               # bumps on any status change (UI refresh)

    # --- pairing
    def new_code(self):
        with self.lock:
            self.code = f"{secrets.randbelow(10**9):09d}"
            self.code_expiry = time.monotonic() + 600
            self.fails = 0
            self.generation += 1
            return self.code

    def pair(self, code, name):
        with self.lock:
            now = time.monotonic()
            if now < self.locked_until:
                return None, 'locked'
            ok = (self.code and now < self.code_expiry and isinstance(code, str)
                  and hmac.compare_digest(code.replace(' ', '').encode(), self.code.encode()))
            if not ok:
                self.fails += 1
                if self.fails >= 5:
                    self.locked_until, self.fails = now + 30, 0
                return None, 'bad_code'
            self.code = None                              # single use
            self.session = secrets.token_urlsafe(24)
            self.device = str(name)[:40]
            return self.session, None

    def resume(self, session):
        with self.lock:
            if self.session and isinstance(session, str) and hmac.compare_digest(session.encode(), self.session.encode()):
                return True
            self.fails += 1
            if self.fails >= 5:
                self.locked_until, self.fails = time.monotonic() + 30, 0
            return False

    def forget(self):
        with self.lock:
            self.session = None
            self.device = ''
            self.generation += 1

    # --- input (latest wins)
    def set_input(self, msg):
        mode = msg.get('mode')
        d = {'mode': mode if mode in MODES else 'analog',
             'mx': _num(msg.get('mx'), -1, 1), 'my': _num(msg.get('my'), -1, 1), 'mz': _num(msg.get('mz'), -1, 1),
             'lx': _num(msg.get('lx'), -1, 1), 'ly': _num(msg.get('ly'), -1, 1), 'zoom': _num(msg.get('zoom'), -1, 1),
             'freeze': bool(msg.get('fr')), 'q': None}
        qv = msg.get('q')                       # native app: device->earth quaternion [w,x,y,z] + screen angle 's'
        if isinstance(qv, list) and len(qv) == 4:
            vals = [_num(x, -2, 2, None) for x in qv]
            if None not in vals and sum(v * v for v in vals) > 0.25:
                sa = _num(msg.get('s'), -720, 720, 0.0)
                d['q'] = qnormalize(qmul(qnormalize(tuple(vals)), qaxis((0, 0, 1), -math.radians(sa))))
        o = msg.get('o')
        if d['q'] is None and isinstance(o, list) and len(o) == 4:
            a, b, g, s = (_num(x, -720, 720, None) for x in o)
            if None not in (a, b, g, s):
                d['q'] = device_quaternion(a, b, g, s)
        with self.lock:
            self.input = d
            self.input_time = time.monotonic()

    def get_input(self):
        with self.lock:
            if self.input is None:
                return None, 1e9
            return dict(self.input), time.monotonic() - self.input_time

    def clear_input(self):
        with self.lock:
            self.input = None

    def push_cmd(self, cmd):
        try:
            self.cmds.put_nowait(cmd)
            return True
        except queue.Full:
            return False

    def toast(self, msg, level='info'):
        self.events.append({'t': 'toast', 'msg': str(msg)[:160], 'level': level})

    def set_status(self, status, error=''):
        with self.lock:
            self.status, self.error = status, error
            self.generation += 1


# ---------------------------------------------------------------- websocket plumbing
class WSError(Exception):
    pass


async def read_message(reader, writer, lock):
    """Return (opcode, bytes). Handles fragmentation, ping and close."""
    buf, first = b'', None
    while True:
        b0, b1 = await reader.readexactly(2)
        fin, op, masked, ln = b0 & 0x80, b0 & 0x0f, b1 & 0x80, b1 & 0x7f
        if not masked:
            raise WSError('unmasked client frame')
        if ln == 126:
            ln = struct.unpack('>H', await reader.readexactly(2))[0]
        elif ln == 127:
            ln = struct.unpack('>Q', await reader.readexactly(8))[0]
        if ln > MAX_FRAME:
            raise WSError('frame too large')
        mask = await reader.readexactly(4)
        data = await reader.readexactly(ln)
        if ln:
            data = (int.from_bytes(data, 'big') ^ int.from_bytes((mask * (ln // 4 + 1))[:ln], 'big')).to_bytes(ln, 'big')
        if op == 9:
            await send_frame(writer, lock, 10, data); continue
        if op == 10:
            continue
        if op == 8:
            return 8, data
        if op in (1, 2):
            first = op
        buf += data
        if len(buf) > MAX_FRAME:
            raise WSError('message too large')
        if fin:
            return first or 1, buf


async def send_frame(writer, lock, op, payload):
    n = len(payload)
    head = bytes([0x80 | op]) + (bytes([n]) if n < 126 else b'\x7e' + struct.pack('>H', n) if n < 65536 else b'\x7f' + struct.pack('>Q', n))
    async with lock:
        writer.write(head + payload)
        await writer.drain()


class Conn:
    def __init__(self, writer):
        self.writer, self.lock, self.closed = writer, asyncio.Lock(), False

    async def send(self, obj):
        await send_frame(self.writer, self.lock, 1, json.dumps(obj, separators=(',', ':')).encode())

    async def close(self):
        if not self.closed:
            self.closed = True
            try:
                await send_frame(self.writer, self.lock, 8, struct.pack('>H', 1000))
            except Exception:
                pass
            self.writer.close()


# ---------------------------------------------------------------- server
class AlexServer:
    def __init__(self, hub, web_dir, cert_dir, port=47800, host=None):
        self.hub, self.web_dir, self.cert_dir, self.port, self.host = hub, web_dir, cert_dir, port, host
        self.loop = None
        self.thread = None
        self.files = {}

    def start(self):
        self.hub.set_status('starting')
        self.thread = threading.Thread(target=self._run, name='alex1bc-net', daemon=True)
        self.thread.start()

    def stop(self):
        loop = self.loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if self.thread:
            self.thread.join(timeout=3)
        self.hub.set_status('stopped')
        self.hub.clear_input()
        self.hub.session = None

    def kick(self):
        conn = self.hub.conn
        if conn and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(conn.close(), self.loop)

    # --- thread body
    def _run(self):
        loop = self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        servers = []
        try:
            for name in os.listdir(self.web_dir):
                ext = os.path.splitext(name)[1]
                if ext in CTYPES:
                    with open(os.path.join(self.web_dir, name), 'rb') as f:
                        self.files['/' + name] = (f.read(), CTYPES[ext])
            self.files['/'] = self.files['/index.html']
            cert, key = certgen.ensure_cert(self.cert_dir)
            self.hub.fingerprint = certgen.fingerprint(cert)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(cert, key)
            ip = self.host or lan_ip()
            urls = {}
            if ip:
                servers.append(loop.run_until_complete(asyncio.start_server(
                    lambda r, w: self._http(r, w, True), ip, self.port, ssl=ctx)))
                urls['lan'] = f"https://{ip}:{self.port}"
            servers.append(loop.run_until_complete(asyncio.start_server(
                lambda r, w: self._http(r, w, False), '127.0.0.1', self.port + 1)))
            urls['usb'] = f"http://localhost:{self.port + 1}"
            self.hub.urls = urls
            self.hub.set_status('waiting')
            loop.run_forever()
        except OSError as e:
            self.hub.set_status('error', f"Could not open port {self.port}: {e.strerror or e}")
        except Exception as e:                                   # never die silently
            self.hub.set_status('error', f"{type(e).__name__}: {e}")
        finally:
            for s in servers:
                s.close()
            try:
                loop.run_until_complete(asyncio.sleep(0.05))
            finally:
                loop.close()

    # --- HTTP
    async def _http(self, reader, writer, secure):
        try:
            sock = writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            raw = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 10)
            lines = raw.decode('latin-1').split('\r\n')
            method, path, _ = lines[0].split(' ', 2)
            h = {}
            for ln in lines[1:]:
                if ':' in ln:
                    k, v = ln.split(':', 1)
                    h[k.strip().lower()] = v.strip()
            path = path.split('?')[0]
            if method != 'GET':
                return await self._reply(writer, 405, b'method not allowed')
            if path == '/ws' and h.get('upgrade', '').lower() == 'websocket':
                return await self._ws(reader, writer, h)
            item = self.files.get(path)
            if not item:
                return await self._reply(writer, 404, b'not found')
            await self._reply(writer, 200, item[0], item[1])
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, asyncio.LimitOverrunError,
                ConnectionError, ssl.SSLError, ValueError, UnicodeError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _reply(self, writer, code, body, ctype='text/plain'):
        msg = {200: 'OK', 404: 'Not Found', 405: 'Method Not Allowed', 400: 'Bad Request', 403: 'Forbidden'}[code]
        writer.write((f"HTTP/1.1 {code} {msg}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n"
                      "Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n").encode() + body)
        await writer.drain()

    # --- WebSocket
    async def _ws(self, reader, writer, h):
        origin, host = h.get('origin'), h.get('host', '')
        if origin and origin.split('://', 1)[-1] != host:       # block cross-site WebSocket hijacking
            return await self._reply(writer, 403, b'bad origin')
        key = h.get('sec-websocket-key')
        if not key:
            return await self._reply(writer, 400, b'bad request')
        acc = base64.b64encode(hashlib.sha1(key.encode() + GUID).digest()).decode()
        writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      f"Sec-WebSocket-Accept: {acc}\r\n\r\n").encode())
        await writer.drain()
        conn = Conn(writer)
        hub = self.hub
        pusher = None
        authed = False

        async def recv(timeout):
            op, data = await asyncio.wait_for(read_message(reader, writer, conn.lock), timeout)
            if op == 8:
                raise ConnectionError('closed')
            return json.loads(data.decode())

        try:
            msg = await recv(10)
            if not isinstance(msg, dict):
                raise WSError('bad message')
            if msg.get('t') == 'pair':
                session, err = hub.pair(msg.get('code'), msg.get('name') or 'Phone')
                if err:
                    await conn.send({'t': 'error', 'code': err,
                                     'msg': 'Too many wrong codes. Wait 30 seconds.' if err == 'locked'
                                     else 'That code is wrong or expired. Press "New code" in Blender.'})
                    return
            elif msg.get('t') == 'resume':
                if not hub.resume(msg.get('session')):
                    await conn.send({'t': 'error', 'code': 'bad_session', 'msg': 'Session expired. Scan the QR code again.'})
                    return
                session = msg['session']
            else:
                raise WSError('expected pair/resume')
            if hub.conn is not None:                             # newest device wins
                await hub.conn.close()
            hub.conn, authed = conn, True
            hub.clear_input()
            hub.set_status('connected')
            hub.push_cmd({'c': '_connected'})
            await conn.send({'t': 'paired', 'session': session, 'device': hub.device})
            pusher = asyncio.create_task(self._push(conn))
            while True:
                msg = await recv(5)                              # phone must talk at least every 5 s
                t = msg.get('t') if isinstance(msg, dict) else None
                if t == 'in':
                    hub.set_input(msg)
                elif t == 'cmd':
                    c = msg.get('c')
                    if c not in CMD_ALLOW:
                        await conn.send({'t': 'toast', 'msg': 'Unknown command', 'level': 'error'})
                    elif not hub.push_cmd({'c': c, 'v': msg.get('v')}):
                        await conn.send({'t': 'toast', 'msg': 'Blender is busy', 'level': 'error'})
                elif t == 'ping':
                    await conn.send({'t': 'pong', 'ts': msg.get('ts')})
                    r = msg.get('rtt')
                    if isinstance(r, (int, float)) and math.isfinite(r):
                        hub.rtt_ms = max(0.0, min(9999.0, float(r)))
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, ConnectionError, WSError,
                ValueError, UnicodeError, ssl.SSLError, OSError):
            pass
        finally:
            if pusher:
                pusher.cancel()
            if authed and hub.conn is conn:
                hub.conn = None
                hub.clear_input()
                hub.push_cmd({'c': '_disconnected'})
                hub.set_status('waiting')
            await conn.close()

    async def _push(self, conn):
        last, last_t = None, 0.0
        while True:
            await asyncio.sleep(0.05)
            while self.hub.events:
                await conn.send(self.hub.events.popleft())
            st = self.hub.state
            now = time.monotonic()
            if st and (st != last or now - last_t > 1.0) and now - last_t > 0.09:
                await conn.send({'t': 'state', **st})
                last, last_t = dict(st), now
