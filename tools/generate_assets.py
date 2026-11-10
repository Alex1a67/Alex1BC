"""Generate high-resolution visual previews, screenshots, and GIF demonstration for Alex1BC.
Used in README.md and the website to showcase the features clearly.
"""
import math, os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Helper fonts
def get_font(size, bold=False):
    # Try common Windows fonts, fallback to default
    candidates = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\consola.ttf"
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_title = get_font(26, bold=True)
font_head = get_font(20, bold=True)
font_sub = get_font(15, bold=True)
font_body = get_font(14, bold=False)
font_sm = get_font(12, bold=False)
font_mono = get_font(13, bold=True)

# ==============================================================================
# 1. BLENDER UI SCREENSHOT (Blender 5.1 with Alex1BC N-panel and 3D Viewport)
# ==============================================================================
def generate_blender_ui():
    W, H = 1280, 720
    im = Image.new("RGB", (W, H), "#181818")
    d = ImageDraw.Draw(im)

    # Top Menu Bar
    d.rectangle([0, 0, W, 32], fill="#242424")
    d.text((16, 7), "Blender 5.1  •  Alex1BC_Studio_Rig.blend", font=font_sub, fill="#d0d0d0")
    menus = ["File", "Edit", "Render", "Window", "Help"]
    mx = 360
    for m in menus:
        d.text((mx, 7), m, font=font_body, fill="#999999")
        mx += 50
    
    # Workspace tabs
    tabs = ["Layout", "Modeling", "Sculpting", "Shading", "Animation", "Compositing"]
    tx = 650
    for t in tabs:
        active = (t == "Animation")
        tw = int(d.textlength(t, font=font_body)) + 24
        if active:
            d.rectangle([tx, 4, tx + tw, 28], fill="#3e3e3e", outline="#505050")
            d.text((tx + 12, 7), t, font=font_body, fill="#00d2ff")
        else:
            d.text((tx + 12, 7), t, font=font_body, fill="#888888")
        tx += tw + 4

    # Main 3D Viewport Area
    vp_w = 900
    d.rectangle([0, 32, vp_w, H - 140], fill="#11151c")

    # Viewport 3D Grid lines
    for gy in range(80, H - 140, 40):
        d.line([0, gy, vp_w, gy], fill="#19202c", width=1)
    for gx in range(40, vp_w, 40):
        d.line([gx, 32, gx, H - 140], fill="#19202c", width=1)

    # 3D Origin Axes
    cx, cy = 420, 310
    d.line([cx - 280, cy + 90, cx + 280, cy - 90], fill="#b33636", width=2) # X red axis
    d.line([cx - 180, cy - 120, cx + 180, cy + 120], fill="#3b823b", width=2) # Y green axis
    d.line([cx, cy - 200, cx, cy + 160], fill="#3b6eb3", width=2) # Z blue axis

    # 3D Cinema Camera Frustum in Viewport
    cam_x, cam_y = 260, 220
    d.rectangle([cam_x - 30, cam_y - 20, cam_x + 30, cam_y + 20], fill="#2b3b55", outline="#00d2ff", width=2)
    # Frustum pyramid cone
    target_x, target_y = 520, 290
    d.line([cam_x + 30, cam_y - 20, target_x + 70, target_y - 80], fill="#00d2ff", width=1)
    d.line([cam_x + 30, cam_y + 20, target_x + 70, target_y + 80], fill="#00d2ff", width=1)
    d.line([cam_x - 30, cam_y - 20, target_x - 70, target_y - 80], fill="#00d2ff", width=1)
    d.line([cam_x - 30, cam_y + 20, target_x - 70, target_y + 80], fill="#00d2ff", width=1)
    # Framing rectangle
    d.rectangle([target_x - 70, target_y - 80, target_x + 70, target_y + 80], outline="#00d2ff", width=2)
    d.text((cam_x - 40, cam_y - 42), "Camera: Alex1BC Cam", font=font_mono, fill="#00d2ff")

    # Viewport overlay labels
    d.text((20, 48), "User Perspective (Active Cine Camera)", font=font_body, fill="#7e94b2")
    d.text((20, 68), "Focal Length: 50.0mm  •  Full Frame (36x24mm)", font=font_sm, fill="#5a6d85")

    # Right Sidebar (N-panel) - ALEX1BC TAB
    d.rectangle([vp_w, 32, W, H - 140], fill="#222730")
    d.line([vp_w, 32, vp_w, H - 140], fill="#384355", width=2)

    # N-panel header
    d.rectangle([vp_w, 32, W, 72], fill="#181e28")
    d.text((vp_w + 18, 42), "ALEX1BC // CAMERA RIG", font=font_head, fill="#00d2ff")
    d.line([vp_w, 72, W, 72], fill="#384355", width=1)

    # Server Status Card
    sy = 86
    d.rounded_rectangle([vp_w + 14, sy, W - 14, sy + 58], radius=8, fill="#131922", outline="#2575fc", width=1)
    d.ellipse([vp_w + 26, sy + 18, vp_w + 38, sy + 30], fill="#00ff9d")
    d.text((vp_w + 46, sy + 12), "SERVER ACTIVE  •  PORT 47800", font=font_sub, fill="#f0f5fc")
    d.text((vp_w + 46, sy + 32), "Local IP: 192.168.1.104  |  TLS Secured", font=font_sm, fill="#7e94b2")

    # QR Code Pairing Box
    qy = 158
    d.rounded_rectangle([vp_w + 14, qy, W - 14, qy + 195], radius=10, fill="#0e131c", outline="#00d2ff", width=2)
    d.text((vp_w + 22, qy + 12), "SCAN WITH PHONE APP", font=font_sub, fill="#00d2ff")

    # Mock QR Code matrix
    qr_x, qr_y, qr_s = vp_w + 35, qy + 40, 110
    d.rectangle([qr_x, qr_y, qr_x + qr_s, qr_y + qr_s], fill="#ffffff")
    d.rectangle([qr_x + 8, qr_y + 8, qr_x + 38, qr_y + 38], fill="#000000")
    d.rectangle([qr_x + 14, qr_y + 14, qr_x + 32, qr_y + 32], fill="#ffffff")
    d.rectangle([qr_x + 72, qr_y + 8, qr_x + 102, qr_y + 38], fill="#000000")
    d.rectangle([qr_x + 78, qr_y + 14, qr_x + 96, qr_y + 32], fill="#ffffff")
    d.rectangle([qr_x + 8, qr_y + 72, qr_x + 38, qr_y + 102], fill="#000000")
    d.rectangle([qr_x + 14, qr_y + 78, qr_x + 32, qr_y + 96], fill="#ffffff")
    # Random pattern blocks
    for bx in range(4, 10):
        for by in range(4, 10):
            if (bx + by) % 3 == 0 or (bx * by) % 5 == 0:
                d.rectangle([qr_x + bx * 10, qr_y + by * 10, qr_x + (bx + 1) * 10, qr_y + (by + 1) * 10], fill="#000000")

    # Pairing PIN readout
    d.text((vp_w + 165, qy + 55), "PAIRING PIN:", font=font_sm, fill="#7e94b2")
    d.text((vp_w + 165, qy + 75), "482 910", font=font_title, fill="#00d2ff")
    d.text((vp_w + 165, qy + 115), "Status: Linked", font=font_sm, fill="#00ff9d")
    d.text((vp_w + 165, qy + 135), "Latency: 0.6 ms", font=font_sm, fill="#f0f5fc")

    # Mode Selector
    my = 370
    d.text((vp_w + 18, my), "CONTROL MODE", font=font_sm, fill="#7e94b2")
    modes_w = (W - vp_w - 38) // 3
    for i, (m_name, m_act) in enumerate([("GYRO", True), ("HYBRID", False), ("ANALOG", False)]):
        mx_pos = vp_w + 14 + i * (modes_w + 5)
        bg = "#2575fc" if m_act else "#151b26"
        tc = "#ffffff" if m_act else "#8ba2be"
        d.rounded_rectangle([mx_pos, my + 18, mx_pos + modes_w, my + 50], radius=6, fill=bg, outline="#384355")
        d.text((mx_pos + (modes_w - len(m_name)*8)//2, my + 26), m_name, font=font_mono, fill=tc)

    # Takes & Recording Section
    ry = 440
    d.text((vp_w + 18, ry), "TAKE MANAGER (NON-DESTRUCTIVE)", font=font_sm, fill="#7e94b2")
    d.rounded_rectangle([vp_w + 14, ry + 18, W - 14, ry + 64], radius=8, fill="#ff334b")
    d.ellipse([vp_w + 35, ry + 32, vp_w + 49, ry + 46], fill="#ffffff")
    d.text((vp_w + 60, ry + 30), "● RECORD TAKE [A1BC_Take_001]", font=font_sub, fill="#ffffff")

    # Quick Action Buttons
    by = 520
    btn_w = (W - vp_w - 36) // 3
    btns = ["RECENTER", "KEYFRAME", "UNDO TAKE"]
    for i, b_text in enumerate(btns):
        bx_pos = vp_w + 14 + i * (btn_w + 4)
        d.rounded_rectangle([bx_pos, by, bx_pos + btn_w, by + 36], radius=6, fill="#182232", outline="#30415a")
        d.text((bx_pos + 6, by + 10), b_text, font=get_font(10, bold=True), fill="#00d2ff")

    # Bottom Timeline Editor
    d.rectangle([0, H - 140, W, H], fill="#1e222a")
    d.line([0, H - 140, W, H - 140], fill="#303b4d", width=2)
    d.text((16, H - 130), "Timeline  •  Action: A1BC_Take_001  •  Frame: 54 / 250", font=font_sub, fill="#00d2ff")

    # Timeline ticks & keyframes
    for f in range(0, 250, 10):
        fx = 120 + f * 4
        if fx < W - 20:
            d.line([fx, H - 95, fx, H - 75], fill="#3d4c63", width=1)
            if f % 20 == 0:
                d.text((fx - 8, H - 112), str(f), font=font_sm, fill="#6d82a1")

    # Recorded keyframe markers (dense baked F-curves)
    for kf in range(1, 54):
        kfx = 120 + kf * 4
        d.line([kfx, H - 70, kfx, H - 20], fill="#ea7600", width=2)
    # Current playhead scrubber
    cur_x = 120 + 54 * 4
    d.line([cur_x, H - 120, cur_x, H], fill="#00ff9d", width=2)
    d.polygon([(cur_x - 6, H - 120), (cur_x + 6, H - 120), (cur_x, H - 110)], fill="#00ff9d")

    im.save(os.path.join(ASSETS_DIR, "blender-ui-screenshot.png"))
    print("Generated assets/blender-ui-screenshot.png")

# ==============================================================================
# 2. ANDROID CONTROLLER APP SCREENSHOT
# ==============================================================================
def generate_android_app_ui():
    W, H = 640, 1280
    im = Image.new("RGB", (W, H), "#06090e")
    d = ImageDraw.Draw(im)

    # Phone Bezel Outline
    d.rounded_rectangle([12, 12, W - 12, H - 12], radius=44, outline="#2b3b55", width=4)
    # Speaker Notch
    d.rounded_rectangle([W//2 - 60, 24, W//2 + 60, 36], radius=6, fill="#131b29")

    # App Header Bar
    d.rectangle([20, 56, W - 20, 126], fill="#0e1522", outline="#2575fc", width=1)
    d.text((40, 78), "Alex1BC", font=font_title, fill="#00d2ff")
    d.text((180, 84), "Cam: Alex1BC Camera ⌄", font=font_body, fill="#f0f5fc")
    d.text((440, 84), "● 0.4ms (Wi-Fi)", font=font_mono, fill="#00ff9d")

    # Horizon Gyro Indicator
    gy_cy = 380
    d.ellipse([W//2 - 160, gy_cy - 160, W//2 + 160, gy_cy + 160], fill="#090e18", outline="#2575fc", width=2)
    # Horizon line (tilted)
    d.line([W//2 - 140, gy_cy - 30, W//2 + 140, gy_cy + 30], fill="#00d2ff", width=4)
    # Center reticle
    d.ellipse([W//2 - 10, gy_cy - 10, W//2 + 10, gy_cy + 10], fill="#ea7600")

    # Gyro telemetry readouts
    d.text((W//2 - 140, 580), "PITCH: +12.4°     YAW: -45.2°     ROLL: +2.1°", font=font_mono, fill="#f0f5fc")

    # Mode Selector
    d.rounded_rectangle([60, 630, W - 60, 685], radius=14, fill="#101724", outline="#2b3b55")
    d.rounded_rectangle([64, 634, 230, 681], radius=10, fill="#2575fc")
    d.text((105, 646), "GYRO", font=font_head, fill="#ffffff")
    d.text((275, 646), "HYBRID", font=font_head, fill="#7e94b2")
    d.text((450, 646), "ANALOG", font=font_head, fill="#7e94b2")

    # Dual Joysticks
    # Left Joystick (MOVE)
    d.ellipse([50, 740, 250, 940], fill="#0e1522", outline="#2575fc", width=2)
    d.ellipse([120, 810, 180, 870], fill="#00d2ff") # Knob
    d.text((120, 955), "MOVE / DOLLY", font=font_mono, fill="#7e94b2")

    # Right Joystick (PAN/TILT)
    d.ellipse([390, 740, 590, 940], fill="#0e1522", outline="#2575fc", width=2)
    d.ellipse([460, 810, 520, 870], fill="#ea7600") # Knob
    d.text((465, 955), "PAN / TILT", font=font_mono, fill="#7e94b2")

    # Center REC Button
    rec_cy = 840
    d.ellipse([W//2 - 55, rec_cy - 55, W//2 + 55, rec_cy + 55], outline="#ff334b", width=3)
    d.ellipse([W//2 - 42, rec_cy - 42, W//2 + 42, rec_cy + 42], fill="#ff334b")
    d.text((W//2 - 24, rec_cy - 10), "REC", font=font_head, fill="#ffffff")
    d.text((W//2 - 28, rec_cy + 70), "00:14:28", font=font_mono, fill="#ff334b")

    # Lens Presets Rack
    ly = 1040
    d.text((60, ly), "CINEMA PRIME FOCAL PRESETS", font=font_sm, fill="#7e94b2")
    lens_w = (W - 120 - 30) // 6
    for i, mm in enumerate(["18", "24", "35", "50", "85", "135"]):
        lx = 60 + i * (lens_w + 6)
        active = (mm == "50")
        bg = "#2575fc" if active else "#101724"
        d.rounded_rectangle([lx, ly + 20, lx + lens_w, ly + 64], radius=8, fill=bg, outline="#2b3b55")
        d.text((lx + 10, ly + 32), f"{mm}mm", font=font_sm, fill="#ffffff" if active else "#8ba2be")

    # Bottom Transport Buttons
    ty = 1140
    d.rounded_rectangle([60, ty, 230, ty + 56], radius=12, fill="#182232", outline="#2b3b55")
    d.text((105, ty + 16), "HOME (RESET)", font=font_sub, fill="#00d2ff")

    d.rounded_rectangle([250, ty, 420, ty + 56], radius=12, fill="#182232", outline="#2b3b55")
    d.text((290, ty + 16), "KEYFRAME", font=font_sub, fill="#00d2ff")

    d.rounded_rectangle([440, ty, 580, ty + 56], radius=12, fill="#182232", outline="#2b3b55")
    d.text((465, ty + 16), "HOLD FREEZE", font=font_sub, fill="#ea7600")

    im.save(os.path.join(ASSETS_DIR, "android-app-screenshot.png"))
    print("Generated assets/android-app-screenshot.png")

# ==============================================================================
# 3. WORKFLOW DIAGRAM (Step-by-step visual infographic)
# ==============================================================================
def generate_workflow_diagram():
    W, H = 1200, 480
    im = Image.new("RGB", (W, H), "#070b12")
    d = ImageDraw.Draw(im)

    # Title Banner
    d.text((40, 30), "ALEX1BC // PRODUCTION WORKFLOW OVERVIEW", font=font_title, fill="#00d2ff")
    d.text((40, 68), "Physical Camera Control Workflow - From Phone Movement to Editable Blender Keyframes", font=font_body, fill="#7e94b2")

    steps = [
        ("01", "Start in Blender", "Open N-panel in 3D Viewport\nClick 'Start Alex1BC'\nPairing QR code displays", "#2575fc"),
        ("02", "Instant 1s Pairing", "Scan QR with Alex1BC app\nor regular phone camera\nLocal TLS WebSocket links", "#00d2ff"),
        ("03", "Physical Tracking", "Phone gyro aims camera\nDual thumbsticks fly & dolly\nReal-time 60 FPS response", "#ea7600"),
        ("04", "Bake Takes & Actions", "Tap REC to capture motion\nDense editable F-Curves\nUndo take restores safely", "#00ff9d")
    ]

    card_w = 260
    card_h = 320
    start_x = 40
    gap = (W - 80 - card_w * 4) // 3

    for i, (num, title, desc, col) in enumerate(steps):
        x = start_x + i * (card_w + gap)
        y = 110
        # Card body
        d.rounded_rectangle([x, y, x + card_w, y + card_h], radius=16, fill="#0e1522", outline=col, width=2)
        # Step Number Badge
        d.rounded_rectangle([x + 18, y + 18, x + 68, y + 52], radius=8, fill=col)
        d.text((x + 24, y + 22), num, font=font_head, fill="#06090e")
        # Step Title
        d.text((x + 18, y + 74), title, font=font_head, fill="#f0f5fc")
        # Description
        d.text((x + 18, y + 115), desc, font=font_body, fill="#8ba2be", spacing=6)

        # Arrow connector between cards
        if i < 3:
            arrow_x = x + card_w + gap // 2
            arrow_y = y + card_h // 2
            d.line([arrow_x - 12, arrow_y, arrow_x + 12, arrow_y], fill="#30415a", width=3)
            d.polygon([(arrow_x + 14, arrow_y), (arrow_x + 6, arrow_y - 6), (arrow_x + 6, arrow_y + 6)], fill="#30415a")

    im.save(os.path.join(ASSETS_DIR, "alex1bc-workflow-diagram.png"))
    print("Generated assets/alex1bc-workflow-diagram.png")

# ==============================================================================
# 4. ANIMATED DEMONSTRATION GIF (Camera Tracking & REC Take)
# ==============================================================================
def generate_demo_gif():
    W, H = 600, 360
    frames = []
    num_frames = 24

    for i in range(num_frames):
        im = Image.new("RGB", (W, H), "#080d17")
        d = ImageDraw.Draw(im)

        t = i / num_frames
        angle = math.sin(t * math.pi * 2) * 0.45

        # Background grid
        for gy in range(0, H, 30):
            d.line([0, gy, W, gy], fill="#0f1624", width=1)
        for gx in range(0, W, 30):
            d.line([gx, 0, gx, H], fill="#0f1624", width=1)

        # Phone on left
        px, py = 140, 180 + math.sin(t * math.pi * 2) * 8
        d.rounded_rectangle([px - 40, py - 80, px + 40, py + 80], radius=12, fill="#121a28", outline="#00d2ff", width=2)
        # Phone screen horizon
        hx1 = px - 30
        hy1 = py - angle * 50
        hx2 = px + 30
        hy2 = py + angle * 50
        d.line([hx1, hy1, hx2, hy2], fill="#00d2ff", width=3)
        d.ellipse([px - 4, py - 4, px + 4, py + 4], fill="#ea7600")
        d.text((px - 28, py + 92), "PHONE (GYRO)", font=font_mono, fill="#00d2ff")

        # Camera Rig on right
        cx, cy = 440, 180 + math.sin(t * math.pi * 2 + 1) * 8
        d.rectangle([cx - 50, cy - 35, cx + 50, cy + 35], fill="#1c2638", outline="#2575fc", width=2)
        # Lens
        d.rectangle([cx - 75, cy - 20, cx - 50, cy + 20], fill="#0e1522", outline="#00d2ff")
        # Handle & battery
        d.rectangle([cx - 20, cy - 50, cx + 20, cy - 35], fill="#2b3b55")
        d.rectangle([cx + 50, cy - 25, cx + 68, cy + 25], fill="#0e1522")
        d.text((cx - 40, cy + 50), "BLENDER CAMERA", font=font_mono, fill="#2575fc")

        # Tally light
        if i % 4 < 2:
            d.ellipse([cx - 45, cy - 25, cx - 35, cy - 15], fill="#ff334b")

        # Connecting Wireless Telemetry Beam
        beam_x1, beam_y1 = px + 40, py - 30
        beam_x2, beam_y2 = cx - 75, cy
        ctrl_x, ctrl_y = (beam_x1 + beam_x2) / 2, (beam_y1 + beam_y2) / 2 - 40

        for bi in range(25):
            u = (bi / 25.0 + t * 2) % 1.0
            ku = 1.0 - u
            bx = ku * ku * beam_x1 + 2 * ku * u * ctrl_x + u * u * beam_x2
            by = ku * ku * beam_y1 + 2 * ku * u * ctrl_y + u * u * beam_y2
            d.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill="#00d2ff")

        # Header HUD
        d.text((20, 18), "ALEX1BC LIVE TRACKING DEMO", font=font_sub, fill="#f0f5fc")
        d.text((440, 18), "● REC [00:14]", font=font_mono, fill="#ff334b")
        d.text((20, H - 32), f"ROTATION: PITCH: {(angle * 30):.1f}°  |  FPS: 60.0  |  LATENCY: 0.5ms", font=font_sm, fill="#7e94b2")

        frames.append(im)

    frames[0].save(
        os.path.join(ASSETS_DIR, "alex1bc-demo.gif"),
        save_all=True,
        append_images=frames[1:],
        duration=60,
        loop=0
    )
    print("Generated assets/alex1bc-demo.gif")

if __name__ == "__main__":
    generate_blender_ui()
    generate_android_app_ui()
    generate_workflow_diagram()
    generate_demo_gif()
    print("All assets generated successfully!")
