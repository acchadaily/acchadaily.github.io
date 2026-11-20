# accha? daily — daily update

1. Add `data/YYYY-MM-DD.json` (same schema as the existing files: date, day, date_label, note, stories[], also[]) and its photos in `assets/YYYY-MM-DD/`.
   Aim for 25–30 stories. Ranked order: story 1 is the big photo lead, 2–5 are featured, 6+ are grouped into sections by tag:
   India (India, Politics, Your Wallet, Economy) · World (World, Geopolitics) · Startups & Brands (Startups, Founders, Brands, Marketing, Viral, Business) ·
   Tech & AI (AI & Tech, Tech) · Auto & Gadgets (Auto, Cars, Gadgets) · Health & Science (Health, Science, Space) · Climate & Weather (Climate, Weather) · Markets & Money (Markets, Finance) · Sports · Entertainment · Good News. Use exactly these tag names.
   Good news: add 6–10 positive stories with tag "Good News", color "#16A34A", "good": true and an "emoji" (shown when there's no photo). Any other uplifting story (e.g. a sports win) can also get "good": true to appear on the Good News page (/YYYY-MM-DD/good/).
   New sections are used ONLY when warranted: Health & Science only for health/science news that is big and leading across major outlets; Auto & Gadgets only for an important launch (major car/bike/EV/phone/laptop with price), a mass recall or a big safety story; Climate & Weather only when genuinely very important — a cyclone, cold wave, flood or AQI emergency that the major outlets are leading with, never a routine forecast. Suggested colors: Health & Science #DB2777, Auto & Gadgets #0D9488, Climate & Weather #65A30D.
   A section only appears when it has stories, so leaving these out on an ordinary day costs nothing — that is the default, not the exception.
   Explainers: add "explainers": [{"q": "What is X?", "a": "60–90 words in plain language", "slug": "<slug of the related story>"}] — 1–2 per day, explaining a term or concept from today's news (e.g. MDR, UDRHP, repo rate, GMP). Shown as a "💡 Explained" box on the homepage and on that story's page.
   Optional "markets": {"asof": "...", "items": [{"n": "Sensex", "v": "81,200", "c": "+0.4%"}, ...]} shows the markets strip (only verified numbers, with an honest as-of line). Each story needs: slug, tag, color, img (or ""), credit, contain, head, dek, stat ([value, label] or null), sections[{title, paras}], facts[], sources[{name, url}].
2. Run `python3 tools/build_site.py` from anywhere. It rebuilds everything: home, one page per edition (`/YYYY-MM-DD/`), one page per story (`/YYYY-MM-DD/<slug>/`), the swipe mode (`/YYYY-MM-DD/60/`), good news (`/YYYY-MM-DD/good/`), newspaper view (`/YYYY-MM-DD/paper/`), archive, search, RSS, sitemap, and resized WebP/preview images (needs Pillow; skipped gracefully without it).
3. Preview with `python3 -m http.server 8765` in the repo root and open http://localhost:8765/ (pages use root-relative links, so file:// won't work).
4. Commit and push to `main`. GitHub Pages publishes https://acchadaily.github.io/ in about a minute.

Edit the design in `tools/site.css` and `tools/app.js` (copied to `/static/` with a cache-busting version on every build).
No Instagram carousels — dropped on 2026-11-20 and the renderer was deleted. The site and the daily JSON are the only deliverables; don't re-add it.

## Newsletter (Kit)
After the site is pushed, the same edition goes out as an email to Kit subscribers:
`python3 tools/build_newsletter.py` writes newsletter/newsletter-YYYY-MM-DD.html/.txt/.subject.txt from the day's JSON — the top 5 stories, the markets strip and three good-news lines, in the brand's yellow and black. `-n 4` for four stories instead of five.
`KIT_API_KEY=... python3 tools/send_newsletter.py` then creates the Kit broadcast and schedules it ~3 minutes out; `--draft` leaves it unsent, `--check` just tests the key. A non-zero exit means the email did NOT go out — say so rather than reporting success.
The newsletter/ folder is generated and git-ignored; don't commit it.
Signup box: set `KIT_FORM_ACTION` at the top of tools/build_site.py to the form `action` URL from Kit (Grow > Landing Pages & Forms > Embed > HTML). While it's empty no box is rendered.
