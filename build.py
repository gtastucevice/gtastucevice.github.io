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
<a href="../index.html">Mentions légales</a>
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
<meta name="twitter:card" content="summary_large_image">
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


def main():
    arts = json.load(open(os.path.join(ROOT, "articles.json"), encoding="utf-8"))
    arts.sort(key=lambda a: a["date"], reverse=True)
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
    urls += [(f"{BASE}/actus/{a['slug']}.html", a.get("updated", a["date"])[:10]) for a in arts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"<url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"{len(arts)} pages générées dans actus/, sitemap.xml à jour")


if __name__ == "__main__":
    main()
