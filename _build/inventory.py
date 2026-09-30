"""
inventory.py -- uncurated listing of every file in optima-history (the topic-sorted lesson library).

  python _build/inventory.py      -> writes _meta/source_inventory.json

optima-history is a sibling of this folder and is only READ. Every file is listed (except .git); each HTML page
is tagged with what the harvest did with it: entry / excluded / no-content / duplicate / not-harvested.
"""
import os, re, json, hashlib, html as htmllib
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.normpath(os.path.join(HERE, '..'))
REPOS = ['optima-history']
EXCLUDE_PAGE = re.compile(r'primary-source-\d+\.html$', re.I)  # same rule as harvest.py

try:   # rough chronological order of the topic folders (earliest first), editable in _meta/topic_order.yml
    import yaml
    ORDER = (yaml.safe_load(open(os.path.join(REPO, '_meta', 'topic_order.yml'), encoding='utf-8')) or {}).get('order', [])
except Exception:
    ORDER = []

def natkey(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

index = json.load(open(os.path.join(REPO, 'index.json'), encoding='utf-8'))
entry_of = {(s['repo'], s['path']): e['id'] for e in index for s in e.get('sources', [])}
in_manifest, suppressed = set(), {}
mp = os.path.join(REPO, '_meta', 'manifest.jsonl')
if os.path.exists(mp):
    for line in open(mp, encoding='utf-8'):
        m = json.loads(line); k = (m.get('repo'), m.get('path'))
        in_manifest.add(k)
        if m.get('verdict') == 'entry-suppressed': suppressed[k] = m.get('duplicate_of')

out, seen_hash = {}, {}
for repo in REPOS:
    base = os.path.join(SRC, repo); files = []
    if not os.path.isdir(base): out[repo] = {'missing': True, 'files': []}; continue
    for root, dirs, fs in os.walk(base):
        dirs[:] = sorted([d for d in dirs if d != '.git'], key=natkey)
        for f in sorted(fs, key=natkey):
            full = os.path.join(root, f); rel = os.path.relpath(full, base).replace('\\', '/')
            rec = {'path': rel, 'size': os.path.getsize(full)}
            if f.lower().endswith('.html'):
                html = open(full, encoding='utf-8', errors='ignore').read()
                t = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
                rec['title'] = re.sub(r'\s+', ' ', htmllib.unescape(t.group(1))).strip() if t else ''
                k = (repo, rel)
                if '/widgets/' in '/' + rel: rec['fate'] = 'widget'; rec['why'] = 'interactive widget embedded by a lesson in this topic folder'
                elif k in entry_of: rec['fate'] = 'entry'; rec['entry'] = entry_of[k]
                elif k in suppressed: rec['fate'] = 'duplicate'; rec['entry'] = suppressed[k]
                elif EXCLUDE_PAGE.search(rel): rec['fate'] = 'excluded'; rec['why'] = 'primary-source exercise page (out of harvest scope)'
                elif k in in_manifest: rec['fate'] = 'no-content'; rec['why'] = 'read, but no narrative prose passed the harvest rules (widget / assessment / appendix)'
                else:
                    h = hashlib.sha1(html.encode('utf-8', 'ignore')).hexdigest()
                    rec['fate'] = 'duplicate' if h in seen_hash else 'not-harvested'
                    if rec['fate'] == 'duplicate': rec['why'] = 'identical to ' + seen_hash[h]
                    else: seen_hash[h] = f'{repo}/{rel}'
            else:
                rec['fate'] = 'other'
            files.append(rec)
    out[repo] = {'files': files, 'order': [o['folder'] for o in ORDER], 'spans': {o['folder']: o.get('span', '') for o in ORDER}}
    print(repo, len(files), 'files,', sum(1 for r in files if r['fate'] == 'entry'), 'with entries')
json.dump(out, open(os.path.join(REPO, '_meta', 'source_inventory.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)
