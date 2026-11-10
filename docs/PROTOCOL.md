# Protocol (v1)
One WebSocket at `/ws` (wss on LAN, ws on 127.0.0.1:port+1). JSON text frames.

Phone -> Blender
- `{"t":"pair","code":"123456789","name":"Pixel"}` first message; code is single use, valid 10 min, 5 failures = 30 s lock.
- `{"t":"resume","session":"..."}` reconnect with the session issued at pairing.
- `{"t":"in","mode":"gyro|hybrid|analog","mx","my","mz","lx","ly","zoom":-1..1,"o":[alpha,beta,gamma,screenAngle],"fr":0|1}` ~60 Hz. Only the latest is kept (no queue, no lag build-up). Ignored if older than 0.6 s.
- `{"t":"cmd","c":"rec|play|key|recenter|lens|camera|speed|undo_take|rec_stop","v":...}` (allowlist; anything else is rejected)
- `{"t":"ping","ts":..}`
Blender -> Phone: `paired`, `state`, `toast`, `pong`, `error`.

Safety: Origin check (no cross-site hijack), command allowlist, validated/clamped numbers, no code execution, input cleared and camera held when the phone disconnects.
Orientation: W3C DeviceOrientation (Z-up Earth frame) equals Blender's world; camera axes equal device axes, see `core.py` header.

QR payload: `https://<ip>:<port>/#t=<9-digit code>&fp=<SHA-256 of the TLS certificate>`. The native app pins `fp`, so only YOUR PC can accept the connection.
