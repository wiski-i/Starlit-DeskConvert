"""Hızlı öz-test: her kategoride bir dönüştürme dener."""
import os
import tempfile

from engine import convert as engine
from engine.converters import images, media, documents, data, archives

tmp = tempfile.mkdtemp(prefix="dt_selftest_")
print("Geçici klasör:", tmp)
results = []


def check(name, fn):
    try:
        fn()
        results.append((name, True, ""))
        print(f"  ✓ {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  ✗ {name}: {e}")


# --- motor durumları ---
print("\n[Motor durumları]")
for mod in (images, media, documents, data, archives):
    ok, msg = mod.available()
    print(f"  {mod.__name__:35s} {'OK' if ok else 'YOK'} {msg}")

# --- Görsel: PNG üret -> jpg, webp, pdf, ico ---
print("\n[Görsel]")
from PIL import Image
png = os.path.join(tmp, "test.png")
Image.new("RGBA", (64, 48), (200, 30, 30, 255)).save(png)
det = engine.analyze(png)
assert det["category"] == "image", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for ext in ("jpg", "webp", "pdf", "ico", "bmp", "gif"):
    t = {"key": ext, "label": ext.upper(), "ext": ext}
    check(f"png->{ext}", lambda t=t: engine.run(png, det, t, tmp))

# --- Ses: ffmpeg ile sentetik ton üret (wav) -> mp3, flac, ogg ---
print("\n[Ses]")
ff = media.ffmpeg_exe()
import subprocess
wav = os.path.join(tmp, "tone.wav")
subprocess.run([ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
det = engine.analyze(wav)
assert det["category"] == "audio", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for ext in ("mp3", "flac", "ogg", "aac", "m4a"):
    t = {"key": ext, "label": ext.upper(), "ext": ext}
    check(f"wav->{ext}", lambda t=t: engine.run(wav, det, t, tmp))

# --- Video: küçük testsrc üret (mp4) -> mkv, webm, gif, mp3(ses çıkar) ---
print("\n[Video]")
mp4 = os.path.join(tmp, "clip.mp4")
subprocess.run([ff, "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=160x120:rate=10",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-pix_fmt", "yuv420p", "-shortest", mp4],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
det = engine.analyze(mp4)
assert det["category"] == "video", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for ext in ("mkv", "gif", "mp3", "avi"):
    t = {"key": ext, "label": ext.upper(), "ext": ext}
    check(f"mp4->{ext}", lambda t=t: engine.run(mp4, det, t, tmp))

# --- Belge: markdown -> docx, html, rtf, odt ---
print("\n[Belge]")
md = os.path.join(tmp, "doc.md")
with open(md, "w", encoding="utf-8") as fh:
    fh.write("# Başlık\n\nMerhaba **dünya**.\n\n- bir\n- iki\n")
det = engine.analyze(md)
assert det["category"] == "document", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for ext in ("docx", "html", "rtf", "odt", "txt"):
    t = {"key": ext, "label": ext.upper(), "ext": ext}
    check(f"md->{ext}", lambda t=t: engine.run(md, det, t, tmp))

# --- Veri: csv -> xlsx, json, html, md, xml ---
print("\n[Veri]")
csv = os.path.join(tmp, "data.csv")
with open(csv, "w", encoding="utf-8") as fh:
    fh.write("ad,yas\nAli,30\nVeli,25\n")
det = engine.analyze(csv)
assert det["category"] == "data", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for ext in ("xlsx", "json", "html", "md", "xml", "tsv"):
    t = {"key": ext, "label": ext.upper(), "ext": ext}
    check(f"csv->{ext}", lambda t=t: engine.run(csv, det, t, tmp))

# --- Arşiv: zip -> tar.gz, 7z, tar ---
print("\n[Arşiv]")
import zipfile
zp = os.path.join(tmp, "pack.zip")
with zipfile.ZipFile(zp, "w") as z:
    z.writestr("icerik/merhaba.txt", "selam")
    z.writestr("icerik/sub/x.txt", "x")
det = engine.analyze(zp)
assert det["category"] == "archive", det
print("  algılandı:", det["format"], det["category_label"], "hedef sayısı:", len(det["targets"]))
for tg in det["targets"]:
    check(f"zip->{tg['label']}", lambda tg=tg: engine.run(zp, det, tg, tmp))

# --- özet ---
ok = sum(1 for _, s, _ in results if s)
print(f"\n=== SONUÇ: {ok}/{len(results)} dönüşüm başarılı ===")
fails = [(n, m) for n, s, m in results if not s]
if fails:
    print("Başarısızlar:")
    for n, m in fails:
        print(f"  - {n}: {m}")
    raise SystemExit(1)
