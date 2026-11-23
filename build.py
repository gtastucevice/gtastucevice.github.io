#!/usr/bin/env python3
"""Génère une vraie page HTML par article (dossier actus/) + sitemap.xml + robots.txt.

Usage : python3 build.py   (à lancer après chaque modification de articles.json)
La mise en forme reprend les styles de actus.html : une seule source de style.
"""
import hashlib, html, json, os, re, struct
from datetime import datetime, timezone
try:
    from PIL import Image  # facultatif : sert à créer les vignettes
except ImportError:  # pragma: no cover
    Image = None

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


# ---------- Images : dimensions + vignettes (le mobile chargeait des JPEG 1280 px pour des vignettes de 104 px) ----------
def jpeg_size(path):
    """(largeur, hauteur) d'un JPEG sans dépendance ; None si inconnu."""
    try:
        with open(path, "rb") as f:
            if f.read(2) != b"\xff\xd8":
                return None
            while True:
                m = f.read(2)
                if len(m) < 2 or m[0] != 0xFF:
                    return None
                ln = struct.unpack(">H", f.read(2))[0]
                if m[1] in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">xHH", f.read(5))
                    return w, h
                f.seek(ln - 2, 1)
    except OSError:
        return None


THUMB_W = (480, 800)


def thumbs(src):
    """Crée (si besoin) assets/thumbs/<nom>-480.jpg et -800.jpg ; renvoie [(chemin, largeur)]."""
    full = os.path.join(ROOT, src)
    size = jpeg_size(full)
    if not size or not src.endswith(".jpg"):
        return [], size
    out = []
    stem = os.path.splitext(os.path.basename(src))[0]
    for w in THUMB_W:
        if w >= size[0]:
            continue
        rel = f"assets/thumbs/{stem}-{w}.jpg"
        dst = os.path.join(ROOT, rel)
        if Image and (not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(full)):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            im = Image.open(full).convert("RGB")
            im.resize((w, round(size[1] * w / size[0])), Image.LANCZOS).save(dst, "JPEG", quality=78, optimize=True, progressive=True)
        if os.path.exists(dst):
            out.append((rel, w))
    return out, size


SIZES = {"post": "(max-width:640px) 104px, 360px", "mini": "120px", "lead": "(max-width:860px) 100vw, 720px",
         "hero": "(max-width:800px) 100vw, 760px", "search": "(max-width:640px) 104px, 180px", "egg": "(max-width:640px) 100vw, 420px"}


def img_html(src, prefix="", kind="post", alt="", lazy=True, priority=False, extra=""):
    tl, size = thumbs(src)
    attrs = [f'src="{prefix}{e(src)}"', f'alt="{e(alt)}"']
    if tl and size:
        attrs.append('srcset="' + ", ".join(f"{prefix}{e(r)} {w}w" for r, w in tl) + f', {prefix}{e(src)} {size[0]}w"')
        attrs.append(f'sizes="{SIZES[kind]}"')
    if size:
        attrs.append(f'width="{size[0]}" height="{size[1]}"')
    if lazy and not priority:
        attrs.append('loading="lazy"')
    if priority:
        attrs.append('fetchpriority="high"')
    attrs.append('decoding="async"')
    return f"<img {' '.join(attrs)}{extra}>"


# ---------- Texte d'un article (le corps peut contenir des intertitres, étapes et tableaux de commandes) ----------
def text_of(a):
    out = [a["title"], a["chapo"], a.get("quick", "")]
    for b in a["body"]:
        if isinstance(b, str):
            out.append(b)
        elif "h2" in b:
            out.append(b["h2"])
        elif "steps" in b:
            out += [s["t"] + " " + s["d"] for s in b["steps"]]
        elif "controls" in b:
            out += [" ".join(r) for r in b["controls"]["rows"]]
    return " ".join(out)


def trim(s, n=155):
    s = " ".join(str(s).split())
    if len(s) <= n:
        return s
    cut = s[: n - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return cut + "…"


def title_tag(t):
    """Ajoute « – GTASTUCE VICE » seulement si le titre reste lisible en entier dans Google (~65 caractères)."""
    full = f"{t} – GTASTUCE VICE"
    return full if len(full) <= 65 else t


# ---------- Statuts des secrets : une seule définition pour toutes les surfaces ----------
STATUS = {
    "confirme": ("Confirmé", "Vu en jeu et documenté (capture, vidéo ou guide précis) par au moins une source identifiée. Ça ne veut pas dire qu'on l'a testé nous-mêmes."),
    "rumeur": ("Rumeur", "Rapporté par des joueurs ou un média, sans preuve vérifiable pour l'instant."),
    "a-tester": ("À tester", "Décrit par une source, mais l'emplacement exact ou la façon de le déclencher reste à vérifier en jeu."),
}
EGG_ST = {k: v[0] for k, v in STATUS.items()}


def status_badge(s):
    return f'<span class="st st-{e(s)}">{e(EGG_ST.get(s, s))}</span>'


def legend_html(open_=False):
    rows = "".join(f"<dt>{status_badge(k)}</dt><dd>{e(d)}</dd>" for k, (_, d) in STATUS.items())
    return (f'<details class="st-legend" data-status-legend{" open" if open_ else ""}><summary>Que veulent dire les statuts ?</summary>'
            f'<dl>{rows}</dl><p>La mention <strong>« Testé par nous »</strong> n\'apparaît que si l\'équipe l\'a refait en jeu. '
            'Une source citée n\'est pas un test.</p></details>')


def tested_html(x):
    if x.get("teste"):
        return f'<span class="tested yes">Testé par nous le {fr_date(x["teste"])}</span>'
    return '<span class="tested">Pas encore testé par nous</span>'


# ---------- En-tête et pied de page : un seul modèle pour toutes les pages ----------
SEARCH_ICO = '<svg class="ico" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.6"/><path d="M15.5 15.5L21 21" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>'


def nav_html(prefix="", current=""):
    cur = lambda h: ' aria-current="page"' if h == current else ""
    return (f'<nav aria-label="Navigation principale">\n'
            f'<a class="nav-search tb-dup" href="{prefix}recherche.html" aria-label="Rechercher"{cur("recherche.html")}>{SEARCH_ICO}<span>Rechercher</span></a>\n'
            f'<a class="tb-dup" href="{prefix}actus.html"{cur("actus.html")}>Actus</a>\n'
            f'<a href="{prefix}index.html#guides">Guides</a>\n'
            f'<a class="tb-dup" href="{prefix}gta-6-carte.html"{cur("gta-6-carte.html")}>Carte</a>\n'
            f'<a class="nav-cheat" href="{prefix}gta-6-codes-triche.html"{cur("gta-6-codes-triche.html")}><span class="nm">Codes de t</span><span class="nmt">T</span>riche</a>\n'
            f'<a class="tb-dup" href="{prefix}index.html#chasse">Chasse<span class="nm"> aux secrets</span></a>\n'
            f'<a href="{prefix}matos.html"{cur("matos.html")}>Le matos</a>\n'
            f'<a class="btn" href="{prefix}index.html#newsletter">Newsletter</a>\n</nav>')


def footer_inner(prefix=""):
    return (f'<div class="wrap">\n<div>\n<a class="brand" href="{prefix}index.html"><b>GTASTUCE</b><i>Vice</i></a>\n'
            '<small>Site de fans non officiel. Non affilié à Rockstar Games ni à Take-Two Interactive. Grand Theft Auto et les éléments associés sont des marques de Take-Two Interactive. Images : Rockstar Games (captures officielles), sauf mention contraire.</small>\n'
            '</div>\n<nav aria-label="Liens légaux">\n'
            f'<a href="{prefix}a-propos.html">Qui sommes-nous</a>\n<a href="{prefix}contact.html">Contact</a>\n'
            f'<a href="{prefix}mentions-legales.html">Mentions légales</a>\n<a href="{prefix}mentions-legales.html#confidentialite">Confidentialité</a>\n'
            '<button class="motion-toggle" type="button" aria-pressed="false">Couper les animations</button>\n'
            '</nav>\n</div>')


VICO_TAGS = {"secret": "LE SECRET DE VICO", "astuce": "L'ASTUCE DE VICO", "verifier": "VICO VÉRIFIE"}


def vico_box(a):
    """Encadré de Vico dans un article : "vico": {"type": "secret|astuce|verifier", "text": "..."}"""
    v = a.get("vico")
    if not v:
        return ""
    t = v.get("type", "astuce"); assert t in VICO_TAGS, (a["slug"], t)
    return (f'<div class="vico-box v-{t}"><img src="../assets/vico/tete.svg" alt="" width="64" height="56">'
            f'<div><span class="tag">{VICO_TAGS[t]}</span><p>{e(v["text"])}</p></div></div>')


def header_html(prefix="", current=""):
    return (f'<header>\n<div class="wrap">\n<a class="brand" href="{prefix}index.html" aria-label="GTASTUCE VICE, accueil"><img class="vico" src="{prefix}assets/vico/tete.svg" alt="" width="46" height="40"><b>GTASTUCE</b><i>Vice</i></a>\n'
            f'{nav_html(prefix, current)}\n</div>\n</header>')


def footer_html(prefix=""):
    return f"<footer>\n{footer_inner(prefix)}\n</footer>"

EXTRA_CSS = """<style>
.related{margin-top:40px}
.related h2{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:24px;margin:0 0 14px}
.c-guide{background:#B9A7FF}
.cta{margin-top:28px;padding:20px;border-radius:16px;background:linear-gradient(135deg,#2A0F4A,#6B1E6E);border:1px solid var(--line)}
.cta p{margin:0 0 12px;font-size:16px}
.srcs h2{margin:0 0 8px;font-family:Inter,system-ui,sans-serif;font-weight:700;font-size:15px;text-transform:uppercase;letter-spacing:2px;color:var(--teal)}
.related .post h3{margin:0;font-size:17px;line-height:1.3}
.affbox{margin:28px 0;padding:20px;border-radius:16px;background:var(--night2,#21104A);border:1px solid var(--line)}
.affbox h2{margin:0 0 6px;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:20px;line-height:1.2}
.affbox p{margin:0 0 14px}
.affbox .alinks{display:flex;flex-wrap:wrap;gap:10px}
.affbox .alinks a{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:12px;border:1px solid var(--line);color:var(--white,#fff);text-decoration:none;font-weight:700}
.affbox .alinks a.main{background:var(--pink,#FF3EA5);border-color:transparent}
.affbox .adisc{margin:12px 0 0;font-size:12px;color:var(--mute,#8F84B8)}
</style>"""


def body_html(a):
    """Corps d'article : paragraphes, intertitres (sommaire auto), étapes numérotées, tableau de commandes PS5/Xbox."""
    out, toc, n = [], [], 0
    for b in a["body"]:
        if isinstance(b, str):
            out.append(f"<p>{e(b)}</p>")
        elif "h2" in b:
            n += 1
            sid = f"s{n}"
            toc.append((sid, b["h2"]))
            out.append(f'<h2 class="sec2" id="{sid}">{e(b["h2"])}</h2>')
        elif "steps" in b:
            out.append('<ol class="steps">' + "".join(f"<li><strong>{e(s['t'])}</strong>{e(s['d'])}</li>" for s in b["steps"]) + "</ol>")
        elif "retenir" in b:  # tableau « À retenir » : {"retenir": [["Où", "..."], ["Prix", "..."]]}
            rows = "".join(f'<tr><th scope="row">{e(r[0])}</th><td>{e(r[1])}</td></tr>' for r in b["retenir"])
            out.append(f'<div class="retenir"><p class="rt">À retenir</p><table>{rows}</table></div>')
        elif "capture" in b:  # capture en jeu (PS5) : {"capture": "assets/captures/x.jpg", "legende": "...", "credit": "..."}
            leg = e(b.get("legende", ""))
            cr = e(b.get("credit", CAPTURE_CREDIT))
            out.append(f'<figure class="capt">{img_html(b["capture"], "../", "hero", b.get("legende", ""))}'
                       f'<figcaption>{leg}{" · " if leg else ""}<span>{cr}</span></figcaption></figure>')
        elif "controls" in b:
            c = b["controls"]
            rows = "".join(f'<tr><th scope="row">{e(r[0])}</th><td data-label="PS5">{e(r[1])}</td><td data-label="Xbox">{e(r[2])}</td></tr>' for r in c["rows"])
            out.append(f'<div class="ctrl-wrap"><table class="controls"><caption>{e(c["caption"])}</caption>'
                       f'<thead><tr><th scope="col">Action</th><th scope="col">PS5</th><th scope="col">Xbox</th></tr></thead><tbody>{rows}</tbody></table></div>')
    toc_html = ""
    if len(toc) >= 3:
        toc_html = ('<nav class="toc" aria-labelledby="toc-t"><h2 id="toc-t">Sommaire</h2><ol>'
                    + "".join(f'<li><a href="#{sid}">{e(h)}</a></li>' for sid, h in toc) + "</ol></nav>")
    return toc_html, "".join(out)


GAMEPLAY = ("guide", "astuce", "secret")

# ---------- Encart « matos / cadeaux » en bas des articles (liens affiliés Amazon) ----------
# Choix automatique : "tech" pour les articles sur la console (stockage, réglages, plantages), "none" pour les dramas,
# "fan" sinon. Un article peut forcer son encart avec le champ "aff": "fan" | "tech" | "none".
AFF_TECH_WORDS = ("plantage", "reglages", "xbox-one", "heure-de-sortie", "psn", "60-fps", "sans-disque", "telecharg", "stockage")
NOEL_FIN = "2026-12-25"
AFF_DISC_SHORT = ('<p class="adisc">Liens affiliés Amazon : si tu achètes après avoir cliqué, GTASTUCE VICE touche une petite commission, '
                  'sans que ça te coûte plus cher. En tant que Partenaire Amazon, nous réalisons un bénéfice sur les achats remplissant les conditions requises.</p>')


def aff_link(label, q, track, main=False):
    cls = ' class="main"' if main else ""
    return (f'<a{cls} href="{amazon(q)}" target="_blank" rel="sponsored noopener" '
            f'data-goatcounter-click="aff-{track}" data-goatcounter-title="{e(label)}">{e(label)}<span class="sr-only"> (Amazon, lien affilié)</span></a>')


def aff_box(a, prefix="../"):
    kind = a.get("aff")
    if not kind:
        if a["cat"] == "drama":
            kind = "none"
        elif any(w in a["slug"] for w in AFF_TECH_WORDS):
            kind = "tech"
        else:
            kind = "fan"
    if kind == "none":
        return ""
    if kind == "tech":
        return ('<aside class="affbox" aria-labelledby="aff-t"><h2 id="aff-t">Plus de place pour GTA 6&nbsp;?</h2>'
                '<p>Le jeu remplit vite la console. Un SSD M.2 sur PS5 ou une carte d\'extension sur Xbox Series règle le problème sans désinstaller tes autres jeux.</p>'
                '<div class="alinks">' + aff_link("SSD compatibles PS5", "ssd m.2 nvme pcie 4.0 dissipateur ps5 1to", "ssd", True)
                + aff_link("Cartes d'extension Xbox", "carte extension stockage xbox series 1to", "xbox-carte")
                + f'<a href="{prefix}matos.html#ssd">Les critères à vérifier</a></div>{AFF_DISC_SHORT}</aside>')
    if datetime.now(timezone.utc).strftime("%Y-%m-%d") <= NOEL_FIN:
        return ('<aside class="affbox" aria-labelledby="aff-t"><h2 id="aff-t">Un cadeau GTA 6 pour Noël&nbsp;?</h2>'
                '<p>Le jeu, la manette DualSense édition limitée GTA VI, une carte PlayStation Store ou Xbox : on a fait la liste, avec ce qu\'il faut vérifier avant d\'acheter.</p>'
                f'<div class="alinks"><a class="main" href="{prefix}gta-6-idees-cadeaux.html" data-goatcounter-click="aff-cadeaux">Les idées cadeaux GTA 6</a>'
                + aff_link("DualSense GTA VI", "manette dualsense gta 6 blanche edition limitee", "dualsense-gta")
                + aff_link("GTA 6 sur PS5", "gta 6 ps5", "jeu-ps5") + f"</div>{AFF_DISC_SHORT}</aside>")
    return ('<aside class="affbox" aria-labelledby="aff-t"><h2 id="aff-t">Bien équipé pour Leonida</h2>'
            '<p>Une deuxième manette chargée, un casque pour les radios, de la place pour le jeu : notre sélection, avec les critères à vérifier.</p>'
            f'<div class="alinks"><a class="main" href="{prefix}matos.html" data-goatcounter-click="aff-matos">Le matos GTA 6</a>'
            + aff_link("DualSense GTA VI", "manette dualsense gta 6 blanche edition limitee", "dualsense-gta")
            + aff_link("Casques PS5", "casque gaming ps5 sans fil", "casque") + f"</div>{AFF_DISC_SHORT}</aside>")


def page(a, arts, css, secrets_by_id):
    url = f"{BASE}/actus/{a['slug']}.html"
    img_abs = f"{BASE}/{a['img']}"
    size = jpeg_size(os.path.join(ROOT, a["img"]))
    cat = CATS.get(a["cat"], a["cat"])
    desc = a.get("desc") or trim(a["chapo"])
    toc_html, body = body_html(a)
    quick = f'<section class="quick" aria-labelledby="q-t"><h2 id="q-t">Réponse rapide</h2><p>{e(a["quick"])}</p></section>' if a.get("quick") else ""
    srcs = "".join(f'<li><a href="{e(s["u"])}" target="_blank" rel="noopener">{e(s["t"])}</a></li>' for s in a["sources"])
    verif = ""
    if a["cat"] in GAMEPLAY:
        verif = (f'<p class="verif"><strong>Testé par nous en jeu :</strong> oui, le {fr_date(a["teste"])}.</p>' if a.get("teste") else
                 '<p class="verif"><strong>Testé par nous en jeu :</strong> pas encore. Les infos viennent des sources ci-dessus ; on mettra la page à jour après vérification.</p>')
    sbox = ""
    ids = [i for i in a.get("secrets", []) if i in secrets_by_id]
    if ids:
        items = "".join(f'<li>{status_badge(secrets_by_id[i]["status"])}<a href="../index.html#egg-{e(i)}">{e(secrets_by_id[i]["title"])}</a>{tested_html(secrets_by_id[i])}</li>' for i in ids)
        sbox = (f'<section class="statusbox" aria-labelledby="sb-t"><h2 id="sb-t">Le statut des secrets de cet article</h2><ul>{items}</ul>'
                f'{legend_html()}</section>')
    upd = f'<p class="updated">Mis à jour le {fr_date(a["updated"])}</p>' if a.get("updated") else ""
    rel = [x for x in arts if x["slug"] != a["slug"] and x["cat"] == a["cat"]][:3]
    rel += [x for x in arts if x["slug"] != a["slug"] and x not in rel][: 3 - len(rel)]
    rel_html = "".join(
        f'<a class="post" href="{e(x["slug"])}.html">{img_html(x["img"], "../")}<div class="b"><div class="meta"><span class="cat c-{e(x["cat"])}">{e(CATS.get(x["cat"], x["cat"]))}</span><span>{fr_date(x["date"])}</span></div><h3>{e(x["title"])}</h3></div></a>'
        for x in rel)
    if a["cat"] == "secret":
        cta = '<div class="cta"><p><strong>Tu l\'as trouvé ?</strong> Coche-le dans la chasse aux secrets et monte en grade.</p><a class="btn" href="../index.html#chasse">La chasse aux secrets</a></div>'
    else:
        cta = '<div class="cta"><p><strong>Une astuce GTA 6 par jour</strong>, en français et sans spoiler.</p><a class="btn" href="https://www.tiktok.com/@gtastucevice" target="_blank" rel="noopener">Suis-nous sur TikTok</a></div>'
    ld = {
        "@context": "https://schema.org",
        "@type": "Article" if a["cat"] in ("guide", "astuce") else "NewsArticle",
        "headline": a["title"][:110],
        "description": desc,
        "image": [img_abs],
        "datePublished": a["date"],
        "dateModified": a.get("updated", a["date"]),
        "inLanguage": "fr-FR",
        "mainEntityOfPage": url,
        "author": {"@type": "Person", "name": "Roméo", "url": BASE + "/a-propos.html#romeo", "description": AUTHOR_BIO, "image": BASE + "/assets/romeo.jpg", "worksFor": {"@type": "Organization", "name": "GTASTUCE VICE", "url": BASE + "/"}},
        "publisher": {"@type": "Organization", "name": "GTASTUCE VICE", "url": BASE + "/", "logo": {"@type": "ImageObject", "url": f"{BASE}/favicon-512.png"}},
    }
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": BASE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Actus", "item": f"{BASE}/actus.html"},
        {"@type": "ListItem", "position": 3, "name": a["title"], "item": url}]}
    dims = f'<meta property="og:image:width" content="{size[0]}">\n<meta property="og:image:height" content="{size[1]}">' if size else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title_tag(a['title']))}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(a['title'])}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{img_abs}">
{dims}
<meta property="og:url" content="{url}">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="GTASTUCE VICE">
<meta property="og:image:alt" content="{e(a.get('img_alt') or a['title'])}">
<meta property="article:published_time" content="{e(a['date'])}">
<meta name="twitter:card" content="summary_large_image">
{ICONS}
{FONTS}
{css}
{EXTRA_CSS}
<script type="application/ld+json">{json.dumps([ld, crumbs], ensure_ascii=False)}</script>
</head>
<body>
{header_html("../")}
<main class="page" id="contenu"><div class="wrap">
<article class="full">
<a class="back" href="../actus.html">← Toutes les actus</a>
<div class="meta"><span class="cat c-{e(a['cat'])}">{e(cat)}</span><time datetime="{e(a['date'])}">{fr_date(a['date'])}</time><span class="by">Par <a href="../a-propos.html#romeo">Roméo</a></span></div>
<h1>{e(a['title'])}</h1>
<p class="chapo">{e(a['chapo'])}</p>
{upd}
{quick}
{img_html(a["img"], "../", "hero", a.get("img_alt", ""), priority=True, extra=' style="margin-bottom:6px"')}
<p style="font-size:13px;color:#8F84B8;margin:0 0 22px">{e(a.get('credit', ''))}</p>
{vico_box(a)}
{toc_html}
{sbox}
{body}
{aff_box(a)}
<div class="srcs"><h2 class="h3">Sources</h2><ul>{srcs}</ul>{verif}</div>
<aside class="authorbox"><img src="../assets/romeo.jpg" alt="Roméo, fondateur de GTASTUCE VICE" width="64" height="64" loading="lazy"><div><p class="an"><a href="../a-propos.html#romeo">Roméo</a> · fondateur de GTASTUCE VICE</p><p>{e(AUTHOR_BIO)}</p></div></aside>
{cta}
</article>
<section class="related" aria-labelledby="rel-t"><h2 id="rel-t">À lire aussi</h2><div class="feed">{rel_html}</div></section>
</div></main>
{footer_html("../")}
</body>
</html>
"""


ICONS = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#170A33">
<meta name="robots" content="max-image-preview:large">
<script data-goatcounter="https://gtastucevice.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
<script>function loadScript(a){var b=document.getElementsByTagName("head")[0],c=document.createElement("script");c.type="text/javascript",c.src="https://tracker.metricool.com/resources/be.js",c.onreadystatechange=a,c.onload=a,b.appendChild(c)}loadScript(function(){beTracker.t({hash:"4e9f3088e0b1aaa130a3f08644ec4fe8"})});</script>"""

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
    if key == "css":  # dans un <style>, les repères doivent être des commentaires CSS
        pat = re.compile(r"/\*S:css\*/.*?/\*E:css\*/", re.S)
        assert pat.search(src), key
        return pat.sub(lambda m: f"/*S:css*/{html_}/*E:css*/", src)
    pat = re.compile(r"<!--S:%s-->.*?<!--E:%s-->" % (key, key), re.S)
    assert pat.search(src), key
    return pat.sub(lambda m: f"<!--S:{key}-->{html_}<!--E:{key}-->", src)


def meta_html(a):
    return (f'<div class="meta"><span class="cat c-{e(a["cat"])}">{e(CATS.get(a["cat"], a["cat"]))}</span>'
            f'<time datetime="{e(a["date"])}">{fr_date(a["date"])}</time></div>')


def post_card(a, prefix="", h="h3", attrs=""):
    return (f'<a class="post" href="{prefix}actus/{e(a["slug"])}.html"{attrs}>{img_html(a["img"], prefix)}'
            f'<div class="b">{meta_html(a)}<{h}>{e(a["title"])}</{h}><p>{e(a["chapo"])}</p></div></a>')


# Pages « sujet » : chacune regroupe automatiquement les articles qui en parlent.
HUBS = [
    {"slug": "gta-6-argent", "nav": "Argent", "title": "GTA 6 argent : comment gagner de l'argent vite (sans glitch)",
     "h1": "Gagner de l'argent dans GTA 6", "desc": "Toutes nos astuces pour gagner de l'argent dans GTA 6 sans glitch : premières heures, braquages, plongées, voitures à revendre.",
     "intro": "Au début de GTA 6, l'argent est rare, c'est voulu. Ici on rassemble toutes nos astuces pour remplir ton compte proprement, sans glitch ni triche qui risquent de te faire bannir. La page se met à jour à chaque nouvel article.",
     "kw": ["argent", "cash", "fauché"], "pin": ["2026-11-19-argent-debut-gta-6"]},
    {"slug": "gta-6-carte", "nav": "Carte & lieux", "title": "Carte de GTA 6 : Leonida, Vice City et tous les lieux",
     "h1": "La carte de GTA 6 : Leonida et Vice City", "desc": "Les régions de Leonida, les quartiers de Vice City et les lieux à ne pas rater dans GTA 6, mis à jour en continu.",
     "intro": "Leonida, c'est la Floride version Rockstar : Vice City, les Keys, les marais, la côte oubliée, la campagne et la montagne. Retrouve ici tous nos guides et articles sur la carte et les lieux à visiter.",
     "kw": ["carte", "leonida", "région"]},
    {"slug": "gta-6-easter-eggs", "nav": "Easter eggs", "title": "Easter eggs GTA 6 : tous les secrets trouvés",
     "h1": "Tous les easter eggs et secrets de GTA 6", "desc": "Bigfoot, l'œuf de Pâques, l'appartement de Dexter… tous les easter eggs de GTA 6 trouvés par les joueurs, avec où les trouver.",
     "intro": "Rockstar a caché des dizaines de clins d'œil dans Leonida. On liste ici ceux qui sont trouvés et relayés, avec leur statut (confirmé, rumeur, à tester) et où les chercher. Coche ceux que tu as trouvés dans la chasse aux secrets.",
     "kw": ["easter egg", "secret"], "eggs": True},
    {"slug": "gta-6-police", "nav": "Police", "title": "Police GTA 6 : étoiles, recherche et comment semer les flics",
     "h1": "La police dans GTA 6", "desc": "Comment marche le système de recherche de GTA 6 et comment semer la police : étoiles, icônes, zones chaudes.",
     "intro": "La police de GTA 6 a de la mémoire : elle retient ta tenue, ta voiture, ton arme. Tous nos conseils pour comprendre le système de recherche et semer les flics sont ici.",
     "kw": ["police", "flics"]},
    {"slug": "gta-6-debuter", "nav": "Bien débuter", "title": "Bien débuter GTA 6 : astuces, réglages et erreurs à éviter",
     "h1": "Bien débuter sur GTA 6", "desc": "Les astuces, réglages et réflexes à avoir pour bien démarrer GTA 6 sans spoiler.",
     "intro": "Tu lances GTA 6 pour la première fois ? Réglages, premiers réflexes, erreurs à éviter, spoilers à bloquer : tout ce qu'il faut savoir pour bien démarrer, sans rien te gâcher.",
     "kw": ["débuter", "démarrer", "réglages"]},
]


def hub_articles(h, arts):
    """Articles d'une page sujet, triés par pertinence puis par date.
    - champ « topics » de l'article : sujets choisis à la rédaction (le premier = sujet principal) ;
    - sans « topics » (vieux articles) : mot-clé entier dans le titre ou le chapô seulement, jamais dans le corps
      (avant, « dollars » dans un article sur les licenciements le faisait apparaître dans « Argent »).
    Renvoie (principaux, secondaires)."""
    main_, side = [], []
    for a in arts:
        if "topics" in a:
            if a["topics"][:1] == [h["slug"]]:
                main_.append(a)
            elif h["slug"] in a["topics"]:
                side.append(a)
        else:
            txt = (a["title"] + " " + a["chapo"]).lower()
            if any(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", txt) for k in h["kw"]):
                side.append(a)
    pin = h.get("pin", [])
    main_.sort(key=lambda a: pin.index(a["slug"]) if a["slug"] in pin else len(pin))  # tri stable : la date reste l'ordre secondaire
    return main_, side


CAPTURE_CREDIT = "Capture en jeu : GTASTUCE VICE"


def egg_card(x, check=False, found_label="Je l'ai trouvé", prefix=""):
    btn = (f'<button class="check" type="button" data-id="{e(x["id"])}" aria-pressed="false">{found_label}</button>' if check else "")
    z = zone_of(x)
    cap = ""
    if x.get("capture"):  # capture en jeu de l'emplacement (mini-carte visible), affichée à l'ouverture de « Où et comment »
        cap = (f'<figure class="capt">{img_html(x["capture"], prefix, "egg", x.get("capture_alt", "Emplacement : " + x["title"]))}'
               f'<figcaption><span>{e(x.get("capture_credit", CAPTURE_CREDIT))}</span></figcaption></figure>')
    return (f'<article class="egg" id="egg-{e(x["id"])}" data-st="{e(x["status"])}" data-zone="{z}">'
            f'<div class="egg-top">{status_badge(x["status"])}{tested_html(x)}</div>'
            f'<h4>{e(x["title"])}</h4>'
            f'<details><summary>Où et comment</summary>{cap}<p><strong>Où :</strong> {e(x["where"])}</p><p>{e(x["how"])}</p>'
            f'<p><a class="src" href="{e(x["source"]["u"])}" target="_blank" rel="noopener">Source : {e(x["source"]["t"])}</a></p></details>'
            f'{btn}</article>')


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
    return (f'<a href="{prefix}gta-6-codes-triche.html">Codes de triche</a>'
            + "".join(f'<a href="{prefix}{h["slug"]}.html">{e(h["nav"])}</a>' for h in HUBS))


def simple_page(path, title, desc, h1, kicker, body, ld=None, topics=True):
    ldj = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    title, desc = title_tag(title), trim(desc)
    more = f'<h2>Les autres sujets</h2>\n<div class="topics">{topics_html()}</div>' if topics else ""
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
{header_html("", path)}
<main id="contenu"><div class="wrap">
<div class="kicker">{e(kicker)}</div>
<h1>{e(h1)}</h1>
{body}
{more}
</div></main>
{footer_html()}
</body>
</html>
"""


AUTHOR_BIO = ("Joueur PS5 depuis le premier jour de GTA 6, il teste les astuces en jeu dès qu'il peut et capture lui-même les images du site. "
              "Quand une info n'est pas encore vérifiée, la source est citée et c'est écrit « à tester ».")
ABOUT_BODY = """<p class="lead">GTASTUCE VICE, c'est le fil français de GTA 6 : l'actu, les astuces, les guides et les secrets de Leonida, expliqués simplement, en français et sans spoiler.</p>
<div class="box"><h2 style="margin-top:0">Qui on est</h2>
<p>Un projet de joueurs passionnés, lancé pour la sortie de GTA 6. On joue sur PS5, on suit tout ce qui sort sur le jeu, et on le partage sur ce site et sur TikTok, Instagram et YouTube (@gtastucevice).</p></div>
<div class="box" id="romeo"><img class="romeo" src="assets/romeo.jpg" alt="Roméo, fondateur de GTASTUCE VICE" width="120" height="120"><h2 style="margin-top:0">Roméo, le fondateur</h2>
<p>Salut, moi c'est Roméo. J'ai lancé GTASTUCE VICE pour la sortie de GTA 6 : je joue sur PS5, je fouille Leonida, je filme mes parties et je teste les astuces avant de les publier quand c'est possible. Les vidéos gameplay et les captures « Capture en jeu : GTASTUCE VICE » du site viennent de mes parties.</p>
<p>Une info fausse, un secret que tu as trouvé ? Écris-moi via la page <a href="contact.html">Contact</a> ou sur TikTok <a href="https://www.tiktok.com/@gtastucevice" target="_blank" rel="noopener">@gtastucevice</a>.</p></div>
<div class="box"><h2 style="margin-top:0">Comment on travaille</h2>
<ul>
<li><strong>On cite toujours nos sources.</strong> Chaque article se termine par la liste des médias d'où viennent les infos, pour que tu puisses vérifier.</li>
<li><strong>On te dit quand ce n'est pas sûr.</strong> Une info qui ne vient que de joueurs est marquée « rumeur » ou « à tester en jeu », un chiffre non officiel « estimation ».</li>
<li><strong>Zéro spoiler, zéro leak, zéro glitch.</strong> Pas de fin d'histoire, pas de contenu volé, pas de glitch d'argent ni de mod qui risque de te faire bannir. Les seuls codes de triche dont on parle sont ceux prévus par Rockstar dans le mode histoire.</li>
<li><strong>Transparence :</strong> nos articles sont rédigés avec l'aide d'outils d'intelligence artificielle, à partir des sources citées, et mis à jour dès qu'une info évolue.</li>
</ul></div>
<div class="box"><h2 style="margin-top:0">Nous contacter</h2>
<p>Une info, une correction, un secret trouvé en jeu, une proposition de partenariat ? Écris-nous à <a href="mailto:gtastucevice@gmail.com">gtastucevice@gmail.com</a> ou en commentaire sur nos réseaux. Tous les moyens de nous joindre sont sur la <a href="contact.html">page Contact</a>.</p>
<p style="color:var(--mute);font-size:14px">Site de fans non officiel. Non affilié à Rockstar Games ni à Take-Two Interactive. Grand Theft Auto est une marque de Take-Two Interactive. Images : Rockstar Games, sauf mention contraire.</p></div>"""


CONTACT_BODY = """<p class="lead">Une info, une correction, un secret trouvé en jeu, une proposition de partenariat ? Voici comment nous joindre.</p>
<div class="box legal"><h2 style="margin-top:0">Par email</h2>
<p><a class="btn" href="mailto:gtastucevice@gmail.com">gtastucevice@gmail.com</a></p>
<p>Pour une correction, indique l'adresse de la page et ce qui ne va pas. On corrige et on met la date de mise à jour sur l'article.</p></div>
<div class="box legal"><h2 style="margin-top:0">Tu as trouvé un secret en jeu ?</h2>
<p>Utilise le formulaire <a href="index.html#proposer">Proposer un secret</a> : on vérifie et on te crédite avec ton pseudo.</p></div>
<div class="box legal"><h2 style="margin-top:0">Sur les réseaux</h2>
<p><a href="https://www.tiktok.com/@gtastucevice" rel="noopener">TikTok</a> · <a href="https://www.instagram.com/gtastucevice/" rel="noopener">Instagram</a> · <a href="https://www.youtube.com/@gtastucevice" rel="noopener">YouTube</a> : @gtastucevice</p></div>
<div class="box legal"><h2 style="margin-top:0">La newsletter</h2>
<p>Le Brief de Vice arrive chaque vendredi. <a href="index.html#newsletter">Inscris-toi sur l'accueil</a>.</p></div>"""

LEGAL_BODY = """<div class="box legal"><h2 style="margin-top:0" id="editeur">Éditeur</h2>
<p>GTASTUCE VICE, site édité par un particulier à titre non professionnel. Conformément à l'article 6, III, 2 de la loi n° 2004-575 du 21 juin 2004 (LCEN), l'éditeur a choisi de ne pas publier son identité ; elle est connue de l'hébergeur. Contact : <a href="mailto:gtastucevice@gmail.com">gtastucevice@gmail.com</a>.</p></div>
<div class="box legal"><h2 style="margin-top:0" id="hebergeur">Hébergeur</h2>
<p>GitHub, Inc. (GitHub Pages), 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p></div>
<div class="box legal"><h2 style="margin-top:0" id="confidentialite">Confidentialité</h2>
<p><strong>Newsletter :</strong> ton adresse est transmise via le service FormSubmit (formsubmit.co) à la boîte mail du projet. Elle sert uniquement à l'envoi du Brief de Vice : elle n'est ni vendue ni partagée. Tu peux te désinscrire depuis chaque email ou demander la suppression de tes données à gtastucevice@gmail.com.</p>
<p><strong>Proposer un secret :</strong> ton pseudo et ta proposition sont transmis par FormSubmit à la boîte mail du projet, uniquement pour vérifier le secret et te créditer. Ne mets pas d'information personnelle.</p>
<p><strong>Chasse aux secrets :</strong> ta progression est enregistrée uniquement dans ton navigateur (stockage local). Rien n'est envoyé. Le choix « Couper les animations » est enregistré de la même façon.</p>
<p><strong>Mesure d'audience :</strong> le site utilise GoatCounter (gtastucevice.goatcounter.com) et Metricool pour compter les visites de façon agrégée.</p>
<p><strong>Polices de caractères :</strong> elles sont chargées depuis Google Fonts ; ton navigateur contacte donc les serveurs de Google à l'ouverture des pages.</p></div>
<div class="box legal"><h2 style="margin-top:0" id="affiliation">Liens affiliés</h2>
<p>Les pages <a href="matos.html">Le matos</a> et <a href="gta-6-idees-cadeaux.html">Idées cadeaux</a>, ainsi que l'encart en bas de certains articles, contiennent des liens affiliés Amazon, toujours signalés. En tant que Partenaire Amazon, GTASTUCE VICE réalise un bénéfice sur les achats remplissant les conditions requises. Ça ne change pas le prix que tu paies.</p></div>
<div class="box legal"><h2 style="margin-top:0" id="marques">Marques et images</h2>
<p>Site de fans non officiel. Non affilié à Rockstar Games ni à Take-Two Interactive. Grand Theft Auto est une marque de Take-Two Interactive. Images : Rockstar Games (captures officielles), sauf mention contraire.</p></div>"""


# ---------- Carte des secrets (schéma, positions approximatives) ----------
ZONES = {
    "kalaga": ("Mount Kalaga", 118, 78), "ambrosia": ("Ambrosia", 238, 112), "gellhorn": ("Port Gellhorn", 92, 196),
    "grassrivers": ("Grassrivers", 196, 290), "vice-city": ("Vice City", 308, 318), "keys": ("Leonida Keys", 262, 420),
    "mer": ("En mer", 352, 432),
}
LEONIDA_PTS = [(14, 58), (120, 50), (232, 50), (344, 44), (354, 84), (342, 124), (340, 172), (352, 222), (368, 272),
               (376, 322), (366, 362), (334, 386), (300, 392), (268, 378), (234, 362), (204, 356), (176, 340), (158, 314),
               (146, 284), (128, 258), (104, 238), (78, 226), (52, 222), (30, 210), (18, 170), (12, 110)]


def smooth_path(pts):
    """Contour arrondi (Catmull-Rom -> Bézier) à partir de points : côtes moins anguleuses."""
    n = len(pts); d = f"M{pts[0][0]} {pts[0][1]}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6); c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]} {p2[1]}"
    return d + " Z"


LEONIDA_PATH = smooth_path(LEONIDA_PTS)
KEYS = [(300, 398, 16, 6), (272, 404, 18, 7), (242, 418, 20, 7), (212, 434, 20, 7), (182, 448, 18, 6), (154, 460, 14, 5), (130, 468, 10, 4)]


def land_svg():
    """Le fond de carte : terre, lac Leonida, relief de Mount Kalaga, marais, Vice City et ses îles, chapelet des Keys, ponts."""
    keys = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}"/>' for x, y, rx, ry in KEYS)
    bridge = " ".join(f"{x},{y}" for x, y, _, _ in KEYS)
    marsh = "".join(f'<path d="M{x} {y} q8 -6 16 0 t16 0"/>' for x, y in [(170, 276), (196, 290), (150, 300), (182, 318), (214, 306), (204, 334), (226, 322), (160, 330)])
    peaks = "".join(f'<path d="M{x} {y} l9 -16 l9 16 z"/>' for x, y in [(96, 92), (112, 84), (128, 94), (142, 86), (106, 106), (152, 100)])
    blocks = "".join(f'<rect x="{x}" y="{y}" width="7" height="7" rx="1"/>' for x, y in [(318, 300), (328, 300), (318, 310), (328, 310), (338, 310), (328, 320), (338, 320), (318, 320), (338, 330), (328, 330)])
    return (f'<g class="land"><path d="{LEONIDA_PATH}"/>{keys}<ellipse class="isle" cx="364" cy="312" rx="5" ry="30"/><ellipse class="isle" cx="352" cy="352" rx="7" ry="5"/></g>'
            f'<polyline class="bridge" points="{bridge}"/>'
            f'<g class="relief">{peaks}</g><ellipse class="lake" cx="262" cy="166" rx="28" ry="20"/>'
            f'<g class="marsh">{marsh}</g><path class="river" d="M120 120 q20 40 10 80 t30 60"/><g class="city">{blocks}</g>')


ZONE_ORDER = ["vice-city", "keys", "grassrivers", "mer", "gellhorn", "ambrosia", "kalaga"]
LOOSE = ("partout", "Partout ou lieu à préciser")


def zone_of(s):
    return s.get("zone") if s.get("zone") in ZONES else LOOSE[0]


def map_svg(secrets, link_prefix=""):
    """Carte schématique de Leonida, zoomable (boutons, double-clic, pincement, Ctrl + molette), un repère par secret localisé."""
    pins, per = [], {}
    for s in secrets:
        z = s.get("zone")
        if z not in ZONES:
            continue
        k = per.get(z, 0); per[z] = k + 1
        _, x, y = ZONES[z]
        x += [0, 22, -22, 12, -12, 30, -30, 0][k % 8]; y += [18, 30, 30, 44, 44, 14, 14, 58][k % 8]
        pins.append(f'<a class="pin" data-id="{e(s["id"])}" data-zone="{e(z)}" href="{link_prefix}#egg-{e(s["id"])}" aria-label="{e(s["title"])}" transform="translate({x} {y})">'
                    f'<title>{e(s["title"])}</title><g class="pg"><circle class="halo" r="14"/><circle class="dot" r="8"/></g></a>')
    LBL = {"keys": (150, 488)}
    labels = "".join(f'<text x="{LBL.get(k, (x, y))[0]}" y="{LBL.get(k, (x, y))[1]}" text-anchor="middle">{e(n)}</text>' for k, (n, x, y) in ZONES.items())
    ctrl = ('<div class="map-ctrl" role="group" aria-label="Zoom de la carte">'
            '<button type="button" data-zoom="in" aria-label="Zoomer">+</button>'
            '<button type="button" data-zoom="out" aria-label="Dézoomer">−</button>'
            '<button type="button" data-zoom="reset" aria-label="Voir toute la carte">⟲</button></div>')
    return (f'<figure class="map" data-map>{ctrl}<svg viewBox="0 0 400 500" role="img" aria-label="Carte simplifiée de Leonida avec les secrets">'
            f'<defs><linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B0D3C"/><stop offset="1" stop-color="#2A1050"/></linearGradient></defs>'
            f'<rect x="-400" y="-500" width="1200" height="1500" fill="url(#sea)"/>'
            f'{land_svg()}'
            f'<g class="lbl">{labels}</g>{"".join(pins)}</svg>'
            f'<figcaption>Positions approximatives. Zoome avec + et −, un double-clic ou deux doigts ; fais glisser pour te déplacer. Rose = à trouver, turquoise = trouvé.</figcaption></figure>')


CARTE_CATS = {"secret": ("Secrets", "#FF3D7F"), "arme": ("Armes gratuites", "#FFE45C"), "plongee": ("Plongée et épaves", "#2EE6D6"),
              "peche": ("Pêche", "#7FB2FF"), "activite": ("Activités", "#FF9A3D")}


def carte_html(secrets):
    """Grande carte interactive de la page Carte : secrets + lieux utiles (lieux.json), filtres par catégorie, fiche au clic, liste sous la carte."""
    lieux = json.load(open(os.path.join(ROOT, "lieux.json"), encoding="utf-8"))
    pts, per = [], {}
    for x in secrets:
        z = x.get("zone")
        if z not in ZONES:
            continue
        k = per.get(z, 0); per[z] = k + 1; _, zx, zy = ZONES[z]
        pts.append({"id": "s-" + x["id"], "cat": "secret", "title": x["title"], "where": x.get("where", ""), "zone": z,
                    "x": zx + [0, 22, -22, 12, -12, 30, -30, 0][k % 8], "y": zy + [18, 30, 30, 44, 44, 14, 14, 58][k % 8],
                    "link": f"index.html#egg-{x['id']}", "st": x.get("status", "")})
    pts += [dict(l) for l in lieux if l.get("zone") in ZONES]
    spots = "".join(
        f'<a class="spot" href="{e(p["link"])}" data-i="{i}" data-cat="{p["cat"]}" transform="translate({p["x"]} {p["y"]})" aria-label="{e(p["title"])}">'
        f'<title>{e(p["title"])}</title><circle class="halo" r="12" fill="{CARTE_CATS[p["cat"]][1]}"/><circle class="dot" r="7" fill="{CARTE_CATS[p["cat"]][1]}"/></a>'
        for i, p in enumerate(pts))
    LBL = {"keys": (150, 488)}
    labels = "".join(f'<text x="{LBL.get(k, (x, y))[0]}" y="{LBL.get(k, (x, y))[1]}" text-anchor="middle">{e(n)}</text>' for k, (n, x, y) in ZONES.items())
    ctrl = ('<div class="map-ctrl" role="group" aria-label="Zoom de la carte"><button type="button" data-zoom="in" aria-label="Zoomer">+</button>'
            '<button type="button" data-zoom="out" aria-label="Dézoomer">−</button><button type="button" data-zoom="reset" aria-label="Voir toute la carte">⟲</button></div>')
    chips = "".join(f'<button type="button" class="chip cchip" data-cat="{k}" aria-pressed="true"><i style="background:{c}"></i>{e(n)} '
                    f'<b>{sum(p["cat"] == k for p in pts)}</b></button>' for k, (n, c) in CARTE_CATS.items())
    lists = ""
    for k, (n, c) in CARTE_CATS.items():
        items = [p for p in pts if p["cat"] == k]
        if items:
            lists += (f'<section class="clist" data-cat="{k}"><h3><i style="background:{c}"></i>{e(n)}</h3><ul>'
                      + "".join(f'<li><a href="{e(p["link"])}"><strong>{e(p["title"])}</strong></a> <span class="cz">{e(ZONES[p["zone"]][0])}</span><br>{e(p["where"])}</li>' for p in items)
                      + "</ul></section>")
    data = json.dumps([{k: p[k] for k in ("title", "where", "link", "cat")} | {"zone": ZONES[p["zone"]][0]} for p in pts], ensure_ascii=False).replace("</", "<\\/")
    return ('<h2>La carte interactive de Leonida</h2>'
            f'<div class="carte-tools" role="group" aria-label="Afficher sur la carte">{chips}</div>'
            f'<div class="carte-grid"><figure class="map map-big" data-map>{ctrl}<svg viewBox="0 0 400 500" role="img" aria-label="Carte schématique de Leonida avec les secrets et les lieux utiles">'
            '<defs><linearGradient id="sea2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1B0D3C"/><stop offset="1" stop-color="#2A1050"/></linearGradient></defs>'
            f'<rect x="-400" y="-500" width="1200" height="1500" fill="url(#sea2)"/>{land_svg()}<g class="lbl">{labels}</g>{spots}</svg>'
            '<figcaption>Carte schématique dessinée par GTASTUCE VICE d\'après les six régions officielles : positions approximatives, à l\'échelle de la région. '
            'Touche un repère pour voir où et comment.</figcaption></figure>'
            '<aside class="spot-info" id="spot-info" aria-live="polite"><p class="si-hint">Touche un repère sur la carte pour voir ce qu\'il cache.</p></aside></div>'
            '<h2>Zoom sur Key Lento, sur la vraie carte du jeu</h2><p>Nos captures de la carte en jeu (PS5), autour de Key Lento, là où démarre l\'aventure : la boutique de Kenton pour les plongées au trésor, et l\'épave Nuestra Señora de la Ética Laxa au large.</p>'
            '<div class="cmaps">' + "".join(f'<figure><img src="assets/captures/{f}.jpg" alt="{e(a)}" loading="lazy" width="1280" height="715"><figcaption>{e(a)} · Capture en jeu : GTASTUCE VICE</figcaption></figure>'
            for f, a in [("carte-gta-6-key-lento-kenton", "Key Lento sur la carte du jeu, avec la fiche de Kenton (plongées au trésor)"),
                         ("carte-gta-6-epave-nuestra-senora", "Le site de plongée Nuestra Señora de la Ética Laxa, au large de Key Lento")]) + '</div>'
            f'<h2>Tous les lieux, région par région</h2><div class="clists">{lists}</div>'
            f'<script>(function(){{var D={data},C={json.dumps({k: v for k, v in CARTE_CATS.items()}, ensure_ascii=False)},box=document.getElementById("spot-info");'
            'function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;"}[c]})}'
            'document.querySelectorAll(".spot").forEach(function(a){a.addEventListener("click",function(ev){ev.preventDefault();var p=D[+a.dataset.i];'
            'document.querySelectorAll(".spot.on").forEach(function(x){x.classList.remove("on")});a.classList.add("on");'
            'box.innerHTML="<p class=\\"si-cat\\"><i style=\\"background:"+C[p.cat][1]+"\\"></i>"+esc(C[p.cat][0])+" · "+esc(p.zone)+"</p><h3>"+esc(p.title)+"</h3><p>"+esc(p.where)+"</p><a class=\\"btn\\" href=\\""+esc(p.link)+"\\">Voir le guide</a>";'
            'if(window.innerWidth<900)box.scrollIntoView({block:"nearest",behavior:"smooth"});});});'
            'document.querySelectorAll(".cchip").forEach(function(b){b.addEventListener("click",function(){var on=b.getAttribute("aria-pressed")!=="true";b.setAttribute("aria-pressed",String(on));'
            'document.querySelectorAll(\'.spot[data-cat="\'+b.dataset.cat+\'"]\').forEach(function(x){x.style.display=on?"":"none"});});});})();</script>')


def hunt_html(secrets, check=True, link_prefix=""):
    """Chasse aux secrets : carte collante + progression par zone à gauche, filtres + secrets rangés par zone à droite."""
    zones = [z for z in ZONE_ORDER if any(zone_of(s) == z for s in secrets)]
    if any(zone_of(s) == LOOSE[0] for s in secrets):
        zones.append(LOOSE[0])
    name = lambda z: ZONES[z][0] if z in ZONES else LOOSE[1]
    zone_btns = "".join(
        f'<li><button type="button" class="zbtn" data-zone="{z}"' + (f' data-x="{ZONES[z][1]}" data-y="{ZONES[z][2]}"' if z in ZONES else "")
        + f' aria-pressed="false"><span>{e(name(z))}</span><b class="zn" data-zone-count="{z}">0/{sum(zone_of(s) == z for s in secrets)}</b></button></li>' for z in zones)
    side = (f'<aside class="hunt-side"><div class="hunt-sticky">{map_svg(secrets, link_prefix)}'
            f'<h3 class="zh">Par zone</h3><ul class="zones">{zone_btns}</ul></div></aside>')
    st_chips = "".join(f'<button type="button" class="chip" data-st="{k}" aria-pressed="{str(k == "all").lower()}">{e(v)}</button>'
                       for k, v in [("all", "Tous")] + [(k, v[0]) for k, v in STATUS.items()])
    tools = ('<div class="hunt-tools"><label class="sr-only" for="egg-q">Chercher un secret</label>'
             '<input id="egg-q" type="search" placeholder="Chercher un secret (ex : Bigfoot, Vice City…)" autocomplete="off">'
             f'<div class="chips" role="group" aria-label="Filtrer par statut">{st_chips}</div>'
             + ('<label class="hide-found"><input type="checkbox" id="egg-hide"> Masquer ceux que j\'ai trouvés</label>' if check else "")
             + '<p class="scount" id="egg-count" role="status" aria-live="polite"></p></div>')
    groups = []
    for z in zones:
        items = [s for s in secrets if zone_of(s) == z]
        groups.append(f'<section class="egg-group" data-zone="{z}" aria-labelledby="zg-{z}"><h3 class="zg" id="zg-{z}">{e(name(z))} '
                      f'<span class="zgn" data-zone-count="{z}">0/{len(items)}</span></h3><div class="eggs">'
                      + "".join(egg_card(x, check) for x in items) + "</div></section>")
    main_ = (f'<div class="hunt-main">{tools}<div id="eggs">{"".join(groups)}</div>'
             '<p class="empty-eggs" hidden>Aucun secret ne correspond. Change de filtre ou de zone.</p></div>')
    return f'<div class="hunt-grid">{side}{main_}</div>'


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
.map .land .isle{fill:#3A1D6B}.map .bridge{fill:none;stroke:#FF5FA2;stroke-width:1;stroke-dasharray:2 3;opacity:.7}.map .relief path{fill:#4C2A85;stroke:#7B5BB8;stroke-width:1}.map .lake{fill:#1F0E45;stroke:#7FB2FF;stroke-width:1.5;opacity:.9}.map .marsh path{fill:none;stroke:#2EE6D6;stroke-width:1.2;opacity:.45}.map .river{fill:none;stroke:#7FB2FF;stroke-width:1.5;opacity:.5}.map .city rect{fill:#FFE45C;opacity:.35}.map-big svg{max-width:640px}.carte-tools{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}.cchip i,.clist h3 i,.si-cat i{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:-1px}.cchip{display:inline-flex;align-items:center;min-height:40px;padding:0 14px;border-radius:999px;background:var(--night2);border:1px solid var(--line);color:var(--white);font:700 14px Inter,sans-serif;cursor:pointer}.cchip[aria-pressed=false]{opacity:.45}.cchip b{margin-left:4px;color:var(--mute)}.spot{cursor:pointer}.spot .dot{stroke:#fff;stroke-width:2}.spot .halo{opacity:.22}.spot.on .dot{stroke:#FFE45C;stroke-width:4}.spot:focus-visible .dot{stroke:#FFE45C;stroke-width:4}.spot-info{background:var(--night2);border:1px solid var(--line);border-radius:18px;padding:18px;margin:0 0 20px}.spot-info h3{margin:6px 0 8px}.si-cat{font-size:13px;color:var(--mute);margin:0}.si-hint{color:var(--soft);margin:0}.cmaps{display:grid;gap:16px;margin:0 0 10px}.cmaps img{width:100%;height:auto;border-radius:14px;border:1px solid var(--line)}.cmaps figcaption{font-size:13px;color:var(--mute);margin-top:6px}@media (min-width:900px){.cmaps{grid-template-columns:1fr 1fr}}.clists{display:grid;gap:16px}.clist ul{margin:0;padding-left:18px}.clist li{margin:0 0 10px;color:var(--soft)}.cz{font-size:12px;color:var(--mute)}@media (min-width:900px){.carte-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:22px;align-items:start}.spot-info{position:sticky;top:90px}.clists{grid-template-columns:1fr 1fr}}.map-loose{margin:10px 0 0;font-size:14px;color:var(--soft);text-align:center}
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
 header .wrap{gap:4px 12px;padding-top:8px;padding-bottom:6px}
 .brand b{font-size:17px}.brand i{font-size:24px}
 header nav a{white-space:nowrap}
 section{padding:34px 0}
 .une{padding-top:18px}
 a.lead{min-height:300px}a.lead .txt{padding:18px}
 a.lead p{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:15px}
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
const ST=__ST__;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const norm=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
let ARTS=[],EGGS=[];
const q=document.getElementById('q'),out=document.getElementById('sres'),cnt=document.getElementById('scount');
const flat=a=>(a.body||[]).map(b=>typeof b==='string'?b:b.h2||(b.steps||[]).map(s=>s.t+' '+s.d).join(' ')||((b.controls||{}).rows||[]).map(r=>r.join(' ')).join(' ')).join(' ')+' '+(a.quick||'');
const thumb=src=>/^assets\/[^/]+\.jpg$/.test(src)?src.replace(/^assets\/(.+)\.jpg$/,'assets/thumbs/$1-480.jpg'):src;
function score(words,fields){let t=0;for(const w of words){let hit=false;fields.forEach(([txt,wt])=>{if(norm(txt).includes(w)){t+=wt;hit=true}});if(!hit)return 0}return t}
function hl(s,words){let h=esc(s);words.forEach(w=>{if(w.length<2)return;const n=norm(h);let i=n.indexOf(w);if(i>=0)h=h.slice(0,i)+'<mark>'+h.slice(i,i+w.length)+'</mark>'+h.slice(i+w.length)});return h}
function run(){
 const v=q.value.trim();history.replaceState(null,'',v?'?q='+encodeURIComponent(v):location.pathname);
 const words=norm(v).split(/\s+/).filter(w=>w.length>1);
 if(!words.length){out.innerHTML='';cnt.textContent='';return}
 const r=[];
 HUBS.forEach(h=>{const s=score(words,[[h.nav,6],[h.title,3],[h.desc,1]]);if(s)r.push([s+5,`<a class="egglink" href="${h.slug}.html"><span class="cat c-guide">Sujet</span> <strong>${hl(h.title,words)}</strong><small>${esc(h.desc)}</small></a>`])});
 ARTS.forEach(a=>{const s=score(words,[[a.title,6],[a.chapo,3],[flat(a),1]]);if(s)r.push([s,`<a class="post" href="actus/${esc(a.slug)}.html"><img src="${esc(thumb(a.img))}" alt="" loading="lazy" width="480" height="270"><div class="b"><div class="meta"><span class="cat c-${esc(a.cat)}">${CATS[a.cat]||esc(a.cat)}</span></div><h3>${hl(a.title,words)}</h3><p>${esc(a.chapo)}</p></div></a>`])});
 EGGS.forEach(e=>{const s=score(words,[[e.title,6],[e.where,3],[e.how,2]]);if(s)r.push([s,`<a class="egglink" href="index.html#egg-${esc(e.id)}"><span class="cat c-secret">Secret</span> <span class="st st-${esc(e.status)}">${ST[e.status]||''}</span> <strong>${hl(e.title,words)}</strong><small>Où : ${esc(e.where)}</small></a>`])});
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


def chips_html(cats, label, current="all"):
    return (f'<div class="chips" role="group" aria-label="{e(label)}">'
            + "".join(f'<button class="chip" type="button" data-c="{c}" aria-pressed="{str(c == current).lower()}">{"Tout" if c == "all" else e(CATS[c])}</button>' for c in cats)
            + "</div>")


def shared_chrome(t, prefix="", current=""):
    """Remplace la navigation et le pied de page d'une page écrite à la main par les modèles communs."""
    t = fill(t, "nav", nav_html(prefix, current))
    t = fill(t, "footer", footer_inner(prefix))
    return t


# ---------- Le matos (piloté par matos.json) ----------
CADEAUX_SLUG = "gta-6-idees-cadeaux.html"
CADEAUX_TITLE = "Idées cadeaux GTA 6 pour Noël 2026 : quoi offrir (PS5 et Xbox)"
CADEAUX_DESC = "Quoi offrir à un fan de GTA 6 pour Noël : le jeu, la manette DualSense édition limitée, une carte PlayStation ou Xbox, un SSD. Ce qu'il faut vérifier avant d'acheter."
AMAZON_TAG = "gtastucevice-21"
MATOS_CSS = """
.mfilters{margin:0 0 6px}
.mfilters .chips{display:flex;flex-wrap:wrap;gap:8px}
.mfilters .chip{min-height:44px;padding:0 16px;border-radius:999px;border:1px solid var(--line);background:var(--night2);color:var(--white);font:700 14px Inter,sans-serif;cursor:pointer}
.mfilters .chip[aria-pressed="true"]{background:var(--white);color:var(--night);border-color:var(--white)}
.scount{color:var(--soft);font-size:14px;margin:8px 0 0;min-height:1em}
.msec{margin:34px 0 14px;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:clamp(24px,3vw,30px)}
.item h3{margin:0 0 6px;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:22px;line-height:1.15}
.item.noill{grid-template-columns:1fr}
.item .plats{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.item .plat{font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;border:1px solid var(--line);color:var(--soft)}
.item .msrc{font-size:13px;color:var(--mute);margin:0 0 12px}
.item .why a,.item li a{color:var(--teal)}
@media (max-width:640px){.item h3{font-size:20px}}
"""


MATOS_DISC = "<p class=\"disc\">Transparence : certains liens de cette page sont des liens affiliés. Si tu achètes après avoir cliqué, GTASTUCE VICE touche une petite commission, sans que ça te coûte plus cher. C'est ce qui nous permet de rester gratuits. On ne recommande que des critères qu'on vérifierait pour nous-mêmes. <strong>En tant que Partenaire Amazon, GTASTUCE VICE réalise un bénéfice sur les achats remplissant les conditions requises.</strong> Les prix et la disponibilité sont ceux affichés par le vendeur au moment de ta visite. Site non affilié à Sony ni à Microsoft.</p>"


def amazon(q):
    from urllib.parse import quote_plus
    return f"https://www.amazon.fr/s?k={quote_plus(q)}&amp;tag={AMAZON_TAG}"


def matos_html(m):
    labels = {p["id"]: p["label"] for p in m["platforms"]}
    out = ['<div class="mfilters"><div class="chips" role="group" aria-label="Filtrer par plateforme">'
           + "".join(f'<button class="chip" type="button" data-p="{p["id"]}" aria-pressed="{str(p["id"] == "all").lower()}">{e(p["label"])}</button>' for p in m["platforms"])
           + '</div><p class="scount" id="mcount" role="status" aria-live="polite"></p></div>',
           f'<section class="quick" aria-labelledby="mq-t"><h2 id="mq-t">L\'essentiel</h2><p>{e(m["intro_quick"])}</p></section>',
           MATOS_DISC]
    for sec in m["sections"]:
        items = [x for x in m["items"] if x["section"] == sec["id"]]
        if not items:
            continue
        out.append(f'<div class="mgroup" data-sec="{sec["id"]}"><h2 class="msec" id="sec-{sec["id"]}">{e(sec["title"])}</h2>')
        for x in items:
            ill = f'<img class="ill" src="{e(x["ill"])}" alt="{e(x.get("ill_alt", ""))}" width="640" height="360" loading="lazy">' if x.get("ill") else ""
            tag = status_badge(x["status"]) if x.get("status") else f'<span class="tag">{e(x["tag"])}</span>'
            plats = "".join(f'<span class="plat">{e(labels[p])}</span>' for p in x["plats"])
            lis = "".join(f"<li>{li}</li>" for li in x["list"])  # HTML écrit à la main dans matos.json (liens internes, gras)
            src = f'<p class="msrc">Source : <a href="{e(x["source"]["u"])}" target="_blank" rel="noopener">{e(x["source"]["t"])}</a></p>' if x.get("source") else ""
            links = []
            for i, l in enumerate(x["links"]):
                if l.get("url"):
                    links.append(f'<a class="ghost" href="{e(l["url"])}" target="_blank" rel="noopener">{e(l["label"])}</a>')
                else:
                    cls = "btn aff" if i == 0 else "ghost aff"
                    links.append(f'<a class="{cls}" href="{amazon(l["q"])}" target="_blank" rel="sponsored noopener" data-goatcounter-click="matos-{e(x["id"])}-{i + 1}" data-goatcounter-title="{e(l["label"])}">{e(l["label"])}<span class="sr-only"> (Amazon, lien affilié)</span></a>')
            lk = f'<div class="links">{"".join(links)}</div>' if links else ""
            out.append(f'<section class="item{"" if ill else " noill"}" id="{e(x["id"])}" data-plats="{" ".join(x["plats"])}">{ill}<div class="itxt">'
                       f'{tag}<h3>{e(x["title"])}</h3><div class="plats">{plats}</div><p class="why">{x["why"]}</p>{src}<ul>{lis}</ul>{lk}</div></section>')
        out.append("</div>")
    return "\n".join(out)


def build_static_pages(arts, secrets):
    home = [a for a in arts if a["cat"] != "guide"]
    guides = [a for a in arts if a["cat"] in ("guide", "astuce")]
    # ---------- Accueil (rendu complet au build : plus de second rendu en JavaScript) ----------
    p = os.path.join(ROOT, "index.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("", "GTAstuce Vice – Astuces, actus et secrets GTA 6 en français",
                                   "GTASTUCE VICE (GTAstuce) : astuces GTA 6, actus, guides, easter eggs et secrets de Leonida, en français, sourcés et sans spoiler."))
    t = shared_chrome(t)
    if home:
        L = home[0]
        t = fill(t, "lead", f'<a class="lead" href="actus/{e(L["slug"])}.html">{img_html(L["img"], "", "lead", priority=True)}<span class="ov"></span><div class="txt">{meta_html(L)}<h2>{e(L["title"])}</h2><p>{e(L["chapo"])}</p></div></a>')
        t = fill(t, "side", "".join(f'<a class="mini" href="actus/{e(a["slug"])}.html">{img_html(a["img"], "", "mini")}<div>{meta_html(a)}<h3>{e(a["title"])}</h3></div></a>' for a in home[1:5]))
        tk = "".join(f'<a href="actus/{e(a["slug"])}.html">{e(a["title"])}</a>' for a in home[:8])
        dup = "".join(f'<a href="actus/{e(a["slug"])}.html" tabindex="-1">{e(a["title"])}</a>' for a in home[:8])
        t = fill(t, "ticker", tk + f'<span aria-hidden="true" style="display:contents">{dup}</span>')
        # Le fil : tous les articles sont dans la page ; le filtre ne fait qu'afficher/masquer (9 max)
        cards = []
        for i, a in enumerate(home):
            vis = 5 <= i < 14
            cards.append(post_card(a, attrs=f' data-cat="{e(a["cat"])}"' + (' data-top="1"' if i < 5 else "") + ("" if vis else " hidden")))
        t = fill(t, "feed", "".join(cards))
        cats = ["all"] + [c for c in CATS if c != "guide" and any(a["cat"] == c for a in home)]
        t = fill(t, "chips", chips_html(cats, "Filtrer les actus"))
    t = fill(t, "guides", "".join(post_card(a) for a in guides[:6]))
    t = fill(t, "topics", topics_html())
    t = fill(t, "legend", legend_html())
    t = fill(t, "hunt", hunt_html(secrets, check=True))
    t = fill(t, "sc", f"0/{len(secrets)}")
    t = fill(t, "css", MAP_CSS + SEARCH_CSS + MOBILE_CSS)
    t = fill(t, "ld", '<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "WebSite", "name": "GTASTUCE VICE", "alternateName": ["GTAstuce", "GTA Stuce", "GTAstuce Vice", "gtastucevice"], "url": BASE + "/", "inLanguage": "fr-FR",
         "potentialAction": {"@type": "SearchAction", "target": BASE + "/recherche.html?q={search_term_string}", "query-input": "required name=search_term_string"}},
        {"@context": "https://schema.org", "@type": "Organization", "name": "GTASTUCE VICE", "alternateName": "GTAstuce", "url": BASE + "/", "logo": BASE + "/favicon-512.png", "email": "gtastucevice@gmail.com",
         "sameAs": ["https://www.tiktok.com/@gtastucevice", "https://www.instagram.com/gtastucevice/", "https://www.youtube.com/@gtastucevice"]}], ensure_ascii=False) + "</script>")
    open(p, "w", encoding="utf-8").write(t)
    # ---------- Liste des actus (statique + filtre) ----------
    p = os.path.join(ROOT, "actus.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("actus.html", "Actus GTA 6 – GTASTUCE VICE", "Toute l'actu GTA 6 en français : news, tests, astuces, secrets et dramas, sourcés."))
    t = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Toute l\'actu GTA 6 en français : news, tests, astuces, secrets et dramas, sourcés.">', t, count=1)
    t = shared_chrome(t, "", "actus.html")
    t = fill(t, "css", SEARCH_CSS + MOBILE_CSS)
    cats = ["all"] + [c for c in CATS if any(a["cat"] == c for a in arts)]
    t = fill(t, "actuslist", '<div class="kicker">Le fil GTA 6</div><h1 class="ptitle">Les actus</h1>'
             '<p class="plead">News, tests, astuces, guides, secrets et dramas de GTA 6. Chaque info est sourcée : si c\'est une rumeur ou à tester en jeu, on te le dit.</p>'
             + chips_html(cats, "Filtrer par catégorie") + '<p class="scount" id="fcount" role="status" aria-live="polite"></p>'
             '<div class="feed">' + "".join(post_card(a, h="h2", attrs=f' data-cat="{e(a["cat"])}"') for a in arts) + "</div>"
             '<p class="note">Images : Rockstar Games (captures officielles), sauf mention contraire. Site de fans non officiel, non affilié à Rockstar Games ni à Take-Two.</p>')
    open(p, "w", encoding="utf-8").write(t)
    # ---------- Matos ----------
    p = os.path.join(ROOT, "matos.html"); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block("matos.html", "Le matos pour GTA 6 : PS5, Xbox, PC et créateurs", "Le matos utile pour GTA 6 sur PS5 et Xbox Series, et pour filmer tes parties : stockage, casque, manette, écran, réseau. Les critères à vérifier avant d'acheter."))
    t = re.sub(r"<title>.*?</title>", "<title>Le matos pour GTA 6 : PS5, Xbox, PC et créateurs</title>", t, count=1)
    t = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Le matos utile pour GTA 6 sur PS5 et Xbox Series, et pour filmer tes parties : stockage, casque, manette, écran, réseau. Les critères avant d\'acheter.">', t, count=1)
    t = shared_chrome(t, "", "matos.html")
    t = fill(t, "css", SEARCH_CSS + MOBILE_CSS + MATOS_CSS)
    matos = json.load(open(os.path.join(ROOT, "matos.json"), encoding="utf-8"))
    for x in matos["items"]:  # garde-fous
        assert x["section"] in {s["id"] for s in matos["sections"]}, x["id"]
        assert set(x["plats"]) <= {p["id"] for p in matos["platforms"]}, x["id"]
    t = fill(t, "matos", matos_html(matos))
    open(p, "w", encoding="utf-8").write(t)
    # ---------- Idées cadeaux (même moteur que Le matos, piloté par cadeaux.json) ----------
    p = os.path.join(ROOT, CADEAUX_SLUG); t = open(p, encoding="utf-8").read()
    t = fill(t, "head", head_block(CADEAUX_SLUG, CADEAUX_TITLE, CADEAUX_DESC))
    t = re.sub(r"<title>.*?</title>", f"<title>{e(CADEAUX_TITLE)}</title>", t, count=1)
    t = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(CADEAUX_DESC)}">', t, count=1)
    t = shared_chrome(t, "", CADEAUX_SLUG)
    t = fill(t, "css", SEARCH_CSS + MOBILE_CSS + MATOS_CSS)
    cad = json.load(open(os.path.join(ROOT, "cadeaux.json"), encoding="utf-8"))
    for x in cad["items"]:
        assert x["section"] in {s["id"] for s in cad["sections"]}, x["id"]
        assert set(x["plats"]) <= {p["id"] for p in cad["platforms"]}, x["id"]
    t = fill(t, "matos", matos_html(cad).replace('data-goatcounter-click="matos-', 'data-goatcounter-click="cadeau-'))
    open(p, "w", encoding="utf-8").write(t)
    # ---------- Pages simples ----------
    org = {"@context": "https://schema.org", "@type": "Organization", "name": "GTASTUCE VICE", "url": BASE + "/", "logo": f"{BASE}/favicon-512.png", "email": "gtastucevice@gmail.com",
           "sameAs": ["https://www.tiktok.com/@gtastucevice", "https://www.instagram.com/gtastucevice/", "https://www.youtube.com/@gtastucevice"]}
    open(os.path.join(ROOT, "a-propos.html"), "w", encoding="utf-8").write(
        simple_page("a-propos.html", "Qui sommes-nous", "Qui est derrière GTASTUCE VICE, comment on choisit et vérifie nos infos sur GTA 6, et comment nous contacter.",
                    "Qui sommes-nous ?", "GTASTUCE VICE", ABOUT_BODY, org))
    open(os.path.join(ROOT, "contact.html"), "w", encoding="utf-8").write(
        simple_page("contact.html", "Contact", "Contacter GTASTUCE VICE : email, correction d'un article, secret trouvé en jeu, réseaux sociaux.",
                    "Nous contacter", "GTASTUCE VICE", CONTACT_BODY, {"@context": "https://schema.org", "@type": "ContactPage", "url": f"{BASE}/contact.html", "about": org}, topics=False))
    open(os.path.join(ROOT, "mentions-legales.html"), "w", encoding="utf-8").write(
        simple_page("mentions-legales.html", "Mentions légales et confidentialité", "Mentions légales, hébergeur, données personnelles, mesure d'audience et liens affiliés du site GTASTUCE VICE.",
                    "Mentions légales et confidentialité", "GTASTUCE VICE", LEGAL_BODY, topics=False))
    # ---------- Recherche ----------
    hubs_js = json.dumps([{"slug": "gta-6-codes-triche", "nav": "Codes de triche cheats", "title": "Codes de triche GTA 6 : la liste complète PS5 et Xbox", "desc": "Les 61 cheats de GTA 6, les combinaisons connues et comment les activer."}]
                         + [{k: h[k] for k in ("slug", "nav", "title", "desc")} for h in HUBS], ensure_ascii=False)
    sp = simple_page("recherche.html", "Rechercher", "Cherche une astuce, un guide ou un secret de GTA 6 sur GTASTUCE VICE.",
                     "Rechercher", "GTASTUCE VICE", SEARCH_BODY.replace("__ICON__", SEARCH_ICO.replace('class="ico"', 'class="ico hs-ico"')) + legend_html())
    sp = sp.replace("</body>", SEARCH_JS.replace("__HUBS__", hubs_js).replace("__ST__", json.dumps(EGG_ST, ensure_ascii=False)) + "\n</body>")
    sp = sp.replace('<meta name="robots" content="max-image-preview:large">', '<meta name="robots" content="noindex,follow">')
    open(os.path.join(ROOT, "recherche.html"), "w", encoding="utf-8").write(sp)
    # ---------- Pages sujets ----------
    hub_dates = {}
    for h in HUBS:
        main_, side = hub_articles(h, arts)
        lst = main_ + side
        hub_dates[h["slug"]] = max([a.get("updated", a["date"]) for a in lst], default="")[:10]
        body = f'<p class="lead">{e(h["intro"])}</p>'
        if h["slug"] == "gta-6-carte":
            body += carte_html(secrets)
        if h.get("eggs"):
            body += ('<h2>La carte et la liste des secrets</h2>' + legend_html() + hunt_html(secrets, check=False)
                     + '<p style="margin-top:16px"><a class="btn" href="index.html#chasse">Coche-les dans la chasse aux secrets</a></p>')
        if main_:
            body += "<h2>L'essentiel</h2><div class=\"feed\">" + "".join(post_card(a) for a in main_) + "</div>"
        if side:
            body += f"<h2>{'Ça en parle aussi' if main_ else 'Nos articles et guides'}</h2><div class=\"feed\">" + "".join(post_card(a) for a in side) + "</div>"
        if not lst:
            body += "<p>Les premiers articles arrivent très vite.</p>"
        ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h["title"], "description": h["desc"], "url": f"{BASE}/{h['slug']}.html", "inLanguage": "fr-FR",
              "hasPart": [{"@type": "Article", "headline": a["title"][:110], "url": f"{BASE}/actus/{a['slug']}.html"} for a in lst[:20]]}
        open(os.path.join(ROOT, h["slug"] + ".html"), "w", encoding="utf-8").write(
            simple_page(h["slug"] + ".html", h["title"], h["desc"], h["h1"], "Le sujet", body, ld))
    return hub_dates


# ---------- Codes de triche (piloté par codes.json) ----------
CHEAT_SLUG = "gta-6-codes-triche"
CHEAT_TITLE = "Codes de triche GTA 6 : la liste complète PS5 et Xbox (et comment les activer)"
CHEAT_DESC = "Tous les codes de triche de GTA 6 sur PS5 et Xbox Series : les 61 cheats, les combinaisons connues, comment les taper sur le téléphone et comment les débloquer."
CHEAT_CATS = {"joueur": "Joueur", "combat": "Armes et combat", "vehicule": "Véhicules", "monde": "Heure et météo", "filtre": "Filtres d'écran"}
ARROW = {"haut": "↑", "bas": "↓", "gauche": "←", "droite": "→"}
CHEAT_CSS = """
.quickans{background:linear-gradient(135deg,#2A0F4A,#6B1E6E);border:1px solid var(--pink2);border-radius:20px;padding:22px 24px;margin:18px 0}
.quickans p{margin:0 0 10px;font-size:17px}.quickans p:last-child{margin:0}
.steps{counter-reset:s;list-style:none;padding:0;margin:0;display:grid;gap:10px}
.steps li{counter-increment:s;position:relative;padding:14px 16px 14px 58px;background:var(--night2);border:1px solid var(--line);border-radius:14px}
.steps li::before{content:counter(s);position:absolute;left:14px;top:12px;width:32px;height:32px;border-radius:50%;background:var(--pink);color:var(--night);font:400 16px 'Archivo Black',sans-serif;display:flex;align-items:center;justify-content:center}
.pads{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}.pads div{background:var(--night2);border:1px solid var(--line);border-radius:14px;padding:12px 14px}
.pads strong{display:block;color:var(--teal);font-size:13px;text-transform:uppercase;letter-spacing:1px}
.ctools{position:sticky;top:72px;z-index:5;background:rgba(23,10,51,.96);padding:12px 0;margin:0 0 6px}
.ctools input{width:100%;min-height:48px;padding:0 16px;border-radius:12px;border:1px solid var(--line);background:var(--night2);color:var(--white);font:500 16px Inter,sans-serif}
.ctools .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ctools .chip{min-height:40px;padding:0 14px;border-radius:999px;border:1px solid var(--line);background:var(--night2);color:var(--white);font:700 14px Inter,sans-serif;cursor:pointer}
.ctools .chip[aria-pressed="true"]{background:var(--white);color:var(--night);border-color:var(--white)}
.ccount{color:var(--soft);font-size:14px;margin:8px 0 0}
.cgroup h2{scroll-margin-top:170px}
.codes{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.code{background:var(--night2);border:1px solid var(--line);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:8px}
.code.known{border-color:var(--teal)}
.code h3{margin:0;font-size:18px;line-height:1.25}.code .en{color:var(--mute);font-size:12px}
.code p{margin:0;font-size:14px;color:var(--soft)}.code .unl strong{color:var(--white)}
.seq{display:flex;flex-wrap:wrap;gap:5px;margin:2px 0}
.seq kbd{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:9px;background:var(--white);color:var(--night);font:700 20px Inter,sans-serif;box-shadow:0 3px 0 #9C8FD0}
.nocode{font-size:13px;font-weight:700;color:var(--orange)}
.copy{align-self:flex-start;min-height:36px;padding:0 12px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--teal);font:700 13px Inter,sans-serif;cursor:pointer}
.faq details{background:var(--night2);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:0 0 10px}
.faq summary{cursor:pointer;font-weight:700;font-size:16px}.faq details p{margin:10px 0 0;color:#F2ECFF}
.srcs a{margin-right:12px}
@media (max-width:640px){.pads{grid-template-columns:1fr}.ctools{position:static}.seq kbd{width:32px;height:32px;font-size:18px}}
"""
CHEAT_JS = r"""<script>
(()=>{const q=document.getElementById('cq'),chips=[...document.querySelectorAll('.ctools .chip')],cards=[...document.querySelectorAll('.code')],groups=[...document.querySelectorAll('.cgroup')],cnt=document.getElementById('ccount');
let cat='all';const norm=s=>s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
function run(){const w=norm(q.value).split(/\s+/).filter(Boolean);let n=0;
cards.forEach(c=>{const ok=(cat==='all'||(cat==='known'?c.classList.contains('known'):c.dataset.cat===cat))&&w.every(x=>c.dataset.t.includes(x));c.hidden=!ok;if(ok)n++});
groups.forEach(g=>g.hidden=!g.querySelector('.code:not([hidden])'));cnt.textContent=n+(n>1?' codes affichés':' code affiché')}
chips.forEach(b=>b.addEventListener('click',()=>{cat=b.dataset.c;chips.forEach(x=>x.setAttribute('aria-pressed',x===b));run()}));
q.addEventListener('input',run);
document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',()=>{const t=b.dataset.seq;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{b.textContent='Copié !';setTimeout(()=>b.textContent='Copier le code',1500)}).catch(()=>{})}));
try{const h=new URLSearchParams(location.search).get('q');if(h){q.value=h}}catch(e){}run()})();
</script>"""

CHEAT_FAQ = [
    ("Y a-t-il des codes de triche dans GTA 6 ?", "Oui. GTA 6 compte 61 codes de triche en mode histoire, sur PS5 et Xbox Series X|S. Mais ils ne sont pas tous disponibles tout de suite : il faut finir l'histoire principale, puis relever des défis pour débloquer chaque code."),
    ("Comment activer un code de triche dans GTA 6 ?", "Appuie sur la flèche du haut pour sortir le téléphone. Maintiens L1 + R1 sur PS5 (LB + RB sur Xbox), puis tape la suite de flèches de la croix directionnelle. Les codes sont les mêmes sur PS5 et Xbox."),
    ("Est-ce qu'il y a des numéros de téléphone à composer comme dans GTA 5 ?", "Non. D'après Red Bull et Beebom, les numéros de triche façon GTA 5 ne marchent pas dans GTA 6 : tout passe par les combinaisons de flèches."),
    ("Est-ce que les codes désactivent les trophées et la sauvegarde ?", "Oui, pour la session en cours : tant qu'un code est actif, tu ne peux plus sauvegarder ni débloquer de trophées ou de succès. Fais une sauvegarde manuelle avant, puis relance-la pour tout retrouver. Ce que tu fais pendant la triche ne sera pas sauvegardé."),
    ("Y a-t-il un code d'argent infini dans GTA 6 ?", "Il existe un code qui donne 250 000 $, débloqué à la fin de l'histoire. Mais selon Vice, cet argent n'est pas conservé dans ta sauvegarde. Méfie-toi des vidéos qui promettent de l'argent infini avec un glitch : ça ne marche pas ou ça peut abîmer ta partie."),
    ("Les codes de triche marchent-ils sur PC ou dans GTA Online ?", "GTA 6 n'est sorti que sur PS5 et Xbox Series X|S, et il n'a pas encore de mode en ligne. Les codes sont réservés au mode histoire."),
]


def cheat_page():
    data = json.load(open(os.path.join(ROOT, "codes.json"), encoding="utf-8"))
    codes = data["codes"]
    ids = [c["id"] for c in codes]
    assert len(ids) == len(set(ids)), "id de code en double"
    for c in codes:
        assert c["cat"] in CHEAT_CATS, c["id"]
        assert c["code"] is None or all(x in ARROW for x in c["code"]), c["id"]
    known = [c for c in codes if c["code"]]
    known_by_cat = ", ".join(f'{c["name"]}' for c in known[:3])
    body = [f'<p class="lead">Les codes de triche sont bien dans GTA 6 : <strong>{len(codes)} cheats</strong> en mode histoire, sur PS5 et Xbox Series. '
            f'Voici la liste complète, les <strong>{len(known)} combinaisons déjà connues</strong> et comment débloquer les autres.</p>',
            '<div class="quickans"><p><strong>En bref :</strong> finis l\'histoire principale, sors le téléphone (flèche haut), maintiens <strong>L1 + R1</strong> (PS5) ou <strong>LB + RB</strong> (Xbox) et tape la suite de flèches.</p>'
            '<p>Chaque code se débloque avec un défi (stand de tir, cascades, courses…). Tant qu\'un code est actif : pas de sauvegarde, pas de trophées.</p></div>',
            '<h2 id="activer">Comment taper un code de triche</h2><ol class="steps">'
            '<li><strong>Finis l\'histoire principale.</strong> Avant ça, les codes ne marchent pas. Ensuite, une page « Triches » apparaît dans le menu Progression : elle te dit quels codes tu as débloqués.</li>'
            '<li><strong>Fais une sauvegarde manuelle.</strong> Les codes bloquent la sauvegarde et les trophées pour la session : tu pourras relancer ta partie propre après.</li>'
            '<li><strong>Sors le téléphone</strong> avec la flèche du haut de la croix directionnelle.</li>'
            '<li><strong>Maintiens les deux gâchettes hautes</strong> et tape la suite de flèches du code.</li></ol>'
            '<div class="pads"><div><strong>PS5</strong>Flèche haut, puis maintiens L1 + R1 et tape les flèches</div><div><strong>Xbox Series X|S</strong>Flèche haut, puis maintiens LB + RB et tape les flèches</div></div>'
            '<p>Pour annuler un code, tape-le une deuxième fois. Pas de numéro de téléphone à composer comme dans GTA 5 : tout se fait avec les flèches.</p>',
            '<h2 id="liste">La liste des 61 codes</h2>'
            '<p>Les codes avec des flèches sont ceux déjà relayés par plusieurs sites spécialisés (mêmes combinaisons partout). Ils restent <strong>à tester en jeu</strong> : si l\'un ne marche pas chez toi, dis-le-nous. Les autres n\'ont pas encore été trouvés : on complète la liste dès qu\'ils sortent.</p>'
            '<div class="ctools"><label class="sr" for="cq">Chercher un code</label><input id="cq" type="search" placeholder="Cherche : argent, tank, munitions, parachute…" autocomplete="off">'
            '<div class="chips" role="group" aria-label="Filtrer les codes">'
            '<button class="chip" type="button" data-c="all" aria-pressed="true">Tout</button>'
            f'<button class="chip" type="button" data-c="known" aria-pressed="false">Codes connus ({len(known)})</button>'
            + "".join(f'<button class="chip" type="button" data-c="{k}" aria-pressed="false">{e(v)}</button>' for k, v in CHEAT_CATS.items())
            + '</div><p class="ccount" id="ccount" role="status" aria-live="polite"></p></div>']
    for k, label in CHEAT_CATS.items():
        grp = [c for c in codes if c["cat"] == k]
        body.append(f'<section class="cgroup"><h2 id="cat-{k}">{e(label)} ({len(grp)})</h2><div class="codes">')
        for c in grp:
            words = " ".join(c["code"] or [])
            t = (c["name"] + " " + c["en"] + " " + c["effect"] + " " + c["unlock"] + " " + label).lower()
            import unicodedata
            t = "".join(ch for ch in unicodedata.normalize("NFD", t) if unicodedata.category(ch) != "Mn")
            if c["code"]:
                seq = ('<div class="seq" role="img" aria-label="' + e(", ".join(c["code"])) + '">'
                       + "".join(f"<kbd>{ARROW[x]}</kbd>" for x in c["code"]) + "</div>"
                       + f'<button class="copy" type="button" data-seq="{e(" ".join(ARROW[x] for x in c["code"]))}">Copier le code</button>')
            else:
                seq = '<span class="nocode">Combinaison pas encore trouvée</span>'
            body.append(f'<article class="code{" known" if c["code"] else ""}" id="code-{e(c["id"])}" data-cat="{k}" data-t="{e(t)}">'
                        f'<h3>{e(c["name"])}</h3><span class="en">En anglais : {e(c["en"])}</span>{seq}'
                        f'<p>{e(c["effect"])}</p><p class="unl"><strong>Déblocage :</strong> {e(c["unlock"])}</p></article>')
        body.append("</div></section>")
    body.append('<h2 id="faq">Questions fréquentes</h2><div class="faq">'
                + "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in CHEAT_FAQ) + "</div>")
    body.append('<div class="box"><p><strong>Codes de triche, oui. Glitchs et mods, non.</strong> Les codes de cette page sont prévus par Rockstar dans le mode histoire. '
                'On ne publie pas de glitch d\'argent, de duplication ni de mod : ça peut casser ta sauvegarde ou te faire bannir.</p></div>')
    body.append(f'<p class="srcs">Mise à jour : {fr_date(data["updated"] + "T12:00:00")}. Sources : '
                + "".join(f'<a href="{e(s["u"])}" target="_blank" rel="noopener">{e(s["t"])}</a>' for s in data["sources"]) + "</p>")
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": CHEAT_TITLE[:110], "description": CHEAT_DESC, "inLanguage": "fr-FR",
           "dateModified": data["updated"], "url": f"{BASE}/{CHEAT_SLUG}.html", "image": SHARE_IMG,
           "author": {"@type": "Organization", "name": "GTASTUCE VICE"}, "publisher": {"@type": "Organization", "name": "GTASTUCE VICE", "logo": {"@type": "ImageObject", "url": f"{BASE}/favicon-512.png"}}},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in CHEAT_FAQ]}]
    html_ = simple_page(CHEAT_SLUG + ".html", CHEAT_TITLE, CHEAT_DESC, "Codes de triche GTA 6", "Le guide", "\n".join(body), None)
    html_ = html_.replace("</head>", f'<style>{CHEAT_CSS}</style>\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n</head>', 1)
    html_ = html_.replace("</body>", CHEAT_JS + "\n</body>", 1)
    open(os.path.join(ROOT, CHEAT_SLUG + ".html"), "w", encoding="utf-8").write(html_)
    return data["updated"]


# ---------- Ressources communes injectées dans toutes les pages ----------
HEAD_ASSETS = ('<link rel="manifest" href="/manifest.webmanifest">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-title" content="GTASTUCE">\n<meta name="apple-mobile-web-app-status-bar-style" content="black">\n'
               '<link rel="stylesheet" href="/assets/motion.css">\n<link rel="stylesheet" href="/assets/base.css">\n'
               "<script>try{if(localStorage.getItem('gtv_motion')==='off')document.documentElement.classList.add('no-motion')}catch(e){}</script>\n"
               '<script src="/assets/motion.js" defer></script>\n<script src="/assets/site.js" defer></script>')

ICO = {
    "home": '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "actus": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h10M7 13h10M7 17h6"/>',
    "carte": '<path d="M9 4l6 2 6-2v16l-6 2-6-2-6 2V6z"/><path d="M9 4v16M15 6v16"/>',
    "secrets": '<circle cx="12" cy="10" r="3"/><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>'}
TABS = [("home", "Accueil", "/index.html"), ("actus", "Actus", "/actus.html"), ("carte", "Carte", "/gta-6-carte.html"),
        ("secrets", "Secrets", "/index.html#chasse"), ("search", "Chercher", "/recherche.html")]


def tabbar_html(page):
    cur = {"index.html": "home", "actus.html": "actus", "gta-6-carte.html": "carte", "recherche.html": "search"}.get(page, "actus" if "/actus/" in page else "")
    return ('<nav class="tabbar" aria-label="Navigation rapide">' + "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if k == cur else ""}><svg viewBox="0 0 24 24" aria-hidden="true">{ICO[k]}</svg><span>{n}</span></a>'
        for k, n, h in TABS) + '</nav>')


def all_pages():
    files = [os.path.join(ROOT, f) for f in os.listdir(ROOT) if f.endswith(".html")]
    return files + [os.path.join(ROOT, "actus", f) for f in os.listdir(os.path.join(ROOT, "actus")) if f.endswith(".html")]


def inject_assets():
    """Motion design + base.css + site.js + lien d'évitement, sur toutes les pages (idempotent)."""
    for f in all_pages():
        t = open(f, encoding="utf-8").read()
        o = t
        t = re.sub(r'<link rel="manifest" href="/manifest\.webmanifest">\n(?:<meta name="[^"]*" content="[^"]*">\n)*', "", t)
        t = re.sub(r'<link rel="stylesheet" href="/assets/motion\.css">\n(?:<link rel="stylesheet" href="/assets/base\.css">\n<script>try\{.*?</script>\n)?<script src="/assets/motion\.js" defer></script>\n(?:<script src="/assets/site\.js" defer></script>\n)?', "", t, flags=re.S)
        t = t.replace("</head>", HEAD_ASSETS + "\n</head>", 1)
        if 'class="skip"' not in t:
            t = re.sub(r"<body>\n?", '<body>\n<a class="skip" href="#contenu">Aller au contenu</a>\n', t, count=1)
        t = re.sub(r'<nav class="tabbar".*?</nav>\n?', "", t, flags=re.S)
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        t = t.replace("</body>", tabbar_html(rel if not rel.startswith("actus/") else "/actus/" + rel) + "\n</body>", 1)
        if t != o:
            open(f, "w", encoding="utf-8").write(t)


def lastmods(paths, fixed):
    """Date de dernière modification réelle (empreinte du contenu), au lieu de « aujourd'hui » à chaque build."""
    store_p = os.path.join(ROOT, "lastmod.json")
    store = json.load(open(store_p)) if os.path.exists(store_p) else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {}
    for path in paths:
        if fixed.get(path):
            out[path] = fixed[path]
            continue
        txt = open(os.path.join(ROOT, path), encoding="utf-8").read()
        h = hashlib.sha1(txt.encode()).hexdigest()
        if store.get(path, [None])[0] != h:
            store[path] = [h, today]
        out[path] = store[path][1]
    json.dump(store, open(store_p, "w"), indent=0, sort_keys=True)
    return out


def main():
    arts = json.load(open(os.path.join(ROOT, "articles.json"), encoding="utf-8"))
    arts.sort(key=lambda a: a["date"], reverse=True)
    secrets = json.load(open(os.path.join(ROOT, "secrets.json"), encoding="utf-8"))
    sec_ids = {s["id"] for s in secrets}
    hub_slugs = {h["slug"] for h in HUBS}
    for a in arts:  # garde-fous de rédaction
        assert re.fullmatch(r"[a-z0-9-]+", a["slug"]), a["slug"]
        assert os.path.exists(os.path.join(ROOT, a["img"])), a["img"]
        assert set(a.get("topics", [])) <= hub_slugs, (a["slug"], a.get("topics"))
        assert set(a.get("secrets", [])) <= sec_ids, (a["slug"], a.get("secrets"))
        if "topics" not in a:
            print(f"⚠ {a['slug']} : pas de champ topics (classement par mots-clés du titre)")
    for a in arts:
        for b in a["body"]:
            if isinstance(b, dict) and "capture" in b:
                assert os.path.exists(os.path.join(ROOT, b["capture"])), (a["slug"], b["capture"])
    for s in secrets:
        assert s["status"] in STATUS, (s["id"], s["status"])
        if s.get("capture"):
            assert os.path.exists(os.path.join(ROOT, s["capture"])), (s["id"], s["capture"])
    hub_dates = build_static_pages(arts, secrets)
    cheat_date = cheat_page()
    css = styles()
    out = os.path.join(ROOT, "actus")
    os.makedirs(out, exist_ok=True)
    keep = set()
    by_id = {s["id"]: s for s in secrets}
    for a in arts:
        name = a["slug"] + ".html"
        keep.add(name)
        open(os.path.join(out, name), "w", encoding="utf-8").write(page(a, arts, css, by_id))
    for f in os.listdir(out):
        if f.endswith(".html") and f not in keep:
            os.remove(os.path.join(out, f))
    inject_assets()
    newest = max(a.get("updated", a["date"]) for a in arts)[:10]
    static = ["index.html", "gta-6-codes-triche.html", "actus.html", "matos.html", CADEAUX_SLUG] + [h["slug"] + ".html" for h in HUBS] + ["a-propos.html", "contact.html", "mentions-legales.html"]
    lm = lastmods(static, {"index.html": newest, "actus.html": newest, "gta-6-codes-triche.html": cheat_date, **{h["slug"] + ".html": hub_dates.get(h["slug"]) for h in HUBS}})
    urls = [(f"{BASE}/" if p == "index.html" else f"{BASE}/{p}", lm[p]) for p in static]
    urls += [(f"{BASE}/actus/{a['slug']}.html", a.get("updated", a["date"])[:10]) for a in arts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"<url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"{len(arts)} pages générées dans actus/, sitemap.xml à jour")


if __name__ == "__main__":
    main()
