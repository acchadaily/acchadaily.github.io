# accha? daily — daily update

1. Add `data/YYYY-MM-DD.json` (same schema as the existing files: date, day, date_label, note, stories[], also[]) and its photos in `assets/YYYY-MM-DD/`.
   Stories are in ranked order: story 1 is the big lead, 2–5 are featured, 6+ go under "More stories". Each story needs: slug, tag, color, img (or ""), credit, contain, head, dek, stat ([value, label] or null), sections[{title, paras}], facts[], sources[{name, url}].
2. Run `python3 tools/build_site.py` from anywhere. It rebuilds everything: home, one page per edition (`/YYYY-MM-DD/`), one page per story (`/YYYY-MM-DD/<slug>/`), archive, search, RSS, sitemap, and resized WebP/preview images (needs Pillow; skipped gracefully without it).
3. Preview with `python3 -m http.server 8765` in the repo root and open http://localhost:8765/ (pages use root-relative links, so file:// won't work).
4. Commit and push to `main`. GitHub Pages publishes https://acchadaily.github.io/ in about a minute.

Edit the design in `tools/site.css` and `tools/app.js` (copied to `/static/` with a cache-busting version on every build).
`tools/carousel_template.html` + `tools/render_carousel.py` make the Instagram carousel (1080×1350 JPEGs).
