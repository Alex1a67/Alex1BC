# Alex1BC — Your Camera. Your Movement.

> 🌐 **Live Web Introduction, 3D Simulator & Single-File Downloads:**  
> **👉 [https://alex1a67.github.io/Alex1BC/](https://alex1a67.github.io/Alex1BC/) 👈**

---

### 💡 Important Note for Users & 3D Artists
**You do NOT need to download or clone this entire repository!**

Simply open the live website link above:
* 💻 **Download the Blender Add-on (.zip)** (for your PC / Mac / Linux)
* 📱 **Download the Android App (.apk)** (for your phone)
* 🎮 **Interactive 3D Camera Simulator** (test camera controls right in your browser)
* 📖 **Step-by-Step Visual Tutorial** (complete guide for Wi-Fi and USB setup)

---

## ⚡ Quick Start Tutorial

### Step 1: Install in Blender (Computer)
1. Download **`Alex1BC-Blender-Addon-0.1.0.zip`** from the website (do not unzip it).
2. Open Blender (**4.2, 5.0, 5.1, or 5.2**).
3. Go to **Edit > Preferences > Get Extensions**.
4. Click the arrow menu icon `⌄` in the top right corner and select **Install from Disk...**
5. Select the downloaded `.zip` file. Alex1BC will be installed and enabled automatically.
6. In your 3D Viewport, press **N** to open the sidebar, click the **Alex1BC** tab, and click **Start Alex1BC**. A pairing QR code will appear.

### Step 2: Install App on Your Phone
1. Download **`Alex1BC-Android.apk`** from the website to your Android device (or run `adb install Alex1BC-Android.apk`).
2. Tap the APK to install (allow unknown sources if prompted).
3. Open **Alex1BC** and grant camera permissions for QR scanning.
   > *Zero-Install Alternative:* You can also simply scan the Blender QR code using your regular phone camera app to open the built-in mobile web controller in Chrome/Safari without installing anything!

### Step 3: Pair Instantly (1 Second)
1. Point your phone camera at the QR code displayed in Blender's 3D Viewport.
2. Connection established! Telemetry and artificial horizon gyroscope activate immediately.

### Step 4: Shoot & Animate
* **Gyro Mode**: Tilt, pan, and roll your phone like a physical camera rig.
* **Hybrid Mode**: Aim with your phone tilt while using the left thumbstick to dolly/crane, and right stick for fine yaw trimming.
* **Analog Mode**: Classical dual-stick flight controls.
* **REC Button**: One-tap recording. Every take is automatically saved as a separate Blender Action (`A1BC_Take_001`), keeping your existing scene animation completely safe.
* **KEY Button**: Drops an instant keyframe for location, rotation, and focal length at the current playhead frame.

---

## 🔌 Connection Methods

### A. Wi-Fi Wireless Mode (Free Movement)
Connect your PC and phone to the same Wi-Fi router. The add-on broadcasts over local encrypted WebSockets. Zero cables required.

### B. USB Cable Mode (Ultra-Low Sub-ms Latency)
Plug your phone in via USB cable, enable USB Debugging, and click **Enable USB route** in the Blender sidebar panel (or run `adb reverse tcp:47801 tcp:47801`). Provides jitter-free, studio-grade sub-millisecond response.

---

## 📁 Repository Structure (For Developers)

| Part | Path | Description |
|---|---|---|
| **Blender Add-on** | `addon/alex1bc/` | Python server, QR pairing, camera rig math, take manager |
| **Android Native App** | `android/` | Kotlin + Jetpack Compose app source (Android Studio) |
| **Web Introduction Site** | `website/` | Three.js 3D interactive showcase, simulator, and downloads |
| **Automated Tests** | `tests/` | Unit tests & headless Blender 5.1 integration suite |
| **Build Tools** | `tools/build.py` | Packages add-on ZIP and APK into distributions |

---

## 🛠️ Developer Verification
```bash
# Run unit & server tests (no Blender required)
python -m unittest tests.test_core tests.test_server

# Run real Blender integration test inside Blender 5.1
blender -b --python tests/bpy_integration.py
```
