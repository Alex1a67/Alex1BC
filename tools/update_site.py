import re, os

site_path = os.path.join(os.path.dirname(__file__), "..", "website", "index.html")
docs_path = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")

with open(site_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace all em-dashes and en-dashes
content = content.replace("—", "-")
content = content.replace("–", "-")

# 2. Update navigation CSS
old_nav_css = """/* navigation */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 50;
  padding: 16px 0; background: linear-gradient(180deg, rgba(6, 9, 14, 0.94) 0%, rgba(6, 9, 14, 0.6) 70%, transparent 100%);
  backdrop-filter: blur(14px); border-bottom: 1px solid rgba(64, 150, 255, 0.08);
}
nav .wrap { display: flex; align-items: center; justify-content: space-between; }
.logo {
  display: flex; align-items: center; gap: 12px; font-weight: 900; font-size: 21px; letter-spacing: -0.02em;
}
.logo-icon {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg, var(--surf2), var(--surf));
  border: 1px solid var(--border-bright); display: grid; place-items: center;
}
.logo-icon svg { width: 20px; height: 20px; }
.logo span b { color: var(--bright); }
.nav-links { display: flex; align-items: center; gap: 32px; font-size: 14px; font-weight: 600; color: var(--text2); }
.nav-links a:hover { color: var(--text); }
.nav-actions { display: flex; align-items: center; gap: 14px; }"""

new_nav_css = """/* navigation */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 50;
  padding: 14px 0; background: linear-gradient(180deg, rgba(6, 9, 14, 0.96) 0%, rgba(6, 9, 14, 0.8) 70%, transparent 100%);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(64, 150, 255, 0.1);
}
nav .wrap { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.logo {
  display: flex; align-items: center; gap: 12px; font-weight: 900; font-size: 21px; letter-spacing: -0.02em;
  flex-shrink: 0;
}
.logo-icon {
  width: 34px; height: 34px; border-radius: 10px;
  background: linear-gradient(135deg, var(--surf2), var(--surf));
  border: 1px solid var(--border-bright); display: grid; place-items: center;
}
.logo-icon svg { width: 20px; height: 20px; }
.logo span b { color: var(--bright); }
.nav-links { display: flex; align-items: center; gap: 28px; font-size: 14px; font-weight: 600; color: var(--text2); white-space: nowrap; }
.nav-links a { transition: color 0.2s ease; }
.nav-links a:hover { color: var(--bright); }
.nav-actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }"""

assert old_nav_css in content, "Could not find old_nav_css"
content = content.replace(old_nav_css, new_nav_css, 1)

# 3. Update responsive media query
old_media = """@media (max-width: 960px) {
  .g3, .download-grid, .demo-box, .tutorial-steps { grid-template-columns: 1fr; }
  .nav-links { display: none; }
  .viewport-frame { min-height: 380px; }
  section { padding: 90px 0; }
  .custom-cursor { display: none; }
}"""

new_media = """@media (max-width: 960px) {
  .g3, .download-grid, .demo-box, .tutorial-steps, .showcase-grid, .screenshot-grid { grid-template-columns: 1fr !important; }
  .nav-links { display: none; }
  .viewport-frame { min-height: 380px; }
  section { padding: 90px 0; }
  .custom-cursor { display: none; }
}"""

assert old_media in content, "Could not find old_media"
content = content.replace(old_media, new_media, 1)

# 4. Update Header Nav HTML
old_nav_html = """<!-- Header Navigation -->
<nav>
  <div class="wrap">
    <a class="logo" href="#hero">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/></svg>
      </div>
      <span>Alex<b>1BC</b></span>
    </a>
    <div class="nav-links">
      <a href="#how">How It Works</a>
      <a href="#tutorial">Tutorial</a>
      <a href="#architecture">Architecture</a>
      <a href="#features">Rig Features</a>
      <a href="#demo">Live 3D Demo</a>
      <a href="#downloads">Downloads</a>
      <a href="#faq">FAQ</a>
      <a href="https://github.com/Alex1a67/Alex1BC" target="_blank" rel="noopener">GitHub</a>
    </div>
    <div class="nav-actions">
      <span class="badge"><span class="dot"></span>Blender 4.2 - 5.2</span>
      <a class="btn sm" href="https://github.com/Alex1a67/Alex1BC" target="_blank" rel="noopener" title="View Source on GitHub">
        <svg style="width: 16px; height: 16px;" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub
      </a>
      <a class="btn primary sm" href="#downloads">Get Downloads</a>
    </div>
  </div>
</nav>"""

new_nav_html = """<!-- Header Navigation -->
<nav>
  <div class="wrap">
    <a class="logo" href="#hero">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/></svg>
      </div>
      <span>Alex<b>1BC</b></span>
    </a>
    <div class="nav-links">
      <a href="#tutorial">Tutorial</a>
      <a href="#features">Features</a>
      <a href="#demo">3D Simulator</a>
      <a href="#downloads">Downloads</a>
    </div>
    <div class="nav-actions">
      <a class="btn sm" href="https://github.com/Alex1a67/Alex1BC" target="_blank" rel="noopener" title="View Source on GitHub">
        <svg style="width: 16px; height: 16px;" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub
      </a>
      <a class="btn primary sm" href="#downloads">Download</a>
    </div>
  </div>
</nav>"""

assert old_nav_html in content, "Could not find old_nav_html"
content = content.replace(old_nav_html, new_nav_html, 1)

# 5. Add Visual Motion Showcase in #how section
old_how_end = """        <div class="card">
          <div class="card-num"><span>STEP 03</span><span class="badge orange">RECORD TAKES</span></div>
          <h3>Capture &amp; Animate</h3>
          <p>Tap <b>REC</b> to start real-time timeline playback. Stop whenever you’re done: the entire take bakes into clean, editable location and rotation F-Curves in a new Blender Action.</p>
        </div>
      </div>
    </div>
  </section>"""

new_how_end = """        <div class="card">
          <div class="card-num"><span>STEP 03</span><span class="badge orange">RECORD TAKES</span></div>
          <h3>Capture &amp; Animate</h3>
          <p>Tap <b>REC</b> to start real-time timeline playback. Stop whenever you’re done: the entire take bakes into clean, editable location and rotation F-Curves in a new Blender Action.</p>
        </div>
      </div>

      <!-- Live Motion Showcase (Animated GIF Demo + Workflow Diagram) -->
      <div class="card" style="margin-top: 48px; padding: 32px; border-color: rgba(0, 210, 255, 0.35);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; flex-wrap: wrap; gap: 14px;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <span class="badge orange"><span class="dot"></span>LIVE RIG MOTION</span>
            <h3 style="font-size: 20px; margin: 0;">See Alex1BC in Action</h3>
          </div>
          <span style="font-family: var(--mono); font-size: 13px; color: var(--bright);">Real-time Telemetry &bull; 60 FPS Response</span>
        </div>
        
        <div class="showcase-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: start;">
          <!-- Animated Demo GIF -->
          <div style="background: rgba(6, 9, 14, 0.7); border-radius: 16px; padding: 14px; border: 1px solid var(--border);">
            <div style="border-radius: 12px; overflow: hidden; background: #080d17; border: 1px solid rgba(0, 210, 255, 0.2);">
              <img src="assets/alex1bc-demo.gif" alt="Alex1BC Live Tracking Animated Demonstration" style="width: 100%; height: auto; display: block;" loading="lazy">
            </div>
            <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 13.5px; font-weight: 700; color: var(--text);">Wireless Gyro Telemetry Stream</span>
              <span class="badge" style="font-size: 10px; padding: 3px 8px;">60 FPS &bull; REC</span>
            </div>
            <p style="font-size: 12.5px; color: var(--text2); margin-top: 6px; line-height: 1.5; margin-bottom: 0;">
              Aim your phone to drive the active Blender cinema camera in real time with sub-millisecond local TLS latency.
            </p>
          </div>

          <!-- Production Workflow Diagram -->
          <div style="background: rgba(6, 9, 14, 0.7); border-radius: 16px; padding: 14px; border: 1px solid var(--border);">
            <div style="border-radius: 12px; overflow: hidden; background: #070b12; border: 1px solid rgba(37, 117, 252, 0.2);">
              <img src="assets/alex1bc-workflow-diagram.png" alt="Alex1BC Production Workflow Diagram" style="width: 100%; height: auto; display: block;" loading="lazy">
            </div>
            <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 13.5px; font-weight: 700; color: var(--text);">4-Step Production Pipeline</span>
              <span class="badge" style="font-size: 10px; padding: 3px 8px;">NON-DESTRUCTIVE</span>
            </div>
            <p style="font-size: 12.5px; color: var(--text2); margin-top: 6px; line-height: 1.5; margin-bottom: 0;">
              Pair in 1 second, track 6-DOF handheld moves, and bake takes automatically into isolated Blender Actions.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>"""

assert old_how_end in content, "Could not find old_how_end"
content = content.replace(old_how_end, new_how_end, 1)

# 6. Add Visual Interface Tour in #tutorial section
old_tut_insert_marker = """      <!-- Connection Route Details -->
      <div class="grid g2" style="margin-top: 28px;">"""

new_tut_content = """      <!-- Visual Interface Tour (Screenshots) -->
      <div class="card" style="margin-top: 36px; padding: 32px; border-color: rgba(37, 117, 252, 0.35);">
        <div class="eyebrow" style="margin-bottom: 12px;">Visual Interface Tour</div>
        <h3 style="font-size: 24px; margin-bottom: 8px;">Blender N-Panel &amp; Android Controller</h3>
        <p style="color: var(--text2); font-size: 15px; margin-bottom: 24px;">
          Crisp, clean tools designed specifically for 3D animators and cinematographers.
        </p>

        <div class="screenshot-grid" style="display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; align-items: start;">
          <!-- Blender UI Screenshot -->
          <div style="background: rgba(6, 9, 14, 0.8); border-radius: 16px; padding: 14px; border: 1px solid var(--border);">
            <div style="border-radius: 10px; overflow: hidden; border: 1px solid rgba(0, 210, 255, 0.3);">
              <img src="assets/blender-ui-screenshot.png" alt="Blender 5.1 Alex1BC Interface Screenshot" style="width: 100%; height: auto; display: block;" loading="lazy">
            </div>
            <div style="margin-top: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 700; font-size: 14px; color: var(--bright);">Blender 5.1 N-Panel &amp; 3D Viewport</span>
                <span class="badge">SERVER ACTIVE</span>
              </div>
              <p style="font-size: 13px; color: var(--text2); line-height: 1.5; margin: 0;">
                Displays the 1-second pairing QR code, numeric PIN, control mode toggles, and one-tap <b>Record Take</b> button with live timeline F-curve baking.
              </p>
            </div>
          </div>

          <!-- Android App Screenshot -->
          <div style="background: rgba(6, 9, 14, 0.8); border-radius: 16px; padding: 14px; border: 1px solid var(--border);">
            <div style="border-radius: 10px; overflow: hidden; border: 1px solid rgba(234, 118, 0, 0.3); text-align: center;">
              <img src="assets/android-app-screenshot.png" alt="Android Alex1BC Controller App Screenshot" style="max-height: 480px; width: auto; margin: 0 auto; display: block; border-radius: 8px;" loading="lazy">
            </div>
            <div style="margin-top: 12px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 700; font-size: 14px; color: var(--orange-bright);">Android Studio Controller</span>
                <span class="badge orange">60 HZ GYRO</span>
              </div>
              <p style="font-size: 13px; color: var(--text2); line-height: 1.5; margin: 0;">
                Real-time artificial horizon reticle, dual joysticks for dolly/crane, 18-135mm cinema prime rack buttons, and prominent REC transport.
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Connection Route Details -->
      <div class="grid g2" style="margin-top: 28px;">"""

assert old_tut_insert_marker in content, "Could not find old_tut_insert_marker"
content = content.replace(old_tut_insert_marker, new_tut_content, 1)

with open(site_path, "w", encoding="utf-8") as f:
    f.write(content)

with open(docs_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully updated website/index.html and docs/index.html!")
