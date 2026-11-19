# GTASTUCE VICE

Site d'astuces, tutos, secrets et actus GTA 6 en français. Site de fans non officiel, non affilié à Rockstar Games ni à Take-Two Interactive.

- `index.html` : accueil
- `actus.html` : rubrique Actus (lit `articles.json`)
- `assets/` : images (crédit Rockstar Games) et vidéo

## Publier un article
1. Ajouter l'article en tête de `articles.json` (et son image dans `assets/`).
2. Lancer `python3 build.py` : génère `actus/<slug>.html`, `sitemap.xml` et `robots.txt`.
3. Commit + push sur `main`.
