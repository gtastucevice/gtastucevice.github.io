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
    return (f'<div class="egg"><div class="row" style="margin:0"><span class="st st-{e(x["status"])}">{EGG_ST.get(x["status"], x["status"])}</span></div>'
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
.topics{display:flex;flex-wrap:wrap;gap:10px}.topics a{min-height:44px;display:inline-flex;align-items:center;padding:0 18px;border-radius:999px;background:var(--night2);border:1px solid var(--line);color:var(--white);text-decoration:none;font-weight:700}
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


def build_static_pages(arts, secrets):
    home = [a for a in arts if a["cat"] != "guide"]
    guides = [a for a in arts if a["cat"] in ("guide", "astuce")]
    # Accueil
    p = os.path.join(ROOT, "index.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("", "GTASTUCE VICE – Actus, astuces et secrets GTA 6",
                                   "Toute l'actu GTA 6 en français, en direct : news, astuces, easter eggs et dramas, sourcés. Et la chasse aux secrets de Leonida."))
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
    open(p, "w", encoding="utf-8").write(t)
    # Liste des actus
    p = os.path.join(ROOT, "actus.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("actus.html", "Actus GTA 6 – GTASTUCE VICE", "Toute l'actu GTA 6 en français : news, tests, astuces, secrets et dramas, sourcés."))
    t = fill(t, "actuslist", '<div class="kicker">Le fil GTA 6</div><h1 class="ptitle">Les actus</h1><div class="feed">' + "".join(post_card(a, h="h2") for a in arts) + "</div>")
    open(p, "w", encoding="utf-8").write(t)
    # Matos
    p = os.path.join(ROOT, "matos.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("matos.html", "Le matos pour GTA 6 : SSD, casque, manette – GTASTUCE VICE", "Le matos utile pour jouer à GTA 6 sur PS5 et Xbox et les critères à vérifier avant d'acheter."))
    open(p, "w", encoding="utf-8").write(t)
    # Qui sommes-nous
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "GTASTUCE VICE", "url": BASE, "logo": f"{BASE}/favicon-512.png", "email": "gtastucevice@gmail.com",
           "sameAs": ["https://www.tiktok.com/@gtastucevice", "https://www.instagram.com/gtastucevice/", "https://www.youtube.com/@gtastucevice"]}
    open(os.path.join(ROOT, "a-propos.html"), "w", encoding="utf-8").write(
        simple_page("a-propos.html", "Qui sommes-nous – GTASTUCE VICE", "Qui est derrière GTASTUCE VICE, comment on choisit et vérifie nos infos sur GTA 6, et comment nous contacter.",
                    "Qui sommes-nous ?", "GTASTUCE VICE", ABOUT_BODY, org))
    # Pages sujets
    for h in HUBS:
        lst = hub_articles(h, arts)
        body = f'<p class="lead">{e(h["intro"])}</p>'
        if h.get("eggs"):
            body += '<h2>Les secrets trouvés</h2><div class="eggs">' + "".join(egg_card(x) for x in secrets) + '</div><p style="margin-top:16px"><a class="btn" href="index.html#chasse">Coche-les dans la chasse aux secrets</a></p>'
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
