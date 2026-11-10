# Status (v0.1.0)

Blender tested for real (bpy module): **4.2.0, 5.0.1, 5.1.1, 5.2.3 LTS** - all integration checks pass on all four.

## Verified by automated tests (run in this repo)
- Camera math / rig: 16 unit tests (orientation mapping incl. landscape, no-jump alignment, analog fly, limits, bad input).
- Network: real TLS + WebSocket client: pairing, single-use code, rate limit, session resume, origin check, garbage input, command allowlist, path traversal.
- Certificate generator: validated with OpenSSL (`verify`, `rsa -check`), loads in `ssl`.
- Phone page: loaded headless (jsdom) against the real server: pairs, hides code from URL, drags sticks, sends sensor data, buttons -> commands, HUD renders state.
- Inside REAL Blender (bpy module) 4.2.0 and 5.0.1, `tests/bpy_integration.py`: server start, QR file, pairing, gyro yaw/pitch, analog move/zoom/rise, freeze, keyframe, record -> editable dense keyframes, take library, existing animation preserved, undo take, disconnect holds camera, resume without jump, manual camera move adopted, camera switch, clean stop.
- Extension ZIP passes Blender's own `extension validate/build` and installs + enables as a real extension in 4.2.

## Android app (native)
- `net/Protocol.kt` compiled and run with kotlinc; the 1,413-line project parses cleanly. **Not compiled against the Android SDK, never run on a phone** (no SDK available here). See `android/README.md`.
- Server side of the native protocol (quaternion input, cert fingerprint in QR) is unit-tested.

## Website
- Real three.js r128 + GSAP/ScrollTrigger executed in a DOM emulator with a stubbed GPU renderer: no runtime errors, 164 frames across both 3D scenes, downloads logic works. Visual look is unverified (no GPU here).
- APK button stays disabled until `downloads/Alex1BC-Android.apk` exists.

## NOT verified (needs your hardware)
- A real phone: real sensor feel, landscape behaviour on your device, certificate prompt flow, Wi-Fi latency, `adb reverse` USB route.
- Windows firewall behaviour. Interactive Blender UI look (panels were registered but not viewed).
- Website 3D visuals (WebGL cannot be rendered here; JS syntax checked only). Test in your browser.

## Not implemented
- Native Android APK / ARCore walking-position tracking (browser gives rotation only). Live viewfinder. Cinematic presets. Take JSON export. iOS motion on Safari untested.
