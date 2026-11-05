"""Shared parts of the studio check kit: the job config, serving, browsers, result recording, shots.

Every path is resolved from this file or from the job folder, never from a machine, so the kit runs
the same inside a cloud container that holds only this repo.
"""
import datetime
import functools
import http.server
import io
import json
import os
import re
import shutil
import socketserver
import threading
import time
import traceback
import urllib.parse
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[2]
GROUPS = ['truth', 'layout', 'grid', 'spacing', 'hierarchy', 'type_colour', 'controls', 'motion',
          'engines', 'system']
ENGINES = ['chromium', 'webkit', 'firefox']

# every check's contract, filled in by each group module: {group: {check: {protects, limit, taught_by}}}
REGISTRY = {}


def register(group, checks):
    REGISTRY[group] = checks
    return checks


# ==== config
def deep_merge(base, over):
    """dicts merge key by key; anything else (lists included) is replaced whole"""
    if not isinstance(base, dict) or not isinstance(over, dict):
        return over
    out = dict(base)
    for k, v in over.items():
        out[k] = deep_merge(base[k], v) if k in base and isinstance(base[k], dict) and isinstance(v, dict) else v
    return out


class Job:
    """job.json merged over limits.json; paths resolve against the job folder"""

    def __init__(self, job_dir):
        self.dir = Path(job_dir).resolve()
        jf = self.dir / 'job.json'
        if not jf.exists():
            raise SystemExit('studio_check: no job.json in %s' % self.dir)
        self.raw = json.loads(jf.read_text(encoding='utf-8'))
        kit = json.loads((KIT / 'limits.json').read_text(encoding='utf-8'))
        self.cfg = deep_merge(kit['defaults'], self.raw)
        over = self.raw.get('limits') or {}
        self.limits = dict(kit['limits'])
        self.lists = dict(kit['lists'])
        for k, v in over.items():
            (self.lists if k in self.lists else self.limits)[k] = v
        self.sizes = deep_merge(kit['sizes'], over.get('sizes') or {})
        t = self.cfg.get('type') or {}
        if t.get('max_sizes_per_fold') is not None:
            self.limits['sizes_per_fold'] = t['max_sizes_per_fold']
        if t.get('min_display_to_body') is not None:
            self.limits['display_to_body'] = t['min_display_to_body']
        self.name = self.cfg.get('name') or self.dir.name

    def path(self, rel):
        """a path from job.json: relative to the job root (an absolute path is taken as given)"""
        if not rel:
            return None
        return (self.dir / rel).resolve()

    def get(self, *keys, default=None):
        v = self.cfg
        for k in keys:
            if not isinstance(v, dict) or k not in v or v[k] is None:
                return default
            v = v[k]
        return v


# ==== serving
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        # a fresh copy every request: a cached stylesheet would test yesterday's build
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Server:
    """serves a folder on 127.0.0.1 at a free port (127.0.0.1, not 0.0.0.0: font kits key on the host)"""

    def __init__(self, root):
        self.root = Path(root)
        if not self.root.is_dir():
            raise SystemExit('studio_check: serve.root is not a folder: %s' % self.root)
        handler = functools.partial(_Quiet, directory=str(self.root))
        self.httpd = _Server(('127.0.0.1', 0), handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:%d' % self.port

    def stop(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass


def join_url(base, path):
    """base URL plus a page path from job.json; spaces and accents are quoted, query strings kept"""
    if re.match(r'^https?://', path or ''):
        return path
    p = path or '/'
    if not p.startswith('/'):
        p = '/' + p
    parts = urllib.parse.urlsplit(p)
    q = urllib.parse.quote(urllib.parse.unquote(parts.path), safe='/%')
    b = base.rstrip('/')
    bp = urllib.parse.urlsplit(b)
    url = b + q if not bp.query else b
    if parts.query:
        url += '?' + parts.query
    if parts.fragment:
        url += '#' + parts.fragment
    return url


# ==== results
class _Blank(dict):
    def __missing__(self, k):
        return '{' + k + '}'


class Report:
    def __init__(self, job, run, target, live, mode='full', groups=None):
        self.job, self.run, self.target, self.live = job, run, target, live
        self.mode = mode
        self.groups = list(groups or [])
        self.engines = []          # every engine a group tried to launch, in the order tried
        self.results = []
        self.notes = []
        self.lock = threading.Lock()

    def add(self, group, check, status, measured, page=None, viewport=None, engine=None,
            evidence=None, limit=None, limits=None):
        assert status in ('pass', 'fail', 'skip', 'error'), status
        reg = REGISTRY.get(group, {})
        spec = reg.get(check) or (reg.get('flow') if check.startswith('flow: ') else None) or {}
        lim = limit if limit is not None else spec.get('limit', '')
        if limits is not None and isinstance(lim, str):
            lim = lim.format_map(_Blank({k: v for k, v in limits.items()}))
        row = {'group': group, 'check': check, 'page': page,
               'viewport': list(viewport) if viewport else None, 'engine': engine,
               'status': status, 'measured': str(measured), 'limit': lim,
               'protects': spec.get('protects', ''), 'taught_by': spec.get('taught_by', ''),
               'evidence': list(evidence or [])}
        with self.lock:
            self.results.append(row)
        mark = {'pass': ' ok ', 'fail': 'FAIL', 'skip': 'skip', 'error': 'ERR '}[status]
        where = ' '.join(x for x in [page or '', ('%dx%d' % tuple(viewport)) if viewport else '',
                                      engine or ''] if x)
        print('%s  %-11s %-26s %-28s %s' % (mark, group, check, where, str(measured)[:150]), flush=True)
        return row

    def summary(self):
        s = {'pass': 0, 'fail': 0, 'skip': 0, 'error': 0}
        for r in self.results:
            s[r['status']] += 1
        return s

    def write(self, run_dir):
        data = {'job': self.job, 'run': self.run, 'target': self.target, 'live': self.live,
                'mode': self.mode, 'groups': self.groups, 'engines': self.engines,
                'summary': self.summary(), 'results': self.results}
        (run_dir / 'report.json').write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
        (run_dir / 'report.md').write_text(self.markdown(), encoding='utf-8')

    def markdown(self):
        s = self.summary()
        out = ['# Check kit report , %s' % self.job, '',
               'Run `%s` against %s%s. Mode **%s**; groups %s; engines %s.' % (
                   self.run, self.target, ' (live)' if self.live else '', self.mode,
                   ', '.join(self.groups) or 'none', ', '.join(self.engines) or 'none'), '',
               '**%d pass, %d fail, %d skip, %d error.** %s' % (
                   s['pass'], s['fail'], s['skip'], s['error'],
                   'The run is red: a builder\'s done is still a claim.' if (s['fail'] or s['error'])
                   else 'Nothing failed. Skips below are not passes; read their reasons.'), '']
        if self.notes:
            out += ['## Notes', ''] + ['- ' + n for n in self.notes] + ['']

        def where(r):
            v = ('%dx%d' % tuple(r['viewport'])) if r['viewport'] else ''
            return ' '.join(x for x in [r['page'] or '', v, r['engine'] or ''] if x) or 'job'

        def esc(t):
            return str(t).replace('|', '\\|').replace('\n', ' ')

        for status, title in (('error', 'Errors (the kit could not measure)'), ('fail', 'Failures'),
                              ('skip', 'Skipped, with the reason')):
            rows = [r for r in self.results if r['status'] == status]
            if not rows:
                continue
            out += ['## %s (%d)' % (title, len(rows)), '']
            for g in GROUPS:
                gr = [r for r in rows if r['group'] == g]
                if not gr:
                    continue
                out += ['### %s' % g, '', '| check | where | measured | limit | evidence |', '|---|---|---|---|---|']
                for r in gr:
                    ev = ', '.join('[%s](%s)' % (Path(e).name, e) for e in r['evidence'][:3])
                    out.append('| %s | %s | %s | %s | %s |' % (r['check'], where(r), esc(r['measured'])[:400],
                                                             esc(r['limit']), ev))
                out.append('')
        out += ['## Passes by check', '', '| group | check | passes | protects |', '|---|---|---|---|']
        seen = {}
        for r in self.results:
            if r['status'] == 'pass':
                k = (r['group'], r['check'])
                seen[k] = seen.get(k, 0) + 1
        for (g, c), n in sorted(seen.items(), key=lambda x: (GROUPS.index(x[0][0]) if x[0][0] in GROUPS else 99, x[0][1])):
            out.append('| %s | %s | %d | %s |' % (g, c, n, esc(REGISTRY.get(g, {}).get(c, {}).get('protects', ''))))
        out.append('')
        return '\n'.join(out)


# ==== the page library
# Injected into every page before its own scripts. Every group measures with the same definitions of
# "visible", "a text leaf", "fixed chrome" and "clipped", so two groups never disagree about a page.
LIB_JS = r"""
(() => {
  if (window.__sc) return;
  const keys = new WeakMap(); let n = 0;
  const L = {};
  L.key = el => { if (!keys.has(el)) keys.set(el, ++n); return keys.get(el); };
  L.vw = () => document.documentElement.clientWidth || innerWidth;
  L.desc = el => {
    if (!el || el.nodeType !== 1) return String(el);
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const c = (el.className && el.className.baseVal !== undefined) ? el.className.baseVal : el.className;
    if (c && typeof c === 'string' && c.trim()) s += '.' + c.trim().split(/\s+/).slice(0, 2).join('.');
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 28);
    return t ? s + ' "' + t + '"' : s;
  };
  L.ownText = el => [...el.childNodes].filter(x => x.nodeType === 3).map(x => x.textContent).join(' ').replace(/\s+/g, ' ').trim();
  L.effOpacity = el => {
    let o = 1;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) {
      const v = parseFloat(getComputedStyle(a).opacity);
      if (!isNaN(v)) o *= v;
      if (o <= 0.001) return 0;
    }
    return o;
  };
  // a clip-path that leaves nothing of the box (a mask reveal waiting to run)
  L.clipHidden = el => {
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) {
      const cp = getComputedStyle(a).clipPath;
      if (!cp || cp === 'none') continue;
      const m = cp.match(/^inset\(([^)]*)\)/);
      if (m) {
        const p = m[1].replace(/round.*$/, '').trim().split(/\s+/).map(v => v.endsWith('%') ? parseFloat(v) : NaN);
        const [t, r, b, l] = [p[0], p[1] ?? p[0], p[2] ?? p[0], p[3] ?? p[1] ?? p[0]];
        if ((t + b) >= 99.5 || (l + r) >= 99.5) return true;
      }
      if (/^circle\(0(px|%)?[\s)]/.test(cp)) return true;
    }
    return false;
  };
  L.vis = el => {
    if (!el || el.nodeType !== 1) return false;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse') return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 2 || r.height <= 2) return false;
    if (L.effOpacity(el) <= 0.05) return false;
    return true;
  };
  L.hiddenTree = el => !!el.closest('svg, [aria-hidden="true"], script, style, noscript, template, head');
  L.chrome = el => {
    for (let a = el; a && a !== document.documentElement; a = a.parentElement) {
      const p = getComputedStyle(a).position;
      if (p === 'fixed' || p === 'sticky') return true;
    }
    return false;
  };
  L.rangeRect = el => { const rg = document.createRange(); rg.selectNodeContents(el); return rg.getBoundingClientRect(); };
  // a Range rect ignores ancestor clipping; intersect with every clipping box, starting at the element
  L.clipTo = (el, r) => {
    let b = {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
    for (let a = el; a && a !== document.documentElement; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
        const c = a.getBoundingClientRect();
        b = {left: Math.max(b.left, c.left), top: Math.max(b.top, c.top),
             right: Math.min(b.right, c.right), bottom: Math.min(b.bottom, c.bottom)};
      }
    }
    return b;
  };
  L.scrollerAncestor = el => {
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (/(auto|scroll)/.test(s.overflowX + ' ' + s.overflowY)) return true;
    }
    return false;
  };
  L.inView = r => r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < L.vw();
  // elements that carry their own words (a text node of 2 or more characters), visible, not hidden from people
  L.textLeaves = () => [...document.body.querySelectorAll('*')].filter(el =>
    !L.hiddenTree(el) && L.ownText(el).length > 1 && L.vis(el));
  L.isBlock = el => /^(block|flex|grid|table|list-item|flow-root|table-cell|table-caption)$/.test(getComputedStyle(el).display);
  L.MEDIA = 'img, video, canvas, picture, iframe, object, embed';
  // the element that actually scrolls: the document, or a body or wrapper that took the scroll over
  L.scroller = () => {
    const se = document.scrollingElement || document.documentElement;
    if (se.scrollHeight > se.clientHeight + 2) return se;
    let best = null, bh = 0;
    for (const el of [document.body, ...document.querySelectorAll('body > *, main')]) {
      if (!el) continue;
      const s = getComputedStyle(el);
      if (/(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 2
          && el.clientHeight > innerHeight * 0.6 && el.scrollHeight > bh) { best = el; bh = el.scrollHeight; }
    }
    return best || se;
  };
  L.isDoc = s => s === document.scrollingElement || s === document.documentElement;
  L.maxY = () => { const s = L.scroller(); return Math.max(0, s.scrollHeight - s.clientHeight); };
  L.y = () => { const s = L.scroller(); return L.isDoc(s) ? scrollY : s.scrollTop; };
  L.to = y => {
    const s = L.scroller();
    if (L.isDoc(s)) window.scrollTo({top: y, left: 0, behavior: 'instant'});
    else s.scrollTo({top: y, left: 0, behavior: 'instant'});
    return L.y();
  };
  window.__sc = L;
})();
"""


# ==== the session
class Session:
    def __init__(self, job, args, report, base, run_dir):
        self.job, self.args, self.report, self.base, self.run_dir = job, args, report, base, run_dir
        self.quick = bool(args.quick)
        self.shots = run_dir / 'shots'
        self.films = run_dir / 'films'
        self.sheets = run_dir / 'sheets'
        for d in (self.shots, self.films, self.sheets):
            d.mkdir(parents=True, exist_ok=True)
        self.pw = None
        self._browsers = {}
        self._launch_fail = {}
        self.fold_shots = {}      # (page, w, h, engine) -> [relative paths], filled by the sweep
        self.full_shots = {}
        self.cache = {}           # groups share measurements here (page, size) -> dict
        pages = job.get('pages', default=[]) or []
        if args.pages:
            want = [p.strip() for p in args.pages.split(',') if p.strip()]
            pages = [p for p in pages if p.get('name') in want]
        self.pages = pages
        self.L = job.limits

    # sizes
    def sweep_sizes(self):
        s = self.job.sizes
        if self.quick:
            return [(w, s['height']) for w in s['quick_widths']]
        return [(w, s['height']) for w in s['widths']] + [tuple(x) for x in s['extra']]

    def size_set(self, key):
        sz = [tuple(x) for x in self.job.sizes.get(key, [])]
        if self.quick:
            qw = set(self.job.sizes['quick_widths'])
            sz = [x for x in sz if x[0] in qw] or sz
        return sz

    def engines(self):
        return ['chromium'] if self.quick else list(ENGINES)

    def settle_ms(self):
        return self.L['quick_settle_ms'] if self.quick else self.L['settle_ms']

    def is_phone(self, size):
        w, h = size
        return w <= self.job.sizes['phone_max_width'] or (h <= self.job.sizes['phone_max_width'] and w < 1000)

    def url(self, page):
        return join_url(self.base, page.get('path') or '/')

    # browsers
    def browser(self, engine):
        """(browser, None) or (None, reason). A missing engine is a skip with its reason, never a pass."""
        if engine not in self.report.engines:
            self.report.engines.append(engine)
        if engine in self._browsers:
            return self._browsers[engine], None
        if engine in self._launch_fail:
            return None, self._launch_fail[engine]
        bt = getattr(self.pw, engine)
        try:
            exe = bt.executable_path
            if exe and not os.path.exists(exe):
                raise RuntimeError('%s is not installed for this Playwright (%s missing); '
                                   'run `playwright install %s`' % (engine, exe.split('ms-playwright/')[-1], engine))
            b = bt.launch(headless=True)
        except Exception as e:
            msg = str(e).strip().splitlines()[0][:220] if str(e).strip() else repr(e)
            self._launch_fail[engine] = '%s could not launch: %s' % (engine, msg)
            return None, self._launch_fail[engine]
        self._browsers[engine] = b
        return b, None

    def context(self, engine, size, touch=None, reduced_motion=None, dpr=1):
        b, why = self.browser(engine)
        if not b:
            return None, why
        w, h = size
        phone = self.is_phone(size) if touch is None else touch
        kw = dict(viewport={'width': w, 'height': h}, device_scale_factor=dpr)
        if phone:
            kw['has_touch'] = True
            if engine != 'firefox':
                kw['is_mobile'] = True
        if reduced_motion:
            kw['reduced_motion'] = reduced_motion
        ctx = b.new_context(**kw)
        ctx.add_init_script(LIB_JS)
        return ctx, None

    def open(self, ctx, page_info, settle=True):
        """load a page the way a person would wait for it: load, fonts, a quiet network, the loader's time"""
        pg = ctx.new_page()
        pg.set_default_timeout(45000)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.goto(self.url(page_info), wait_until='load', timeout=60000)
        try:
            pg.wait_for_load_state('networkidle', timeout=6000)
        except Exception:
            pass
        try:
            pg.evaluate("() => Promise.race([document.fonts.ready.then(() => 1), new Promise(r => setTimeout(r, 5000))])")
        except Exception:
            pass
        if settle:
            pg.wait_for_timeout(self.L['load_settle_ms'] if not self.quick else min(900, self.L['load_settle_ms']))
        pg._sc_errors = errs
        return pg

    def close(self):
        for b in self._browsers.values():
            try:
                b.close()
            except Exception:
                pass

    # recording
    def rec(self, group, check, status, measured, page=None, size=None, engine=None, evidence=None, limit=None):
        name = page.get('name') if isinstance(page, dict) else page
        return self.report.add(group, check, status, measured, page=name, viewport=size, engine=engine,
                               evidence=evidence, limit=limit, limits=self.L)

    def guard(self, group, check, fn, page=None, size=None, engine=None):
        """run one measurement; a crash is an `error` result with its reason, never a silent pass"""
        try:
            return fn()
        except Exception as e:
            tb = traceback.format_exc().strip().splitlines()
            where = next((l.strip() for l in reversed(tb) if l.strip().startswith('File ')), '')
            self.rec(group, check, 'error', '%s: %s (%s)' % (type(e).__name__, str(e).splitlines()[0][:200] if str(e) else '', where[-120:]),
                     page=page, size=size, engine=engine)
            return None

    def rel(self, p):
        return str(Path(p).relative_to(self.run_dir))


# ==== files
def shot_name(page, w, h, engine, fold=None):
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '-', page).strip('-') or 'page'
    base = '%s__%dx%d__%s' % (safe, w, h, engine)
    return base + ('__fold%d.png' % fold if fold else '.png')


def safe_name(s):
    return re.sub(r'[^A-Za-z0-9_.-]+', '-', s).strip('-') or 'page'


def machine_load():
    try:
        return os.getloadavg()[0], os.cpu_count() or 1
    except Exception:
        return None, os.cpu_count() or 1


def wait_for_quiet_machine(limits, report=None):
    """a timing result from a loaded machine invents failures; wait a while, then say what it was"""
    load, cpus = machine_load()
    if load is None:
        return None, True
    ceiling = limits['load_max_per_cpu'] * cpus
    t0 = time.time()
    while load > ceiling and time.time() - t0 < limits['load_wait_s']:
        time.sleep(5)
        load, _ = machine_load()
    return load, load <= ceiling


def stamp():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')


def have(tool):
    return shutil.which(tool) is not None


def contact_sheet(items, dest, cell_h=320, cols=None, label_h=22, bg=(236, 235, 231), max_w=4200):
    """items: [(path, label)]; each tile keeps its own ratio (nothing is cropped), height cell_h"""
    from PIL import Image, ImageDraw
    tiles = []
    for p, label in items:
        try:
            im = Image.open(p).convert('RGB')
        except Exception:
            continue
        w = max(1, round(im.width * cell_h / im.height))
        tiles.append((im.resize((w, cell_h)), label))
    if not tiles:
        return None
    pad = 12
    rows, row, x = [], [], pad
    for t in tiles:
        if row and (x + t[0].width + pad > max_w or (cols and len(row) >= cols)):
            rows.append(row)
            row, x = [], pad
        row.append(t)
        x += t[0].width + pad
    if row:
        rows.append(row)
    W = max(sum(t[0].width + pad for t in r) + pad for r in rows)
    H = len(rows) * (cell_h + label_h + pad) + pad
    sheet = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(sheet)
    y = pad
    for r in rows:
        x = pad
        for im, label in r:
            sheet.paste(im, (x, y))
            d.text((x, y + cell_h + 5), label, fill=(20, 20, 18))
            x += im.width + pad
        y += cell_h + label_h + pad
    sheet.save(dest)
    return dest
