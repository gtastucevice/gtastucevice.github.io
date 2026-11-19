#!/usr/bin/env python3
"""Générateur de carrousels GTASTUCE VICE (charte Vice City).
Usage : python3 gtastuce_carrousel.py spec.json dossier_sortie
spec.json = {
  "slug": "nom-court",
  "cover": {"lines": ["5 TRUCS", "À SAVOIR"], "highlight": "AVANT", "after": ["DE LANCER", "GTA 6"]},
  "tips": [{"title": "TITRE COURT", "body": "Une ou deux phrases."}, ...],   (3 à 5)
  "end": {"title": ["ENREGISTRE", "CE POST"], "body": "Texte court."}
}
Sortie : <slug>_1.jpg ... <slug>_N.jpg (1080x1350).
Polices téléchargées depuis GitHub (google/fonts) si absentes.
"""
import json, os, re, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
NIGHT = (23, 10, 51); PINK = (255, 61, 127); PINK2 = (255, 95, 162)
TEAL = (46, 230, 214); YEL = (255, 228, 92); WHITE = (255, 255, 255); PALM = (18, 6, 42)
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS = {
    'arch': ('ArchivoBlack.ttf', 'https://raw.githubusercontent.com/google/fonts/main/ofl/archivoblack/ArchivoBlack-Regular.ttf'),
    'yt': ('Yellowtail.ttf', 'https://raw.githubusercontent.com/google/fonts/main/apache/yellowtail/Yellowtail-Regular.ttf'),
    'inter': ('Inter.ttf', 'https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf'),
}

def fontpath(k):
    os.makedirs(FD, exist_ok=True)
    name, url = FONTS[k]
    p = os.path.join(FD, name)
    if not os.path.exists(p):
        urllib.request.urlretrieve(url, p)
    return p

def F(k, s, bold=False):
    f = ImageFont.truetype(fontpath(k), s)
    if k == 'inter':
        try: f.set_variation_by_axes([14, 650])
        except Exception: pass
    return f

def vgrad(h, stops):
    ys = np.linspace(0, 1, h); out = np.zeros((h, 3)); pos = [s[0] for s in stops]
    for c in range(3): out[:, c] = np.interp(ys, pos, [s[1][c] for s in stops])
    return out

def make_sun(d):
    g = vgrad(d, [(0, (255, 228, 92)), (0.55, (255, 154, 61)), (1, (255, 61, 127))])
    rgb = np.repeat(g[:, None, :], d, axis=1).astype(np.uint8)
    yy, xx = np.mgrid[0:d, 0:d]; r = d / 2
    m = ((xx - r + .5) ** 2 + (yy - r + .5) ** 2 <= r * r)
    for y0, hh in [(.575, .02), (.655, .03), (.75, .04), (.855, .05)]:
        m &= ~((yy >= y0 * d) & (yy < (y0 + hh) * d))
    return Image.fromarray(np.dstack([rgb, (m * 255).astype(np.uint8)]), 'RGBA')

PALM_PATHS = ["M118 400 C 112 300, 70 210, 92 118 L 104 120 C 86 210, 128 300, 134 400 Z", "M98 118 Q 55 80 0 104 Q 55 94 98 126 Z", "M98 118 Q 145 82 200 100 Q 145 96 100 126 Z", "M98 118 Q 68 56 22 40 Q 74 72 98 124 Z", "M98 118 Q 128 54 176 42 Q 124 74 100 124 Z", "M98 118 Q 94 64 104 10 Q 110 66 102 120 Z", "M98 120 Q 46 130 12 186 Q 56 144 98 128 Z", "M100 120 Q 154 132 186 184 Q 144 144 100 128 Z"]

def path_pts(d):
    t = re.findall(r'[MLCQZ]|-?\d+\.?\d*', d.replace(',', ' ')); pts = []; i = 0; cur = (0, 0); cmd = None
    while i < len(t):
        if t[i] in 'MLCQZ':
            cmd = t[i]; i += 1
            if cmd == 'Z': continue
        n = lambda k: [float(x) for x in t[i:i + k]]
        if cmd in 'ML':
            x, y = n(2); i += 2; cur = (x, y); pts.append(cur)
        elif cmd == 'Q':
            x1, y1, x, y = n(4); i += 4
            for s in np.linspace(0, 1, 16)[1:]:
                pts.append(((1-s)**2*cur[0]+2*(1-s)*s*x1+s*s*x, (1-s)**2*cur[1]+2*(1-s)*s*y1+s*s*y))
            cur = (x, y)
        elif cmd == 'C':
            x1, y1, x2, y2, x, y = n(6); i += 6
            for s in np.linspace(0, 1, 20)[1:]:
                m = 1 - s
                pts.append((m**3*cur[0]+3*m*m*s*x1+3*m*s*s*x2+s**3*x, m**3*cur[1]+3*m*m*s*y1+3*m*s*s*y2+s**3*y))
            cur = (x, y)
        else: i += 1
    return pts

def make_palm(h, flip=False):
    sc = h / 400; w = int(200 * sc)
    im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for p in PALM_PATHS: d.polygon([(x * sc * 2, y * sc * 2) for x, y in path_pts(p)], fill=PALM + (255,))
    im = im.resize((w, h), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im

def text_layer(txt, fnt, fill, shadow=None, glow=None):
    b = fnt.getbbox(txt); pad = 60
    w = b[2] - b[0] + pad * 2; h = b[3] - b[1] + pad * 2
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ox, oy = pad - b[0], pad - b[1]
    if glow:
        g = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ImageDraw.Draw(g).text((ox, oy), txt, font=fnt, fill=glow + (255,))
        for r in (20, 8): lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(r)))
    d = ImageDraw.Draw(lay)
    for dx, dy, c in (shadow or []): d.text((ox + dx, oy + dy), txt, font=fnt, fill=c + (255,))
    d.text((ox, oy), txt, font=fnt, fill=fill + (255,))
    return lay, pad, ox, oy

def chip(txt, bg, fg, size):
    f = F('arch', size); b = f.getbbox(txt); w = b[2] - b[0] + 60; h = b[3] - b[1] + 36
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=bg + (255,)); d.text((30 - b[0], 18 - b[1]), txt, font=f, fill=fg + (255,))
    return lay

SUN = None
def background():
    global SUN
    if SUN is None: SUN = make_sun(420)
    g = vgrad(H, [(0, (23, 10, 51)), (.45, (42, 15, 74)), (.72, (107, 30, 110)), (.88, (194, 59, 118)), (1, (255, 138, 91))])
    im = Image.fromarray(np.repeat(g[:, None, :], W, axis=1).astype(np.uint8)).convert('RGBA')
    im.alpha_composite(SUN, (W // 2 - 210, H - 300))
    d = ImageDraw.Draw(im); d.rectangle([0, H - 110, W, H], fill=(30, 11, 61, 255)); d.rectangle([0, H - 114, W, H - 110], fill=TEAL + (255,))
    pl = make_palm(560); pr = make_palm(440, True)
    im.alpha_composite(pl, (-70, H - pl.height + 40)); im.alpha_composite(pr, (W - pr.width + 60, H - pr.height + 60))
    return im

def header(im, n, total):
    a, pad, ox, oy = text_layer('GTASTUCE', F('arch', 38), WHITE, shadow=[(3, 3, PINK)])
    im.alpha_composite(a, (80 - pad, 70 - pad))
    b, pad2, _, _ = text_layer('Vice', F('yt', 60), PINK2, glow=PINK)
    im.alpha_composite(b, (80 - pad + a.width - 2 * pad + 14, 70 - pad2 - 14))
    ImageDraw.Draw(im).text((W - 80, 75), f'{n} / {total}', font=F('inter', 30), fill=WHITE + (255,), anchor='ra')

def wrap(text, fnt, maxw):
    words = text.split(); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if fnt.getbbox(t)[2] <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def lines_draw(im, lines, fnt, x, y, fill, lh, shadow=None):
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        if shadow: d.text((x + shadow[0], y + i * lh + shadow[1]), l, font=fnt, fill=shadow[2] + (255,))
        d.text((x, y + i * lh), l, font=fnt, fill=fill + (255,))
    return y + len(lines) * lh

def fit(lines, maxw, start):
    s = start
    while s > 40 and any(F('arch', s).getbbox(l)[2] > maxw for l in lines): s -= 4
    return F('arch', s), s

def illu_fit(path, w, h):
    ill = Image.open(path).convert('RGB')
    a = np.array(ill).astype(int); bgc = a[ill.height // 2, 2]
    col = (np.abs(a - bgc).sum(2) > 25).mean(0) > 0.2; xs = np.where(col)[0]
    if len(xs) and xs[-1] - xs[0] > ill.width * 0.5: ill = ill.crop((xs[0], 0, xs[-1] + 1, ill.height))
    s = max(w / ill.width, h / ill.height); ill = ill.resize((int(ill.width * s) + 1, int(ill.height * s) + 1), Image.LANCZOS)
    l = (ill.width - w) // 2; t = (ill.height - h) // 2
    return ill.crop((l, t, l + w, t + h)).convert('RGBA')

def credit(im, txt):
    if not txt: return
    f = F('inter', 22); ImageDraw.Draw(im).text((W - 30, H - 34), txt, font=f, fill=(255, 255, 255, 200), anchor='ra')

def cover(spec, total):
    if spec.get('image'):
        im = illu_fit(spec['image'], W, H)
        a = np.concatenate([np.full(560, 200), np.linspace(200, 40, 420), np.full(H - 980, 40)])
        g = np.zeros((H, W, 4), np.uint8); g[..., :3] = (14, 6, 34); g[..., 3] = a[:, None].astype(np.uint8)
        im.alpha_composite(Image.fromarray(g)); top = 200; chip_y = 1200
    else:
        im = background(); top = 260; chip_y = None
    header(im, 1, total)
    allr = spec.get('lines', []) + [spec.get('highlight', '')] + spec.get('after', [])
    f, s = fit([l for l in allr if l], 920, 118); lh = int(s * 1.04)
    y = lines_draw(im, spec.get('lines', []), f, 80, top, WHITE, lh, (6, 6, NIGHT))
    if spec.get('highlight'):
        d = ImageDraw.Draw(im); d.text((86, y + 6), spec['highlight'], font=f, fill=PINK + (255,)); d.text((80, y), spec['highlight'], font=f, fill=YEL + (255,)); y += lh
    y = lines_draw(im, spec.get('after', []), f, 80, y, WHITE, lh, (6, 6, NIGHT))
    im.alpha_composite(chip('GLISSE →', PINK, NIGHT, 40), (80, chip_y or min(y + 50, 900)))
    credit(im, spec.get('credit'))
    return im

def tip(i, t, total):
    if t.get('image'):
        im = background(); im.alpha_composite(Image.new('RGBA', (W, H), (14, 6, 34, 150)))
        ih = 640; ill = illu_fit(t['image'], W, ih)
        m = np.ones((ih, W), np.float32); m[ih - 200:] = np.linspace(1, 0, 200)[:, None]
        ill.putalpha(Image.fromarray((m * 255).astype(np.uint8))); im.alpha_composite(ill, (0, 0))
        g = np.zeros((220, W, 4), np.uint8); g[..., :3] = (14, 6, 34); g[..., 3] = np.linspace(170, 0, 220)[:, None].astype(np.uint8)
        im.alpha_composite(Image.fromarray(g), (0, 0)); header(im, i + 2, total)
        d = ImageDraw.Draw(im); num = f'{i + 1:02d}'; fn = F('arch', 130); y0 = 560
        d.text((86, y0 + 6), num, font=fn, fill=PINK + (255,)); d.text((80, y0), num, font=fn, fill=YEL + (255,))
        ft = F('arch', 70); y = lines_draw(im, wrap(t['title'].upper(), ft, 920), ft, 80, y0 + 150, WHITE, 80, (5, 5, NIGHT))
        fb = F('inter', 42); lines_draw(im, wrap(t['body'], fb, 920)[:4], fb, 80, y + 30, (242, 236, 255), 56, (2, 2, NIGHT))
        credit(im, t.get('credit'))
        return im
    im = background(); header(im, i + 2, total); d = ImageDraw.Draw(im)
    num = f'{i + 1:02d}'; fn = F('arch', 200)
    d.text((88, 208), num, font=fn, fill=PINK + (255,)); d.text((80, 200), num, font=fn, fill=YEL + (255,))
    ft = F('arch', 76); y = lines_draw(im, wrap(t['title'].upper(), ft, 920), ft, 80, 470, WHITE, 86, (5, 5, NIGHT))
    fb = F('inter', 44); lines_draw(im, wrap(t['body'], fb, 900)[:6], fb, 80, y + 40, (242, 236, 255), 60, (2, 2, NIGHT))
    return im

def end(spec, total):
    im = background(); header(im, total, total)
    f, s = fit(spec.get('title', ['ENREGISTRE', 'CE POST']), 920, 100)
    y = lines_draw(im, spec.get('title', ['ENREGISTRE', 'CE POST']), f, 80, 260, WHITE, int(s * 1.08), (6, 6, NIGHT))
    fb = F('inter', 46); y = lines_draw(im, wrap(spec.get('body', 'Une astuce, un tuto ou un secret de GTA 6 chaque jour.'), fb, 900), fb, 80, y + 40, (242, 236, 255), 62, (2, 2, NIGHT))
    im.alpha_composite(chip('ABONNE-TOI', PINK, NIGHT, 52), (80, y + 50))
    im.alpha_composite(chip('@gtastucevice', NIGHT, WHITE, 40), (80, y + 180))
    return im

def main(spec_path, out):
    spec = json.load(open(spec_path, encoding='utf-8')); os.makedirs(out, exist_ok=True)
    tips = spec['tips'][:5]; total = len(tips) + 2
    slides = [cover(spec['cover'], total)] + [tip(i, t, total) for i, t in enumerate(tips)] + [end(spec.get('end', {}), total)]
    paths = []
    for n, s in enumerate(slides, 1):
        p = os.path.join(out, f"{spec['slug']}_{n}.jpg"); s.convert('RGB').save(p, quality=92); paths.append(p)
    print('\n'.join(paths))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
