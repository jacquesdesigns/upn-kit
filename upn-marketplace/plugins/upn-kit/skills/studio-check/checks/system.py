"""SYSTEM , the job's design system is used, not redrawn.

- Components byte-identical: when job.json `components.manifest` names a manifest, every component it
  lists must appear in the built output exactly as its source file says, byte for byte (surrounding
  whitespace aside). A component re-typed by hand drifts, and a drifted component is a new component.
- Tokens only: the site's own CSS and JS (everything under serve.root except the tokens file, the
  component sources and vendor code), plus <style> blocks and style="" attributes in its HTML, carry no
  hex or rgb/hsl colour, no font name, no easing curve and no duration. Those live in the tokens file.
Both read the files on disk under serve.root, including on a --url or --live run.

Manifest format (JSON): a list of {"id", "source", "in"} or an object {id: {"source", "in"}} or
{id: "source"}. `source` is relative to the job root; `in` (optional) is the built file, relative to
serve.root, that must contain it; without `in`, any built .html under serve.root may.
"""
import json
import re
from pathlib import Path

from common import register

G = 'system'
CHECKS = register(G, {
    'components-identical': {
        'protects': 'components are copied from the system, never redrawn',
        'limit': '{component_drift} components that differ from their source',
        'taught_by': 'the studio build notes: drifted starred components (an earlier job)'},
    'tokens-only': {
        'protects': 'every colour, face, curve and duration comes from the tokens, so the system holds',
        'limit': '{token_leaks} raw values in the site\'s own CSS, JS and inline styles',
        'taught_by': 'an earlier job site test.py: the token gate over the site\'s own css and js'},
})

HEX = re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])')
COLFN = re.compile(r'\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*[\d.]', re.I)
TIME = re.compile(r'(?<![\w.-])(\d*\.?\d+)(ms|s)(?![\w-])')
BEZ = re.compile(r'cubic-bezier\s*\(', re.I)
DECL = re.compile(r'([a-zA-Z-]+)\s*:\s*([^;{}]+?)\s*(?=[;}]|$)')
JS_HEX = re.compile(r'([\'"`])#((?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4}))\1')
JS_DUR = re.compile(r'\bduration\s*:\s*\d*\.?\d+')
JS_EASE = re.compile(r'\bease\s*:\s*([\'"`])(?!none\1)[A-Za-z]+(?:\.[A-Za-z]+)?(?:\([^)]*\))?\1')
JS_FONT = re.compile(r'\b(?:fontFamily|font-family)\s*[:=]\s*([\'"`])(?!var\()[^\'"`]+\1')
JS_CUSTOM_EASE = re.compile(r'CustomEase\.create\s*\(\s*[\'"`][^\'"`]*[\'"`]\s*,\s*[\'"`][^\'"`]*\d')


def _css_hits(text, where):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'url\([^)]*\)', 'url()', text)
    hits = []
    for m in DECL.finditer(text):
        prop, val = m.group(1).lower(), m.group(2)
        line = text.count('\n', 0, m.start()) + 1
        tag = '%s:%d %s' % (where, line, prop)
        for h in HEX.findall(val):
            hits.append('%s colour %s' % (tag, h))
        if COLFN.search(val):
            hits.append('%s colour %s' % (tag, val.strip()[:30]))
        if prop in ('font-family',) and not re.match(r'^\s*(var\(|inherit|initial|unset|revert)', val):
            hits.append('%s font %s' % (tag, val.strip()[:30]))
        if prop == 'font' and 'var(' not in val and re.search(r'["\']|\b(serif|sans-serif|monospace)\b', val):
            hits.append('%s font %s' % (tag, val.strip()[:30]))
        if BEZ.search(val):
            hits.append('%s easing %s' % (tag, val.strip()[:34]))
        for num, unit in TIME.findall(val):
            if float(num) != 0 and not prop.startswith('--'):
                hits.append('%s duration %s%s' % (tag, num, unit))
                break
    return hits


def _js_hits(text, where):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'(?<![:\'"\\/])//[^\n]*', ' ', text)
    hits = []
    for rx, kind in ((JS_HEX, 'colour'), (JS_DUR, 'duration'), (JS_EASE, 'easing'), (JS_FONT, 'font'),
                     (JS_CUSTOM_EASE, 'easing'), (BEZ, 'easing')):
        for m in rx.finditer(text):
            if kind == 'colour' and not re.search(r'\d', m.group(2)):
                continue   # '#add' could be an id; a colour with no digit is left to review
            hits.append('%s:%d %s %s' % (where, text.count('\n', 0, m.start()) + 1, kind, m.group(0)[:36]))
    return hits


def _vendor(rel, lists):
    r = rel.replace('\\', '/').lower()
    return any(v.lower() in r for v in lists['vendor_paths'])


def tokens_only(sess):
    job = sess.job
    root = job.path(job.get('serve', 'root', default='.'))
    tok = job.path(job.get('tokens'))
    if not tok:
        sess.rec(G, 'tokens-only', 'skip', 'job.json names no tokens file, so there is nothing to hold values to')
        return
    if not tok.exists():
        sess.rec(G, 'tokens-only', 'fail', 'the tokens file %s does not exist' % job.get('tokens'))
        return
    src_dir = job.path(job.get('components', 'source_dir'))
    hits, files = [], 0
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in ('.css', '.js', '.mjs', '.html', '.htm'):
            continue
        rel = str(p.relative_to(root))
        if p.resolve() == tok or _vendor(rel, job.lists) or '/.' in '/' + rel or 'evidence/' in rel.replace('\\', '/'):
            continue
        if src_dir and src_dir in p.resolve().parents:
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        files += 1
        if p.suffix.lower() == '.css':
            hits += _css_hits(text, rel)
        elif p.suffix.lower() in ('.js', '.mjs'):
            hits += _js_hits(text, rel)
        else:
            for m in re.finditer(r'<style\b[^>]*>(.*?)</style>', text, re.S | re.I):
                hits += _css_hits(m.group(1), rel + ' <style>')
            for m in re.finditer(r'\sstyle\s*=\s*"([^"]*)"', text, re.I):
                hits += _css_hits(m.group(1) + ';', rel + ' style=')
            for m in re.finditer(r'<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>', text, re.S | re.I):
                hits += _js_hits(m.group(1), rel + ' <script>')
    lim = sess.L['token_leaks']
    sess.rec(G, 'tokens-only', 'pass' if len(hits) <= lim else 'fail',
             ('%d raw values in %d files: %s' % (len(hits), files, '; '.join(hits[:8]))) if hits
             else '%d files carry only tokens' % files)


def components(sess):
    job = sess.job
    man = job.get('components', 'manifest')
    if not man:
        why = 'job.json components.manifest is not set'
        if job.get('components', 'source_dir'):
            why += ' (a source_dir alone does not say what was included)'
        sess.rec(G, 'components-identical', 'skip', why)
        return
    mp = job.path(man)
    if not mp.exists():
        sess.rec(G, 'components-identical', 'fail', 'the manifest %s does not exist' % man)
        return
    data = json.loads(mp.read_text(encoding='utf-8'))
    entries = []
    if isinstance(data, list):
        entries = [(e.get('id') or e.get('source'), e) for e in data]
    elif isinstance(data, dict):
        for k, v in data.items():
            entries.append((k, {'source': v} if isinstance(v, str) else v))
    root = job.path(job.get('serve', 'root', default='.'))
    built = {}

    def read(p):
        if p not in built:
            built[p] = p.read_bytes() if p.exists() else None
        return built[p]
    htmls = [p for p in root.rglob('*.html') if 'evidence' not in p.parts]
    bad, n = [], 0
    for cid, e in entries:
        src = e.get('source')
        if not src:
            bad.append('%s: no source' % cid)
            continue
        sp = job.path(src)
        if not sp.exists():
            bad.append('%s: source %s is gone' % (cid, src))
            continue
        needle = sp.read_bytes().strip()
        n += 1
        if e.get('in'):
            hay = read((root / e['in']).resolve())
            if hay is None:
                bad.append('%s: built file %s is missing' % (cid, e['in']))
            elif needle not in hay:
                bad.append('%s: differs from %s in %s' % (cid, src, e['in']))
        elif not any(needle in (read(h) or b'') for h in htmls):
            bad.append('%s: %s appears byte for byte in no built page' % (cid, src))
    lim = sess.L['component_drift']
    sess.rec(G, 'components-identical', 'pass' if len(bad) <= lim else 'fail',
             ('%d of %d: %s' % (len(bad), len(entries), '; '.join(bad[:6]))) if bad
             else '%d components byte-identical to source' % n)


def run(sess):
    sess.guard(G, 'components-identical', lambda: components(sess))
    sess.guard(G, 'tokens-only', lambda: tokens_only(sess))
