"""python tools/build.py
 -> dist/Alex1BC-Blender-Addon-<ver>.zip            (Blender extension)
 -> dist/Alex1BC-Android-Studio-Project-<ver>.zip   (open in Android Studio)
 -> copies both (and the APK, if you built one) into website/downloads/ so the site's buttons switch on."""
import re, shutil, zipfile
from pathlib import Path
root = Path(__file__).resolve().parent.parent
src = root / "addon" / "alex1bc"
ver = re.search(r'^version\s*=\s*"([^"]+)"', (src / "blender_manifest.toml").read_text(), re.M).group(1)
out = root / "dist"; out.mkdir(exist_ok=True)
dl = root / "website" / "downloads"; dl.mkdir(parents=True, exist_ok=True)
for old in list(dl.glob("*.zip")): old.unlink()

z = out / f"Alex1BC-Blender-Addon-{ver}.zip"
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
    for p in sorted(src.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            f.write(p, p.relative_to(src).as_posix())          # manifest at the ZIP root = Blender extension layout
shutil.copy(z, dl / z.name)

SKIP = {"build", ".gradle", ".idea", "captures", ".cxx"}
a = out / f"Alex1BC-Android-Studio-Project-{ver}.zip"
with zipfile.ZipFile(a, "w", zipfile.ZIP_DEFLATED) as f:
    for p in sorted((root / "android").rglob("*")):
        rel = p.relative_to(root / "android")
        if p.is_file() and not (set(rel.parts) & SKIP) and p.name not in ("local.properties",):
            f.write(p, ("Alex1BC-Android/" / rel).as_posix())
# shutil.copy(a, dl / a.name)  # Kept in dist/ only; users download phone APK or blender addon

apk = root / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
if apk.exists():
    shutil.copy(apk, dl / "Alex1BC-Android.apk"); print("APK copied to website/downloads")
else:
    print("No APK yet: build in Android Studio (Build > Build APK), then run this script again.")
for p in (z, a): print(f"Built {p.name} ({p.stat().st_size//1024} KB)")
