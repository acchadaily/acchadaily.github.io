"""Builds the accha? daily website from data/*.json.  Run from anywhere:  python3 tools/build_site.py

Input (unchanged):  data/YYYY-MM-DD.json  +  photos in assets/YYYY-MM-DD/<file>
Output:
  index.html                     latest edition (home)
  YYYY-MM-DD/index.html          every edition
  YYYY-MM-DD/<slug>/index.html   one page per story (shareable, with link previews)
  archive/  search/  404.html  feed.xml  sitemap.xml  robots.txt  search.json
  assets/YYYY-MM-DD/w/*          resized WebP (320/720/1200) + 1200x630 preview JPEG, made once per photo
  d/YYYY-MM-DD.html              redirects for old links
"""
import glob, hashlib, html, json, math, os, re, shutil
from datetime import datetime
from email.utils import format_datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://acchadaily.github.io'
IG = 'https://instagram.com/accha.daily'
e = html.escape

try:
    from PIL import Image, ImageFilter
except ImportError:  # still builds, just without resized images
    Image = None

days = sorted((json.load(open(p, encoding='utf-8')) for p in glob.glob('data/*.json')), key=lambda d: d['date'], reverse=True)

# ---------- static files (cache-busted) ----------
os.makedirs('static', exist_ok=True)
VER = {}
for f in ('site.css', 'app.js'):
    src = open(f'tools/{f}', 'rb').read()
    open(f'static/{f}', 'wb').write(src)
    VER[f] = hashlib.md5(src).hexdigest()[:8]
CSS = f'/static/site.css?v={VER["site.css"]}'
JS = f'/static/app.js?v={VER["app.js"]}'


# ---------- images ----------
def opt(date, name):
    """Returns {'w320':url,'w720':url,'w1200':url,'og':url,'orig':url}; creates the files once."""
    src = f'assets/{date}/{name}'
    base = f'/assets/{date}/'
    if not name or not os.path.exists(src):
        return None
    if Image is None:
        u = base + name
        return dict(w320=u, w720=u, w1200=u, og=u, orig=u)
    stem = os.path.splitext(name)[0]
    out = f'assets/{date}/w'
    os.makedirs(out, exist_ok=True)
    r = {'orig': base + name}
    im = None
    for w in (320, 720, 1200):
        p = f'{out}/{stem}-{w}.webp'
        if not os.path.exists(p) or os.path.getmtime(p) < os.path.getmtime(src):
            im = im or Image.open(src).convert('RGB')
            k = im.copy()
            if k.width > w:
                k = k.resize((w, round(k.height * w / k.width)), Image.LANCZOS)
            k.save(p, 'WEBP', quality=78, method=6)
        r[f'w{w}'] = f'{base}w/{stem}-{w}.webp'
    p = f'{out}/{stem}-og.jpg'
    if not os.path.exists(p) or os.path.getmtime(p) < os.path.getmtime(src):
        im = im or Image.open(src).convert('RGB')
        W, H = 1200, 630
        s = max(W / im.width, H / im.height)
        bg = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg.save(p, 'JPEG', quality=82, optimize=True, progressive=True)
    r['og'] = f'{base}w/{stem}-og.jpg'
    return r


def pic(d, s, sizes, eager=False):
    o = opt(d['date'], s.get('img', ''))
    if not o:
        return f'<div class="im ph" style="--c:{s["color"]}" aria-hidden="true">?</div>'
    srcset = f'{o["w320"]} 320w, {o["w720"]} 720w, {o["w1200"]} 1200w'
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    alt = e(s.get('alt') or s['head'])
    if s.get('contain'):
        return (f'<div class="im contain"><div class="bg" style="background-image:url({o["w320"]})"></div>'
                f'<img src="{o["w720"]}" srcset="{srcset}" sizes="{sizes}" alt="{alt}" {load} decoding="async"></div>')
    return f'<div class="im"><img src="{o["w720"]}" srcset="{srcset}" sizes="{sizes}" alt="{alt}" {load} decoding="async"></div>'


# ---------- helpers ----------
def url(d, s=None):
    return f'/{d["date"]}/' + (f'{s["slug"]}/' if s else '')


def words(s):
    return sum(len(p.split()) for x in s.get('sections', []) for p in x['paras'])


def rt(s):
    return f'{max(1, math.ceil(words(s) / 200))} min read'


def tag(s):
    return f'<span class="tag" style="--c:{s["color"]}"><i></i>{e(s["tag"])}</span>'


def iso(d):
    return d['date'] + 'T07:30:00+05:30'


ICON_SEARCH = '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'


def shell(title, desc, path, img=None, body='', kind='website', extra='', active='', bar=False):
    og = SITE + (img or '/static/og.png')
    nav = ''.join(f'<a href="{h}"{" aria-current=page" if active == k else ""}{c}>{t}</a>' for k, h, t, c in (
        ('today', '/', 'Today', ''), ('archive', '/archive/', 'Archive', ' class="hide-s"'),
        ('search', '/search/', ICON_SEARCH + '<span class="hide-s"> Search</span>', ' aria-label="Search"')))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0E0F12" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="/static/icon-180.png"><link rel="manifest" href="/manifest.webmanifest">
<link rel="alternate" type="application/rss+xml" title="accha? daily" href="/feed.xml">
<meta property="og:site_name" content="accha? daily"><meta property="og:type" content="{kind}"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{SITE}{path}"><meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400..900&display=swap" media="print" onload="this.media='all'">
<link rel="stylesheet" href="{CSS}">{extra}
</head><body>{'<div id="bar"></div>' if bar else ''}<a class="skip" href="#main">Skip to content</a>
<header><div class="wrap"><a class="logo" href="/" aria-label="accha? daily home">accha<b>?</b> <span>daily</span></a>
<nav>{nav}<a class="ig hide-s" href="{IG}" target="_blank" rel="noopener">Follow</a></nav></div></header>
<main id="main">{body}</main>
<footer><div class="wrap"><p>accha? daily explains the day's news in its own words and links to the original reporting. Photos are credited to their sources. Not investment advice.</p>
<nav><a href="/archive/">Archive</a><a href="/feed.xml">RSS</a><a href="{IG}" target="_blank" rel="noopener">Instagram</a></nav></div></footer>
<script src="{JS}" defer></script></body></html>'''


# ---------- edition page ----------
def edition(d, home):
    S = d['stories']
    lead, grid, rest = S[0], S[1:5], S[5:]
    tags = list(dict.fromkeys(s['tag'] for s in S))
    chips = ''
    if len(tags) > 2:
        chips = '<div class="chips" role="toolbar" aria-label="Filter by topic"><button class="chip" data-t="*" aria-pressed="true">All</button>' + \
                ''.join(f'<button class="chip" data-t="{e(t)}" aria-pressed="false">{e(t)}</button>' for t in tags) + '</div>'
    st = lead.get('stat')
    statline = f'<div class="statline" style="--c:{lead["color"]}"><b>{e(st[0])}</b><span>{e(st[1])}</span></div>' if st else ''
    lead_h = f'''<section data-block><a class="lead st" href="{url(d, lead)}" data-tag="{e(lead['tag'])}">
 {pic(d, lead, '(max-width:640px) 100vw, 600px', eager=True)}
 <div>{tag(lead)} <span class="rt">· {rt(lead)}</span><h2>{e(lead['head'])}</h2><p>{e(lead['dek'])}</p>{statline}<span class="go">Read the full story →</span></div></a></section>'''
    grid_h = '<section class="grid" data-block>' + ''.join(f'''<a class="st" href="{url(d, s)}" data-tag="{e(s['tag'])}">{pic(d, s, '(max-width:640px) 104px, (max-width:900px) 50vw, 260px')}
 <div class="txt">{tag(s)}<h3>{e(s['head'])}</h3><p>{e(s['dek'])}</p></div></a>''' for s in grid) + '</section>' if grid else ''
    rest_h = ''
    if rest:
        rows = ''.join(f'''<a class="row st" href="{url(d, s)}" data-tag="{e(s['tag'])}"{'' if s.get('img') else ' style="grid-template-columns:1fr"'}><div>{tag(s)}<h4>{e(s['head'])}</h4><p>{e(s['dek'])}</p></div>{pic(d, s, '104px') if s.get('img') else ''}</a>''' for s in rest)
        rest_h = f'<section data-block><div class="sec"><h2>More stories</h2></div><div class="list">{rows}</div></section>'
    others = [o for o in days if o is not d][:6]
    past = ''
    if others:
        past = '<div class="sec"><h2>Past editions</h2><a href="/archive/">All →</a></div><div class="days">' + ''.join(
            f'<a class="day" href="{url(o)}"><small>{e(o["day"])}</small><b>{e(o["date_label"])}</b><span>{e(o["stories"][0]["head"])}</span></a>' for o in others) + '</div>'
    h1 = "Today's" if home else e(d['day']) + "'s"
    note = f'<div class="note">{e(d["note"])}</div>' if d.get('note') else ''
    body = f'''<div class="wrap">
<div class="top"><div><div class="kick">{e(d['day'])} · {e(d['date_label'])}</div><h1>{h1} biggest stories<b>.</b></h1>
<p>{len(S)} stories from India and the world — brands, startups, tech, sports and your wallet, explained simply.</p></div>{note}</div>
{chips}{lead_h}{grid_h}{rest_h}
<div class="cta"><div><h3>accha<b>?</b> Now you know.</h3><p>The day's biggest stories, every morning on Instagram.</p></div><a class="btn" href="{IG}" target="_blank" rel="noopener">Follow @accha.daily</a></div>
{past}</div>'''
    extra = ''
    if home:
        slugs = {s['slug']: url(o, s) for o in reversed(days) for s in o['stories']}
        extra = f'\n<script>window.SLUGS={json.dumps(slugs)}</script>'
    o = opt(d['date'], lead.get('img', ''))
    title = (f"accha? daily — Today's biggest stories" if home else f"accha? daily — {d['day']}, {d['date_label']}")
    desc = f"{d['date_label']}: " + ' · '.join(s['head'] for s in S[:3]) + ' — and more, explained simply.'
    return shell(title, desc, '/' if home else url(d), o and o['og'], body, extra=extra, active='today' if home else '')


# ---------- story page ----------
def story(d, i):
    S = d['stories']
    s = S[i]
    nxt = S[(i + 1) % len(S)]
    secs = ''.join(f'<h2>{e(x["title"])}</h2>' + ''.join(f'<p>{e(p)}</p>' for p in x['paras']) for x in s.get('sections', []))
    st = s.get('stat')
    big = f'<div class="big"><b>{e(st[0])}</b><span>{e(st[1])}</span></div>' if st else ''
    facts = ''.join(f'<li><i></i><span>{e(f)}</span></li>' for f in s.get('facts', []))
    short = f'<div class="short" style="--c:{s["color"]}"><div class="bt">In short</div>{big}{f"<ul>{facts}</ul>" if facts else ""}</div>' if (big or facts) else ''
    srcs = ''.join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}<span>↗</span></a>' for x in s.get('sources', []))
    fig = f'<figure class="hero">{pic(d, s, "(max-width:720px) 100vw, 680px", eager=True)}<figcaption>📷 {e(s.get("credit", ""))}</figcaption></figure>' if s.get('img') else ''
    link = SITE + url(d, s)
    wa = e('https://wa.me/?text=' + quote(s['head'] + ' — ' + link))
    share = f'''<div class="share"><a class="wa" href="{wa}" target="_blank" rel="noopener">WhatsApp</a><button data-share>Share</button></div>'''
    more = ''.join(f'''<a class="row st" href="{url(d, o)}"{'' if o.get('img') else ' style="grid-template-columns:1fr"'}><div>{tag(o)}<h4>{e(o['head'])}</h4></div>{pic(d, o, '88px') if o.get('img') else ''}</a>'''
                   for o in [x for x in S if x is not s and x is not nxt][:6])
    o = opt(d['date'], s.get('img', ''))
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": s['head'], "description": s['dek'],
          "datePublished": iso(d), "dateModified": iso(d), "mainEntityOfPage": link, "articleSection": s['tag'],
          "image": [SITE + o['og']] if o else [SITE + '/static/og.png'],
          "author": {"@type": "Organization", "name": "accha? daily", "url": SITE},
          "publisher": {"@type": "Organization", "name": "accha? daily", "logo": {"@type": "ImageObject", "url": SITE + '/static/icon-512.png'}}}
    body = f'''<div class="narrow"><article class="art">
<a class="crumb" href="{url(d)}">← {e(d['day'])}'s stories</a>
<div style="margin-top:18px">{tag(s)}</div>
<h1>{e(s['head'])}</h1><p class="dek">{e(s['dek'])}</p>
<div class="meta"><div class="by"><b>accha? daily</b> · <time datetime="{d['date']}">{e(d['date_label'])}</time> · {rt(s)}</div>{share}</div>
{fig}{short}<div class="body">{secs}</div>
{f'<div class="src"><div class="bt">Read the original reporting</div>{srcs}</div>' if srcs else ''}
</article>
<a class="next st" href="{url(d, nxt)}"><div><small>Next story →</small><h3>{e(nxt['head'])}</h3></div>{pic(d, nxt, '120px') if nxt.get('img') else ''}</a>
<div class="sec"><h2>More from {e(d['day'])}</h2><a href="{url(d)}">All {len(S)} →</a></div>{more}
<div class="cta"><div><h3>accha<b>?</b> Now you know.</h3><p>Get stories like this every morning.</p></div><a class="btn" href="{IG}" target="_blank" rel="noopener">Follow @accha.daily</a></div>
</div>'''
    extra = f'\n<meta property="article:published_time" content="{iso(d)}"><meta property="article:section" content="{e(s["tag"])}">\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    return shell(f"{s['head']} — accha? daily", s['dek'], url(d, s), o and o['og'], body, kind='article', extra=extra, bar=True)


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)


# ---------- build ----------
for d in days:
    write(f'{d["date"]}/index.html', edition(d, False))
    for i in range(len(d['stories'])):
        write(f'{d["date"]}/{d["stories"][i]["slug"]}/index.html', story(d, i))
    # old link format -> new
    write(f'd/{d["date"]}.html', f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/{d["date"]}/"><link rel="canonical" href="{SITE}/{d["date"]}/"><a href="/{d["date"]}/">accha? daily — {e(d["date_label"])}</a>')
write('index.html', edition(days[0], True))

# archive
months = {}
for d in days:
    months.setdefault(datetime.strptime(d['date'], '%Y-%m-%d').strftime('%B %Y'), []).append(d)
arch = ''.join(f'<div class="sec"><h2>{m}</h2></div><div class="days">' + ''.join(
    f'<a class="day" href="{url(d)}"><small>{e(d["day"])} · {len(d["stories"])} stories</small><b>{e(d["date_label"])}</b><span>{e(d["stories"][0]["head"])}</span></a>' for d in ds) + '</div>' for m, ds in months.items())
write('archive/index.html', shell('Archive — accha? daily', 'Every accha? daily edition.', '/archive/',
      body=f'<div class="wrap"><div class="top"><div><div class="kick">Archive</div><h1>Every edition<b>.</b></h1><p>{sum(len(d["stories"]) for d in days)} stories so far.</p></div></div>{arch}</div>', active='archive'))

# search
write('search/index.html', shell('Search — accha? daily', 'Search every accha? daily story.', '/search/', active='search',
      body=f'<div class="narrow"><div class="top"><div><div class="kick">Search</div><h1>Find a story<b>.</b></h1></div></div><label class="sbox">{ICON_SEARCH}<input id="q" type="search" placeholder="Blinkit, Ronaldo, gold…" autocomplete="off" autofocus aria-label="Search stories"></label><div id="res"></div></div>'))
write('search.json', json.dumps([{"h": s['head'], "k": s['dek'], "g": s['tag'], "c": s['color'], "d": d['date_label'], "u": url(d, s)}
                                 for d in days for s in d['stories']], ensure_ascii=False, separators=(',', ':')))

write('404.html', shell('Not found — accha? daily', 'Page not found.', '/404.html',
      body='<div class="narrow"><div class="top"><div><div class="kick">404</div><h1>accha<b>?</b> This page doesn\'t exist.</h1><p><a class="go" href="/">Go to today\'s stories →</a></p></div></div></div>'))

# feeds
items = [(d, s) for d in days[:14] for s in d['stories']]
rss = ''.join(f'''<item><title>{e(s['head'])}</title><link>{SITE}{url(d, s)}</link><guid>{SITE}{url(d, s)}</guid><category>{e(s['tag'])}</category>
<pubDate>{format_datetime(datetime.fromisoformat(iso(d)))}</pubDate><description>{e(s['dek'])}</description></item>''' for d, s in items)
write('feed.xml', f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>accha? daily</title><link>{SITE}/</link><description>The day\'s biggest stories, explained simply.</description><language>en-in</language>{rss}</channel></rss>')
urls = ['/', '/archive/'] + [url(d) for d in days] + [url(d, s) for d in days for s in d['stories']]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
      ''.join(f'<url><loc>{SITE}{u}</loc></url>' for u in urls) + '</urlset>')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
write('manifest.webmanifest', json.dumps({"name": "accha? daily", "short_name": "accha?", "start_url": "/", "display": "standalone",
      "background_color": "#FFFFFF", "theme_color": "#0F1115", "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
      {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}]}))
write('.nojekyll', '')
print('built', len(days), 'edition(s),', sum(len(d['stories']) for d in days), 'stories; latest', days[0]['date'])
