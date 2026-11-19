#!/usr/bin/env python3
"""Génère une vraie page HTML par article (dossier actus/) + sitemap.xml + robots.txt.

Usage : python3 build.py   (à lancer après chaque modification de articles.json)
La mise en forme reprend les styles de actus.html : une seule source de style.
"""
import html, json, os, re
from datetime import datetime, timezone

BASE = "https://gtastucevice.fr"
ROOT = os.path.dirname(os.path.abspath(__file__))
CATS = {"actu": "Actu", "test": "Tests", "astuce": "Astuces", "secret": "Secrets", "drama": "Drama", "guide": "Guides"}
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

e = lambda s: html.escape(str(s), quote=True)


def fr_date(iso):
    d = datetime.fromisoformat(iso)
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def styles():
    src = open(os.path.join(ROOT, "actus.html"), encoding="utf-8").read()
    return "\n".join(re.findall(r"<style>.*?</style>", src, re.S))


HEADER = """<header>
<div class="wrap">
<a class="brand" href="../index.html" aria-label="GTASTUCE VICE, accueil"><b>GTASTUCE</b><i>Vice</i></a>
<nav aria-label="Navigation principale">
<a class="nav-search" href="../recherche.html" aria-label="Rechercher"><svg class="ico" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.6"/><path d="M15.5 15.5L21 21" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg><span>Rechercher</span></a>
<a href="../actus.html">Actus</a>
<a href="../index.html#guides">Guides</a>
<a href="../index.html#chasse">Chasse aux secrets</a>
<a href="../matos.html">Le matos</a>
<a class="btn" href="../index.html#newsletter">Newsletter</a>
</nav>
</div>
</header>"""

FOOTER = """<footer>
<div class="wrap">
<div>
<a class="brand" href="../index.html"><b>GTASTUCE</b><i>Vice</i></a>
<small>Site de fans non officiel. Non affilié à Rockstar Games ni à Take-Two Interactive. Grand Theft Auto et les éléments associés sont des marques de Take-Two Interactive.</small>
</div>
<nav aria-label="Liens légaux">
<a href="../a-propos.html">Qui sommes-nous</a>
<a href="../index.html#newsletter">Contact</a>
</nav>
</div>
</footer>"""

EXTRA_CSS = """<style>
.related{margin-top:40px}
.related h2{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:24px;margin:0 0 14px}
.c-guide{background:#B9A7FF}
.cta{margin-top:28px;padding:20px;border-radius:16px;background:linear-gradient(135deg,#2A0F4A,#6B1E6E);border:1px solid var(--line)}
.cta p{margin:0 0 12px;font-size:16px}
</style>"""


def page(a, arts, css):
    url = f"{BASE}/actus/{a['slug']}.html"
    img_abs = f"{BASE}/{a['img']}"
    cat = CATS.get(a["cat"], a["cat"])
    body = "".join(f"<p>{e(p)}</p>" for p in a["body"])
    srcs = "".join(f'<li><a href="{e(s["u"])}" target="_blank" rel="noopener">{e(s["t"])}</a></li>' for s in a["sources"])
    rel = [x for x in arts if x["slug"] != a["slug"] and x["cat"] == a["cat"]][:3]
    rel += [x for x in arts if x["slug"] != a["slug"] and x not in rel][: 3 - len(rel)]
    rel_html = "".join(
        f'<a class="post" href="{e(x["slug"])}.html"><img src="../{e(x["img"])}" alt="" loading="lazy"><div class="b"><div class="meta"><span class="cat c-{e(x["cat"])}">{e(CATS.get(x["cat"], x["cat"]))}</span><span>{fr_date(x["date"])}</span></div><h2>{e(x["title"])}</h2></div></a>'
        for x in rel)
    if a["cat"] == "secret":
        cta = '<div class="cta"><p><strong>Tu l\'as trouvé ?</strong> Coche-le dans la chasse aux secrets et monte en grade.</p><a class="btn" href="../index.html#chasse">La chasse aux secrets</a></div>'
    else:
        cta = '<div class="cta"><p><strong>Une astuce GTA 6 par jour</strong>, en français et sans spoiler.</p><a class="btn" href="https://www.tiktok.com/@gtastucevice" target="_blank" rel="noopener">Suis-nous sur TikTok</a></div>'
    ld = {
        "@context": "https://schema.org",
        "@type": "Article" if a["cat"] == "guide" else "NewsArticle",
        "headline": a["title"][:110],
        "description": a["chapo"],
        "image": [img_abs],
        "datePublished": a["date"],
        "dateModified": a.get("updated", a["date"]),
        "inLanguage": "fr-FR",
        "mainEntityOfPage": url,
        "author": {"@type": "Organization", "name": "GTASTUCE VICE", "url": BASE},
        "publisher": {"@type": "Organization", "name": "GTASTUCE VICE", "url": BASE},
    }
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(a['title'])} – GTASTUCE VICE</title>
<meta name="description" content="{e(a['chapo'])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(a['title'])}">
<meta property="og:description" content="{e(a['chapo'])}">
<meta property="og:image" content="{img_abs}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="GTASTUCE VICE">
<meta property="og:image:alt" content="{e(a['title'])}">
<meta name="twitter:card" content="summary_large_image">
{ICONS}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Yellowtail&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
{css}
{EXTRA_CSS}
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
{HEADER}
<main class="page"><div class="wrap">
<article class="full">
<a class="back" href="../actus.html">← Toutes les actus</a>
<div class="meta"><span class="cat c-{e(a['cat'])}">{e(cat)}</span><time datetime="{e(a['date'])}">{fr_date(a['date'])}</time></div>
<h1>{e(a['title'])}</h1>
<p class="chapo">{e(a['chapo'])}</p>
<img src="../{e(a['img'])}" alt="" style="margin-bottom:6px">
<p style="font-size:13px;color:#8F84B8;margin:0 0 22px">{e(a.get('credit', ''))}</p>
{body}
<div class="srcs"><h3>Sources</h3><ul>{srcs}</ul></div>
{cta}
</article>
<section class="related" aria-label="À lire aussi"><h2>À lire aussi</h2><div class="feed">{rel_html}</div></section>
</div></main>
{FOOTER}
</body>
</html>
"""


ICONS = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#170A33">
<meta name="robots" content="max-image-preview:large">"""

SHARE_IMG = f"{BASE}/assets/partage.jpg"


def head_block(path, title, desc, image=None, kind="website"):
    """Bloc <head> commun : icônes + aperçu de partage (Open Graph / Twitter)."""
    image = image or SHARE_IMG
    url = f"{BASE}/{path}" if path else f"{BASE}/"
    return f"""
<link rel="canonical" href="{url}">
{ICONS}
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="GTASTUCE VICE">
<meta property="og:locale" content="fr_FR">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
"""


def fill(src, key, html_):
    """Remplace le contenu entre <!--S:key--> et <!--E:key-->."""
    pat = re.compile(r"<!--S:%s-->.*?<!--E:%s-->" % (key, key), re.S)
    assert pat.search(src), key
    return pat.sub(lambda m: f"<!--S:{key}-->{html_}<!--E:{key}-->", src)


def meta_html(a):
    return f'<div class="meta"><span class="cat c-{e(a["cat"])}">{e(CATS.get(a["cat"], a["cat"]))}</span><span>{fr_date(a["date"])}</span></div>'


def post_card(a, prefix="", h="h3"):
    return (f'<a class="post" href="{prefix}actus/{e(a["slug"])}.html"><img src="{prefix}{e(a["img"])}" alt="" loading="lazy">'
            f'<div class="b">{meta_html(a)}<{h}>{e(a["title"])}</{h}><p>{e(a["chapo"])}</p></div></a>')


# Pages « sujet » : chacune regroupe automatiquement les articles qui en parlent.
HUBS = [
    {"slug": "gta-6-argent", "nav": "Argent", "title": "GTA 6 argent : comment gagner de l'argent vite (sans glitch)",
     "h1": "Gagner de l'argent dans GTA 6", "desc": "Toutes nos astuces pour gagner de l'argent dans GTA 6 sans glitch : premières heures, braquages, plongées, voitures à revendre.",
     "intro": "Au début de GTA 6, l'argent est rare, c'est voulu. Ici on rassemble toutes nos astuces pour remplir ton compte proprement, sans glitch ni triche qui risquent de te faire bannir. La page se met à jour à chaque nouvel article.",
     "kw": ["argent", "cash", "braquage", "épave", "revend", "dollars", "fauché"]},
    {"slug": "gta-6-carte", "nav": "Carte & lieux", "title": "Carte de GTA 6 : Leonida, Vice City et tous les lieux",
     "h1": "La carte de GTA 6 : Leonida et Vice City", "desc": "Les régions de Leonida, les quartiers de Vice City et les lieux à ne pas rater dans GTA 6, mis à jour en continu.",
     "intro": "Leonida, c'est la Floride version Rockstar : Vice City, les Keys, les marais, la côte oubliée, la campagne et la montagne. Retrouve ici tous nos guides et articles sur la carte et les lieux à visiter.",
     "kw": ["carte", "région", "leonida", "keys", "grassrivers", "port gellhorn", "ambrosia", "kalaga", "washington island", "quartier"]},
    {"slug": "gta-6-easter-eggs", "nav": "Easter eggs", "title": "Easter eggs GTA 6 : tous les secrets trouvés",
     "h1": "Tous les easter eggs et secrets de GTA 6", "desc": "Bigfoot, l'œuf de Pâques, l'appartement de Dexter… tous les easter eggs de GTA 6 trouvés par les joueurs, avec où les trouver.",
     "intro": "Rockstar a caché des dizaines de clins d'œil dans Leonida. On liste ici ceux qui sont trouvés et relayés, avec leur statut (confirmé, rumeur, à tester) et où les chercher. Coche ceux que tu as trouvés dans la chasse aux secrets.",
     "kw": ["easter egg", "secret", "bigfoot", "clin d'œil", "dexter"], "cats": ["secret"], "eggs": True},
    {"slug": "gta-6-police", "nav": "Police", "title": "Police GTA 6 : étoiles, recherche et comment semer les flics",
     "h1": "La police dans GTA 6", "desc": "Comment marche le système de recherche de GTA 6 et comment semer la police : étoiles, icônes, zones chaudes.",
     "intro": "La police de GTA 6 a de la mémoire : elle retient ta tenue, ta voiture, ton arme. Tous nos conseils pour comprendre le système de recherche et semer les flics sont ici.",
     "kw": ["police", "flic", "étoile", "recherche"]},
    {"slug": "gta-6-debuter", "nav": "Bien débuter", "title": "Bien débuter GTA 6 : astuces, réglages et erreurs à éviter",
     "h1": "Bien débuter sur GTA 6", "desc": "Les astuces, réglages et réflexes à avoir pour bien démarrer GTA 6 sans spoiler.",
     "intro": "Tu lances GTA 6 pour la première fois ? Réglages, premiers réflexes, erreurs à éviter, spoilers à bloquer : tout ce qu'il faut savoir pour bien démarrer, sans rien te gâcher.",
     "kw": ["débuter", "démarrer", "réglage", "spoiler", "plant", "astuces pour"], "cats": ["astuce"]},
]


def hub_articles(h, arts):
    out = []
    for a in arts:
        txt = (a["title"] + " " + a["chapo"] + " " + " ".join(a["body"])).lower()
        if a["cat"] in h.get("cats", []) or any(k in txt for k in h["kw"]):
            out.append(a)
    return out


EGG_ST = {"confirme": "Confirmé", "rumeur": "Rumeur", "a-tester": "À tester"}


def egg_card(x):
    return (f'<div class="egg" id="egg-{e(x["id"])}"><div class="row" style="margin:0"><span class="st st-{e(x["status"])}">{EGG_ST.get(x["status"], x["status"])}</span></div>'
            f'<h3>{e(x["title"])}</h3><p><strong>Où :</strong> {e(x["where"])}</p><p>{e(x["how"])}</p>'
            f'<div class="row"><span></span><a class="src" href="{e(x["source"]["u"])}" target="_blank" rel="noopener">Source : {e(x["source"]["t"])}</a></div></div>')


SIMPLE_CSS = """<style>
:root{--night:#170A33;--night2:#221042;--line:#3A2366;--pink:#FF3D7F;--pink2:#FF5FA2;--teal:#2EE6D6;--yel:#FFE45C;--orange:#FF9A3D;--soft:#C9BFE8;--mute:#A99BD6;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--night);color:var(--white);font-family:Inter,system-ui,sans-serif;line-height:1.55}
a{color:var(--teal)}a:hover{color:var(--white)}img{display:block;max-width:100%}
.wrap{max-width:1100px;margin:0 auto;padding:0 20px}
.brand{display:flex;align-items:baseline;gap:8px;text-decoration:none;color:var(--white)}
.brand b{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:22px;text-shadow:2px 2px 0 var(--pink)}
.brand i{font-family:Yellowtail,cursive;font-style:normal;font-size:32px;color:var(--pink2);text-shadow:0 0 10px var(--pink)}
header{position:sticky;top:0;z-index:10;background:rgba(23,10,51,.94);backdrop-filter:blur(8px);border-bottom:1px solid #2E1A57}
header .wrap{max-width:1200px;display:flex;flex-wrap:wrap;gap:10px 24px;justify-content:space-between;align-items:center;padding-top:12px;padding-bottom:12px}
nav{display:flex;flex-wrap:wrap;gap:4px 18px;align-items:center;font-weight:700;font-size:15px}nav a{color:var(--white);text-decoration:none;padding:8px 0}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 20px;border-radius:12px;background:var(--pink);color:var(--night);font-family:'Archivo Black',sans-serif;font-size:15px;text-decoration:none}
nav .btn{min-height:38px;padding:0 16px;border-radius:999px;font-size:14px}
main{padding:36px 0 0}.kicker{font-size:12px;font-weight:700;letter-spacing:3px;color:var(--teal);text-transform:uppercase}
h1{margin:6px 0 12px;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:clamp(28px,4.4vw,46px);line-height:1.05}
h2{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:26px;margin:40px 0 14px}
.lead{color:var(--soft);font-size:18px;max-width:760px}
.feed{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px}
.post{display:flex;flex-direction:column;background:var(--night2);border:1px solid var(--line);border-radius:16px;overflow:hidden;color:var(--white);text-decoration:none}
.post:hover{border-color:var(--pink2);color:var(--white)}.post img{width:100%;aspect-ratio:16/9;object-fit:cover}
.post .b{padding:16px;display:flex;flex-direction:column;gap:8px}.post h3{margin:0;font-size:17px;line-height:1.3}.post p{margin:0;color:var(--soft);font-size:14px}
.meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--mute)}
.cat{color:var(--night);font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;text-transform:uppercase}
.c-actu{background:var(--teal)}.c-test{background:var(--yel)}.c-astuce{background:var(--orange)}.c-secret{background:var(--pink2)}.c-drama{background:#FF4D4D;color:#fff}.c-guide{background:#B9A7FF}
.eggs{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px}
.egg{display:flex;flex-direction:column;gap:8px;background:var(--night2);border:1px solid var(--line);border-radius:16px;padding:18px}.egg h3{margin:0;font-size:17px}.egg p{margin:0;font-size:14px;color:var(--soft)}
.egg .row{display:flex;justify-content:space-between;gap:10px;margin-top:4px}.src{font-size:13px}
.st{font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;text-transform:uppercase}.st-confirme{background:var(--teal);color:var(--night)}.st-rumeur{background:var(--orange);color:var(--night)}.st-a-tester{background:#5A3B8F;color:#fff}
.topics{display:flex;flex-wrap:wrap;gap:10px}
.map .pin{cursor:pointer}.topics a{min-height:44px;display:inline-flex;align-items:center;padding:0 18px;border-radius:999px;background:var(--night2);border:1px solid var(--line);color:var(--white);text-decoration:none;font-weight:700}
.box{background:var(--night2);border:1px solid var(--line);border-radius:20px;padding:26px;margin:18px 0}.box p,.box li{color:#F2ECFF}
footer{border-top:4px solid var(--teal);background:#12062A;padding:36px 0;margin-top:56px}footer small{display:block;max-width:640px;color:var(--mute);font-size:13px;margin-top:8px}
</style>"""

FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Yellowtail&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">"""


def topics_html(prefix=""):
    return "".join(f'<a href="{prefix}{h["slug"]}.html">{e(h["nav"])}</a>' for h in HUBS)


def simple_page(path, title, desc, h1, kicker, body, ld=None):
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{head_block(path, title, desc)}
{FONTS}
{SIMPLE_CSS}
<style>{MAP_CSS}{SEARCH_CSS}{MOBILE_CSS}</style>
{ldj}
</head>
<body>
{HEADER.replace('../', '')}
<main><div class="wrap">
<div class="kicker">{e(kicker)}</div>
<h1>{e(h1)}</h1>
{body}
<h2>Les autres sujets</h2>
<div class="topics">{topics_html()}</div>
</div></main>
{FOOTER.replace('../', '')}
</body>
</html>
"""


ABOUT_BODY = """<p class="lead">GTASTUCE VICE, c'est le fil français de GTA 6 : l'actu, les astuces, les guides et les secrets de Leonida, expliqués simplement, en français et sans spoiler.</p>
<div class="box"><h2 style="margin-top:0">Qui on est</h2>
<p>Un projet de joueurs passionnés, lancé pour la sortie de GTA 6. On joue sur PS5, on suit tout ce qui sort sur le jeu, et on le partage sur ce site et sur TikTok, Instagram et YouTube (@gtastucevice).</p></div>
<div class="box"><h2 style="margin-top:0">Comment on travaille</h2>
<ul>
<li><strong>On cite toujours nos sources.</strong> Chaque article se termine par la liste des médias d'où viennent les infos, pour que tu puisses vérifier.</li>
<li><strong>On te dit quand ce n'est pas sûr.</strong> Une info qui ne vient que de joueurs est marquée « rumeur » ou « à tester en jeu », un chiffre non officiel « estimation ».</li>
<li><strong>Zéro spoiler, zéro leak, zéro triche.</strong> Pas de fin d'histoire, pas de contenu volé, pas de glitch d'argent qui risque de te faire bannir.</li>
<li><strong>Transparence :</strong> nos articles sont rédigés avec l'aide d'outils d'intelligence artificielle, à partir des sources citées, et mis à jour dès qu'une info évolue.</li>
</ul></div>
<div class="box"><h2 style="margin-top:0">Nous contacter</h2>
<p>Une info, une correction, un secret trouvé en jeu, une proposition de partenariat ? Écris-nous à <strong>gtastucevice@gmail.com</strong> ou en commentaire sur nos réseaux.</p>
<p style="color:var(--mute);font-size:14px">Site de fans non officiel. Non affilié à Rockstar Games ni à Take-Two Interactive. Grand Theft Auto est une marque de Take-Two Interactive. Images : Rockstar Games, sauf mention contraire.</p></div>"""


# ---------- Carte des secrets (schéma, positions approximatives) ----------
ZONES = {
    "kalaga": ("Mount Kalaga", 118, 78), "ambrosia": ("Ambrosia", 238, 112), "gellhorn": ("Port Gellhorn", 92, 196),
    "grassrivers": ("Grassrivers", 196, 290), "vice-city": ("Vice City", 308, 318), "keys": ("Leonida Keys", 262, 420),
    "mer": ("En mer", 352, 432),
}
LEONIDA_PATH = ("M60 40 L330 34 L338 70 L300 92 L292 140 L318 200 L346 262 L358 330 L344 372 L300 384 "
                "L262 360 L226 336 L188 330 L160 300 L136 252 L104 226 L62 214 L40 170 L48 110 Z")
KEYS = [(250, 410, 26, 9), (214, 430, 22, 8), (180, 446, 20, 7), (150, 458, 16, 6), (282, 398, 14, 6)]


def map_svg(secrets, link_prefix=""):
    """Carte schématique de Leonida avec un repère par secret localisé."""
    pins, per = [], {}
    for s in secrets:
        z = s.get("zone")
        if z not in ZONES:
            continue
        k = per.get(z, 0); per[z] = k + 1
        _, x, y = ZONES[z]
        x += [0, 22, -22, 12, -12][k % 5]; y += [18, 30, 30, 44, 44][k % 5]
        pins.append(f'<a class="pin" data-id="{e(s["id"])}" href="{link_prefix}#egg-{e(s["id"])}" aria-label="{e(s["title"])}">'
                    f'<title>{e(s["title"])}</title><circle class="halo" cx="{x}" cy="{y}" r="14"/><circle class="dot" cx="{x}" cy="{y}" r="8"/></a>')
    LBL = {"keys": (150, 488)}
    labels = "".join(f'<text x="{LBL.get(k, (x, y))[0]}" y="{LBL.get(k, (x, y))[1]}" text-anchor="middle">{e(n)}</text>' for k, (n, x, y) in ZONES.items())
    keys = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x, y, rx, ry in KEYS)
    loose = [s for s in secrets if s.get("zone") not in ZONES]
    loose_html = ""
    if loose:
        loose_html = ('<p class="map-loose"><strong>Pas sur la carte</strong> (partout ou lieu inconnu) : '
                      + ", ".join(f'<a href="{link_prefix}#egg-{e(s["id"])}">{e(s["title"])}</a>' for s in loose) + "</p>")
    return (f'<figure class="map"><svg viewBox="0 0 400 500" role="img" aria-label="Carte simplifiée de Leonida avec les secrets">'
            f'<defs><linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B0D3C"/><stop offset="1" stop-color="#2A1050"/></linearGradient></defs>'
            f'<rect width="400" height="500" rx="18" fill="url(#sea)"/>'
            f'<g class="land"><path d="{LEONIDA_PATH}"/>{keys}</g>'
            f'<g class="lbl">{labels}</g>{"".join(pins)}</svg>'
            f'<figcaption>Carte simplifiée, positions approximatives. Touche un repère pour voir le secret. Rose = à trouver, turquoise = trouvé.</figcaption>'
            f'{loose_html}</figure>')


MAP_CSS = """
.map{margin:0 0 20px;background:var(--night);border:1px solid var(--line);border-radius:18px;padding:14px}
.map svg{display:block;width:100%;max-width:420px;margin:0 auto;height:auto}
.map .land path,.map .land ellipse{fill:#3A1D6B;stroke:#FF5FA2;stroke-width:2}
.map .lbl text{fill:#C9BFE8;font:700 13px Inter,sans-serif;letter-spacing:.5px}
.map .pin .dot{fill:#FF3D7F;stroke:#fff;stroke-width:2}
.map .pin .halo{fill:#FF3D7F;opacity:.25;animation:pinpulse 1.6s infinite;transform-box:fill-box;transform-origin:center}
.map .pin.found .dot{fill:#2EE6D6}.map .pin.found .halo{fill:#2EE6D6;animation:none;opacity:.2}
.map .pin:focus-visible .dot{stroke:#FFE45C;stroke-width:4}
@keyframes pinpulse{50%{transform:scale(1.5);opacity:0}}
.map figcaption{margin-top:10px;font-size:13px;color:var(--mute);text-align:center}
.map-loose{margin:10px 0 0;font-size:14px;color:var(--soft);text-align:center}
.egg.flash{border-color:var(--yel);box-shadow:0 0 0 3px var(--yel)}
@media (min-width:900px){.hunt-grid{display:grid;grid-template-columns:380px minmax(0,1fr);gap:22px;align-items:start}.hunt-grid .map{position:sticky;top:90px}}
"""

SEARCH_CSS = """
.nav-search{display:inline-flex;align-items:center;gap:6px}
.nav-search .ico{flex:none}
.homesearch{display:flex;align-items:center;gap:8px;margin:0 0 18px;background:var(--night2);border:2px solid var(--line);border-radius:14px;padding:6px 6px 6px 14px;max-width:720px}
.homesearch:focus-within{border-color:var(--teal)}
.homesearch .hs-ico{color:var(--mute);flex:none}
.homesearch input{flex:1;min-width:0;height:44px;border:0;background:transparent;color:var(--white);font:16px Inter,sans-serif;outline:none}
.homesearch input::placeholder{color:var(--mute)}
.homesearch .btn{min-height:42px;padding:0 16px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.sres{display:flex;flex-direction:column;gap:10px;margin-top:18px}
.sres .post{display:grid;grid-template-columns:180px minmax(0,1fr);align-items:center}
.sres .post img{width:180px;height:100%;min-height:110px;aspect-ratio:auto;object-fit:cover}
.sres .post p{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.sres .egglink{display:block;padding:14px 16px;border-radius:14px;background:var(--night2);border:1px solid var(--line);color:var(--white);text-decoration:none}
.sres .egglink:hover{border-color:var(--pink2)}
.sres .egglink small{display:block;color:var(--soft);margin-top:4px}
.sugg{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.sugg button{min-height:38px;padding:0 14px;border-radius:999px;border:1px solid var(--line);background:var(--night2);color:var(--white);font:700 14px Inter,sans-serif;cursor:pointer}
.scount{color:var(--mute);font-size:14px;margin-top:14px}
mark{background:rgba(255,228,92,.3);color:inherit;border-radius:3px}
@media (max-width:640px){.nav-search span{display:none}.homesearch .btn{display:none}.homesearch{margin-bottom:14px}}
"""

MOBILE_CSS = """
@media (max-width:640px){
 header .wrap{flex-wrap:nowrap;gap:12px;padding-top:8px;padding-bottom:8px}
 .brand b{font-size:17px}.brand i{font-size:24px}
 header nav{flex-wrap:nowrap;overflow-x:auto;gap:14px;font-size:14px;scrollbar-width:none;-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent)}
 header nav::-webkit-scrollbar{display:none}
 header nav a{white-space:nowrap}
 header nav .btn{display:none}
 section{padding:34px 0}
 .une{padding-top:18px}
 .lead{min-height:300px}.lead .txt{padding:18px}
 .lead p{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:15px}
 .facts{display:flex;overflow-x:auto;gap:8px;margin-top:16px;padding-bottom:4px;scroll-snap-type:x mandatory;scrollbar-width:none}
 .facts::-webkit-scrollbar{display:none}
 .fact{flex:0 0 auto;padding:10px 14px;scroll-snap-align:start}.fact b{font-size:16px}.fact span{font-size:12px}
 .chips,.topics{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;padding-bottom:4px}
 .chips::-webkit-scrollbar,.topics::-webkit-scrollbar{display:none}
 .chip,.topics a{flex:none}
 .feed{grid-template-columns:1fr;gap:10px}
 .post{display:grid;grid-template-columns:104px minmax(0,1fr);align-items:center;border-radius:14px}
 .post img{width:104px;height:100%;min-height:92px;aspect-ratio:auto}
 .post .b{padding:10px 12px;gap:5px}
 .post h2,.post h3{font-size:15px}
 .post p{display:none}
 .eggs{gap:10px}.egg{padding:14px}.egg h3{font-size:16px}
 .eggs.short .egg:nth-child(n+5){display:none}
 .more-eggs{display:flex!important}
 h1.page,h1{font-size:26px}
}
.more-eggs{display:none;justify-content:center;margin-top:14px}
"""


SEARCH_JS = r"""<script>
const HUBS=__HUBS__;
const CATS={actu:'Actu',test:'Tests',astuce:'Astuces',secret:'Secrets',drama:'Drama',guide:'Guides'};
const ST={confirme:'Confirmé',rumeur:'Rumeur','a-tester':'À tester'};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const norm=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
let ARTS=[],EGGS=[];
const q=document.getElementById('q'),out=document.getElementById('sres'),cnt=document.getElementById('scount');
function score(words,fields){let t=0;for(const w of words){let hit=false;fields.forEach(([txt,wt])=>{if(norm(txt).includes(w)){t+=wt;hit=true}});if(!hit)return 0}return t}
function hl(s,words){let h=esc(s);words.forEach(w=>{if(w.length<2)return;const n=norm(h);let i=n.indexOf(w);if(i>=0)h=h.slice(0,i)+'<mark>'+h.slice(i,i+w.length)+'</mark>'+h.slice(i+w.length)});return h}
function run(){
 const v=q.value.trim();history.replaceState(null,'',v?'?q='+encodeURIComponent(v):location.pathname);
 const words=norm(v).split(/\s+/).filter(w=>w.length>1);
 if(!words.length){out.innerHTML='';cnt.textContent='';return}
 const r=[];
 HUBS.forEach(h=>{const s=score(words,[[h.nav,6],[h.title,3],[h.desc,1]]);if(s)r.push([s+5,`<a class="egglink" href="${h.slug}.html"><span class="cat c-guide">Sujet</span> <strong>${hl(h.title,words)}</strong><small>${esc(h.desc)}</small></a>`])});
 ARTS.forEach(a=>{const s=score(words,[[a.title,6],[a.chapo,3],[(a.body||[]).join(' '),1]]);if(s)r.push([s,`<a class="post" href="actus/${esc(a.slug)}.html"><img src="${esc(a.img)}" alt="" loading="lazy"><div class="b"><div class="meta"><span class="cat c-${esc(a.cat)}">${CATS[a.cat]||esc(a.cat)}</span></div><h3>${hl(a.title,words)}</h3><p>${esc(a.chapo)}</p></div></a>`])});
 EGGS.forEach(e=>{const s=score(words,[[e.title,6],[e.where,3],[e.how,2]]);if(s)r.push([s,`<a class="egglink" href="index.html#egg-${esc(e.id)}"><span class="cat c-secret">Secret · ${ST[e.status]||''}</span> <strong>${hl(e.title,words)}</strong><small>Où : ${esc(e.where)}</small></a>`])});
 r.sort((a,b)=>b[0]-a[0]);
 cnt.textContent=r.length?r.length+' résultat'+(r.length>1?'s':''):'';
 out.innerHTML=r.length?r.map(x=>x[1]).join(''):'<p>Rien trouvé pour « '+esc(v)+' ». Essaie un autre mot, ou demande-nous en commentaire sur <a href="https://www.tiktok.com/@gtastucevice" target="_blank" rel="noopener">TikTok</a> : on en fera peut-être un guide.</p>';
}
q.addEventListener('input',run);
document.querySelectorAll('.sugg button').forEach(b=>b.onclick=()=>{q.value=b.textContent;run();q.focus()});
Promise.all([fetch('articles.json').then(r=>r.json()),fetch('secrets.json').then(r=>r.json())]).then(([a,e])=>{ARTS=a.sort((x,y)=>y.date.localeCompare(x.date));EGGS=e;const p=new URLSearchParams(location.search).get('q');if(p){q.value=p}run()});
</script>"""

SEARCH_BODY = """<form class="homesearch" role="search" onsubmit="return false"><label class="sr" for="q">Rechercher</label>__ICON__<input id="q" type="search" placeholder="Une astuce, un secret, un lieu…" autocomplete="off" autofocus></form>
<div class="sugg" aria-label="Recherches populaires"><button type="button">argent</button><button type="button">police</button><button type="button">Bigfoot</button><button type="button">carte</button><button type="button">réglages PS5</button><button type="button">spoilers</button></div>
<p class="scount" id="scount" role="status" aria-live="polite"></p>
<div class="sres feed" id="sres"></div>"""


def build_static_pages(arts, secrets):
    home = [a for a in arts if a["cat"] != "guide"]
    guides = [a for a in arts if a["cat"] in ("guide", "astuce")]
    # Accueil
    p = os.path.join(ROOT, "index.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("", "GTAstuce Vice – Astuces, actus et secrets GTA 6 en français",
                                   "GTASTUCE VICE (GTAstuce) : astuces GTA 6, actus, guides, easter eggs et secrets de Leonida, en français, sourcés et sans spoiler."))
    t = re.sub(r"<title>.*?</title>", "<title>GTAstuce Vice – Astuces, actus et secrets GTA 6 en français</title>", t, count=1)
    t = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="GTASTUCE VICE (GTAstuce) : astuces GTA 6, actus, guides, easter eggs et secrets de Leonida, en français, sourcés et sans spoiler.">', t, count=1)
    if home:
        L = home[0]
        t = fill(t, "lead", f'<a class="lead" href="actus/{e(L["slug"])}.html"><img src="{e(L["img"])}" alt=""><span class="ov"></span><div class="txt">{meta_html(L)}<h2>{e(L["title"])}</h2><p>{e(L["chapo"])}</p></div></a>')
        t = fill(t, "side", "".join(f'<a class="mini" href="actus/{e(a["slug"])}.html"><img src="{e(a["img"])}" alt="" loading="lazy"><div>{meta_html(a)}<h3>{e(a["title"])}</h3></div></a>' for a in home[1:5]))
        tk = "".join(f'<a href="actus/{e(a["slug"])}.html">{e(a["title"])}</a>' for a in home[:8])
        t = fill(t, "ticker", tk + tk)
        t = fill(t, "feed", "".join(post_card(a) for a in home[5:14]))
    t = fill(t, "guides", "".join(post_card(a) for a in guides[:6]))
    t = fill(t, "topics", topics_html())
    t = fill(t, "eggs", "".join(egg_card(x) for x in secrets))
    t = fill(t, "sc", f"0/{len(secrets)}")
    t = fill(t, "map", map_svg(secrets))
    t = fill(t, "css", MAP_CSS + SEARCH_CSS + MOBILE_CSS)
    t = fill(t, "ld", '<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "WebSite", "name": "GTASTUCE VICE", "alternateName": ["GTAstuce", "GTA Stuce", "GTAstuce Vice", "gtastucevice"], "url": BASE + "/", "inLanguage": "fr-FR"},
        {"@context": "https://schema.org", "@type": "Organization", "name": "GTASTUCE VICE", "alternateName": "GTAstuce", "url": BASE + "/", "logo": BASE + "/favicon-512.png", "email": "gtastucevice@gmail.com",
         "sameAs": ["https://www.tiktok.com/@gtastucevice", "https://www.instagram.com/gtastucevice/", "https://www.youtube.com/@gtastucevice"]}], ensure_ascii=False) + "</script>")
    open(p, "w", encoding="utf-8").write(t)
    # Liste des actus
    p = os.path.join(ROOT, "actus.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("actus.html", "Actus GTA 6 – GTASTUCE VICE", "Toute l'actu GTA 6 en français : news, tests, astuces, secrets et dramas, sourcés."))
    t = fill(t, "css", SEARCH_CSS + MOBILE_CSS)
    t = fill(t, "actuslist", '<div class="kicker">Le fil GTA 6</div><h1 class="ptitle">Les actus</h1><div class="feed">' + "".join(post_card(a, h="h2") for a in arts) + "</div>")
    open(p, "w", encoding="utf-8").write(t)
    # Matos
    p = os.path.join(ROOT, "matos.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("matos.html", "Le matos pour GTA 6 : SSD, casque, manette – GTASTUCE VICE", "Le matos utile pour jouer à GTA 6 sur PS5 et Xbox et les critères à vérifier avant d'acheter."))
    open(p, "w", encoding="utf-8").write(t)
    # Qui sommes-nous
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "GTASTUCE VICE", "url": BASE, "logo": f"{BASE}/favicon-512.png", "email": "gtastucevice@gmail.com",
           "sameAs": ["https://www.tiktok.com/@gtastucevice", "https://www.instagram.com/gtastucevice/", "https://www.youtube.com/@gtastucevice"]}
    p = os.path.join(ROOT, "matos.html"); t = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(fill(t, "css", SEARCH_CSS + MOBILE_CSS))
    open(os.path.join(ROOT, "a-propos.html"), "w", encoding="utf-8").write(
        simple_page("a-propos.html", "Qui sommes-nous – GTASTUCE VICE", "Qui est derrière GTASTUCE VICE, comment on choisit et vérifie nos infos sur GTA 6, et comment nous contacter.",
                    "Qui sommes-nous ?", "GTASTUCE VICE", ABOUT_BODY, org))
    # Recherche
    hubs_js = json.dumps([{k: h[k] for k in ("slug", "nav", "title", "desc")} for h in HUBS], ensure_ascii=False)
    sp = simple_page("recherche.html", "Rechercher – GTASTUCE VICE", "Cherche une astuce, un guide ou un secret de GTA 6 sur GTASTUCE VICE.",
                     "Rechercher", "GTASTUCE VICE", SEARCH_BODY.replace("__ICON__", '<svg class="ico hs-ico" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.6"/><path d="M15.5 15.5L21 21" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>'))
    sp = sp.replace("</body>", SEARCH_JS.replace("__HUBS__", hubs_js) + "\n</body>")
    sp = sp.replace('<meta name="robots" content="max-image-preview:large">', '<meta name="robots" content="noindex,follow">')
    open(os.path.join(ROOT, "recherche.html"), "w", encoding="utf-8").write(sp)
    # Pages sujets
    for h in HUBS:
        lst = hub_articles(h, arts)
        body = f'<p class="lead">{e(h["intro"])}</p>'
        if h.get("eggs"):
            body += '<h2>La carte des secrets</h2>' + map_svg(secrets, "index.html") + '<h2>Les secrets trouvés</h2><div class="eggs">' + "".join(egg_card(x) for x in secrets) + '</div><p style="margin-top:16px"><a class="btn" href="index.html#chasse">Coche-les dans la chasse aux secrets</a></p>'
        body += "<h2>Nos articles et guides</h2>" + ('<div class="feed">' + "".join(post_card(a) for a in lst) + "</div>" if lst else "<p>Les premiers articles arrivent très vite.</p>")
        ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h["title"], "description": h["desc"], "url": f"{BASE}/{h['slug']}.html", "inLanguage": "fr-FR",
              "hasPart": [{"@type": "Article", "headline": a["title"][:110], "url": f"{BASE}/actus/{a['slug']}.html"} for a in lst[:20]]}
        open(os.path.join(ROOT, h["slug"] + ".html"), "w", encoding="utf-8").write(
            simple_page(h["slug"] + ".html", h["title"] + " – GTASTUCE VICE", h["desc"], h["h1"], "Le sujet", body, ld))


def main():
    arts = json.load(open(os.path.join(ROOT, "articles.json"), encoding="utf-8"))
    arts.sort(key=lambda a: a["date"], reverse=True)
    secrets = json.load(open(os.path.join(ROOT, "secrets.json"), encoding="utf-8"))
    build_static_pages(arts, secrets)
    css = styles()
    out = os.path.join(ROOT, "actus")
    os.makedirs(out, exist_ok=True)
    keep = set()
    for a in arts:
        assert re.fullmatch(r"[a-z0-9-]+", a["slug"]), a["slug"]
        assert os.path.exists(os.path.join(ROOT, a["img"])), a["img"]
        name = a["slug"] + ".html"
        keep.add(name)
        open(os.path.join(out, name), "w", encoding="utf-8").write(page(a, arts, css))
    for f in os.listdir(out):
        if f.endswith(".html") and f not in keep:
            os.remove(os.path.join(out, f))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(f"{BASE}/", now), (f"{BASE}/actus.html", now), (f"{BASE}/matos.html", now)]
    urls += [(f"{BASE}/{h['slug']}.html", now) for h in HUBS] + [(f"{BASE}/a-propos.html", now)]
    urls += [(f"{BASE}/actus/{a['slug']}.html", a.get("updated", a["date"])[:10]) for a in arts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"<url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"{len(arts)} pages générées dans actus/, sitemap.xml à jour")


if __name__ == "__main__":
    main()
