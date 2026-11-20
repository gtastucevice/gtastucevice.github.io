#!/usr/bin/env python3
"""Captures en jeu GTA 6 (PS5) -> images prêtes pour le site.

Deux étapes :

1) TRIER : python3 outils/captures.py trier <dossier_source> [--sortie /tmp/gtv_captures] [--par-video 24]
   - Photos PS5 (.png/.jpg/.jpeg/.webp) : reprises telles quelles.
   - Vidéos de gameplay (.mp4/.webm/.mov/.mkv) : extraction d'images aux changements de plan
     + 1 image toutes les 4 s, on jette les images floues et les doublons, on garde les plus nettes.
   Sortie : <sortie>/cand_XXX.jpg (1600 px) + <sortie>/planche_N.jpg (planche contact numérotée)
   + <sortie>/index.json (numéro -> fichier source, instant dans la vidéo).

2) PUBLIER : python3 outils/captures.py publier <cand_ou_fichier> <nom-slug> [--recadrer x,y,l,h]
   -> assets/captures/<nom-slug>.jpg (1280 px, JPG q82, sans métadonnées).
   --recadrer en fractions de l'image (ex : 0,0.55,0.45,0.45 = coin bas gauche, la mini-carte).
   Ensuite : référencer l'image dans articles.json ({"capture": ..., "legende": ...}) ou secrets.json ("capture")
   puis python3 build.py (les miniatures 480/800 sont faites par build.py).

Règles (voir le skill images-gtastuce) : uniquement nos propres captures (Roméo ou son pote),
jamais de cinématique d'histoire (spoilers), jamais de capture d'un autre créateur.
Crédit par défaut affiché sur le site : « Capture en jeu : GTASTUCE VICE ».
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO = (".png", ".jpg", ".jpeg", ".webp")
VIDEO = (".mp4", ".webm", ".mov", ".mkv")


def nettete(im):
    g = ImageOps.grayscale(im.resize((480, int(480 * im.height / im.width))))
    return ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).var[0]


def empreinte(im):
    g = ImageOps.grayscale(im.resize((9, 8)))
    p = list(g.tobytes())
    return sum(1 << i for i in range(64) if p[(i // 8) * 9 + i % 8] > p[(i // 8) * 9 + i % 8 + 1])


def ecart(a, b):
    return bin(a ^ b).count("1")


def duree(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True, check=True).stdout
        return float(out.strip())
    except Exception:
        return 0.0


def images_video(path, tmp):
    """Images aux changements de plan + une toutes les 4 s ; renvoie [(fichier, secondes)]."""
    d = os.path.join(tmp, os.path.basename(path) + "_f")
    os.makedirs(d, exist_ok=True)
    vf = "select='gt(scene,0.30)+not(mod(t\\,4))*lt(mod(t\\,4)\\,0.04)',scale=1600:-2"
    # -vsync vfr + showinfo pour retrouver l'instant de chaque image
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostdin", "-i", path, "-vf", vf + ",showinfo", "-vsync", "vfr",
                        "-q:v", "3", os.path.join(d, "f_%05d.jpg")], capture_output=True, text=True)
    temps = [float(l.split("pts_time:")[1].split()[0]) for l in r.stderr.splitlines() if "pts_time:" in l]
    files = sorted(os.listdir(d))
    return [(os.path.join(d, f), temps[i] if i < len(temps) else None) for i, f in enumerate(files)]


def planches(cands, sortie):
    try:
        font = ImageFont.truetype(os.path.join(ROOT, "outils", "fonts", os.listdir(os.path.join(ROOT, "outils", "fonts"))[0]), 34)
    except Exception:
        font = ImageFont.load_default()
    W, H, C = 400, 225, 4
    out = []
    for p in range(0, len(cands), 24):
        lot = cands[p:p + 24]
        rows = (len(lot) + C - 1) // C
        sheet = Image.new("RGB", (W * C, H * rows), (23, 10, 51))
        dr = ImageDraw.Draw(sheet)
        for i, c in enumerate(lot):
            im = Image.open(c["fichier"]).convert("RGB")
            im = ImageOps.fit(im, (W - 6, H - 6))
            x, y = (i % C) * W + 3, (i // C) * H + 3
            sheet.paste(im, (x, y))
            dr.rectangle([x, y, x + 64, y + 44], fill=(255, 61, 127))
            dr.text((x + 8, y + 2), str(c["n"]), fill=(23, 10, 51), font=font)
        f = os.path.join(sortie, f"planche_{p // 24 + 1}.jpg")
        sheet.save(f, quality=80)
        out.append(f)
    return out


def trier(src, sortie, par_video):
    os.makedirs(sortie, exist_ok=True)
    fichiers = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(src) for f in fs if not f.startswith("."))
    cands, vus = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for f in fichiers:
            ext = os.path.splitext(f)[1].lower()
            if ext in PHOTO:
                lot = [(f, None)]
                garder = len(lot)
            elif ext in VIDEO:
                lot = images_video(f, tmp)
                garder = par_video
                print(f"{os.path.basename(f)} : {len(lot)} images extraites ({duree(f):.0f} s)")
            else:
                continue
            notes = []
            for img, t in lot:
                try:
                    im = Image.open(img).convert("RGB")
                except Exception:
                    continue
                notes.append((nettete(im), img, t, empreinte(im)))
            if ext in VIDEO and notes:
                seuil = sorted(n[0] for n in notes)[len(notes) // 4]  # on jette le quart le plus flou
                notes = [n for n in notes if n[0] >= seuil]
                notes.sort(key=lambda n: n[0], reverse=True)
            pris = 0
            for score, img, t, h in notes:
                if pris >= garder:
                    break
                if ext in VIDEO and any(ecart(h, v) <= 6 for v in vus):
                    continue  # quasi doublon
                vus.append(h)
                n = len(cands) + 1
                dst = os.path.join(sortie, f"cand_{n:03d}.jpg")
                im = Image.open(img).convert("RGB")
                if im.width > 1600:
                    im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
                im.save(dst, quality=88)
                cands.append({"n": n, "fichier": dst, "source": os.path.basename(f),
                              "instant": None if t is None else f"{int(t // 60)}:{int(t % 60):02d}"})
                pris += 1
        cands.sort(key=lambda c: c["n"])
    pl = planches(cands, sortie)
    json.dump(cands, open(os.path.join(sortie, "index.json"), "w"), ensure_ascii=False, indent=1)
    print(f"{len(cands)} candidates dans {sortie} ; planches : {', '.join(os.path.basename(p) for p in pl)}")


def publier(src, nom, recadrer=None):
    assert all(c.isalnum() or c == "-" for c in nom) and nom == nom.lower(), "nom-slug : minuscules, chiffres et tirets"
    if src.isdigit():
        src = os.path.join("/tmp/gtv_captures", f"cand_{int(src):03d}.jpg")
    im = Image.open(src).convert("RGB")
    if recadrer:
        x, y, w, h = (float(v) for v in recadrer.split(","))
        im = im.crop((round(x * im.width), round(y * im.height), round((x + w) * im.width), round((y + h) * im.height)))
    if im.width > 1280:
        im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
    os.makedirs(os.path.join(ROOT, "assets", "captures"), exist_ok=True)
    dst = os.path.join(ROOT, "assets", "captures", nom + ".jpg")
    im.save(dst, quality=82, optimize=True, progressive=True)  # Pillow ne recopie pas l'EXIF : métadonnées retirées
    print(f"assets/captures/{nom}.jpg ({im.width}x{im.height}, {os.path.getsize(dst) // 1024} Ko)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "trier":
        sortie = a[a.index("--sortie") + 1] if "--sortie" in a else "/tmp/gtv_captures"
        pv = int(a[a.index("--par-video") + 1]) if "--par-video" in a else 24
        trier(a[1], sortie, pv)
    elif len(a) >= 3 and a[0] == "publier":
        publier(a[1], a[2], a[a.index("--recadrer") + 1] if "--recadrer" in a else None)
    else:
        print(__doc__)
        sys.exit(1)
