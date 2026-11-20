# accha? daily — daily update

1. Add `data/YYYY-MM-DD.json` (same schema as the existing files: date, day, date_label, note, stories[], also[]) and its photos in `assets/YYYY-MM-DD/`.
   Aim for 25–30 stories. Ranked order: story 1 is the big photo lead, 2–5 are featured, 6+ are grouped into sections by tag:
   India (India, Politics, Your Wallet, Economy) · World (World, Geopolitics) · Startups & Brands (Startups, Founders, Brands, Marketing, Viral, Business) ·
   Tech & AI (AI & Tech, Tech) · Auto & Gadgets (Auto, Gadgets) · Health & Science (Health, Science, Space) · Climate (Climate) · Markets & Money (Markets, Finance) · Sports · Entertainment · Good News. Use exactly these tag names.
   Good news: add 6–10 positive stories with tag "Good News", color "#16A34A", "good": true and an "emoji" (shown when there's no photo). Any other uplifting story (e.g. a sports win) can also get "good": true to appear on the Good News page (/YYYY-MM-DD/good/).
   New sections are used ONLY when warranted: Health & Science only for health/science news that is big and leading across major outlets; Auto & Gadgets only for an important launch (major car/bike/EV/phone/laptop with price); Climate only when genuinely very important. Suggested colors: Health & Science #DB2777, Auto & Gadgets #0D9488, Climate #65A30D.
   Explainers: add "explainers": [{"q": "What is X?", "a": "60–90 words in plain language", "slug": "<slug of the related story>"}] — 1–2 per day, explaining a term or concept from today's news (e.g. MDR, UDRHP, repo rate, GMP). Shown as a "💡 Explained" box on the homepage and on that story's page.
   Optional "markets": {"asof": "...", "items": [{"n": "Sensex", "v": "81,200", "c": "+0.4%"}, ...]} shows the markets strip (only verified numbers, with an honest as-of line). Each story needs: slug, tag, color, img (or ""), credit, contain, head, dek, stat ([value, label] or null), sections[{title, paras}], facts[], sources[{name, url}].
2. Run `python3 tools/build_site.py` from anywhere. It rebuilds everything: home, one page per edition (`/YYYY-MM-DD/`), one page per story (`/YYYY-MM-DD/<slug>/`), the swipe mode (`/YYYY-MM-DD/60/`), good news (`/YYYY-MM-DD/good/`), newspaper view (`/YYYY-MM-DD/paper/`), archive, search, RSS, sitemap, and resized WebP/preview images (needs Pillow; skipped gracefully without it).
3. Preview with `python3 -m http.server 8765` in the repo root and open http://localhost:8765/ (pages use root-relative links, so file:// won't work).
4. Commit and push to `main`. GitHub Pages publishes https://acchadaily.github.io/ in about a minute.

Edit the design in `tools/site.css` and `tools/app.js` (copied to `/static/` with a cache-busting version on every build).
`tools/carousel_template.html` + `tools/render_carousel.py` make the Instagram carousel (1080×1350 JPEGs).
