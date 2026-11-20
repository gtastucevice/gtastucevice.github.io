# GTASTUCE VICE

Site d'astuces, tutos, secrets et actus GTA 6 en français. Site de fans non officiel, non affilié à Rockstar Games ni à Take-Two Interactive.

- `index.html` : accueil
- `actus.html` : rubrique Actus (lit `articles.json`)
- `assets/` : images (crédit Rockstar Games) et vidéo

## Publier un article
1. Ajouter l'article en tête de `articles.json` (et son image dans `assets/`).
2. Lancer `python3 build.py` : génère `actus/<slug>.html`, `sitemap.xml` et `robots.txt`.
3. Commit + push sur `main`.

## Carte des secrets
Chaque secret de `secrets.json` peut avoir un champ `zone` pour apparaître sur la carte :
`vice-city`, `grassrivers`, `keys`, `mer`, `kalaga`, `ambrosia`, `gellhorn`.
Laisser `zone` vide si le secret est « partout » ou si le lieu est inconnu : il est alors listé sous la carte.
`build.py` dessine la carte (accueil + page easter eggs), rien d'autre à faire.

## Vidéo du jour (outils/video_site.py)
`python3 outils/video_site.py spec.json` fabrique une vidéo verticale (accroche sur une image Rockstar, pages du site filmées dans un téléphone, fin « gtastucevice.fr / lien en bio ») avec une musique synthwave générée (libre de droits). Le format du spec est décrit en tête du script. Sortie : `assets/videos/<slug>.mp4` et `.jpg`, à pousser pour que Metricool puisse la récupérer. Historique des sujets : `assets/videos/historique.json`.
Effets sonores (fournis par Roméo, licence Pixabay : jamais dans ce dépôt public) : dossier Drive « GTASTUCE VICE / Musiques / Effets », à télécharger dans /tmp/gtv_sfx (ou $GTV_SFX) : riser.wav (montée sur la fin de l'accroche), swoosh1.wav (chaque changement de plan), swoosh2.wav (avant la fin), typewriter.wav (pendant un plan « search »). L'outil les mixe automatiquement.

## Captures en jeu (outils/captures.py)
Depuis la sortie du jeu, on illustre les astuces avec nos propres captures PS5 (crédit « Capture en jeu : GTASTUCE VICE »).
1. Roméo dépose ses captures PS5 ou les vidéos brutes de gameplay dans le dossier Drive « GTASTUCE VICE / Captures PS5 ».
2. `python3 outils/captures.py trier <dossier>` : extrait les meilleures images des vidéos (nettes, sans doublon) et fait des planches numérotées dans /tmp/gtv_captures.
3. `python3 outils/captures.py publier <numéro ou fichier> <nom-slug> [--recadrer x,y,l,h]` : écrit `assets/captures/<nom-slug>.jpg` (1280 px).
4. Article : bloc `{"capture": "assets/captures/x.jpg", "legende": "..."}` dans `body`. Secret : champ `"capture"` dans `secrets.json` (s'affiche dans « Où et comment »). Puis `python3 build.py`.
Jamais de cinématique d'histoire (spoilers) ni de capture d'un autre créateur.
