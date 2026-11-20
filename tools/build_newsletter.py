#!/usr/bin/env python3
"""Build the daily "accha? daily" email from a data/YYYY-MM-DD.json edition.

Platform-agnostic: it writes an HTML email, a plain-text fallback and a subject
line. Whatever service sends it (beehiiv, Kit, MailerLite...) just takes these
strings — nothing here is tied to one provider.

    python3 tools/build_newsletter.py                 # latest edition, top 5
    python3 tools/build_newsletter.py 2026-11-20 -n 4
    python3 tools/build_newsletter.py --out /tmp/mail # where to write

Writes <out>/newsletter-YYYY-MM-DD.html, .txt and .subject.txt.

Design: the brand's yellow (#F2B705) and black, used throughout — black bars,
yellow number tiles, heavy display headlines. Deliberately old-fashioned HTML:
tables, inline styles, bgcolor attributes for Outlook, no external CSS, no
webfonts, no webp. That is what survives Gmail, Outlook and Apple Mail.
"""
import argparse
import glob
import html
import json
import os
import re

SITE = 'https://acchadaily.github.io'
INSTAGRAM = 'https://instagram.com/accha.daily'

YEL = '#F2B705'      # brand yellow
INK = '#0F1115'      # near-black
BODY = '#33373F'     # body copy on white
MUT = '#6B7079'
LINE = '#E4E5E8'
CREAM = '#FFFBF0'
WHITE = '#FFFFFF'

# No webfonts in email. A heavy, widely-installed stack for display type.
DISP = "'Arial Black','Arial Bold',Helvetica,Arial,sans-serif"
SANS = "'Helvetica Neue',Helvetica,Arial,sans-serif"


def e(s):
    return html.escape(str(s or ''), quote=True)


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(date=None):
    root = repo_root()
    if date:
        p = os.path.join(root, 'data', f'{date}.json')
        if not os.path.exists(p):
            raise SystemExit(f'no edition at {p}')
    else:
        files = sorted(glob.glob(os.path.join(root, 'data', '*.json')))
        if not files:
            raise SystemExit('no editions in data/')
        p = files[-1]
    with open(p, encoding='utf-8') as f:
        return json.load(f), os.path.splitext(os.path.basename(p))[0]


def img_url(date, story):
    """Absolute URL of the 1200x630 JPEG share crop, or '' when there's none."""
    name = story.get('img') or ''
    if not name:
        return ''
    stem = os.path.splitext(name)[0]
    local = os.path.join(repo_root(), 'assets', date, 'w', f'{stem}-og.jpg')
    if os.path.exists(local):
        return f'{SITE}/assets/{date}/w/{stem}-og.jpg'
    return f'{SITE}/assets/{date}/{name}'


def story_url(date, story):
    return f"{SITE}/{date}/{story['slug']}/"


def pick(data, n):
    return [s for s in data['stories'] if s.get('tag') != 'Good News'][:n]


def good_ones(data, n=3):
    return [s for s in data['stories'] if s.get('tag') == 'Good News'][:n]


def email_head(story):
    """Punchier headline for email.

    Site headlines often pack two clauses split by a semicolon ("X does Y;
    Z happens from 1 December"). In a 600px email the first clause reads far
    better and the dek carries the rest. Only trim when what's left still
    stands on its own.
    """
    head = story['head']
    first = head.split(';')[0].strip()
    return first if len(first) >= 40 else head


def story_block(date, story, idx, lead=False):
    """One story: yellow number + tag bar, photo, heavy headline, stat, link."""
    url = story_url(date, story)
    img = img_url(date, story)
    head_size = '30px' if lead else '24px'
    head_cls = 'hl' if lead else 'hs'

    photo = ''
    if img:
        photo = (
            f'<tr><td style="padding:0 0 18px;">'
            f'<a href="{e(url)}" style="text-decoration:none;">'
            f'<img src="{e(img)}" width="552" alt="" '
            f'style="display:block;width:100%;max-width:552px;height:auto;border:0;" /></a>'
            f'</td></tr>'
        )

    stat = ''
    if story.get('stat'):
        val, label = story['stat'][0], story['stat'][1]
        stat = (
            f'<tr><td style="padding:18px 0 0;">'
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
            f'bgcolor="{INK}" style="width:100%;background:{INK};"><tr>'
            f'<td style="padding:16px 18px;">'
            f'<span style="font:900 26px/1 {DISP};color:{YEL};">{e(val)}</span>'
            f'<span style="font:700 13px/1.4 {SANS};color:{WHITE};">&nbsp;&nbsp;{e(label)}</span>'
            f'</td></tr></table></td></tr>'
        )

    # number tile + tag, side by side
    bar = (
        f'<tr><td style="padding:0 0 14px;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td bgcolor="{YEL}" style="background:{YEL};padding:7px 11px;">'
        f'<span style="font:900 15px/1 {DISP};color:{INK};">{idx:02d}</span></td>'
        f'<td bgcolor="{INK}" style="background:{INK};padding:7px 12px;">'
        f'<span style="font:700 12px/1 {SANS};color:{WHITE};letter-spacing:.1em;'
        f'text-transform:uppercase;">{e(story["tag"])}</span></td>'
        f'</tr></table></td></tr>'
    )

    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="width:100%;border-collapse:collapse;">'
        f'{bar}{photo}'
        f'<tr><td style="padding:0 0 10px;">'
        f'<a href="{e(url)}" style="text-decoration:none;">'
        f'<span class="{head_cls}" style="font:900 {head_size}/1.15 {DISP};color:{INK};'
        f'letter-spacing:-.4px;">{e(email_head(story))}</span></a></td></tr>'
        f'<tr><td style="font:400 16px/1.55 {SANS};color:{BODY};">'
        f'{e(story.get("dek"))}</td></tr>'
        f'{stat}'
        f'<tr><td style="padding:18px 0 0;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td bgcolor="{YEL}" style="background:{YEL};padding:11px 18px;">'
        f'<a href="{e(url)}" style="font:900 13px/1 {DISP};color:{INK};'
        f'text-decoration:none;letter-spacing:.03em;text-transform:uppercase;">'
        f'Read the full story &rarr;</a></td></tr></table></td></tr>'
        f'</table>'
    )


def good_block(date, stories):
    if not stories:
        return ''
    rows = ''
    for s in stories:
        rows += (
            f'<tr><td style="padding:0 0 12px;font:700 15px/1.45 {SANS};color:{INK};">'
            f'<span style="font-size:18px;">{e(s.get("emoji") or "☀️")}</span>&nbsp;&nbsp;'
            f'<a href="{e(story_url(date, s))}" style="color:{INK};text-decoration:none;">'
            f'{e(s["head"])}</a></td></tr>'
        )
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'bgcolor="{YEL}" style="width:100%;background:{YEL};">'
        f'<tr><td style="padding:24px;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">'
        f'<tr><td style="padding:0 0 16px;font:900 20px/1 {DISP};color:{INK};'
        f'letter-spacing:-.3px;">ONLY GOOD NEWS</td></tr>'
        f'{rows}'
        f'<tr><td style="padding:6px 0 0;">'
        f'<a href="{SITE}/{date}/good/" style="font:900 13px/1 {DISP};color:{INK};'
        f'text-decoration:none;border-bottom:3px solid {INK};padding-bottom:2px;'
        f'text-transform:uppercase;">All of today&rsquo;s good news &rarr;</a></td></tr>'
        f'</table></td></tr></table>'
    )


def markets_block(data):
    m = data.get('markets') or {}
    items = (m.get('items') or [])[:5]
    if not items:
        return ''
    cells = ''
    for it in items:
        cells += (
            f'<td style="padding:0 20px 0 0;font:700 11px/1.5 {SANS};color:{YEL};'
            f'letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;">'
            f'{e(it.get("n"))}<br />'
            f'<span style="font:900 18px/1.3 {DISP};color:{WHITE};letter-spacing:0;'
            f'text-transform:none;">{e(it.get("v"))}</span>'
            f'<span style="font:700 12px/1 {SANS};color:{WHITE};text-transform:none;'
            f'letter-spacing:0;">&nbsp;{e(it.get("c"))}</span></td>'
        )
    asof = m.get('asof')
    note = (f'<tr><td colspan="{len(items)}" style="padding:12px 0 0;'
            f'font:400 11px/1.4 {SANS};color:#9AA0AA;">{e(asof)}</td></tr>') if asof else ''
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'bgcolor="{INK}" style="width:100%;background:{INK};">'
        f'<tr><td style="padding:20px 24px;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'<tr>{cells}</tr>{note}</table></td></tr></table>'
    )


def build_html(data, date, n):
    top = pick(data, n)
    if not top:
        raise SystemExit('edition has no regular stories')
    good = good_ones(data)
    total = len([s for s in data['stories'] if s.get('tag') != 'Good News'])
    n_good = len([s for s in data['stories'] if s.get('tag') == 'Good News'])
    more = max(0, total - len(top))

    preheader = ' · '.join(s['head'] for s in top[:3])[:150]

    blocks = ''
    for i, s in enumerate(top):
        blocks += (f'<tr><td>{story_block(date, s, i + 1, lead=(i == 0))}</td></tr>')
        if i != len(top) - 1:
            blocks += (f'<tr><td style="padding:30px 0;">'
                       f'<div style="height:4px;background:{INK};line-height:4px;'
                       f'font-size:4px;">&nbsp;</div></td></tr>')

    mk = markets_block(data)
    mk_row = f'<tr><td style="padding:34px 24px 0;">{mk}</td></tr>' if mk else ''
    gd = good_block(date, good)
    gd_row = f'<tr><td style="padding:30px 24px 0;">{gd}</td></tr>' if gd else ''

    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<meta name="color-scheme" content="light" />
<meta name="supported-color-schemes" content="light" />
<title>accha? daily &mdash; {e(data.get('date_label'))}</title>
<style>
  /* Phones. Clients that ignore <style> simply keep the inline sizes. */
  @media only screen and (max-width:480px) {{
    .hl {{ font-size:25px !important; }}
    .hs {{ font-size:21px !important; }}
    .wordmark {{ font-size:32px !important; }}
    .bignum {{ font-size:26px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#E9EAEC;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{e(preheader)}</div>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
 bgcolor="#E9EAEC" style="width:100%;background:#E9EAEC;border-collapse:collapse;">
<tr><td align="center" style="padding:24px 12px 36px;">

<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600"
 bgcolor="{WHITE}" style="width:100%;max-width:600px;background:{WHITE};border-collapse:collapse;">

<!-- masthead -->
<tr><td bgcolor="{INK}" style="background:{INK};padding:26px 24px 22px;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
  <tr><td class="wordmark" style="font:900 40px/1 {DISP};letter-spacing:-1.4px;padding:0 0 10px;">
      <a href="{SITE}/" style="text-decoration:none;">
        <span style="color:{YEL};">accha?</span><span style="color:{WHITE};">&nbsp;daily</span>
      </a></td></tr>
  <tr><td>
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      <td bgcolor="{YEL}" style="background:{YEL};padding:6px 10px;">
        <span style="font:900 11px/1 {DISP};color:{INK};letter-spacing:.08em;">
          {e(data.get('day', '')).upper()}, {e(data.get('date_label', '')).upper()}</span></td>
      </tr></table></td></tr>
  <tr><td style="padding:12px 0 0;font:700 13px/1.4 {SANS};color:#B9BDC4;
      letter-spacing:.06em;text-transform:uppercase;">
      Today&rsquo;s {len(top)} biggest stories</td></tr>
  </table>
</td></tr>

<!-- stories -->
<tr><td style="padding:32px 24px 0;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
   style="width:100%;border-collapse:collapse;">
  {blocks}
  </table>
</td></tr>

{mk_row}
{gd_row}

<!-- full edition -->
<tr><td style="padding:34px 24px 0;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
   bgcolor="{INK}" style="width:100%;background:{INK};">
  <tr><td align="center" style="padding:30px 24px;">
    <div class="bignum" style="font:900 32px/1.05 {DISP};color:{YEL};letter-spacing:-.8px;padding:0 0 8px;">
      {more} MORE<br />STORIES TODAY</div>
    <div style="font:400 14px/1.55 {SANS};color:#B9BDC4;padding:0 0 20px;">
      Plus {n_good} good-news stories, the 60-second scroll<br />and the newspaper view.</div>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"><tr>
    <td bgcolor="{YEL}" style="background:{YEL};padding:15px 28px;">
      <a href="{SITE}/{date}/" style="font:900 15px/1 {DISP};color:{INK};
         text-decoration:none;text-transform:uppercase;letter-spacing:.03em;">
        Read the full edition</a></td>
    </tr></table>
  </td></tr></table>
</td></tr>

<!-- links -->
<tr><td style="padding:24px;" align="center">
  <a href="{SITE}/{date}/60/" style="font:900 12px/1.8 {DISP};color:{INK};text-decoration:none;text-transform:uppercase;">60-second scroll</a>
  <span style="color:{YEL};font-weight:900;">&nbsp;&nbsp;/&nbsp;&nbsp;</span>
  <a href="{SITE}/{date}/good/" style="font:900 12px/1.8 {DISP};color:{INK};text-decoration:none;text-transform:uppercase;">Good news</a>
  <span style="color:{YEL};font-weight:900;">&nbsp;&nbsp;/&nbsp;&nbsp;</span>
  <a href="{INSTAGRAM}" style="font:900 12px/1.8 {DISP};color:{INK};text-decoration:none;text-transform:uppercase;">@accha.daily</a>
</td></tr>

<!-- footer -->
<tr><td bgcolor="{INK}" style="background:{INK};padding:26px 24px;" align="center">
  <div style="font:900 15px/1 {DISP};color:{YEL};padding:0 0 10px;letter-spacing:-.2px;">accha? daily</div>
  <div style="font:400 12px/1.7 {SANS};color:#9AA0AA;">
    You get this because you subscribed to accha? daily.<br />
    The day&rsquo;s biggest stories on brands, startups, tech and your wallet &mdash; explained simply.
    <div style="padding:12px 0 0;">{{$unsubscribe}}</div>
  </div>
</td></tr>

</table>
</td></tr></table>
</body></html>
'''


def build_text(data, date, n):
    top = pick(data, n)
    good = good_ones(data)
    total = len([s for s in data['stories'] if s.get('tag') != 'Good News'])
    out = [f"accha? daily - {data.get('day')}, {data.get('date_label')}",
           f"Today's {len(top)} biggest stories", '']
    for i, s in enumerate(top, 1):
        out += [f"{i:02d}. [{s['tag']}] {s['head']}", f"    {s.get('dek')}",
                f"    {story_url(date, s)}", '']
    if good:
        out += ['-- ONLY GOOD NEWS --']
        out += [f"* {s['head']}  {story_url(date, s)}" for s in good]
        out += ['']
    out += [f"{max(0, total - len(top))} more stories today: {SITE}/{date}/",
            f"60-second scroll: {SITE}/{date}/60/",
            f"Good news: {SITE}/{date}/good/",
            f"Instagram: {INSTAGRAM}", '',
            'You get this because you subscribed to accha? daily.',
            '{$unsubscribe}']
    return '\n'.join(out)


def build_subject(data, n):
    top = pick(data, n)
    head = re.split(r'[;:]', top[0]['head'])[0].strip() if top else 'Today'
    if len(head) > 62:
        head = head[:59].rsplit(' ', 1)[0] + '...'
    return head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date', nargs='?', help='YYYY-MM-DD (default: latest edition)')
    ap.add_argument('-n', '--stories', type=int, default=5, help='how many top stories (default 5)')
    ap.add_argument('--out', default=None, help='output directory (default: repo /newsletter)')
    a = ap.parse_args()

    data, date = load(a.date)
    out = a.out or os.path.join(repo_root(), 'newsletter')
    os.makedirs(out, exist_ok=True)

    html_s = build_html(data, date, a.stories)
    text_s = build_text(data, date, a.stories)
    subj = build_subject(data, a.stories)

    base = os.path.join(out, f'newsletter-{date}')
    for suffix, body in (('.html', html_s), ('.txt', text_s), ('.subject.txt', subj + '\n')):
        with open(base + suffix, 'w', encoding='utf-8') as f:
            f.write(body)

    print(f'{date}: {a.stories} stories, {len(html_s):,} bytes html')
    print(f'subject: {subj}')
    print(f'wrote {base}.html / .txt / .subject.txt')


if __name__ == '__main__':
    main()
