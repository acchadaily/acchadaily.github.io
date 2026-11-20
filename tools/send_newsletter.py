#!/usr/bin/env python3
"""Send the daily "accha? daily" email as a Kit (kit.com) broadcast.

Reads the files tools/build_newsletter.py produced, then creates a broadcast
over Kit's v4 API. Run build_newsletter.py first.

    export KIT_API_KEY=...                       # Kit > Settings > Developer
    python3 tools/send_newsletter.py             # schedule the latest edition
    python3 tools/send_newsletter.py --draft     # create a draft, don't send
    python3 tools/send_newsletter.py 2026-11-20  # a specific edition
    python3 tools/send_newsletter.py --check     # just verify the API key works

Kit has no "send now" field. A broadcast with send_at in the future is
scheduled; send_at null is a draft. So "send now" is send_at = a couple of
minutes from now, which also leaves a small window to cancel in the Kit UI.

Exit codes: 0 ok, 1 usage/config error, 2 API error. The daily run should
treat a non-zero exit as "the email did not go out" and say so.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
import urllib.error
import urllib.request

API = 'https://api.kit.com/v4'
LEAD_MINUTES = 3  # how far ahead to schedule, so there is time to cancel


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(path, method='GET', payload=None, key=None):
    """One Kit API call. Returns (status, parsed_body)."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    req.add_header('X-Kit-Api-Key', key)
    req.add_header('Accept', 'application/json')
    if data:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as ex:
        body = ex.read().decode(errors='replace')
        try:
            return ex.code, json.loads(body)
        except ValueError:
            return ex.code, {'raw': body[:600]}
    except urllib.error.URLError as ex:
        return 0, {'error': f'could not reach Kit: {ex.reason}'}


def find_files(date=None):
    out = os.path.join(repo_root(), 'newsletter')
    if date:
        base = os.path.join(out, f'newsletter-{date}')
    else:
        found = sorted(glob.glob(os.path.join(out, 'newsletter-*.html')))
        if not found:
            raise SystemExit(f'no built newsletter in {out} — run tools/build_newsletter.py first')
        base = found[-1][:-len('.html')]
    html_p, subj_p = base + '.html', base + '.subject.txt'
    for p in (html_p, subj_p):
        if not os.path.exists(p):
            raise SystemExit(f'missing {p} — run tools/build_newsletter.py first')
    with open(html_p, encoding='utf-8') as f:
        body = f.read()
    with open(subj_p, encoding='utf-8') as f:
        subject = f.read().strip()
    return body, subject, os.path.basename(base).replace('newsletter-', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('date', nargs='?', help='YYYY-MM-DD (default: newest built)')
    ap.add_argument('--draft', action='store_true', help='create a draft instead of scheduling')
    ap.add_argument('--check', action='store_true', help='verify the API key and exit')
    a = ap.parse_args()

    key = os.environ.get('KIT_API_KEY', '').strip()
    if not key:
        print('KIT_API_KEY is not set. Kit > Settings > Developer > API key.', file=sys.stderr)
        return 1

    if a.check:
        status, body = api('/account', key=key)
        if status == 200:
            name = (body.get('account') or {}).get('name', '(unnamed)')
            print(f'OK — key works. Account: {name}')
            return 0
        print(f'Key check failed (HTTP {status}): {json.dumps(body)[:400]}', file=sys.stderr)
        return 2

    body_html, subject, date = find_files(a.date)

    send_at = None
    when_ist = None
    if not a.draft:
        when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=LEAD_MINUTES)
        send_at = when.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        # the API takes UTC, but this runs for an Indian paper and is read by a
        # human in Kolkata, so report IST too. Fixed offset: India has no DST.
        when_ist = (when + dt.timedelta(hours=5, minutes=30)).strftime('%H:%M IST')

    payload = {
        'subject': subject,
        'content': body_html,
        'description': f'accha? daily {date}',
        'preview_text': subject,
        'public': False,       # don't publish it on Kit's own site
        'send_at': send_at,    # null = draft
    }

    status, resp = api('/broadcasts', method='POST', payload=payload, key=key)
    if status not in (200, 201):
        print(f'Kit rejected the broadcast (HTTP {status}): {json.dumps(resp)[:600]}', file=sys.stderr)
        return 2

    b = resp.get('broadcast') or {}
    bid = b.get('id')
    if a.draft:
        print(f'Draft created for {date} (id {bid}). Review and send it in Kit.')
    else:
        print(f'Scheduled for {date} (id {bid}), sending at {when_ist} '
              f'({send_at}), in ~{LEAD_MINUTES} min. Cancel in Kit before then if needed.')
    print(f'Subject: {subject}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
