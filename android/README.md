# Alex1BC for Android (Kotlin + Jetpack Compose)

1. Install **Android Studio** (Ladybug or newer). Open this folder (`android/`). Let Gradle sync
   (it downloads Gradle 8.9 and the libraries; if it asks about the Gradle wrapper, accept).
2. Plug in your phone (USB debugging on) and press **Run**, or **Build > Build APK(s)** for `app-debug.apk`.
3. Run `python tools/build.py` in the repo root: it copies the APK to `website/downloads/Alex1BC-Android.apk`
   and the website's Android button switches on by itself.

## Screens
Splash -> Onboarding (3 parallax pages) -> Connect (scroll-animated cards: scan QR, reconnect, USB code) ->
QR Scanner (CameraX + ML Kit) -> Controller (2 sticks, rise + zoom sliders, GYRO/HYBRID/ANALOG, REC, PLAY, KEY, HOME, HOLD, lens presets, camera picker, connection info).
Transitions between screens are animated (slide + fade + scale).

## How it connects
Scan Blender's QR: `https://<ip>:<port>/#t=<code>&fp=<cert SHA-256>`. The app opens a WebSocket and **pins the
certificate fingerprint from the QR**, so only your own PC is accepted. USB route: `adb reverse` + `localhost` (plain, loopback only).
Orientation comes from the game rotation vector sensor, sent as a quaternion (see `docs/PROTOCOL.md`).

## Honest status
This project was written without access to the Android SDK, so it has **not been compiled or run on a phone yet**.
What *was* verified: the protocol code compiles and runs (`net/Protocol.kt`, unit tests in `src/test`), all 1,400 lines parse
cleanly with the Kotlin compiler, and the server side it talks to is tested against real Blender. Expect to fix a few
small compile errors on first sync (versions, imports); they will be one-liners.
Not included yet: ARCore walking-position tracking (planned; the protocol is ready for a position field).
