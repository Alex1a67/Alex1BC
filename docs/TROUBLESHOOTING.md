# Troubleshooting
- **Page does not open / "can't reach Blender"**: same Wi-Fi as the PC (not guest Wi-Fi, no "client isolation"); allow Blender in Windows Defender Firewall for *Private* networks; if you use a VPN or several adapters set Advanced > Bind address to your Wi-Fi IP.
- **Certificate warning**: expected. The certificate is created on your PC the first time you press Start and never leaves it. Choose Advanced > Continue.
- **Gyro does nothing on the Wi-Fi link**: some browsers only allow motion sensors on trusted HTTPS. Use the USB route (`http://localhost:47801`), or on Android Chrome enable `chrome://flags/#unsafely-treat-insecure-origin-as-secure` for your PC link. On iPhone tap Allow when asked for Motion access.
- **Wrong code / locked**: five wrong codes lock pairing for 30 s. Press **New code** in Blender.
- **Camera jumps when you hold the phone differently**: press HOME. The camera keeps heading and glides to the phone's tilt.
