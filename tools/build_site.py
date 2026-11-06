"""Builds the accha? daily website from data/*.json.

- index.html          -> latest day (homepage) with article pages via #/slug
- d/YYYY-MM-DD.html   -> every day's edition (archive)
Images live in assets/YYYY-MM-DD/<file> and are referenced by relative path.
Run from the repo root:  python3 tools/build_site.py
"""
import glob, html, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CSS = open('tools/site.css').read()
e = html.escape

days = sorted((json.load(open(p)) for p in glob.glob('data/*.json')), key=lambda d: d['date'], reverse=True)


def page(d, prefix, others):
    a = f"{prefix}assets/{d['date']}/"
    cards = ''.join(f'''<a class="card" href="#/{s['slug']}">
  <div class="thumb" style="background-image:url('{a}{s['img']}')"></div>
  <div class="cbody"><div class="tag" style="--c:{s['color']}"><i></i>{e(s['tag'])}</div>
  <h3>{e(s['head'])}</h3><p>{e(s['dek'])}</p><span class="more">Read the full story →</span></div></a>''' if s.get('img') else f'''<a class="card" style="grid-template-columns:1fr" href="#/{s['slug']}">
  <div class="cbody"><div class="tag" style="--c:{s['color']}"><i></i>{e(s['tag'])}</div>
  <h3>{e(s['head'])}</h3><p>{e(s['dek'])}</p><span class="more">Read the full story →</span></div></a>''' for s in d['stories'][:5])
    more = ''.join(f'''<a class="mrow" href="#/{s['slug']}">{f'<div class="mthumb" style="background-image:url({chr(39)}{a}{s["img"]}{chr(39)})"></div>' if s.get('img') else ''}<div><div class="tag" style="--c:{s['color']}"><i></i>{e(s['tag'])}</div><h4>{e(s['head'])}</h4><p>{e(s['dek'])}</p></div></a>''' for s in d['stories'][5:])
    arts = ''
    for s in d['stories']:
        secs = ''.join(f'<h2>{e(x["title"])}</h2>' + ''.join(f'<p>{e(p)}</p>' for p in x['paras']) for x in s['sections'])
        stat = f'<div class="stat"><div class="v" style="color:{s["color"]}">{e(s["stat"][0])}</div><div class="l">{e(s["stat"][1])}</div></div>' if s.get('stat') else ''
        facts = ''.join(f'<li><i style="background:{s["color"]}"></i>{e(f)}</li>' for f in s.get('facts', []))
        srcs = ''.join(f'<li><a href="{x["url"]}" target="_blank" rel="noopener">{e(x["name"])} ↗</a></li>' for x in s.get('sources', []))
        fig = (f'<figure class="hero {"contain" if s.get("contain") else "cover"}" style="--img:url(\'{a}{s["img"]}\')"><div class="ph"></div>'
               f'<figcaption>📷 {e(s.get("credit",""))}</figcaption></figure>') if s.get('img') else ''
        arts += f'''<article class="art" id="a-{s['slug']}" data-slug="{s['slug']}">
  <a class="back" href="#/">← All stories</a>
  <div class="tag" style="--c:{s['color']}"><i></i>{e(s['tag'])}</div>
  <h1>{e(s['head'])}</h1><p class="dek">{e(s['dek'])}</p>
  <div class="meta">accha? daily · {e(d['date_label'])} · 2 min read</div>
  {fig}{stat}<div class="body">{secs}</div>
  {f'<div class="box"><div class="bt">Key numbers</div><ul class="facts">{facts}</ul></div>' if facts else ''}
  {f'<div class="box"><div class="bt">Read the original reporting</div><ul class="src">{srcs}</ul></div>' if srcs else ''}
  <a class="back big" href="#/">← Back to the stories</a></article>'''
    also = ''.join(f'<li><a href="{x["url"]}" target="_blank" rel="noopener"><b>{e(x["title"])}</b><span>{e(x["text"])}</span></a></li>' for x in d.get('also', []))
    arch = ''.join(f'<li><a href="{prefix}d/{o["date"]}.html">{e(o["day"])}, {e(o["date_label"])}<span>{len(o["stories"])} stories →</span></a></li>' for o in others)
    title_line = "Today's" if not prefix else e(d['day']) + "'s"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>accha? daily — {e(d['date_label'])}</title>
<meta name="description" content="The day's biggest stories on brands, startups, tech and your wallet — explained simply. By @accha.daily.">
<meta property="og:title" content="accha? daily — {e(d['stories'][0]['head'])}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header><div class="wrap"><a class="logo" href="{prefix or './'}">accha<b>?</b> <span>daily</span></a><div class="date">{e(d['day'])}, {e(d['date_label'])}</div></div></header>
<main class="wrap">
<section id="home">
 <div class="hero-t"><div class="kick">{e(d['day'])} · {e(d['date_label'])}</div><h1>{title_line} biggest stories<b>.</b></h1>
 <p>{len(d['stories'])} stories from India and the world — brands, startups, tech, sports and your wallet, explained simply.</p></div>
 <div class="cards">{cards}</div>
 {f'<div class="sec-t">More stories</div><div class="more-list">{more}</div>' if more else ''}
 {f'<div class="sec-t">Also today</div><ul class="also">{also}</ul>' if also else ''}
 {f'<div class="note">{e(d["note"])}</div>' if d.get('note') else ''}
 <div class="cta"><h4>accha<b>?</b> Now you know.</h4><p>The day's biggest stories, every morning, in 60 seconds.</p><a class="btn" href="https://instagram.com/accha.daily" target="_blank" rel="noopener">Follow @accha.daily</a></div>
 {f'<div class="sec-t">Past days</div><ul class="arch">{arch}</ul>' if arch else ''}
</section>
{arts}
<footer>accha? daily summarises news in its own words and links to the original reporting. Photos are credited to their sources. Not investment advice.</footer>
</main>
<script>
function route(){{var s=(location.hash||'').replace('#/','');document.querySelectorAll('.art').forEach(function(a){{a.style.display=a.dataset.slug===s?'block':'none'}});
var a=document.getElementById('a-'+s);document.body.classList.toggle('reading',!!a);window.scrollTo(0,0);
document.title=a?a.querySelector('h1').textContent+' — accha? daily':'accha? daily — {e(d['date_label'])}';}}
window.addEventListener('hashchange',route);route();
</script></body></html>'''


os.makedirs('d', exist_ok=True)
for i, d in enumerate(days):
    open(f"d/{d['date']}.html", 'w').write(page(d, '../', [o for o in days if o is not d][:30]))
open('index.html', 'w').write(page(days[0], '', days[1:31]))
print('built', len(days), 'day(s); latest', days[0]['date'])
