"""
build_index.py -- generate the dashboard index from the entry files (never hand-maintained).

Reads  repo/entries/<topic-area>/*.md, repo/_meta/manifest.jsonl, repo/_meta/taxonomy.yml
Writes repo/index.json          one record per entry (frontmatter + derived fields)
       repo/_meta/tracker.csv   the proofreading tracker as a flat table
       repo/_meta/gate.json     completeness + vocabulary gate results (fails loudly)
Exit code 1 if the gate fails.
"""
import os, re, sys, json, csv, glob, hashlib
from collections import Counter, defaultdict
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath((os.path.join(HERE, '..', 'repo') if os.path.isdir(os.path.join(HERE, '..', 'repo')) else os.path.join(HERE, '..')))

def split_front(text):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.S)
    if not m: raise ValueError('no frontmatter')
    return yaml.safe_load(m.group(1)), m.group(2)

def parse_body(body):
    """Return blocks: [{ordinal, role, flags, text}] and sections in order."""
    blocks = []; section = None
    parts = re.split(r'\n?<!-- (section: [^>]*|block \d+ [^>]*) -->\n?', body)
    # parts alternates: text, marker, text, marker ...
    cur = None
    for i, part in enumerate(parts):
        if i % 2 == 1:
            if part.startswith('section: '):
                section = part[len('section: '):].strip()
            else:
                m = re.match(r'block (\d+) role=(\S+)(.*)', part)
                cur = {'ordinal': int(m.group(1)), 'role': m.group(2), 'flags': m.group(3).split(), 'section': section}
        else:
            txt = part.strip()
            if cur is not None and txt:
                cur['text'] = txt; blocks.append(cur); cur = None
    return blocks

def main():
    tax = yaml.safe_load(open(os.path.join(REPO, '_meta', 'taxonomy.yml'), encoding='utf-8'))
    controlled = {k: set(v if isinstance(v, list) else v.keys()) for k, v in tax['controlled'].items()}
    global ALL_CODES, TOPICS
    try: ALL_CODES = set(json.load(open(os.path.join(REPO, '_meta', 'standards', 'all_codes.json'), encoding='utf-8')))
    except Exception: ALL_CODES = set()
    try: TOPICS = set(yaml.safe_load(open(os.path.join(REPO, '_meta', 'topics.yml'), encoding='utf-8'))['topics'].keys())
    except Exception: TOPICS = set()
    files = sorted(glob.glob(os.path.join(REPO, 'entries', '*', '*.md')))
    index = []; problems = []; vocab_errors = []
    words_re = re.compile(r"[A-Za-z0-9'’]+")
    for f in files:
        raw = open(f, encoding='utf-8').read()
        try:
            fm, body = split_front(raw)
        except Exception as e:
            problems.append({'file': f, 'error': str(e)}); continue
        blocks = parse_body(body)
        rel = os.path.relpath(f, REPO).replace('\\', '/')
        body_hash = hashlib.sha1(body.strip().encode('utf-8')).hexdigest()[:12]
        rec = dict(fm)
        rec.update({
            'file': rel,
            'paragraphs': len(blocks),
            'words': sum(len(words_re.findall(re.sub(r'\*', '', b['text']))) for b in blocks),
            'voice_flagged': sum(1 for b in blocks if 'voice' in b['flags']),
            'roles': dict(Counter(b['role'] for b in blocks)),
            'sections': [s for s in dict.fromkeys(b['section'] for b in blocks if b['section'])],
            'body_hash': body_hash,
            'extracted_hash': fm.get('extracted_hash') or body_hash,
        })
        rec['changed_since_extraction'] = rec['body_hash'] != rec['extracted_hash']
        # entries are organized by topic area (the optima-history topic folder); course is only metadata
        src0 = (fm.get('sources') or [{}])[0]
        if src0.get('repo') == 'optima-history' and fm.get('area') != str(src0.get('path', '')).split('/')[0]:
            problems.append({'file': f, 'error': f"area {fm.get('area')!r} does not match the lesson's topic folder"})
        for field, allowed in controlled.items():
            val = fm.get(field)
            vals = val if isinstance(val, list) else ([val] if val not in (None, '', []) else [])
            for v in vals:
                if v not in allowed:
                    vocab_errors.append({'id': fm.get('id'), 'field': field, 'value': v})
        # standards codes must exist in the extracted slices (FL/TX/MS ELA 6-12)
        if ALL_CODES:
            for field in ('standards_fl', 'standards_tx', 'standards_ccss'):
                for v in fm.get(field) or []:
                    if v not in ALL_CODES:
                        vocab_errors.append({'id': fm.get('id'), 'field': field, 'value': v})
        # topics must exist in topics.yml
        for v in fm.get('topics') or []:
            if TOPICS and v not in TOPICS:
                vocab_errors.append({'id': fm.get('id'), 'field': 'topics', 'value': v})
        rec['proposals'] = len(fm.get('proposed_standards') or []) + len(fm.get('proposed_topics') or []) + (1 if fm.get('category_suggestion') else 0) + len(fm.get('texts_suggestion') or [])
        index.append(rec)

    # completeness: every source page with harvested blocks in the manifest must have an entry, and vice versa
    man_pages = defaultdict(int); suppressed = set()
    with open(os.path.join(REPO, '_meta', 'manifest.jsonl'), encoding='utf-8') as mf:
        for line in mf:
            r = json.loads(line)
            key = f"{r.get('repo')}/{r.get('path')}"
            if r.get('verdict') in ('harvest', 'excerpt', 'definition'): man_pages[key] += 1
            if r.get('verdict') == 'entry-suppressed': suppressed.add(key)
    entry_pages = defaultdict(list)
    for rec in index:
        for s in rec.get('sources', []):
            entry_pages[f"{s['repo']}/{s['path']}"].append(rec['id'])
    missing_entries = sorted(k for k, n in man_pages.items() if n and k not in entry_pages and k not in suppressed)
    orphan_entries = sorted(k for k in entry_pages if k not in man_pages)
    count_mismatch = []
    for rec in index:
        src = rec['sources'][0]; key = f"{src['repo']}/{src['path']}"
        if key in man_pages and man_pages[key] != rec['paragraphs'] and not rec['changed_since_extraction'] and rec.get('status') == 'extracted':
            count_mismatch.append({'id': rec['id'], 'manifest': man_pages[key], 'entry': rec['paragraphs']})

    ids = Counter(r['id'] for r in index)
    dup_ids = [i for i, n in ids.items() if n > 1]
    gate = {
        'entries': len(index),
        'paragraphs': sum(r['paragraphs'] for r in index),
        'by_status': dict(Counter(r.get('status') for r in index)),
        'by_area': dict(Counter(r.get('area') for r in index)),
        'by_course_fit': dict(Counter(r.get('course') for r in index)),
        'by_category': dict(Counter(r.get('category') for r in index)),
        'manifest_pages_with_content': len([k for k, n in man_pages.items() if n]),
        'entries_missing_for_pages': missing_entries,
        'orphan_entries_not_in_manifest': orphan_entries,
        'paragraph_count_mismatch': count_mismatch,
        'duplicate_ids': dup_ids,
        'frontmatter_problems': problems,
        'vocabulary_errors': vocab_errors[:50],
        'vocabulary_error_count': len(vocab_errors),
    }
    ok = not (missing_entries or orphan_entries or count_mismatch or dup_ids or problems or vocab_errors)
    gate['pass'] = ok
    json.dump(index, open(os.path.join(REPO, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(gate, open(os.path.join(REPO, '_meta', 'gate.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(REPO, '_meta', 'tracker.csv'), 'w', encoding='utf-8', newline='') as cf:
        w = csv.writer(cf)
        w.writerow(['id', 'title', 'area', 'course', 'grade', 'module', 'category', 'scope', 'status', 'paragraphs', 'words', 'voice_flagged', 'changed_since_extraction', 'topics', 'texts', 'standards_fl', 'standards_tx', 'standards_ccss', 'pairs_with', 'visuals', 'source_url'])
        for r in index:
            w.writerow([r['id'], r.get('title'), r.get('area'), r.get('course'), r.get('grade'), r.get('module'), r.get('category'), r.get('scope'), r.get('status'), r['paragraphs'], r['words'], r['voice_flagged'], r['changed_since_extraction'],
                        ';'.join(r.get('topics') or []), ';'.join(r.get('texts') or []), ';'.join(r.get('standards_fl') or []), ';'.join(r.get('standards_tx') or []), ';'.join(r.get('standards_ccss') or []),
                        ';'.join(r.get('pairs_with') or []), len(r.get('visuals') or []), r['sources'][0]['url']])
    print(json.dumps({k: v for k, v in gate.items() if k not in ('entries_missing_for_pages', 'orphan_entries_not_in_manifest', 'paragraph_count_mismatch', 'vocabulary_errors')}, indent=1))
    for k in ('entries_missing_for_pages', 'orphan_entries_not_in_manifest', 'paragraph_count_mismatch', 'duplicate_ids', 'frontmatter_problems'):
        if gate[k]: print(f'!! {k}: {len(gate[k])} -> {gate[k][:5]}')
    if vocab_errors: print(f'!! vocabulary errors: {len(vocab_errors)} -> {vocab_errors[:5]}')
    print('GATE', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
