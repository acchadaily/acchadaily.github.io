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
    from PIL import Image, ImageFilter, ImageDraw, ImageFont
except ImportError:  # still builds, just without resized images
    Image = ImageFont = None

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


# ---------- branded share cards (link previews on WhatsApp / Instagram / X) ----------
_FONTS = {}


def _font(w, size, ext=False):
    k = (w, size, ext)
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(f'tools/fonts/inter-{"latin-ext" if ext else "latin"}-{w}-normal.woff2', size)
    return _FONTS[k]


def _runs(text, w, size):
    """Split text into (segment, font) runs, falling back to latin-ext for chars like ₹."""
    base, ext = _font(w, size), _font(w, size, True)
    out = []
    for ch in text:
        f = base if (ch == ' ' or base.getmask(ch).getbbox() or ord(ch) < 0x2000) and ord(ch) not in (0x20B9,) else ext
        if out and out[-1][1] is f:
            out[-1][0] += ch
        else:
            out.append([ch, f])
    return out


def _len(text, w, size):
    return sum(f.getlength(t) for t, f in _runs(text, w, size))


def _draw(dr, x, y, text, w, size, fill):
    for t, f in _runs(text, w, size):
        dr.text((x, y), t, font=f, fill=fill)
        x += f.getlength(t)


def _wrap(text, w, size, maxw):
    lines, cur = [], ''
    for word in text.split():
        t = (cur + ' ' + word).strip()
        if _len(t, w, size) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def card(d, s=None):
    """1200x630 JPEG: photo + dark gradient + accha? logo + tag + headline. s=None -> edition card."""
    if Image is None or ImageFont is None:
        return None
    S = d['stories']
    src_story = s or S[0]
    name = f'{s["slug"]}-card.jpg' if s else 'edition-card.jpg'
    out = f'assets/{d["date"]}/w/{name}'
    dj = f'data/{d["date"]}.json'
    if os.path.exists(out) and os.path.getmtime(out) >= max(os.path.getmtime(dj), os.path.getmtime(__file__)):
        return f'/{out}'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    W, H = 1200, 630
    img_path = f'assets/{d["date"]}/{src_story.get("img")}' if src_story.get('img') else None
    if img_path and os.path.exists(img_path):
        im = Image.open(img_path).convert('RGB')
        sc = max(W / im.width, H / im.height)
        im = im.resize((math.ceil(im.width * sc), math.ceil(im.height * sc)), Image.LANCZOS)
        im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    else:
        im = Image.new('RGB', (W, H), (15, 17, 21))
    # gradient: strong at left/bottom so text is readable
    g = Image.new('L', (W, H))
    gp = g.load()
    for yy in range(H):
        for xx in range(0, W, 4):
            a = max(0.55 * (1 - xx / W) + 0.35, 0.25 + 0.7 * (yy / H) ** 1.6)
            v = int(min(1, a) * 235)
            for k in range(4):
                if xx + k < W:
                    gp[xx + k, yy] = v
    im = Image.composite(Image.new('RGB', (W, H), (8, 9, 12)), im, g)
    dr = ImageDraw.Draw(im)
    X = 64
    # logo
    _draw(dr, X, 50, 'accha', 900, 46, (255, 255, 255))
    lx = X + _len('accha', 900, 46)
    _draw(dr, lx, 50, '?', 900, 46, (242, 183, 5))
    _draw(dr, lx + _len('? ', 900, 46), 56, 'daily', 600, 38, (170, 175, 185))
    # headline
    if s:
        kick = s['tag'].upper()
        head = s['head']
        foot = f'{d["date_label"]} · Read the full story'
    else:
        kick = f'{d["day"].upper()} · {len(S)} STORIES'
        head = f"Today's {len(S)} biggest stories."
        foot = 'Top: ' + S[0]['head']
    size = 76
    while size > 44:
        lines = _wrap(head, 900, size, W - 2 * X - 40)
        if len(lines) <= 3:
            break
        size -= 4
    lines = lines[:3]
    lh = int(size * 1.08)
    y = H - 70 - 34 - 26 - lh * len(lines) - 60
    # tag pill
    col = _hex((s or S[0])['color']) if s else (242, 183, 5)
    if sum(col) < 120:
        col = (90, 95, 105)
    pw = _len(kick, 800, 22) + 40
    dr.rounded_rectangle((X, y, X + pw, y + 42), radius=21, fill=col)
    _draw(dr, X + 20, y + 8, kick, 800, 22, (15, 17, 21) if not s or sum(col) > 500 else (255, 255, 255))
    y += 62
    for i, ln in enumerate(lines):
        _draw(dr, X, y + i * lh, ln, 900, size, (255, 255, 255))
    y += lh * len(lines) + 22
    f = foot if _len(foot, 600, 26) < W - 2 * X else foot[:int(len(foot) * (W - 2 * X) / _len(foot, 600, 26)) - 2].rstrip() + '…'
    _draw(dr, X, y, f, 600, 26, (200, 204, 212))
    # yellow bar + url
    dr.rectangle((0, H - 10, W, H), fill=(242, 183, 5))
    u = 'acchadaily.github.io'
    _draw(dr, W - X - _len(u, 800, 22), 58, u, 800, 22, (200, 204, 212))
    im.save(out, 'JPEG', quality=84, optimize=True, progressive=True)
    return f'/{out}'


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
        ('today', '/', 'Today', ''), ('sixty', f'/{days[0]["date"]}/60/', '▶ 60s', ' class="n60"'), ('archive', '/archive/', 'Archive', ' class="hide-s"'),
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


# ---------- sections ----------
SECTIONS = [  # (name, tags)
    ('India', {'India', 'Politics', 'Your Wallet', 'Economy'}),
    ('World', {'World', 'Geopolitics'}),
    ('Startups & Brands', {'Startups', 'Founders', 'Brands', 'Marketing', 'Viral', 'Business'}),
    ('Tech & AI', {'AI & Tech', 'Tech', 'Science', 'Space'}),
    ('Markets & Money', {'Markets', 'Finance'}),
    ('Sports', {'Sports'}),
    ('Entertainment', {'Entertainment', 'Movies', 'Culture'}),
]


def section_of(s):
    for n, tags in SECTIONS:
        if s['tag'] in tags:
            return n
    return 'More news'


def mins_total(d):
    return max(1, round(sum(words(s) for s in d['stories']) / 200))


def ticker(d):
    items = ''.join(f'<a href="{url(d, s)}"><i style="background:{s["color"]}"></i>{e(s["head"])}</a>' for s in d['stories'])
    return f'<div class="ticker" aria-label="Headlines"><div class="tk-l">Today</div><div class="tk-w"><div class="tk-t">{items}{items}</div></div></div>'


def markets(d):
    m = d.get('markets')
    if not m:
        return ''
    cells = ''.join(f'''<div class="mk"><span>{e(x['n'])}</span><b>{e(x['v'])}</b><em class="{'up' if str(x.get('c','')).startswith('+') else 'dn' if str(x.get('c','')).startswith(('-','−')) else ''}">{e(x.get('c',''))}</em></div>''' for x in m['items'])
    return f'<div class="mkts"><div class="wrap"><div class="mk-row">{cells}</div><div class="mk-as">{e(m.get("asof",""))}</div></div></div>'


def edition(d, home):
    S = d['stories']
    lead, top4, rest = S[0], S[1:5], S[5:]
    o = opt(d['date'], lead.get('img', ''))
    st = lead.get('stat')
    lead_h = f'''<a class="hero2 st" href="{url(d, lead)}">
 {pic(d, lead, '100vw', eager=True)}<div class="shade"></div>
 <div class="hero-txt"><span class="tag lt" style="--c:{lead['color']}"><i></i>{e(lead['tag'])}</span><span class="rt lt">Top story · {rt(lead)}</span>
 <h2>{e(lead['head'])}</h2><p>{e(lead['dek'])}</p>{f'<div class="hero-stat"><b>{e(st[0])}</b><span>{e(st[1])}</span></div>' if st else ''}</div></a>'''
    top_h = '<section class="top4">' + ''.join(f'''<a class="st c4" href="{url(d, s)}">{pic(d, s, '(max-width:640px) 100vw, (max-width:1000px) 50vw, 25vw')}
 <div class="txt"><span class="num">{i:02d}</span>{tag(s)}<h3>{e(s['head'])}</h3><p>{e(s['dek'])}</p></div></a>''' for i, s in enumerate(top4, 2)) + '</section>'
    brief = f'''<a class="brief-cta" href="{url(d)}60/"><div><div class="bc-k">New · Swipe mode</div><div class="bc-h">Today in 60 seconds<b>.</b></div>
<div class="bc-p">All {len(S)} stories, one swipe at a time. Like reels — but news.</div></div><span class="bc-b">Start ▶</span></a>'''
    nums = [s for s in S if s.get('stat')]
    num_h = ''
    if nums:
        num_h = '<div class="sec"><h2>Numbers of the day</h2></div><div class="nums">' + ''.join(
            f'<a class="nm" href="{url(d, s)}" style="--c:{s["color"]}"><b>{e(s["stat"][0])}</b><span>{e(s["stat"][1])}</span><em>{e(s["tag"])} →</em></a>' for s in nums[:12]) + '</div>'
    groups = {}
    for s in rest:
        groups.setdefault(section_of(s), []).append(s)
    order = [n for n, _ in SECTIONS] + ['More news']
    secs = ''
    nav = ''
    for n in order:
        g = groups.get(n)
        if not g:
            continue
        sid = re.sub(r'[^a-z]+', '-', n.lower()).strip('-')
        nav += f'<a class="chip" href="#{sid}">{e(n)} <small>{len(g)}</small></a>'
        first, others = g[0], g[1:]
        feat = f'''<a class="sf st" href="{url(d, first)}">{pic(d, first, '(max-width:640px) 100vw, 400px')}<div>{tag(first)}<h3>{e(first['head'])}</h3><p>{e(first['dek'])}</p></div></a>'''
        rows = ''.join(f'''<a class="row st" href="{url(d, s)}"{'' if s.get('img') else ' style="grid-template-columns:1fr"'}><div>{tag(s)}<h4>{e(s['head'])}</h4><p>{e(s['dek'])}</p></div>{pic(d, s, '104px') if s.get('img') else ''}</a>''' for s in others)
        secs += f'<section class="secblock" id="{sid}"><div class="sh"><h2>{e(n)}</h2><span>{len(g)} {"story" if len(g) == 1 else "stories"}</span></div><div class="sgrid{" solo" if not others else ""}">{feat}<div class="srows">{rows}</div></div></section>'
    others = [x for x in days if x is not d][:6]
    past = ''
    if others:
        past = '<div class="sec"><h2>Past editions</h2><a href="/archive/">All →</a></div><div class="days">' + ''.join(
            f'<a class="day" href="{url(x)}"><small>{e(x["day"])}</small><b>{e(x["date_label"])}</b><span>{e(x["stories"][0]["head"])}</span></a>' for x in others) + '</div>'
    note = f'<span class="mh-note">{e(d["note"])}</span>' if d.get('note') else ''
    body = f'''{ticker(d)}{markets(d)}
<div class="wrap">
<div class="mast"><div class="mh-k"><span>{e(d['day'])}, {e(d['date_label'])}</span><span>{len(S)} stories · {mins_total(d)} min read</span>{note}</div>
<h1>{"Today's" if home else e(d['day']) + "'s"} biggest stories<b>.</b></h1>
<p>India and the world — brands, startups, tech, sports, money and more. Explained simply, in our own words.</p></div>
{lead_h}{top_h}{brief}
<nav class="jump" aria-label="Sections">{nav}</nav>
{secs}
{num_h}
<div class="cta"><div><h3>accha<b>?</b> Now you know.</h3><p>The day's top stories every morning on Instagram — and all of them here.</p></div><a class="btn" href="{IG}" target="_blank" rel="noopener">Follow @accha.daily</a></div>
{past}</div>'''
    extra = ''
    if home:
        slugs = {s['slug']: url(x, s) for x in reversed(days) for s in x['stories']}
        extra = f'\n<script>window.SLUGS={json.dumps(slugs)}</script>'
    title = "accha? daily — Today's biggest stories" if home else f"accha? daily — {d['day']}, {d['date_label']}"
    desc = f"{len(S)} stories for {d['date_label']}: " + ' · '.join(s['head'] for s in S[:3]) + ' — and more, explained simply.'
    return shell(title, desc, '/' if home else url(d), card(d) or (o and o['og']), body, extra=extra, active='today' if home else '')


# ---------- 60-second swipe mode ----------
def brief_page(d):
    S = d['stories']
    cards = ''
    for i, s in enumerate(S):
        o = opt(d['date'], s.get('img', ''))
        bg = f'<img src="{o["w720"]}" srcset="{o["w720"]} 720w, {o["w1200"]} 1200w" sizes="(max-width:520px) 100vw, 480px" alt="" {"fetchpriority=high" if i == 0 else "loading=lazy"} decoding="async">' if o else f'<div class="bf-ph" style="--c:{s["color"]}">?</div>'
        st = s.get('stat')
        cards += f'''<section class="bf" data-i="{i}"><div class="bf-img{' contain' if s.get('contain') else ''}"{f' style="--bgimg:url({o["w320"]})"' if (o and s.get('contain')) else ''}>{bg}</div>
<div class="bf-body"><div class="bf-meta">{tag(s)}<span>{i + 1} / {len(S)}</span></div><h2>{e(s['head'])}</h2><p>{e(s['dek'])}</p>
{f'<div class="bf-stat" style="--c:{s["color"]}"><b>{e(st[0])}</b><span>{e(st[1])}</span></div>' if st else ''}
<a class="bf-go" href="{url(d, s)}">Read the full story →</a></div></section>'''
    cards += f'''<section class="bf end"><div class="bf-body"><div class="bf-done">accha<b>?</b></div><h2>That's all {len(S)}. Now you know.</h2>
<p>New stories every morning.</p><a class="btn" href="{IG}" target="_blank" rel="noopener">Follow @accha.daily</a><a class="bf-go" href="{url(d)}">← Back to all stories</a></div></section>'''
    body = f'''<div class="bf-wrap" id="bf"><div class="bf-top"><a href="{url(d)}" aria-label="Close">✕</a><div class="bf-bar"><i id="bfp"></i></div><span id="bfn">1/{len(S)}</span></div>{cards}</div>
<div class="bf-hint" id="bfh">Swipe up ↑</div>'''
    o = opt(d['date'], S[0].get('img', ''))
    html_ = shell(f"Today in 60 seconds — accha? daily, {d['date_label']}", f"All {len(S)} of today's stories, one swipe at a time.", url(d) + '60/', card(d) or (o and o['og']), body)
    return html_.replace('<body>', '<body class="bfmode">', 1)


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
    return shell(f"{s['head']} — accha? daily", s['dek'], url(d, s), card(d, s) or (o and o['og']), body, kind='article', extra=extra, bar=True)


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    open(path, 'w', encoding='utf-8').write(text)


# ---------- build ----------
for d in days:
    write(f'{d["date"]}/index.html', edition(d, False))
    write(f'{d["date"]}/60/index.html', brief_page(d))
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
urls = ['/', '/archive/'] + [url(d) for d in days] + [url(d) + '60/' for d in days] + [url(d, s) for d in days for s in d['stories']]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
      ''.join(f'<url><loc>{SITE}{u}</loc></url>' for u in urls) + '</urlset>')
write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
write('manifest.webmanifest', json.dumps({"name": "accha? daily", "short_name": "accha?", "start_url": "/", "display": "standalone",
      "background_color": "#FFFFFF", "theme_color": "#0F1115", "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
      {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}]}))
write('.nojekyll', '')
print('built', len(days), 'edition(s),', sum(len(d['stories']) for d in days), 'stories; latest', days[0]['date'])
