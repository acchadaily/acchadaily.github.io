# accha? daily — daily update

1. Add `data/YYYY-MM-DD.json` (same schema as the existing files) and its photos in `assets/YYYY-MM-DD/`.
2. Run `python3 tools/build_site.py` from the repo root. It rebuilds `index.html` (latest day) and `d/<date>.html` (archive).
3. Commit and push to `main`. GitHub Pages publishes https://jdhruv0000-boop.github.io/accha-daily/ in about a minute.

`tools/carousel_template.html` + `tools/render_carousel.py` make the Instagram carousel (1080×1350 JPEGs).
