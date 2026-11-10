'use strict';
(() => {
const $ = s => document.querySelector(s);
const S = { ws: null, session: null, pending: null, mode: 'hybrid', ax: { mx: 0, my: 0, mz: 0, lx: 0, ly: 0, zoom: 0 },
            o: null, oriAt: 0, frozen: false, st: {}, open: false, rtt: 0, tries: 0, started: false, lastSend: 0, wake: null };
try { S.session = localStorage.getItem('a1bc_session'); S.mode = localStorage.getItem('a1bc_mode') || 'hybrid'; } catch (e) {}
const buzz = ms => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} };
const send = o => { if (S.ws && S.ws.readyState === 1) S.ws.send(JSON.stringify(o)); };
const cmd = (c, v) => send({ t: 'cmd', c, v });
const deviceName = () => { const m = /Android[^;)]*;\s*([^;)]+)/.exec(navigator.userAgent); return m ? m[1].trim().slice(0, 30) : (/iPhone|iPad/.test(navigator.userAgent) ? 'iPhone' : 'Phone'); };

function toast(msg, level) {
  const el = document.createElement('div'); el.className = 'toast ' + (level || ''); el.textContent = msg;
  $('#toasts').appendChild(el); setTimeout(() => { el.style.opacity = 0; setTimeout(() => el.remove(), 300); }, 2600);
}

// ---------------------------------------------------------------- touch controls
function stick(el, cb) {
  const knob = el.querySelector('.knob'); let id = null;
  const R = () => el.clientWidth / 2 * 0.62;
  function set(x, y) { knob.style.transform = `translate(${x * R()}px,${y * R()}px)`; cb(x, -y); }
  function move(e) {
    const r = el.getBoundingClientRect(); let x = (e.clientX - r.left - r.width / 2) / R(), y = (e.clientY - r.top - r.height / 2) / R();
    const m = Math.hypot(x, y); if (m > 1) { x /= m; y /= m; } set(x, y);
  }
  el.addEventListener('pointerdown', e => { if (id !== null) return; id = e.pointerId; el.setPointerCapture && el.setPointerCapture(id); el.classList.add('on'); buzz(8); move(e); });
  el.addEventListener('pointermove', e => { if (e.pointerId === id) move(e); });
  const end = e => { if (e.pointerId !== id) return; id = null; el.classList.remove('on'); set(0, 0); };
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(n => el.addEventListener(n, end));
}
function vslider(el, cb) {
  const knob = el.querySelector('.knob'); let id = null;
  const H = () => (el.clientHeight - knob.offsetHeight) / 2;
  function set(v) { knob.style.transform = `translateY(${-v * H()}px)`; cb(v); }
  function move(e) { const r = el.getBoundingClientRect(); set(Math.max(-1, Math.min(1, -((e.clientY - r.top - r.height / 2) / (H() || 1))))); }
  el.addEventListener('pointerdown', e => { if (id !== null) return; id = e.pointerId; el.setPointerCapture && el.setPointerCapture(id); el.classList.add('on'); buzz(8); move(e); });
  el.addEventListener('pointermove', e => { if (e.pointerId === id) move(e); });
  const end = e => { if (e.pointerId !== id) return; id = null; el.classList.remove('on'); set(0); };
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(n => el.addEventListener(n, end));
}
stick($('#stickMove'), (x, y) => { S.ax.mx = x; S.ax.my = y; });
stick($('#stickLook'), (x, y) => { S.ax.lx = x; S.ax.ly = y; });
vslider($('#rise'), v => { S.ax.mz = v; });
vslider($('#zoom'), v => { S.ax.zoom = v; });

// ---------------------------------------------------------------- buttons
function setMode(m, quiet) {
  S.mode = m; try { localStorage.setItem('a1bc_mode', m); } catch (e) {}
  const order = ['gyro', 'hybrid', 'analog'];
  $('#modes .thumb').style.transform = `translateX(${order.indexOf(m) * 100}%)`;
  document.querySelectorAll('#modes button').forEach(b => b.classList.toggle('on', b.dataset.m === m));
  if (!quiet) buzz(12);
  if (m !== 'analog') setTimeout(() => { if (S.mode !== 'analog' && performance.now() - S.oriAt > 1500) toast('No motion sensor data - use ANALOG, or check browser sensor permission', 'error'); }, 1800);
}
document.querySelectorAll('#modes button').forEach(b => b.addEventListener('click', () => setMode(b.dataset.m)));
$('#rec').addEventListener('click', () => { buzz(30); cmd('rec'); });
$('#play').addEventListener('click', () => { buzz(15); cmd('play'); });
$('#key').addEventListener('click', () => { buzz([10, 30, 10]); cmd('key'); });
$('#home').addEventListener('click', () => { buzz(20); cmd('recenter'); });
$('#hold').addEventListener('click', () => { S.frozen = !S.frozen; $('#hold').classList.toggle('on', S.frozen); $('#hold').setAttribute('aria-pressed', S.frozen); buzz(S.frozen ? 40 : 15); if (!S.frozen) cmd('recenter'); });
const LENSES = [18, 24, 35, 50, 85, 135];
LENSES.forEach(mm => { const b = document.createElement('button'); b.textContent = mm; b.dataset.mm = mm; b.addEventListener('click', () => { buzz(10); cmd('lens', mm); }); $('#lenses').appendChild(b); });
$('#camBtn').addEventListener('click', () => {
  const list = $('#sheetList'); list.innerHTML = '';
  (S.st.cams || []).forEach(n => { const b = document.createElement('button'); b.textContent = n; if (n === S.st.cam) b.className = 'on'; b.addEventListener('click', () => { cmd('camera', n); $('#sheet').hidden = true; }); list.appendChild(b); });
  if (!list.children.length) list.textContent = 'No cameras in the scene. Add one in Blender.';
  $('#sheet').hidden = false;
});
$('#sheet').addEventListener('click', e => { if (e.target.id === 'sheet') $('#sheet').hidden = true; });

// ---------------------------------------------------------------- HUD
function render(st) {
  S.st = st;
  $('#camName').textContent = st.cam || 'No camera';
  $('#lensRead').textContent = Math.round(st.lens);
  $('#frameRead').textContent = st.frame;
  document.querySelectorAll('#lenses button').forEach(b => b.classList.toggle('on', Math.abs(+b.dataset.mm - st.lens) < 1));
  const rec = $('#rec'); rec.classList.toggle('on', st.rec === 'rec'); rec.classList.toggle('pause', st.rec === 'pause');
  const s = Math.floor(st.rec_s || 0);
  $('#recLbl').textContent = st.rec === 'off' ? 'REC' : `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  const playing = st.playing; $('#play').classList.toggle('on', playing);
  $('#playIcon').setAttribute('d', playing ? 'M7 5h4v14H7zM13 5h4v14h-4z' : 'M8 5v14l11-7z');
  $('#playLbl').textContent = st.rec !== 'off' ? (playing ? 'PAUSE' : 'RESUME') : (playing ? 'PAUSE' : 'PLAY');
}
function link(ok) { $('#dot').classList.toggle('ok', ok); if (!ok) $('#ping').textContent = '--'; }

// ---------------------------------------------------------------- sensors
function onOri(e) { if (e.alpha == null || e.beta == null) return; S.o = [e.alpha, e.beta, e.gamma || 0]; S.oriAt = performance.now(); }
async function startSensors() {
  try {
    if (window.DeviceOrientationEvent && typeof DeviceOrientationEvent.requestPermission === 'function') {
      const r = await DeviceOrientationEvent.requestPermission(); if (r !== 'granted') toast('Motion access denied - only ANALOG will work', 'error');
    }
  } catch (e) { toast('Could not enable motion sensors', 'error'); }
  window.addEventListener('deviceorientation', onOri);
  try { await document.documentElement.requestFullscreen(); } catch (e) {}
  try { await screen.orientation.lock('landscape'); } catch (e) {}
  try { S.wake = await navigator.wakeLock.request('screen'); } catch (e) {}
}
document.addEventListener('visibilitychange', async () => { if (!document.hidden && S.started) { try { S.wake = await navigator.wakeLock.request('screen'); } catch (e) {} } });

// ---------------------------------------------------------------- connection
function showGate(msg, needCode) {
  $('#gate').hidden = false; $('#app').hidden = true; $('#gateMsg').textContent = msg;
  $('#code').hidden = !needCode; $('#go').textContent = needCode ? 'Connect' : 'Start';
}
function connect() {
  if (S.ws && S.ws.readyState <= 1) return;
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
  let ws; try { ws = new WebSocket(url); } catch (e) { return retry(); }
  S.ws = ws;
  ws.onopen = () => {
    S.open = true;
    if (S.pending) send({ t: 'pair', code: S.pending, name: deviceName() });
    else if (S.session) send({ t: 'resume', session: S.session });
    else { ws.close(); showGate('Type the pairing code shown in Blender.', true); }
  };
  ws.onmessage = ev => {
    let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
    if (m.t === 'paired') {
      S.session = m.session; S.pending = null; S.tries = 0; try { localStorage.setItem('a1bc_session', S.session); } catch (e) {}
      $('#gate').hidden = true; $('#app').hidden = false; $('#banner').hidden = true; link(true); setMode(S.mode, true); toast('Connected to Blender', 'ok'); buzz([20, 40, 20]);
    } else if (m.t === 'state') render(m);
    else if (m.t === 'toast') { toast(m.msg, m.level); if (m.level === 'error') buzz(60); }
    else if (m.t === 'pong') { S.rtt = performance.now() - m.ts; $('#ping').textContent = Math.round(S.rtt) + ' ms'; }
    else if (m.t === 'error') {
      S.pending = null; if (m.code === 'bad_session') { S.session = null; try { localStorage.removeItem('a1bc_session'); } catch (e) {} }
      showGate(m.msg, true); S.tries = 99;
    }
  };
  ws.onclose = () => {
    S.open = false; link(false);
    if (S.tries >= 99) return;
    if (!$('#app').hidden) { $('#banner').hidden = false; $('#banner').textContent = 'Reconnecting to Blender...'; }
    retry();
  };
  ws.onerror = () => {};
}
function retry() {
  S.tries++;
  if (S.tries === 4) {
    $('#gate').hidden = false; $('#gateHint').hidden = false;
    $('#gateHint').textContent = "Can't reach Blender. Check: same Wi-Fi (not a guest network), Blender's Alex1BC is running, and Windows Firewall allows Blender on private networks. Or use the USB cable route.";
  }
  setTimeout(connect, Math.min(2500, 400 * S.tries));
}
$('#go').addEventListener('click', async () => {
  const typed = $('#code').value.replace(/\D/g, '');
  if (!$('#code').hidden) { if (typed.length < 9) { toast('Enter the 9-digit code from Blender', 'error'); return; } S.pending = typed; S.tries = 0; }
  if (!S.started) { S.started = true; await startSensors(); }
  S.tries = S.tries >= 99 ? 0 : S.tries; connect();
});

// ---------------------------------------------------------------- send loop (latest state only; never queues)
setInterval(() => {
  if (!S.open || !S.ws || S.ws.bufferedAmount > 4096 || $('#app').hidden) return;
  const a = S.ax, now = performance.now();
  const idle = !a.mx && !a.my && !a.mz && !a.lx && !a.ly && !a.zoom && S.mode === 'analog';
  if (idle && now - S.lastSend < 200) return;
  const msg = { t: 'in', mode: S.mode, mx: a.mx, my: a.my, mz: a.mz, lx: a.lx, ly: a.ly, zoom: a.zoom, fr: S.frozen ? 1 : 0 };
  if (S.mode !== 'analog' && S.o && now - S.oriAt < 500) { const sa = ((screen.orientation && screen.orientation.angle) || window.orientation || 0); msg.o = [S.o[0], S.o[1], S.o[2], ((sa % 360) + 360) % 360]; }
  send(msg); S.lastSend = now;
}, 16);
setInterval(() => { if (S.open) send({ t: 'ping', ts: performance.now(), rtt: Math.round(S.rtt) }); }, 1000);

// ---------------------------------------------------------------- boot
setMode(S.mode, true);
const h = /[#&]t=(\d+)/.exec(location.hash);
if (h) { S.pending = h[1]; history.replaceState(null, '', location.pathname); }
if (S.pending) showGate('Ready to connect to Blender.', false);
else if (S.session) showGate('Reconnect to Blender.', false);
else showGate('Scan the QR code in Blender, or type the code shown there.', true);
window.__a1bc = S;
})();
