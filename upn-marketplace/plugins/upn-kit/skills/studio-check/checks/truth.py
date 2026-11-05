"""TRUTH , the page says nothing untrue, nothing it should not, and in the studio's voice.

Read from the RENDERED page (the DOM after its scripts ran, so words a script writes are checked too),
text joined per block so a heading split into letters still reads as its words, plus the attributes a
person reads (alt, title, aria-label, placeholder, meta descriptions and link previews).

- no em dash, no spaced en dash, no double hyphen;
- no mention of AI or the tools (the studio never names them in anything a visitor sees);
- British spelling; no hype; nothing on the job's own banned list;
- no price and no day-level date unless job.json `copy.allow_prices` / `copy.allow_dates` says so
  (a bare year is not a date here);
- an unknown is written as the job's `copy.unknown_marker`, never as TBC, lorem, a placeholder;
- no picture on the page comes from a folder the job marks as mockups (`copy.mockup_dirs`) or is on
  its `copy.banned_images` list: words baked into pixels are invisible to every text check.
OCR is not attempted.
"""
import re

from common import register

G = 'truth'
_T_COPY = 'v1 BUILD-LOG, 27 Sep: the copy check failed the first draft on 15 counts'
CHECKS = register(G, {
    'no-dashes': {
        'protects': 'the studio\'s punctuation: no em dash, no spaced en dash, no double hyphen',
        'limit': '{copy_hits} hits',
        'taught_by': _T_COPY},
    'no-ai-mention': {
        'protects': 'nothing a visitor sees names AI, a model or a tool',
        'limit': '{copy_hits} hits',
        'taught_by': 'the copy rule (switch off per job in job.json lists.ai_mentions)'},
    'british-spelling': {
        'protects': 'British English everywhere',
        'limit': '{copy_hits} US spellings',
        'taught_by': _T_COPY},
    'no-hype': {
        'protects': 'plain words, never press-release copy',
        'limit': '{copy_hits} hype words',
        'taught_by': 'the root voice rules: no hype, no empty intensifiers'},
    'banned-words': {
        'protects': 'the job\'s own words to avoid stay out',
        'limit': '{copy_hits} hits from job.json copy.banned',
        'taught_by': 'v1 copy check, 27 Sep: "loader", "ground", "component" in visitor copy'},
    'no-price': {
        'protects': 'no price is stated unless the job allows it',
        'limit': '{copy_hits} prices (copy.allow_prices false)',
        'taught_by': 'v1 PLAN.md: no prices anywhere'},
    'no-date': {
        'protects': 'no day-level date is invented or stated unless the job allows it',
        'limit': '{copy_hits} dates (copy.allow_dates false)',
        'taught_by': 'v1 BUILD-LOG, 28 Sep: an earlier job mockups printing "Sat 9 July 2027", a Friday'},
    'unknowns-marked': {
        'protects': 'what is not known yet says so in the job\'s words, never a placeholder',
        'limit': '{copy_hits} placeholders; unknowns read "{unknown_marker}"',
        'taught_by': 'the studio build notes: 15 of 45 reversals were invented facts'},
    'no-mockup-imagery': {
        'protects': 'no picture carries a fact the page cannot stand behind',
        'limit': '{mockup_images} pictures from a mockups folder or the banned list',
        'taught_by': 'an earlier job site test.py: poster mockups printing "12-14 JUL 2025" and "ARTIST NAME"'},
})

TEXT_JS = r"""() => {
  const L = __sc, blocks = new Map();
  const skip = el => !!el.closest('script, style, noscript, template, svg, head, [data-sc-ignore]');
  const blockOf = el => { for (let a = el; a && a !== document.body; a = a.parentElement) if (L.isBlock(a) || getComputedStyle(a).display === 'none') return a; return document.body; };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let t;
  while ((t = walker.nextNode())) {
    if (!t.textContent.trim() || !t.parentElement || skip(t.parentElement)) continue;
    const b = blockOf(t.parentElement);
    blocks.set(b, (blocks.get(b) || '') + t.textContent);
  }
  const attrs = [];
  for (const el of document.querySelectorAll('[alt], [title], [aria-label], [placeholder]'))
    for (const a of ['alt', 'title', 'aria-label', 'placeholder']) { const v = el.getAttribute(a); if (v && v.trim()) attrs.push(v); }
  for (const m of document.querySelectorAll('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')) {
    const v = m.getAttribute('content'); if (v && !/^https?:|\.(png|jpe?g|webp|gif)$/i.test(v)) attrs.push(v);
  }
  if (document.title) attrs.push(document.title);
  return {text: [...blocks.values()].map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean), attrs};
}"""

IMAGES_JS = r"""() => {
  const out = new Set();
  const add = u => { if (u && !u.startsWith('data:')) { try { out.add(new URL(u, location.href).pathname); } catch (e) {} } };
  for (const i of document.images) { add(i.currentSrc); add(i.getAttribute('src')); (i.getAttribute('srcset') || '').split(',').forEach(s => add(s.trim().split(/\s+/)[0])); }
  for (const s of document.querySelectorAll('source[srcset], source[src]')) { add(s.getAttribute('src')); (s.getAttribute('srcset') || '').split(',').forEach(x => add(x.trim().split(/\s+/)[0])); }
  for (const v of document.querySelectorAll('video[poster]')) add(v.getAttribute('poster'));
  for (const el of document.querySelectorAll('body *')) {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg !== 'none') for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) add(m[1]);
  }
  return [...out].map(decodeURIComponent);
}"""

MONTHS = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
DAYS = r'(?:mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)(?:day)?'
DATE_RX = re.compile(
    r'\b\d{1,2}(?:st|nd|rd|th)?(?:\s*[-\u2013/]\s*\d{1,2}(?:st|nd|rd|th)?)?\s+' + MONTHS + r'\b'
    r'|\b' + MONTHS + r'\.?\s+\d{1,2}(?:st|nd|rd|th)?\b(?!\s*(?:am|pm|%|px))'
    r'|\b' + DAYS + r'\.?,?\s+\d{1,2}(?:st|nd|rd|th)?\b'
    r'|\b\d{1,2}[/.]\d{1,2}[/.](?:\d{2}|\d{4})\b', re.I)
PRICE_RX = re.compile(r'[£$€]\s?\d|\b\d+(?:\.\d+)?\s?(?:GBP|EUR|USD)\b|\bper (?:day|hour|head)\b|\bfrom £', re.I)


def _hits(rx, text, n=6):
    out = []
    for m in rx.finditer(text):
        a, b = max(0, m.start() - 28), min(len(text), m.end() + 28)
        out.append('"%s" in "...%s..."' % (m.group(0), text[a:b].replace('\n', ' ')))
    return out


def _words_rx(words):
    parts = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        e = re.escape(w)
        parts.append((r'(?<![\w-])' if w[0].isalnum() else '') + e + (r'(?![\w-])' if w[-1].isalnum() else ''))
    return re.compile('|'.join(parts), re.I) if parts else None


def check_page(sess, page):
    size = (1440, 900)
    ctx, why = sess.context('chromium', size)
    if not ctx:
        for c in CHECKS:
            sess.rec(G, c, 'skip', why, page, size, 'chromium')
        return
    try:
        pg = sess.open(ctx, page)
        got = pg.evaluate(TEXT_JS)
        imgs = pg.evaluate(IMAGES_JS)
    finally:
        ctx.close()
    text = '\n'.join(got['text'] + got['attrs'])
    lists = sess.job.lists
    copy = sess.job.get('copy') or {}
    lim = sess.L['copy_hits']

    def out(check, hits, ok):
        sess.rec(G, check, 'pass' if len(hits) <= lim else 'fail',
                 ('%d: %s' % (len(hits), '; '.join(hits[:6]))) if hits else ok, page, size, 'chromium')

    dashes = _hits(re.compile('\u2014'), text) + _hits(re.compile('\\s\u2013\\s'), text) + \
        _hits(re.compile(r'(?<![<!-])--(?![->])'), text)
    out('no-dashes', dashes, 'no em dash, spaced en dash or double hyphen in %d blocks' % len(got['text']))
    if lists['ai_mentions']:
        ai = re.compile('|'.join(lists['ai_mentions']), re.I)
        out('no-ai-mention', _hits(ai, text), 'no mention of AI or the tools')
    us = re.compile(r'(?<![\w-])(' + '|'.join(re.escape(w) for w in lists['us_spellings']) + r')(?![\w-])', re.I)
    out('british-spelling', _hits(us, text), 'no US spellings from the list of %d' % len(lists['us_spellings']))
    hype = _words_rx(lists['hype'])
    out('no-hype', _hits(hype, text) if hype else [], 'no hype words')
    banned = _words_rx(copy.get('banned') or [])
    if banned:
        out('banned-words', _hits(banned, text), 'none of the job\'s %d banned words' % len(copy.get('banned') or []))
    else:
        sess.rec(G, 'banned-words', 'skip', 'job.json copy.banned is empty', page, size, 'chromium')
    if copy.get('allow_prices'):
        sess.rec(G, 'no-price', 'skip', 'the job allows prices (copy.allow_prices)', page, size, 'chromium')
    else:
        out('no-price', _hits(PRICE_RX, text), 'no price')
    if copy.get('allow_dates'):
        sess.rec(G, 'no-date', 'skip', 'the job allows dates (copy.allow_dates)', page, size, 'chromium')
    else:
        out('no-date', _hits(DATE_RX, text), 'no day-level date')
    marker = copy.get('unknown_marker') or 'to confirm'
    ph = re.compile('|'.join(lists['placeholders']), re.I)
    n_marker = len(re.findall(re.escape(marker), text, re.I))
    sess.rec(G, 'unknowns-marked', 'pass' if len(_hits(ph, text)) <= lim else 'fail',
             ('%d placeholders (write "%s" instead): %s' % (len(_hits(ph, text)), marker, '; '.join(_hits(ph, text)[:6])))
             if _hits(ph, text) else 'no placeholders; "%s" appears %d times' % (marker, n_marker),
             page, size, 'chromium', limit='0 placeholders; unknowns read "%s"' % marker)
    dirs = [d.strip('/').lower() for d in (copy.get('mockup_dirs') or []) if d.strip('/')]
    banned_imgs = {b.lower() for b in (copy.get('banned_images') or [])}
    bad = []
    for u in imgs:
        segs = [s.lower() for s in u.split('/') if s]
        leaf = segs[-1] if segs else ''
        joined = '/'.join(segs[:-1])
        if any(d in segs[:-1] or ('/' in d and ('/' + d + '/') in ('/' + joined + '/')) for d in dirs) or leaf in banned_imgs:
            bad.append(u)
    sess.rec(G, 'no-mockup-imagery', 'pass' if len(bad) <= sess.L['mockup_images'] else 'fail',
             ('%d: %s' % (len(bad), '; '.join(bad[:6]))) if bad else '%d pictures, none from %s or the banned list' % (len(imgs), dirs or 'no mockup folder'),
             page, size, 'chromium')


def run(sess):
    for page in sess.pages:
        sess.guard(G, 'no-dashes', lambda: check_page(sess, page), page=page.get('name'), size=(1440, 900), engine='chromium')
