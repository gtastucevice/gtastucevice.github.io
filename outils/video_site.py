#!/usr/bin/env python3
"""Vidéo verticale « élément du site » pour GTASTUCE VICE.

Usage : python3 outils/video_site.py spec.json
Le spec décrit l'accroche, les plans (pages du site filmées dans un téléphone) et la fin.
Sortie : assets/videos/<slug>.mp4 (+ .jpg de couverture). Musique synthwave générée (libre de droits).

Exemple de spec :
{
 "slug": "2026-11-21-secret-bigfoot",
 "hook": {"lines": [["CE SECRET", "w"], ["EST DANS", "w"], ["GTA 6", "y"]], "image": "assets/rs_grassrivers_pilotis.jpg"},
 "shots": [
   {"page": "gta-6-easter-eggs.html", "from": ".map", "to": 120, "caption": [["BIGFOOT", "w"], ["À GRASSRIVERS", "y"]], "bars": 2, "pins": true, "sub": "Dans les marais, au bord des routes"},
   {"search": "bigfoot", "caption": [["TOUT EST", "w"], ["SUR LE SITE", "y"]], "bars": 1.5}
 ],
 "outro": {"line": "Abonne-toi : une astuce GTA 6 par jour"}
}
"from"/"to" : nombre de pixels CSS, ou sélecteur CSS (to = nombre = décalage depuis from).
"""
import asyncio, json, math, os, subprocess, sys, threading, http.server, socketserver, functools, hashlib
import numpy as np
from scipy.signal import lfilter, butter
from scipy.io import wavfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "outils", "fonts") + "/"
TMP = "/tmp/gtv_video"; os.makedirs(TMP, exist_ok=True)
SFX = os.path.join(ROOT, "outils", "sfx")
W, H, FPS = 1080, 1920, 30
BPM = 112; BEAT = 60 / BPM; BAR = 4 * BEAT
NIGHT=(23,10,51); PINK=(255,61,127); PINK2=(255,95,162); YEL=(255,228,92); TEAL=(46,230,214); WHITE=(255,255,255)
COL = {"w": WHITE, "y": YEL, "t": TEAL, "p": PINK2}
CHROME = "/usr/bin/google-chrome"
fnt = lambda n, s: ImageFont.truetype(FONTS + n, s)
ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, t)))

# ---------- serveur local ----------
def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    h.log_message = lambda *a: None
    s = socketserver.TCPServer(("127.0.0.1", 0), h); threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, s.server_address[1]

# ---------- captures ----------
async def capture(spec, port):
    out = []
    async with async_playwright() as p:
        kw = {"args": ["--no-sandbox"]}
        if os.path.exists(CHROME): kw["executable_path"] = CHROME
        b = await p.chromium.launch(**kw)
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = await ctx.new_page()
        for i, sh in enumerate(spec["shots"]):
            if "search" in sh:
                frames = []
                q = sh["search"]
                for k in range(len(q) + 1):
                    await pg.goto(f"http://127.0.0.1:{port}/recherche.html" + (f"?q={q[:k]}" if k else "")); await pg.wait_for_timeout(500)
                    f = f"{TMP}/s{i}_{k}.png"; await pg.screenshot(path=f); frames.append(f)
                out.append({"type": "search", "frames": frames}); continue
            await pg.goto(f"http://127.0.0.1:{port}/" + sh.get("page", "")); await pg.wait_for_timeout(1200)
            await pg.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
            hgt = await pg.evaluate("document.body.scrollHeight")
            for y in range(0, hgt, 500):
                await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(50)
            await pg.add_style_tag(content=".ticker .track{animation:none!important}.map .pin .halo{display:none!important}header{position:static!important}.eggs.short .egg{display:flex!important}.more-eggs{display:none!important}")
            await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(700)
            async def ypos(v, base=0):
                if isinstance(v, str):
                    return await pg.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(v)});return e?e.getBoundingClientRect().top+scrollY:0}})()")
                return base + v
            y0 = await ypos(sh.get("from", 0)) - sh.get("pad", 40 if isinstance(sh.get("from"), str) else 0)
            y1 = await ypos(sh.get("to", 300), y0)
            pins = await pg.evaluate("[...document.querySelectorAll('.map .pin .dot')].map(c=>{const r=c.getBoundingClientRect();return [r.left+r.width/2,r.top+scrollY+r.height/2,r.width/2]})") if sh.get("pins") else []
            f = f"{TMP}/p{i}.png"; await pg.screenshot(path=f, full_page=True)
            out.append({"type": "page", "file": f, "y0": max(0, y0), "y1": max(0, y1), "pins": pins})
        await b.close()
    return out

# ---------- musique ----------
def music(path, dur, seed):
    SR = 44100; N = int(SR * (dur + 1)); mix = np.zeros((N, 2)); rng = np.random.default_rng(seed)
    progs = [([[57,60,64],[53,57,60],[48,52,55],[55,59,62]],[45,41,48,43]),
             ([[57,60,64],[55,59,62],[53,57,60],[52,56,59]],[45,43,41,40]),
             ([[50,53,57],[46,50,53],[48,52,55],[45,48,52]],[38,34,36,33])]
    chords, roots = progs[seed % len(progs)]
    def env(n, a, d, s, r):
        e = np.ones(n) * s; A, D, R = int(a*SR), int(d*SR), int(r*SR)
        e[:A] = np.linspace(0, 1, A); e[A:A+D] = np.linspace(1, s, len(e[A:A+D]))
        if R and n > R: e[-R:] *= np.linspace(1, 0, R)
        return e
    def lp(x, fc): b, a = butter(2, min(fc/(SR/2), .99)); return lfilter(b, a, x)
    def hp(x, fc): b, a = butter(2, fc/(SR/2), 'high'); return lfilter(b, a, x)
    def saw(f, n, det=0):
        t = np.arange(n)/SR; ds = [0] if not det else [-det, 0, det]
        return sum(2*((t*f*(1+d)) % 1)-1 for d in ds)/len(ds)
    sq = lambda f, n: np.sign(np.sin(2*np.pi*f*np.arange(n)/SR))
    nf = lambda m: 440*2**((m-69)/12)
    def add(sig, st, pan=0, g=1):
        i = int(st*SR)
        if i >= N: return
        j = min(N, i+len(sig)); s = sig[:j-i]*g
        mix[i:j, 0] += s*(1-max(0, pan)); mix[i:j, 1] += s*(1+min(0, pan))
    for b in range(int(dur/BAR)+2):
        t0 = b*BAR; c = chords[b % 4]; r = roots[b % 4]
        n = int(BAR*SR); add(lp(sum(saw(nf(m), n, .004) for m in c)/3, 1800)*env(n, .25, .3, .8, .25), t0, 0, .22)
        for k in range(8):
            n = int(BEAT/2*SR); add(lp(saw(nf(r-12), n), 600)*env(n, .003, .12, .5, .03), t0+k*BEAT/2, 0, .38)
        if b >= 1:
            notes = [c[0]+12, c[1]+12, c[2]+12, c[1]+24]
            for k in range(16):
                n = int(BEAT/4*SR); add(lp(sq(nf(notes[k % 4]), n), 3200)*env(n, .002, .08, .2, .02), t0+k*BEAT/4, .35 if k % 2 else -.35, .09)
        for k in range(4):
            tb = t0+k*BEAT; n = int(.35*SR); tt = np.arange(n)/SR
            add(np.sin(2*np.pi*np.cumsum(50+90*np.exp(-tt*30))/SR)*np.exp(-tt*9), tb, 0, .85)
            if k in (1, 3) and b >= 1:
                n = int(.45*SR); tt = np.arange(n)/SR
                add(hp(rng.standard_normal(n), 900)*np.exp(-tt*7)*.5+np.sin(2*np.pi*190*tt)*np.exp(-tt*25)*.5, tb, 0, .42)
            if b >= 1:
                for h in range(2):
                    n = int(.06*SR); add(hp(rng.standard_normal(n), 7000)*np.exp(-np.arange(n)/SR*60), tb+h*BEAT/2, .2, .12)
    mix = mix/np.max(np.abs(mix))*.9
    wavfile.write(path, SR, (mix*32767).astype(np.int16))

# ---------- effets sonores (outils/sfx, libres de droits) ----------
def add_sfx(wav, events):
    """events : liste de (nom_fichier, t_debut_s, gain). Mixe dans wav (en place)."""
    sr, mix = wavfile.read(wav); mix = mix.astype(np.float64) / 32767
    for name, t0, g in events:
        p = os.path.join(SFX, name)
        if not os.path.exists(p): continue
        r, x = wavfile.read(p); x = x.astype(np.float64)
        x = x / (32767 if x.dtype != np.float64 or np.abs(x).max() > 1.5 else 1)
        if x.ndim == 1: x = np.stack([x, x], 1)
        i = int(t0 * sr)
        if i < 0: x = x[-i:]; i = 0
        j = min(len(mix), i + len(x)); mix[i:j] += x[:j - i] * g
    mix = mix / max(1.0, np.abs(mix).max() / 0.95)
    wavfile.write(wav, sr, (mix * 32767).astype(np.int16))

# ---------- rendu ----------
def synth_bg():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H): d.line([(0, y), (W, y)], fill=tuple(int(a+(b-a)*y/H) for a, b in zip((23,10,51), (90,24,100))))
    sun = Image.new("RGBA", (W, H), (0,0,0,0)); sd = ImageDraw.Draw(sun); cx, cy, r = 540, 1300, 360
    for y in range(cy-r, cy+r):
        t = (y-(cy-r))/(2*r); dx = int(math.sqrt(max(0, r*r-(y-cy)**2)))
        sd.line([(cx-dx, y), (cx+dx, y)], fill=tuple(int(a+(b-a)*t) for a, b in zip((255,228,92), (255,61,127)))+(255,))
    for i, yy in enumerate(range(cy+10, cy+r, 40)): sd.rectangle([0, yy, W, yy+8+i*3], fill=(0,0,0,0))
    g = sun.filter(ImageFilter.GaussianBlur(40)); im.paste(g, (0,0), g); im.paste(sun, (0,0), sun)
    d = ImageDraw.Draw(im); hor = 1480; d.rectangle([0, hor, W, H], fill=(30,11,61))
    for k in range(9): y = hor+int((k/8)**2*(H-hor)); d.line([(0, y), (W, y)], fill=PINK2, width=3)
    for k in range(-8, 9): d.line([(540+k*40, hor), (540+k*260, H)], fill=PINK2, width=3)
    return im

def render(spec, caps, out_mp4):
    BG = synth_bg()
    def ctext(d, y, txt, f, fill, shadow=PINK, off=7):
        w = d.textlength(txt, font=f); x = (W-w)/2
        if shadow: d.text((x+off, y+off), txt, font=f, fill=shadow)
        d.text((x, y), txt, font=f, fill=fill)
    def fit(d, txt, size, maxw=1000):
        while size > 40 and d.textlength(txt, font=fnt("ArchivoBlack.ttf", size)) > maxw: size -= 4
        return size
    def logo(im, y, sc=1.0):
        d = ImageDraw.Draw(im); f1 = fnt("ArchivoBlack.ttf", int(78*sc)); f2 = fnt("Yellowtail.ttf", int(110*sc))
        w1 = d.textlength("GTASTUCE", font=f1); w2 = d.textlength("Vice", font=f2); x = (W-w1-w2-20*sc)/2
        d.text((x+5, y+5), "GTASTUCE", font=f1, fill=PINK); d.text((x, y), "GTASTUCE", font=f1, fill=WHITE)
        g = Image.new("RGBA", (W, H), (0,0,0,0)); ImageDraw.Draw(g).text((x+w1+20*sc, y-int(28*sc)), "Vice", font=f2, fill=PINK)
        g = g.filter(ImageFilter.GaussianBlur(10)); im.paste(g, (0,0), g)
        d.text((x+w1+20*sc, y-int(28*sc)), "Vice", font=f2, fill=PINK2)
    pulse = lambda ta: 1+0.05*math.exp(-((ta/BEAT) % 1)*8)
    def caption(im, lines, ta, tl, top=95, base=104):
        d = ImageDraw.Draw(im); y = top; s = pulse(ta); a = min(1, tl*6)
        for txt, c in lines:
            size = fit(d, txt, base); f = fnt("ArchivoBlack.ttf", int(size*s*(0.7+0.3*a)))
            ctext(d, y, txt, f, COL.get(c, WHITE)); y += int(size*1.12)
    def pill(im, txt, y):
        d = ImageDraw.Draw(im); f = fnt("Inter.ttf", 44); w = d.textlength(txt, font=f)
        d.rounded_rectangle([(W-w)/2-28, y, (W+w)/2+28, y+66], radius=33, fill=NIGHT); d.text(((W-w)/2, y+9), txt, font=f, fill=WHITE)
    SW, SH, PX, PY = 700, 1515, 190, 345; K = SW/780
    def rmask(sz, r):
        m = Image.new("L", sz, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sz[0]-1, sz[1]-1], radius=r, fill=255); return m
    FRAME = BG.copy(); fd = ImageDraw.Draw(FRAME)
    g = Image.new("RGBA", (W, H), (0,0,0,0)); ImageDraw.Draw(g).rounded_rectangle([PX-30, PY-30, PX+SW+30, PY+SH+30], radius=95, outline=PINK2+(255,), width=14)
    g = g.filter(ImageFilter.GaussianBlur(22)); FRAME.paste(g, (0,0), g)
    fd.rounded_rectangle([PX-22, PY-22, PX+SW+22, PY+SH+22], radius=88, fill=(12,6,26), outline=PINK2, width=4)
    MASK = rmask((SW, SH), 66)
    def phone(screen):
        im = FRAME.copy(); im.paste(screen.resize((SW, SH)), (PX, PY), MASK)
        ImageDraw.Draw(im).rounded_rectangle([PX+SW/2-90, PY+12, PX+SW/2+90, PY+46], radius=17, fill=(12,6,26)); return im
    segs = []
    hk = spec["hook"]; himg = Image.open(os.path.join(ROOT, hk.get("image", "assets/rs_vicecity_night.jpg"))).convert("RGB")
    def f_hook(t, ta):
        s = 1.12-0.08*t; w, h = himg.size; ch = h; cw = int(ch*W/H)
        if cw > w: cw = w; ch = int(cw*H/W)
        cw2, ch2 = int(cw/s), int(ch/s); x = (w-cw2)//2+int(30*t); y = (h-ch2)//2
        im = ImageEnhance.Brightness(himg.crop((x, y, x+cw2, y+ch2)).resize((W, H))).enhance(0.5)
        caption(im, hk["lines"], ta, t*3, top=640, base=130)
        ImageDraw.Draw(im).text((40, H-70), "Image : Rockstar Games", font=fnt("Inter.ttf", 30), fill=(220,210,240)); return im
    segs.append((hk.get("bars", 1)*BAR, f_hook))
    for sh, cp in zip(spec["shots"], caps):
        if cp["type"] == "search":
            frs = [Image.open(f).convert("RGB").crop((0, 0, 780, 1688)) for f in cp["frames"]]
            def f(t, ta, frs=frs, sh=sh):
                im = phone(frs[min(len(frs)-1, int(t*1.4*len(frs)))]); caption(im, sh["caption"], ta, t*4)
                if sh.get("sub"): pill(im, sh["sub"], 1835)
                return im
        else:
            full = Image.open(cp["file"]).convert("RGB")
            def f(t, ta, full=full, cp=cp, sh=sh):
                yc = cp["y0"]+ease(t)*(cp["y1"]-cp["y0"]); yc = max(0, min(full.size[1]/2-844, yc)); y = int(yc*2)
                im = phone(full.crop((0, y, 780, y+1688)))
                if cp["pins"]:
                    ov = Image.new("RGBA", (W, H), (0,0,0,0)); od = ImageDraw.Draw(ov)
                    for i, (px, py, r) in enumerate(cp["pins"]):
                        sx = PX+px*2*K; sy = PY+(py-yc)*2*K
                        if not (PY < sy < PY+SH): continue
                        ph = ((ta/BEAT)+i*0.2) % 1; rr = r*2*K*(1.6+3.2*ph)
                        od.ellipse([sx-rr, sy-rr, sx+rr, sy+rr], outline=YEL+(int(200*(1-ph)),), width=6)
                    im = im.convert("RGBA"); im.alpha_composite(ov); im = im.convert("RGB")
                caption(im, sh["caption"], ta, t*4)
                if sh.get("sub"): pill(im, sh["sub"], 1835)
                return im
        segs.append((sh.get("bars", 1.5)*BAR, f))
    ot = spec.get("outro", {})
    def f_out(t, ta):
        im = BG.copy(); logo(im, 250, 1.15); d = ImageDraw.Draw(im)
        ctext(d, 560, "gtastucevice.fr", fnt("ArchivoBlack.ttf", int(112*pulse(ta))), YEL)
        f2 = fnt("ArchivoBlack.ttf", 80); s = ot.get("cta", "LIEN EN BIO"); w = d.textlength(s, font=f2)
        d.rounded_rectangle([(W-w)/2-50, 740, (W+w)/2+50, 870], radius=65, fill=PINK); d.text(((W-w)/2, 755), s, font=f2, fill=NIGHT)
        s = ot.get("line", "Abonne-toi : une astuce GTA 6 par jour"); f3 = fnt("Inter.ttf", 50); w = d.textlength(s, font=f3)
        d.rounded_rectangle([(W-w)/2-34, 915, (W+w)/2+34, 1010], radius=46, fill=NIGHT); d.text(((W-w)/2, 932), s, font=f3, fill=WHITE)
        return im
    segs.append((ot.get("bars", 2.5)*BAR, f_out))
    total = sum(s for s, _ in segs)
    wav = f"{TMP}/music.wav"; music(wav, total, int(hashlib.md5(spec["slug"].encode()).hexdigest(), 16))
    cuts, t = [], 0.0
    for dur, _ in segs: cuts.append(t); t += dur
    ev = [("riser.wav", cuts[1] - 2.1, 0.55)]                       # montée vers la fin de l'accroche
    ev += [("swoosh1.wav", c - 0.12, 0.8) for c in cuts[1:-1]]       # swoosh à chaque changement de plan
    ev += [("swoosh2.wav", cuts[-1] - 0.25, 0.6)]                    # gros swoosh avant la fin
    for (dur, _), c, sh in zip(segs[1:-1], cuts[1:-1], spec["shots"]):
        if "search" in sh: ev.append(("typewriter.wav", c + 0.2, 0.35))  # frappe pendant la recherche
    add_sfx(wav, ev)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav, "-map", "0:v", "-map", "1:a", "-t", f"{total:.3f}", "-af", f"afade=t=out:st={total-1.2:.3f}:d=1.2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_mp4], stdin=subprocess.PIPE)
    t0 = 0.0
    for dur, fn in segs:
        n = round((t0+dur)*FPS)-round(t0*FPS)
        for k in range(n):
            fr = fn(k/max(1, n-1), (round(t0*FPS)+k)/FPS)
            if k < 3: fr = Image.blend(fr, Image.new("RGB", (W, H), WHITE), 0.35*(1-k/3))
            ff.stdin.write(fr.tobytes())
        t0 += dur
    ff.stdin.close(); ff.wait()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.9", "-i", out_mp4, "-frames:v", "1", "-q:v", "3", out_mp4[:-4]+".jpg"])
    return total

def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    srv, port = serve()
    caps = asyncio.run(capture(spec, port)); srv.shutdown()
    os.makedirs(os.path.join(ROOT, "assets", "videos"), exist_ok=True)
    out = os.path.join(ROOT, "assets", "videos", spec["slug"] + ".mp4")
    total = render(spec, caps, out)
    print(f"OK {out} ({total:.1f} s) -> https://gtastucevice.fr/assets/videos/{spec['slug']}.mp4")

if __name__ == "__main__":
    main()
