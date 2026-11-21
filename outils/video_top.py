#!/usr/bin/env python3
"""Vidéo « TOP N » verticale (format validé par Roméo) : une image officielle plein écran par élément,
gros numéro, titre et une ligne d'explication, compte à rebours, musique libre de droits + effets.
Usage : python3 outils/video_top.py spec.json
spec : {"slug", "hook": {"lines": [[txt, "w|y"]...], "image": "banque/x.jpg"},
        "items": [{"title", "text", "image", "tag"(facultatif: "À TESTER"/"RUMEUR")}...]  (dans l'ordre d'affichage),
        "voice": [wav accroche, wav élément 1, ..., wav fin] (facultatif : voix off générée avec Speko),
        "outro": {"line"}, "music": "/chemin.mp3" (facultatif), "bars_per_item": 2.5,
        "order": "up" (facultatif : numérote les étapes 1, 2, 3… au lieu du compte à rebours)}
Gameplay : à la place de "image", un élément (ou l'accroche) peut avoir
  "clip": {"src": "video.mp4", "start": s, "len": 14, "speed": 1, "crop": [x, y, l, h]}
  -> bande 16:9 nette au centre, fond flouté, son du jeu coupé, crédit « Capture en jeu : GTASTUCE VICE »."""
import json, math, os, subprocess, sys, importlib.util
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
spec_ = importlib.util.spec_from_file_location("vs", os.path.join(HERE, "video_site.py")); vs = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(vs)
W, H, FPS, BAR, BEAT = vs.W, vs.H, vs.FPS, vs.BAR, vs.BEAT
NIGHT, PINK, PINK2, YEL, WHITE = vs.NIGHT, vs.PINK, vs.PINK2, vs.YEL, vs.WHITE
fnt = vs.fnt; ease = vs.ease

_CACHE = {}
def cover(img, t, zoom=0.08, pan=30):
    """Zoom lent et continu, calculé au sous-pixel (pas de tremblement). t peut dépasser 1 pendant les fondus."""
    key = id(img)
    if key not in _CACHE:  # pré-agrandit l'image une fois pour un rendu net
        w, h = img.size; k = max(W / (h * W / H), H / h) * 1.25
        _CACHE[key] = img.resize((int(w * k), int(h * k)), Image.LANCZOS)
    src = _CACHE[key]; w, h = src.size
    s_ = 1 + zoom * min(1.15, max(0.0, t))
    ch = h / s_; cw = ch * W / H
    if cw > w: cw = w; ch = cw * H / W
    cx = w / 2 + pan * 1.6 * (t - 0.5); cy = h / 2
    x0 = min(max(0, cx - cw / 2), w - cw); y0 = min(max(0, cy - ch / 2), h - ch)
    sc = cw / W
    return src.transform((W, H), Image.AFFINE, (sc, 0, x0, 0, sc, y0), resample=Image.BICUBIC)

def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = wd
        else: cur = t
    if cur: lines.append(cur)
    return lines

def ease_out(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

# ---------- extraits de gameplay (captures en jeu) ----------
CAPTURE_CREDIT = "Capture en jeu : GTASTUCE VICE"
BAND_Y, BAND_H = 520, 810   # bande au milieu de l'écran vertical (16:9 rogné sur les côtés, plus lisible sur téléphone)
_CLIPS = {}
def clip_frames(c):
    """Extrait une fois les images d'un passage de vidéo (son coupé : jamais le son du jeu, pour les droits)."""
    key = (c["src"], c["start"])
    if key not in _CLIPS:
        d = f"{vs.TMP}/clip_{BAND_H}_{abs(hash(key))}"
        if not os.path.isdir(d) or not os.listdir(d):
            os.makedirs(d, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["start"]), "-i", c["src"], "-t", str(c.get("len", 14)),
                            "-an", "-vf", f"fps={FPS},scale=-2:{BAND_H}:flags=lanczos,crop={W}:{BAND_H}", "-q:v", "2", f"{d}/%05d.jpg"], check=True)
        _CLIPS[key] = sorted(os.path.join(d, f) for f in os.listdir(d))
    return _CLIPS[key]

def clip_frame(c, sec):
    fr = clip_frames(c); i = max(0, min(len(fr) - 1, int(sec * FPS * c.get("speed", 1.0))))
    return Image.open(fr[i]).convert("RGB")

def clip_layout(c, sec, dim=1.0):
    """Fond = même image floutée et assombrie, bande nette au centre, fin liseré rose."""
    band = clip_frame(c, sec)
    if c.get("crop"):  # zoom sur une partie (x, y, l, h en fractions)
        x, y, w, h = c["crop"]; bw, bh = band.size
        band = band.crop((int(x * bw), int(y * bh), int((x + w) * bw), int((y + h) * bh))).resize((W, BAND_H), Image.LANCZOS)
    small = band.resize((W // 8, BAND_H // 8)).filter(ImageFilter.GaussianBlur(3))
    k = H / small.size[1]; bg = small.resize((int(small.size[0] * k), H), Image.BILINEAR)
    x0 = (bg.size[0] - W) // 2; bg = bg.crop((x0, 0, x0 + W, H))
    bg = ImageEnhance.Brightness(bg).enhance(0.35 * dim)
    if dim < 1: band = ImageEnhance.Brightness(band).enhance(0.75)
    bg.paste(band, (0, BAND_Y))
    d = ImageDraw.Draw(bg); d.rectangle([0, BAND_Y - 6, W, BAND_Y - 1], fill=PINK); d.rectangle([0, BAND_Y + BAND_H, W, BAND_Y + BAND_H + 5], fill=PINK)
    return bg

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

def word_times(text, start, dur):
    """Répartit les mots sur la durée de la voix (poids = longueur, pauses sur la ponctuation)."""
    words = text.replace("...", "…").split(); w = []
    for wd in words: w.append(len(wd) + 2 + (5 if wd[-1] in ".,:;!?…" else 0))
    tot = sum(w) or 1; t, out = start, []
    for wd, ww in zip(words, w):
        d = dur * ww / tot; out.append((wd, t, t + d)); t += d
    return out

def chunks_of(wt, maxw=3):
    ch, cur = [], []
    for x in wt:
        cur.append(x)
        if len(cur) >= maxw or x[0][-1] in ".,:;!?…": ch.append(cur); cur = []
    if cur: ch.append(cur)
    return ch

CAP = fnt("ArchivoBlack.ttf", 92)
def draw_caption(im, chunks, sec, y=1180):
    """Sous-titres façon TikTok : le groupe de mots en cours, le mot prononcé en jaune, petite apparition."""
    cur = None
    for c in chunks:
        if c[0][1] - 0.05 <= sec <= c[-1][2] + 0.08: cur = c
    if not cur: return
    d = ImageDraw.Draw(im); words = [x[0].upper() for x in cur]
    sp = d.textlength(" ", font=CAP); widths = [d.textlength(wd, font=CAP) for wd in words]
    lines, line, lw = [], [], 0
    for i, wdt in enumerate(widths):
        if line and lw + sp + wdt > 960: lines.append(line); line, lw = [], 0
        line.append(i); lw += (sp if len(line) > 1 else 0) + wdt
    if line: lines.append(line)
    pop = ease_out((sec - cur[0][1]) / 0.14); scale = 0.88 + 0.12 * pop
    lay = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); yy = 10
    for ln in lines:
        tw = sum(widths[i] for i in ln) + sp * (len(ln) - 1); x = (W - tw) / 2
        for i in ln:
            active = cur[i][1] <= sec < cur[i][2] + 0.02
            ld.text((x, yy), words[i], font=CAP, fill=YEL if active else WHITE, stroke_width=9, stroke_fill=(10, 4, 22))
            x += widths[i] + sp
        yy += 110
    if scale < 0.999:
        lay = lay.resize((int(W * scale), int(420 * scale)), Image.BICUBIC); ox = (W - lay.size[0]) // 2
    else: ox = 0
    im.alpha_composite(lay, (ox, int(y + (1 - scale) * 120)))

def progress(im, idx, N, sec, dur):
    """Barre de compte à rebours en haut de l'écran."""
    d = ImageDraw.Draw(im); gap = 10; bw = (W - 140 - gap * (N - 1)) / N
    for k in range(N):
        x = 70 + k * (bw + gap); d.rounded_rectangle([x, 60, x + bw, 70], radius=5, fill=(255, 255, 255, 70))
        f = 1 if k < idx else (min(1, sec / dur) if k == idx else 0)
        if f > 0: d.rounded_rectangle([x, 60, x + bw * f, 70], radius=5, fill=YEL + (255,))

def frame_item(img, n, it, t, sec, dur, chunks=None, idx=0, N=10):
    """sec = secondes écoulées dans le plan (pour des animations à vitesse fixe)."""
    if it.get("clip"): im = clip_layout(it["clip"], sec).convert("RGBA")
    else: im = cover(img, t).convert("RGBA"); im.alpha_composite(GRAD)
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
    bf = fnt("Inter.ttf", 48); blines = [] if chunks else wrap(d0, it["text"], bf, 940)[:3]
    ytop = H - 150 - len(blines) * 62 - 28 - len(lines) * int(tf.size * 1.1)
    if chunks:
        tf = fnt("ArchivoBlack.ttf", 64); lines = wrap(d0, it["title"].upper(), tf, 940)[:2]; ytop = 340
    a2 = ease_out((sec - 0.15) / 0.5); a3 = ease_out((sec - 0.45) / 0.5)
    def dtitle(d):
        y = ytop
        for ln in lines: shadow_text(d, (70, y), ln, tf, WHITE + (255,)); y += int(tf.size * 1.1)
    def dbody(d):
        y = ytop + len(lines) * int(tf.size * 1.1) + 28
        if blines: d.rectangle([70, y - 14, 150, y - 8], fill=PINK + (255,))
        for ln in blines: d.text((70, y + 6), ln, font=bf, fill=(236, 230, 250, 255)); y += 62
    im.alpha_composite(text_layer(dtitle, a2, int(36 * (1 - a2))))
    im.alpha_composite(text_layer(dbody, a3, int(28 * (1 - a3))))
    # fondu de sortie des textes juste avant la coupe
    out = ease_out((sec - (dur - 0.3)) / 0.3)
    if chunks: draw_caption(im, chunks, sec, y=1390 if it.get("clip") else 1180); progress(im, idx, N, sec, dur)
    ImageDraw.Draw(im).text((70, H - 70), CAPTURE_CREDIT if it.get("clip") else "Image : Rockstar Games", font=fnt("Inter.ttf", 28), fill=(210, 200, 230, 255))
    return im.convert("RGB"), out

def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    P = lambda p: p if os.path.isabs(p) else os.path.join(ROOT, p)
    BG = vs.synth_bg(); segs = []
    hk = spec["hook"]; himg = None if hk.get("clip") else Image.open(P(hk["image"])).convert("RGB")
    def f_hook(t, ta, sec, dur):
        if hk.get("clip"): im = clip_layout(hk["clip"], sec).convert("RGBA")
        else: im = ImageEnhance.Brightness(cover(himg, t, 0.10, 40)).enhance(0.55).convert("RGBA")
        d0 = ImageDraw.Draw(im); y = 110 if hk.get("clip") else 640
        for k, (txt, c) in enumerate(hk["lines"]):
            size = 104 if hk.get("clip") else 124
            while size > 50 and d0.textlength(txt, font=fnt("ArchivoBlack.ttf", size)) > 960: size -= 4
            fz = fnt("ArchivoBlack.ttf", size); w = d0.textlength(txt, font=fz); a = ease_out((sec - 0.12 * k) / 0.45)
            im.alpha_composite(text_layer(lambda d, txt=txt, fz=fz, w=w, y=y, c=c: shadow_text(d, ((W - w) / 2, y), txt, fz, vs.COL.get(c, WHITE) + (255,)), a, int(30 * (1 - a))))
            y += int(size * 1.12)
        ImageDraw.Draw(im).text((40, H - 70), CAPTURE_CREDIT if hk.get("clip") else "Image : Rockstar Games", font=fnt("Inter.ttf", 28), fill=(210, 200, 230, 255))
        if hk.get("clip") and CH[0]: draw_caption(im, CH[0], sec, y=1390)
        return im.convert("RGB"), 0
    segs.append((hk.get("bars", 1.5) * BAR, f_hook))
    items = spec["items"]; N = len(items); bpi = spec.get("bars_per_item", 2.5)
    vt = spec.get("voice_text") or []; vf = spec.get("voice") or []
    def vdur(path):
        try: return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)
        except Exception: return 0
    CH = [chunks_of(word_times(vt[i], 0.18, max(0.5, vdur(vf[i]) - 0.15))) if i < len(vt) and i < len(vf) and vt[i] else None for i in range(N + 2)]
    for i, it in enumerate(items):
        img = None if it.get("clip") else Image.open(P(it["image"])).convert("RGB"); n = i + 1 if spec.get("order") == "up" else N - i  # "up" : étapes 1, 2, 3… au lieu du compte à rebours
        segs.append((bpi * BAR, lambda t, ta, sec, dur, img=img, n=n, it=it, i=i: frame_item(img, n, it, t, sec, dur, CH[i + 1], i, N)))
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
    # Chaque plan dure au moins le temps de sa voix off (+0,35 s), pour ne jamais couper une phrase
    segs = [(max(d, vdur(vf[i]) + 0.35) if i < len(vf) and vf[i] and os.path.exists(vf[i]) else d, fn) for i, (d, fn) in enumerate(segs)]
    total = sum(s for s, _ in segs); wav = f"{vs.TMP}/music.wav"
    if spec.get("music") and os.path.exists(spec["music"]): vs.music_file(spec["music"], wav, total)
    else: vs.music(wav, total, 7)
    cuts, t = [], 0.0
    for dur, _ in segs: cuts.append(t); t += dur
    ev = [("riser", cuts[1] - 2.1, 0.5)] + [("swoosh1", c - 0.1, 0.75) for c in cuts[1:-1]] + [("swoosh2", cuts[-1] - 0.25, 0.6)]
    vs.add_sfx(wav, ev)
    voice = spec.get("voice")  # liste de wav : accroche, chaque élément, fin (même ordre que les plans)
    if voice:
        vs.mix_voice(wav, [(p, c + 0.18) for p, c in zip(voice, cuts)])
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
