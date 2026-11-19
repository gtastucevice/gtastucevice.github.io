#!/usr/bin/env python3
"""Vidéo « TOP N » verticale (format validé par Roméo) : une image officielle plein écran par élément,
gros numéro, titre et une ligne d'explication, compte à rebours, musique libre de droits + effets.
Usage : python3 outils/video_top.py spec.json
spec : {"slug", "hook": {"lines": [[txt, "w|y"]...], "image": "banque/x.jpg"},
        "items": [{"title", "text", "image", "tag"(facultatif: "À TESTER"/"RUMEUR")}...]  (dans l'ordre d'affichage),
        "voice": [wav accroche, wav élément 1, ..., wav fin] (facultatif : voix off générée avec Speko),
        "outro": {"line"}, "music": "/chemin.mp3" (facultatif), "bars_per_item": 2.5}"""
import json, math, os, subprocess, sys, importlib.util
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
spec_ = importlib.util.spec_from_file_location("vs", os.path.join(HERE, "video_site.py")); vs = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(vs)
W, H, FPS, BAR, BEAT = vs.W, vs.H, vs.FPS, vs.BAR, vs.BEAT
NIGHT, PINK, PINK2, YEL, WHITE = vs.NIGHT, vs.PINK, vs.PINK2, vs.YEL, vs.WHITE
fnt = vs.fnt; ease = vs.ease

def cover(img, t, zoom=0.10, pan=40):
    w, h = img.size; s = 1 + zoom * (1 - t)
    ch = h; cw = int(ch * W / H)
    if cw > w: cw = w; ch = int(cw * H / W)
    cw2, ch2 = int(cw / s), int(ch / s); x = (w - cw2) // 2 + int(pan * (t - 0.5)); y = (h - ch2) // 2
    x = max(0, min(w - cw2, x)); return img.crop((x, y, x + cw2, y + ch2)).resize((W, H), Image.LANCZOS)

def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = wd
        else: cur = t
    if cur: lines.append(cur)
    return lines

GRAD = Image.new("RGBA", (W, H), (0, 0, 0, 0)); _g = ImageDraw.Draw(GRAD)
for y in range(H):
    a = 0
    if y < 420: a = int(170 * (1 - y / 420))
    if y > 980: a = max(a, int(235 * min(1, (y - 980) / 520)))
    _g.line([(0, y), (W, y)], fill=(23, 10, 51, a))

def frame_item(img, n, it, t, ta):
    im = cover(img, t).convert("RGBA"); im.alpha_composite(GRAD); d = ImageDraw.Draw(im)
    pop = min(1, t * 6); pul = 1 + 0.05 * math.exp(-((ta / BEAT) % 1) * 8)
    f = fnt("ArchivoBlack.ttf", int(230 * (0.6 + 0.4 * pop) * pul)); s = f"#{n}"
    d.text((70 + 9, 120 + 9), s, font=f, fill=PINK); d.text((70, 120), s, font=f, fill=YEL)
    if it.get("tag"):
        tf = fnt("ArchivoBlack.ttf", 46); tw = d.textlength(it["tag"], font=tf)
        d.rounded_rectangle([W - tw - 130, 170, W - 70, 250], radius=40, fill=PINK); d.text((W - tw - 100, 182), it["tag"], font=tf, fill=NIGHT)
    tf = fnt("ArchivoBlack.ttf", 92); lines = wrap(d, it["title"].upper(), tf, 940)
    while len(lines) > 3: tf = fnt("ArchivoBlack.ttf", tf.size - 8); lines = wrap(d, it["title"].upper(), tf, 940)
    bf = fnt("Inter.ttf", 50); blines = wrap(d, it["text"], bf, 940)[:3]
    y = H - 140 - len(blines) * 64 - 30 - len(lines) * int(tf.size * 1.08)
    for ln in lines:
        d.text((70 + 6, y + 6), ln, font=tf, fill=PINK); d.text((70, y), ln, font=tf, fill=WHITE); y += int(tf.size * 1.08)
    y += 30
    for ln in blines: d.text((70, y), ln, font=bf, fill=(240, 232, 255)); y += 64
    d.text((70, H - 70), "Image : Rockstar Games", font=fnt("Inter.ttf", 30), fill=(220, 210, 240))
    return im.convert("RGB")

def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    P = lambda p: p if os.path.isabs(p) else os.path.join(ROOT, p)
    BG = vs.synth_bg(); segs = []
    hk = spec["hook"]; himg = Image.open(P(hk["image"])).convert("RGB")
    def f_hook(t, ta):
        im = ImageEnhance.Brightness(cover(himg, t, 0.12, 60)).enhance(0.5); d = ImageDraw.Draw(im); y = 620
        pul = 1 + 0.05 * math.exp(-((ta / BEAT) % 1) * 8)
        for txt, c in hk["lines"]:
            size = 132
            while size > 50 and d.textlength(txt, font=fnt("ArchivoBlack.ttf", size)) > 980: size -= 4
            fz = fnt("ArchivoBlack.ttf", int(size * pul * (0.7 + 0.3 * min(1, t * 4)))); w = d.textlength(txt, font=fz)
            d.text(((W - w) / 2 + 7, y + 7), txt, font=fz, fill=PINK); d.text(((W - w) / 2, y), txt, font=fz, fill=vs.COL.get(c, WHITE)); y += int(size * 1.12)
        d.text((40, H - 70), "Image : Rockstar Games", font=fnt("Inter.ttf", 30), fill=(220, 210, 240)); return im
    segs.append((hk.get("bars", 1.5) * BAR, f_hook))
    items = spec["items"]; N = len(items); bpi = spec.get("bars_per_item", 2.5)
    for i, it in enumerate(items):
        img = Image.open(P(it["image"])).convert("RGB"); n = N - i
        segs.append((bpi * BAR, lambda t, ta, img=img, n=n, it=it: frame_item(img, n, it, t, ta)))
    ot = spec.get("outro", {})
    def f_out(t, ta):
        im = BG.copy(); d = ImageDraw.Draw(im); pul = 1 + 0.05 * math.exp(-((ta / BEAT) % 1) * 8)
        f1 = fnt("ArchivoBlack.ttf", 78); w1 = d.textlength("GTASTUCE", font=f1)
        d.text(((W - w1) / 2 + 5, 255), "GTASTUCE", font=f1, fill=PINK); d.text(((W - w1) / 2, 250), "GTASTUCE", font=f1, fill=WHITE)
        f = fnt("ArchivoBlack.ttf", int(100 * pul)); s = "gtastucevice.fr"; w = d.textlength(s, font=f)
        d.text(((W - w) / 2 + 7, 437), s, font=f, fill=PINK); d.text(((W - w) / 2, 430), s, font=f, fill=YEL)
        for k, s in enumerate([ot.get("line", "La carte de tous les secrets est sur le site"), ot.get("cta", "Abonne-toi pour la suite 🔔".replace(" 🔔", ""))]):
            f3 = fnt("Inter.ttf", 52); w = d.textlength(s, font=f3); yy = 620 + k * 120
            d.rounded_rectangle([(W - w) / 2 - 34, yy, (W + w) / 2 + 34, yy + 96], radius=48, fill=PINK if k else NIGHT); d.text(((W - w) / 2, yy + 18), s, font=f3, fill=NIGHT if k else WHITE)
        return im
    segs.append((ot.get("bars", 2.5) * BAR, f_out))
    total = sum(s for s, _ in segs); wav = f"{vs.TMP}/music.wav"
    if spec.get("music") and os.path.exists(spec["music"]): vs.music_file(spec["music"], wav, total)
    else: vs.music(wav, total, 7)
    cuts, t = [], 0.0
    for dur, _ in segs: cuts.append(t); t += dur
    ev = [("riser", cuts[1] - 2.1, 0.5)] + [("swoosh1", c - 0.1, 0.75) for c in cuts[1:-1]] + [("swoosh2", cuts[-1] - 0.25, 0.6)]
    vs.add_sfx(wav, ev)
    voice = spec.get("voice")  # liste de wav : accroche, chaque élément, fin (même ordre que les plans)
    if voice:
        import numpy as np
        from scipy.io import wavfile
        sr, mix = wavfile.read(wav); mix = mix.astype(np.float64) / 32767 * 0.42   # musique en fond sous la voix
        for path, c in zip(voice, cuts):
            if not path or not os.path.exists(path): continue
            tmpw = f"{vs.TMP}/voice.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ar", str(sr), "-ac", "2", "-af", "highpass=f=70,acompressor=threshold=-18dB:ratio=3", tmpw], check=True)
            _, v = wavfile.read(tmpw); v = v.astype(np.float64) / 32767
            v = v / max(1e-6, np.abs(v).max()) * 0.9
            i = int((c + 0.18) * sr); j = min(len(mix), i + len(v)); mix[i:j] += v[: j - i]
        mix = mix / max(1.0, np.abs(mix).max() / 0.97)
        wavfile.write(wav, sr, (mix * 32767).astype(np.int16))
    os.makedirs(os.path.join(ROOT, "assets", "videos"), exist_ok=True); out = os.path.join(ROOT, "assets", "videos", spec["slug"] + ".mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
        "-map", "0:v", "-map", "1:a", "-t", f"{total:.3f}", "-af", f"afade=t=out:st={total-1.2:.3f}:d=1.2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    t0 = 0.0
    for dur, fn in segs:
        n = round((t0 + dur) * FPS) - round(t0 * FPS)
        for k in range(n):
            fr = fn(k / max(1, n - 1), (round(t0 * FPS) + k) / FPS)
            if k < 3: fr = Image.blend(fr, Image.new("RGB", (W, H), WHITE), 0.35 * (1 - k / 3))
            ff.stdin.write(fr.tobytes())
        t0 += dur
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.9", "-i", out, "-frames:v", "1", "-q:v", "3", out[:-4] + ".jpg"])
    print(f"OK {out} ({total:.1f} s)")

if __name__ == "__main__": main()
