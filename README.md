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
Effets sonores (fournis par Roméo, libres de droits) dans `outils/sfx/` : riser.wav (montée sur la fin de l'accroche), swoosh1.wav (chaque changement de plan), swoosh2.wav (avant la fin), typewriter.wav (pendant un plan « search »). L'outil les mixe automatiquement.
