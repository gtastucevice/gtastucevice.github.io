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

def cover(img, t, zoom=0.08, pan=30):
    """Zoom lent et régulier (style cinéma), t peut dépasser 1 pendant les fondus."""
    w, h = img.size; s = 1 + zoom * min(1.15, max(0, t))
    ch = h; cw = int(ch * W / H)
    if cw > w: cw = w; ch = int(cw * H / W)
    cw2, ch2 = int(cw / s), int(ch / s); x = (w - cw2) // 2 + int(pan * (t - 0.5)); y = (h - ch2) // 2
    x = max(0, min(w - cw2, x)); return img.crop((x, y, x + cw2, y + ch2)).resize((W, H), Image.BICUBIC)

def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = wd
        else: cur = t
    if cur: lines.append(cur)
    return lines

def ease_out(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

GRAD = Image.new("RGBA", (W, H), (0, 0, 0, 0)); _g = ImageDraw.Draw(GRAD)
for y in range(H):
    a = 0
    if y < 380: a = int(140 * (1 - y / 380) ** 1.5)
    if y > 900: a = max(a, int(230 * min(1, (y - 900) / 620) ** 1.2))
    _g.line([(0, y), (W, y)], fill=(12, 6, 26, a))

def text_layer(draw_fn, alpha, dy):
    """Dessine sur un calque transparent puis l'applique avec une opacité et un décalage vertical."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(lay))
    if dy: lay = lay.transform(lay.size, Image.AFFINE, (1, 0, 0, 0, 1, -dy))
    if alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    return lay

def shadow_text(d, xy, txt, f, fill):
    x, y = xy
    d.text((x + 3, y + 4), txt, font=f, fill=(0, 0, 0, 150)); d.text((x, y), txt, font=f, fill=fill)

def frame_item(img, n, it, t, sec, dur):
    """sec = secondes écoulées dans le plan (pour des animations à vitesse fixe)."""
    im = cover(img, t).convert("RGBA"); im.alpha_composite(GRAD)
    # numéro : glisse depuis la gauche
    a1 = ease_out(sec / 0.45)
    nf = fnt("ArchivoBlack.ttf", 190)
    def dnum(d):
        shadow_text(d, (70, 110), f"#{n}", nf, YEL + (255,))
        if it.get("tag"):
            tf = fnt("ArchivoBlack.ttf", 40); tw = d.textlength(it["tag"], font=tf)
            d.rounded_rectangle([W - tw - 120, 160, W - 70, 228], radius=34, fill=PINK + (235,)); d.text((W - tw - 95, 171), it["tag"], font=tf, fill=NIGHT)
    lay = text_layer(dnum, a1, 0); lay = lay.transform(lay.size, Image.AFFINE, (1, 0, int(-60 * (1 - a1)), 0, 1, 0)); im.alpha_composite(lay)
    # titre puis texte : montent en fondu, l'un après l'autre
    d0 = ImageDraw.Draw(im)
    tf = fnt("ArchivoBlack.ttf", 86); lines = wrap(d0, it["title"].upper(), tf, 940)
    while len(lines) > 3: tf = fnt("ArchivoBlack.ttf", tf.size - 6); lines = wrap(d0, it["title"].upper(), tf, 940)
    bf = fnt("Inter.ttf", 48); blines = wrap(d0, it["text"], bf, 940)[:3]
    ytop = H - 150 - len(blines) * 62 - 28 - len(lines) * int(tf.size * 1.1)
    a2 = ease_out((sec - 0.15) / 0.5); a3 = ease_out((sec - 0.45) / 0.5)
    def dtitle(d):
        y = ytop
        for ln in lines: shadow_text(d, (70, y), ln, tf, WHITE + (255,)); y += int(tf.size * 1.1)
    def dbody(d):
        y = ytop + len(lines) * int(tf.size * 1.1) + 28
        d.rectangle([70, y - 14, 150, y - 8], fill=PINK + (255,))
        for ln in blines: d.text((70, y + 6), ln, font=bf, fill=(236, 230, 250, 255)); y += 62
    im.alpha_composite(text_layer(dtitle, a2, int(36 * (1 - a2))))
    im.alpha_composite(text_layer(dbody, a3, int(28 * (1 - a3))))
    # fondu de sortie des textes juste avant la coupe
    out = ease_out((sec - (dur - 0.3)) / 0.3)
    ImageDraw.Draw(im).text((70, H - 70), "Image : Rockstar Games", font=fnt("Inter.ttf", 28), fill=(210, 200, 230, 255))
    return im.convert("RGB"), out

def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    P = lambda p: p if os.path.isabs(p) else os.path.join(ROOT, p)
    BG = vs.synth_bg(); segs = []
    hk = spec["hook"]; himg = Image.open(P(hk["image"])).convert("RGB")
    def f_hook(t, ta, sec, dur):
        im = ImageEnhance.Brightness(cover(himg, t, 0.10, 40)).enhance(0.55).convert("RGBA")
        d0 = ImageDraw.Draw(im); y = 640
        for k, (txt, c) in enumerate(hk["lines"]):
            size = 124
            while size > 50 and d0.textlength(txt, font=fnt("ArchivoBlack.ttf", size)) > 960: size -= 4
            fz = fnt("ArchivoBlack.ttf", size); w = d0.textlength(txt, font=fz); a = ease_out((sec - 0.12 * k) / 0.45)
            im.alpha_composite(text_layer(lambda d, txt=txt, fz=fz, w=w, y=y, c=c: shadow_text(d, ((W - w) / 2, y), txt, fz, vs.COL.get(c, WHITE) + (255,)), a, int(30 * (1 - a))))
            y += int(size * 1.12)
        ImageDraw.Draw(im).text((40, H - 70), "Image : Rockstar Games", font=fnt("Inter.ttf", 28), fill=(210, 200, 230, 255))
        return im.convert("RGB"), 0
    segs.append((hk.get("bars", 1.5) * BAR, f_hook))
    items = spec["items"]; N = len(items); bpi = spec.get("bars_per_item", 2.5)
    for i, it in enumerate(items):
        img = Image.open(P(it["image"])).convert("RGB"); n = N - i
        segs.append((bpi * BAR, lambda t, ta, sec, dur, img=img, n=n, it=it: frame_item(img, n, it, t, sec, dur)))
    ot = spec.get("outro", {})
    def f_out(t, ta, sec, dur):
        im = BG.copy().convert("RGBA")
        def dlogo(d):
            f1 = fnt("ArchivoBlack.ttf", 74); w1 = d.textlength("GTASTUCE VICE", font=f1); shadow_text(d, ((W - w1) / 2, 270), "GTASTUCE VICE", f1, WHITE + (255,))
            f = fnt("ArchivoBlack.ttf", 96); s_ = "gtastucevice.fr"; w = d.textlength(s_, font=f); shadow_text(d, ((W - w) / 2, 420), s_, f, YEL + (255,))
        def dcta(d):
            for k, s_ in enumerate([ot.get("line", "La carte de tous les secrets est sur le site"), ot.get("cta", "Abonne-toi pour la suite")]):
                f3 = fnt("Inter.ttf", 50); w = d.textlength(s_, font=f3); yy = 620 + k * 120
                d.rounded_rectangle([(W - w) / 2 - 34, yy, (W + w) / 2 + 34, yy + 94], radius=47, fill=(PINK if k else NIGHT) + (255,)); d.text(((W - w) / 2, yy + 18), s_, font=f3, fill=(NIGHT if k else WHITE) + (255,))
        a = ease_out(sec / 0.5); b2 = ease_out((sec - 0.35) / 0.5)
        im.alpha_composite(text_layer(dlogo, a, int(30 * (1 - a)))); im.alpha_composite(text_layer(dcta, b2, int(30 * (1 - b2))))
        return im.convert("RGB"), 0
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
    XF = 9  # fondu enchaîné de 0,3 s entre deux plans
    t0 = 0.0; prev = None
    for idx, (dur, fn) in enumerate(segs):
        n = round((t0 + dur) * FPS) - round(t0 * FPS)
        for k in range(n):
            fr, _ = fn(k / max(1, n - 1), (round(t0 * FPS) + k) / FPS, k / FPS, dur)
            if prev is not None and k < XF:
                pdur, pfn, pn = prev
                pf, _ = pfn(1 + (k + 1) / max(1, pn - 1), 0, pdur + (k + 1) / FPS, 10**6)
                fr = Image.blend(pf, fr, ease_out((k + 1) / XF))
            ff.stdin.write(fr.tobytes())
        prev = (dur, fn, n); t0 += dur
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.9", "-i", out, "-frames:v", "1", "-q:v", "3", out[:-4] + ".jpg"])
    print(f"OK {out} ({total:.1f} s)")

if __name__ == "__main__": main()
