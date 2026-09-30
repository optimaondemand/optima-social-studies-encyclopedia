"""
harvest.py -- read the lesson library (optima-history, a sibling folder, READ-ONLY) and write
encyclopedia entries: one entry per lesson page, informative content paragraphs only,
paragraphs kept whole, edge cases included and flagged.

Outputs (under ../repo):
  entries/<course>/<id>.md        YAML frontmatter + Markdown body (portable subset)
  visuals/<id>--vN.html           raw HTML of visual candidates (rendered later)
  _meta/manifest.jsonl            every text block seen, with verdict + reason
  _meta/report.json               counts per course
Never writes into optima-history. A fresh run REPLACES each course's entries wholesale, including their tags and edits.
"""
import os, re, sys, json, hashlib, subprocess, unicodedata, glob
from collections import Counter
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.environ.get('ENC_SRC') or os.path.normpath(os.path.join(HERE, '..', '..'))  # optima-history is a sibling folder of this repo
REPO = os.path.normpath((os.path.join(HERE, '..', 'repo') if os.path.isdir(os.path.join(HERE, '..', 'repo')) else os.path.join(HERE, '..')))

LIB = 'optima-history'   # topic folders of lessons; a lesson's file name says nothing about any course
COURSES = {  # course slug (metadata: which course a lesson naturally fits) -> (course slug, grade, course code, display)
 'wh6':     ('wh6',     6, '2109010',   'M/J World History: Dawn of Civilization to Roman Empire'),
 'txhist7': ('txhist7', 7, '113.19(b)', 'Grade 7 Texas History'),
}
# Which course each lesson fits and its position in that course live in the encyclopedia, not in the lesson's name:
#   _meta/lesson_map.json  {"<topic>/<lesson>.html": {"course": "wh6", "position": "week-16/lesson-2.html"}}
# Lessons absent from the map are not harvested.
LESSON_MAP = json.load(open(os.path.join(REPO, '_meta', 'lesson_map.json'), encoding='utf-8'))['lessons']
def lib_sha(rel):
    return subprocess.run(['git', '-C', os.path.join(SRC, LIB), 'log', '-1', '--format=%H', '--', rel], capture_output=True, text=True).stdout.strip()
LIB_URL = f'https://github.com/optimaondemand/{LIB}/blob/main/'
EXCLUDE_PAGE = re.compile(r'primary-source-\d+\.html$', re.I)

SKIP_CLASS_PREFIX = ('widget', 'ora-', 'optima-widget', 'er-controls', 'rj-', 'ws-', 'map-card', 'ow-', 'match-col', 'sr-only')
LEAF_TAGS = {'p','div','li','blockquote','h1','h2','h3','h4','h5','summary','tr','figcaption','dd','dt'}
BLOCK_TAGS = LEAF_TAGS | {'ul','ol','details','section','article','aside','table','tr','tbody','thead','figure','main','header','footer','nav','body','html'}
REGION_SKIP = re.compile(r'^(=+\s*)?(HEADER|METADATA( STRIP)?|FOOTER|WIDGET RUNTIME|.*OPTIMA READ-ALOUD PLAYER)', re.I)
REGION_BODY = re.compile(r'^(=+\s*)?(BODY( WRAPPER)?|Title strip|Lavender title strip|.*END OPTIMA READ-ALOUD)', re.I)

IMPERATIVES = {'read','write','open','choose','pick','record','copy','find','match','drag','click','submit','answer','post','watch','listen','complete','fill','type','use','take','turn','go','look','discuss','share','reflect','compare','hold','set','put','rank','sort','label','draw','bring','save','name','upload','create','build','design','try','practice','notice','consider','remember','reread','return','review','check','mark','highlight','underline','circle','jot','list','pause','stop','start','begin','finish','keep','make','add','decide','identify','explain','describe','tell','ask','skim','scan','locate','play','pair','work','head','move','follow','print','download','join','enter','log','select','tap','scroll','paste','attach','number','collect','gather','prepare','plan','revise','edit','proofread','reply','respond','rewrite','summarize','sketch','spend','wait','count'}
TOOL_WORDS = re.compile(r"\b(Reading Journal|Journal|Organizer|your own copy|own copy of|OneDrive|Canvas|Word doc|submit|submission|upload|turn it in|click|checklist|rubric|due|assignment|discussion board|quiz|this page|below|above|on this page|in this lesson|this lesson|this week|today's lesson|Today's Focus|wrap-up|warm-up|check-in|Workshop Day|VR|headset|ENGAGE|Study Planner|Teams|Claude|ChatGPT|Copilot|AI tool|an AI)\b", re.I)
VOICE = re.compile(r"\b(you|your|yours|yourself|you'll|you're|you've|we|our|ours|us|let's|we'll|we're|I will be able|I can)\b", re.I)
DEF_PATTERN = re.compile(r"\b(is|are|was|were|means|refers to|is called|are called|known as|describes|defines?)\b", re.I)
TEACHER_NOTE = re.compile(r'\[Teacher:')
SKIP_SECTION = re.compile(r"\bAI\b|AI-awareness|WORTH KNOWING|TRY THIS|\bJOURNAL\b|WORD WORK|\bRISKY\b|\bCAUTION\b|WHAT YOU.?LL DO NEXT|WRAP-?UP|^MATERIALS|^OBJECTIVES|BY THE END|CHECK-?IN|WARM-?UP|COMPREHENSION CHECK|NOW YOU|YOUR TURN|^REFLECT|EXIT TICKET|SELF-?CHECK|Reading Journal task|Today.?s Focus|^Objectives$|^Materials$|WHAT.?S NEXT|NEXT THIS WEEK|CARRY THIS FORWARD|KEEP THIS IN MIND|LOOKING AHEAD|COMING UP|^CLOSING|SEND-?OFF|WHAT YOU NEED|YOU WILL NEED|BEFORE YOU (START|BEGIN|GO)|HOW TO SUBMIT|SUBMIT|TURN IT IN|NOW READ|^READING$|THE READING|READ NOW", re.I)
STOPCAPS = {'The','A','An','This','That','These','Those','It','You','Your','We','Our','In','On','At','For','As','If','When','But','And','Or','So','Then','Now','Here','There','What','Why','How','Who','Which','One','Two','Three','Some','Many','Each','Every','No','Not','Yes','Read','Write','Notice','Part','Lesson','Week','Module','Quarter'}

def slugify(s, maxlen=70):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s[:maxlen].rstrip('-')

def px(style):
    m = re.search(r'font-size\s*:\s*([\d.]+)\s*px', style or '')
    return float(m.group(1)) if m else None

def clean_label(s):
    s = re.sub(r'[=\u2550]+', ' ', s)
    s = re.sub(r'[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F\u25B6\u25A0\u2022\u00b7]+', ' ', s)
    s = ' '.join(s.split()).strip(' :-')
    return s

def inline_md(node):
    """Render a leaf block's inline content to the portable Markdown subset."""
    def render(n):
        if isinstance(n, Comment): return ''
        if isinstance(n, NavigableString): return str(n)
        if not isinstance(n, Tag): return ''
        name = n.name.lower()
        if name in ('script','style'): return ''
        if name == 'br': return ' '
        inner = ''.join(render(c) for c in n.children)
        if name in ('strong','b'):
            return f" **{inner.strip()}** " if inner.strip() else ''
        if name in ('em','i','cite'):
            return f" *{inner.strip()}* " if inner.strip() else ''
        return inner
    s = ''.join(render(c) for c in node.children)
    s = s.replace('\u00a0',' ')
    s = ' '.join(s.split())
    s = re.sub(r'\s+([,.;:!?)])', r'\1', s)
    s = re.sub(r'\(\s+', '(', s)
    return s

def words(s): return len(re.findall(r"[A-Za-z0-9'\u2019]+", s))

def proper_nouns(s):
    sent_starts = set(m.group(1) for m in re.finditer(r"(?:^|[.!?]\s+)\W*([A-Z][a-z\u2019']+)", s))
    caps = re.findall(r"\b[A-Z][a-z\u2019']{2,}\b", s)
    return [c for c in caps if c not in sent_starts and c not in STOPCAPS]

def classify(text, tag, fs, cls, in_details, in_blockquote, section_label):
    """Return (verdict, reason, flags). verdict in harvest|skip|excerpt|reading."""
    flags = []
    w = words(text)
    if not text or w == 0: return 'skip','empty',flags
    if TEACHER_NOTE.search(text): return 'skip','teacher-note',flags
    if re.match(r'^\s*(\u25b6|\u27a4|\u25ba|\u2022)', text): return 'skip','materials-bullet',flags
    if re.match(r'^\s*I will be able', text): return 'skip','objective',flags
    if re.match(r'^\s*(Optima Academy Online|\u00a9|Quarter \d|\d+(TH|ST|ND|RD) GRADE)', text, re.I): return 'skip','chrome',flags
    if fs is not None and fs <= 13: return 'skip','kicker-or-label',flags
    if section_label and SKIP_SECTION.search(section_label): return 'skip','section-'+re.sub(r'[^a-z]+','-',section_label.lower())[:30],flags
    if in_details or (section_label and re.search(r'EMBEDDED READING|THE TEXT', section_label, re.I)):
        return 'reading','embedded-reading',flags
    if in_blockquote or tag == 'blockquote' or (cls and re.search(r'pm-line|sonnet-line|verse|stanza|quote', cls)):
        if w <= 160: return 'excerpt','quoted-passage',flags
        return 'reading','long-quotation',flags
    if w < 12 and fs and fs >= 19: return 'skip','section-title',flags
    if fs and fs >= 20 and w < 22: return 'skip','hook-line',flags
    if w < 12: return 'skip','short-line',flags
    if re.match(r'^\s*[\u201c"].*[\u201d"][.,!?]?\s*$', text) and w <= 160: return 'excerpt','quoted-line',flags
    first = re.sub(r'^[^A-Za-z]+', '', re.sub(r'\*', '', text)).split(' ',1)[0].lower().strip('.,:;')
    if first in IMPERATIVES and re.match(r'^[^A-Za-z]*[A-Z]', text):
        pn0 = proper_nouns(text)
        if w >= 30 and (len(pn0) >= 2 or re.search(r'[\u201c"]', text)) and not TOOL_WORDS.search(text):
            flags.extend(['voice','imperative'])
            return 'harvest','imperative-but-informative',flags
        return 'skip','instruction-imperative',flags
    tool = TOOL_WORDS.search(text)
    voice = VOICE.findall(text)
    pn = proper_nouns(text)
    info = bool(pn) or bool(re.search(r'[\u201c"]', text)) or bool(DEF_PATTERN.search(text)) or w >= 45
    if tool and not pn and w < 60:
        return 'skip','instruction-tool',flags
    if tool: flags.append('tool_mention')
    if not voice:
        if fs and fs >= 19 and w < 30: flags.append('hook')
        return 'harvest','clean',flags
    flags.append('voice')
    if info:
        return 'harvest','voice-but-informative',flags
    return 'skip','framing',flags

def iter_blocks(soup):
    """Yield (kind, node) in document order."""
    body = soup.body or soup
    def is_leaf(t):
        if t.name.lower() == 'tr': return True
        if t.name.lower() not in LEAF_TAGS: return False
        for c in t.children:
            if isinstance(c, Tag) and c.name.lower() in BLOCK_TAGS and c.name.lower() != 'summary':
                return False
        return True
    def walk(t):
        skip_next = False
        for c in list(t.children):
            if isinstance(c, Comment):
                txt = str(c).strip()
                if REGION_SKIP.search(txt): skip_next = True
                yield ('comment', txt); continue
            if not isinstance(c, Tag): continue
            if skip_next:
                skip_next = False
                yield ('skipped-subtree', c); continue
            name = c.name.lower()
            if name in ('script','style','noscript','svg','canvas','iframe','button','select','input','textarea','audio','video','nav'): continue
            cls = ' '.join(c.get('class', [])) if c.get('class') else ''
            if cls and any(tok.startswith(p) for tok in cls.split() for p in SKIP_CLASS_PREFIX):
                yield ('skipped-subtree', c); continue
            if is_leaf(c):
                yield ('leaf', c)
            else:
                yield ('open', c)
                yield from walk(c)
                yield ('close', c)
    yield from walk(body)

def harvest_page(repo, relpath, html):
    soup = BeautifulSoup(html, 'lxml')
    title_tag = soup.title.string.strip() if soup.title and soup.title.string else ''
    blocks = []; manifest = []
    section = None; region_active = True; ordinal = 0
    details_depth = 0; bq_depth = 0; visuals = []; pending_visual = None; visual_node = None; title_cands = []; topic_label_pending = False
    section_titles = []; reading_refs = []
    for kind, node in iter_blocks(soup):
        if kind == 'comment':
            c = node
            if REGION_SKIP.search(c) or REGION_BODY.search(c): continue
            lab = clean_label(c)
            if lab:
                section = lab
                if re.search(r'VISUAL', c, re.I): pending_visual = lab
            continue
        if kind == 'open':
            nm = node.name.lower()
            if nm == 'details': details_depth += 1
            if nm == 'blockquote': bq_depth += 1
            if pending_visual is not None and nm in ('div','figure','table','section'):
                visuals.append((pending_visual, str(node))); pending_visual = None
                visual_node = node
            continue
        if kind == 'close':
            nm = node.name.lower()
            if visual_node is not None and node is visual_node: visual_node = None
            if nm == 'details': details_depth = max(0, details_depth-1)
            if nm == 'blockquote': bq_depth = max(0, bq_depth-1)
            continue
        if kind == 'skipped-subtree':
            # the lesson title often sits in the header/metadata strip at 22px; the module theme at 16px
            for d in node.find_all(True):
                dfs = px(d.get('style') or '')
                if dfs and 21 <= dfs <= 26:
                    dt = ' '.join(d.get_text(' ').split())
                    if 2 <= words(dt) < 14 and not re.search(r'Optima|ENGLISH|GRADE|Quarter|Lesson \d|Language Arts|Student Lesson|Education Experience|Module \d|^\s*(?:World|Texas) History\s*$', dt, re.I):
                        title_cands.append((0, dt))
            txt = ' '.join(node.get_text(' ').split())
            if txt: manifest.append({'ordinal': None, 'verdict':'skip','reason':'interactive-or-chrome-subtree','flags':[],'text':txt[:200],'section':section})
            continue
        el = node
        style = el.get('style') or ''
        fs = px(style)
        cls = ' '.join(el.get('class', [])) if el.get('class') else ''
        # World History kickers are sometimes class="callout-label" (font-size: 11px; color: #c7922c
        # in the page's own <style> block) instead of an inline style. Without this, those kickers
        # never reset `section`, and any label-based classification below misses them too.
        if fs is None and cls and 'callout-label' in cls.split():
            fs = 11.0
        tag = el.name.lower()
        if tag == 'tr':
            cells = [inline_md(td) for td in el.find_all(['td','th'], recursive=False)]
            cells = [re.sub(r'\*\*|\*', '', c).strip() for c in cells if c.strip()]
            if el.find('th', recursive=False) is not None or len(cells) < 2:
                continue
            if words(cells[0]) <= 5 and words(cells[1]) >= 3:
                ordinal += 1
                text = f"**{cells[0]}**: {cells[1]}" + (f" *({cells[2]})*" if len(cells) > 2 and words(cells[2]) <= 30 else '')
                rec = {'ordinal': ordinal, 'verdict': 'definition', 'reason': 'table-row', 'flags': [], 'tag': 'tr', 'fs': fs, 'cls': cls, 'section': section, 'words': words(text), 'text': text}
                manifest.append(rec); blocks.append(rec); continue
            text = ' '.join(cells)
        else:
            text = inline_md(el)
        if not text.strip(): continue
        plain = re.sub(r'\*\*|\*', '', text)
        if ((fs and fs >= 19) or tag in ('h1','h2','h3','h4')) and words(plain) < 14:
            section = clean_label(plain); section_titles.append(section)
        if fs is not None and fs <= 13 and words(plain) < 16 and re.search(r'[A-Z]{3}', plain):
            section = clean_label(plain)
        if fs and fs >= 20 and 2 <= words(plain) < 14 and not re.search(r'Optima|ENGLISH|GRADE|Quarter|Lesson \d|Language Arts|Student Lesson|Education Experience|^\s*(?:World|Texas) History\s*$', plain, re.I):
            title_cands.append((0 if fs >= 21 else 2, plain))
        if topic_label_pending and words(plain) <= 14 and not (fs is not None and fs <= 13):
            title_cands.append((1, plain)); topic_label_pending = False
        if fs is not None and fs <= 13 and plain.strip().lower() in ('topic', 'lesson title', 'title', 'today'):
            topic_label_pending = True
        ordinal += 1
        if visual_node is not None and (words(plain) < 25 or (fs is not None and fs <= 15)):
            verdict, reason, flags = 'skip', 'inside-visual', []
        else:
            verdict, reason, flags = classify(text, tag, fs, cls, details_depth>0, bq_depth>0, section)
            if visual_node is not None and verdict == 'harvest': flags.append('in_visual')
        rec = {'ordinal': ordinal, 'verdict': verdict, 'reason': reason, 'flags': flags, 'tag': tag, 'fs': fs, 'cls': cls, 'section': section, 'words': words(plain), 'text': text}
        manifest.append(rec)
        if verdict in ('harvest','excerpt','definition'): blocks.append(rec)
        elif verdict == 'reading': reading_refs.append({'section': section, 'words': words(plain)})
    title = ''
    if title_cands:
        best = min(p for p, _ in title_cands)
        title = [t for p, t in title_cands if p == best][0]
        if best == 2 and title_tag:
            segs = [x.strip() for x in re.split(r'\s+[|·—-]\s+', title_tag)]
            segs = [x for x in segs if x and not re.search(r'Optima|Lesson \d|Grade|English|Language Arts|Quarter|Module \d|Student', x, re.I)]
            if segs: title = segs[0]
    if not title and title_tag:
        segs = [x.strip() for x in re.split(r'\s+[|\u00b7\u2014-]\s+', title_tag)]
        segs = [x for x in segs if x and not re.search(r'Optima|Lesson \d|Grade|English|Language Arts|Quarter|Module \d', x, re.I)]
        title = segs[0] if segs else ''
    if not title: title = os.path.splitext(os.path.basename(relpath))[0].replace('-', ' ').replace('_', ' ')
    return {'title': title, 'page_title': title_tag, 'blocks': blocks, 'manifest': manifest, 'visuals': visuals,
            'reading_refs': reading_refs, 'section_titles': section_titles}

def module_of(repo, relpath):
    p = relpath.replace('\\','/')
    m = re.search(r'(quarter-\d+)/(week-\d+)', p)
    if m: return f'{m.group(1)}-{m.group(2)}'
    m = re.search(r'(week-\d+)', p)
    if m: return m.group(1)
    return ''

def ystr(s):
    s = str(s).replace('\\','\\\\').replace('"','\\"')
    return f'"{s}"'

def write_entry(area, entry_id, meta, blocks):
    d = os.path.join(REPO, 'entries', area); os.makedirs(d, exist_ok=True)
    fm = ['---', f'id: {entry_id}', f'title: {ystr(meta["title"])}', f'category: {meta["category"]}', f'scope: {meta["scope"]}',
          'status: extracted', 'publish: false', 'rights: unchecked', 'schema: 1',
          f'area: {meta["area"]}', f'course: {meta["course"]}', f'course_code: "{meta["course_code"]}"', f'grade: {meta["grade"]}', f'module: {ystr(meta["module"])}',
          'topics: []', 'texts: []', 'authors: []', 'period: ""', 'standards_fl: []', 'standards_tx: []', 'standards_ccss: []',
          'moves: []', 'genre: ""', 'pairs_with: []', 'see_also: []', 'media: []',
          f'paragraphs: {meta["paragraphs"]}', f'words: {meta["words"]}', f'voice_flagged: {meta["voice_flagged"]}',
          'sources:', f'  - repo: {meta["repo"]}', f'    path: {ystr(meta["path"])}', f'    sha: {meta["sha"]}',
          f'    lesson_title: {ystr(meta["page_title"])}', f'    url: {ystr(meta["url"])}',
          f'    ordinals: [{", ".join(str(b["ordinal"]) for b in blocks)}]']
    if meta.get('reading_refs'):
        fm.append('reading_refs:')
        for r in meta['reading_refs']: fm.append(f'  - {ystr(r)}')
    if meta.get('visuals'):
        fm.append('visuals:')
        for v in meta['visuals']:
            fm.append(f'  - file: {ystr(v["file"])}'); fm.append(f'    label: {ystr(v["label"])}'); fm.append('    status: extracted'); fm.append('    illustrates: []')
    fm.append('---')
    body = []; cur = object()
    for b in blocks:
        sec = b.get('section') or ''
        if sec != cur:
            cur = sec
            if sec: body.append(f'\n<!-- section: {sec} -->')
        role = {'excerpt': 'excerpt', 'definition': 'definition'}.get(b['verdict'], 'content')
        fl = (' ' + ' '.join(b['flags'])) if b['flags'] else ''
        body.append(f'\n<!-- block {b["ordinal"]} role={role}{fl} -->')
        body.append(('> ' + b['text']) if role == 'excerpt' else b['text'])
    with open(os.path.join(d, entry_id + '.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(fm) + '\n' + '\n'.join(body).lstrip('\n') + '\n')

def _front(path, key):
    with open(path, encoding='utf-8') as f:
        m = re.search(rf'^{key}: (\S+)', f.read(4000), re.M)
    return m.group(1) if m else None

def existing_ids():
    return {_front(p, 'id') for p in glob.glob(os.path.join(REPO, 'entries', '*', '*.md'))} - {None}

def clear_course(course):
    """A fresh run replaces a course's entries wholesale, wherever they are filed by topic area, along with their
    frozen originals and visuals."""
    for sub in ('entries', '_original'):
        for p in glob.glob(os.path.join(REPO, sub, '*', '*.md')):
            if _front(p, 'course') == course:
                eid = _front(p, 'id'); os.remove(p)
                for v in glob.glob(os.path.join(REPO, 'visuals', f'{eid}--v*.html')): os.remove(v)

def main(repos=None):
    courses = repos or list(COURSES)
    os.makedirs(os.path.join(REPO,'_meta'), exist_ok=True)
    os.makedirs(os.path.join(REPO,'visuals'), exist_ok=True)
    man = open(os.path.join(REPO,'_meta','manifest.jsonl'), 'w', encoding='utf-8')
    report = {}; seen_hash = {}; std_text = {}   # course family -> list of (entry_id, text)
    import difflib
    def family(course): return course.rstrip('h')
    for prefix in courses:
        course, grade, code, disp = COURSES[prefix]
        # a fresh run replaces the course's entries wholesale (stale files from a previous rule set must not survive)
        clear_course(course)
        used_ids = existing_ids()
        c = Counter(); pages = 0; entries = 0; dup = 0
        for root, dirs, files in os.walk(os.path.join(SRC, LIB)):
            dirs[:] = sorted(d for d in dirs if d != '.git')
            for f in sorted(files):
                full = os.path.join(root, f); rel = os.path.relpath(full, os.path.join(SRC, LIB)).replace('\\','/')
                info = LESSON_MAP.get(rel)
                if not info or info['course'] != prefix: continue
                eq = info['position']; sha = lib_sha(rel)
                if EXCLUDE_PAGE.search(eq): c['pages_excluded'] += 1; continue
                html = open(full, encoding='utf-8', errors='ignore').read()
                h = hashlib.sha1(html.encode('utf-8','ignore')).hexdigest()
                if h in seen_hash: dup += 1; c['pages_duplicate_of_other_repo'] += 1; continue
                seen_hash[h] = f'{LIB}/{rel}'
                pages += 1
                res = harvest_page(LIB, eq, html)
                for m in res['manifest']:
                    m.update({'repo': LIB, 'path': rel}); man.write(json.dumps(m, ensure_ascii=False) + '\n')
                    c['blocks_'+m['verdict']] += 1
                    if m['verdict']=='skip': c['skip_'+m['reason']] += 1
                    if 'voice' in (m.get('flags') or []) and m['verdict']=='harvest': c['harvest_voice_flagged'] += 1
                if not res['blocks']:
                    c['pages_no_content'] += 1; continue
                area = rel.split('/')[0]                      # entries are organized by topic area, not by course
                entry_id = f"{area}-{slugify(res['title'], 48)}"; n = 2
                while entry_id in used_ids: entry_id = f"{area}-{slugify(res['title'], 44)}-{n}"; n += 1
                used_ids.add(entry_id)
                joined = ' '.join(b['text'] for b in res['blocks'])
                fam = family(course)
                if course.endswith('h'):
                    dup_of = None
                    for eid, txt in std_text.get(fam, []):
                        if abs(len(txt) - len(joined)) < 0.2 * max(len(txt), 1) and difflib.SequenceMatcher(None, txt, joined).quick_ratio() >= 0.9 and difflib.SequenceMatcher(None, txt, joined).ratio() >= 0.9:
                            dup_of = eid; break
                    if dup_of:
                        c['entries_near_duplicate_of_standard'] += 1
                        man.write(json.dumps({'repo': LIB, 'path': rel, 'verdict': 'entry-suppressed', 'reason': 'near-duplicate', 'duplicate_of': dup_of}, ensure_ascii=False) + '\n')
                        continue
                else:
                    std_text.setdefault(fam, []).append((entry_id, joined))
                vis = []
                for i,(lab,vh) in enumerate(res['visuals'],1):
                    vf = f'{entry_id}--v{i}.html'
                    with open(os.path.join(REPO,'visuals',vf),'w',encoding='utf-8') as vfh: vfh.write(f'<!-- source: {LIB}/{rel}@{sha} label: {lab} -->\n'+vh)
                    vis.append({'file': vf, 'label': lab})
                c['visual_candidates'] += len(vis)
                meta = {'title': res['title'], 'page_title': res['page_title'], 'category': 'historic-context', 'scope': 'text-specific',
                        'area': area, 'course': course, 'course_code': code, 'grade': grade, 'module': module_of(LIB, eq), 'repo': LIB, 'path': rel, 'sha': sha,
                        'url': LIB_URL + rel,
                        'paragraphs': len(res['blocks']), 'words': sum(b['words'] for b in res['blocks']),
                        'voice_flagged': sum(1 for b in res['blocks'] if 'voice' in b['flags']),
                        'reading_refs': [f"{r['section'] or 'reading'} ({r['words']} words)" for r in res['reading_refs']][:12],
                        'visuals': vis}
                write_entry(area, entry_id, meta, res['blocks']); entries += 1
                # frozen copy of the extracted text for the editor's diff view (never edited)
                odir = os.path.join(REPO, '_original', area); os.makedirs(odir, exist_ok=True)
                with open(os.path.join(REPO, 'entries', area, entry_id + '.md'), encoding='utf-8') as src_f, open(os.path.join(odir, entry_id + '.md'), 'w', encoding='utf-8', newline='\n') as dst_f:
                    dst_f.write(src_f.read())
                c['paragraphs_harvested'] += len(res['blocks'])
        c['pages_harvested'] = pages; c['entries'] = entries
        report[course] = dict(c)
        print(f"{course:28s} pages={pages:4d} entries={entries:4d} paras={c['paragraphs_harvested']:5d} voiceflag={c['harvest_voice_flagged']:4d} excerpts={c['blocks_excerpt']:4d} defs={c['blocks_definition']:4d} skipped={c['blocks_skip']:5d} reading={c['blocks_reading']:5d} visuals={c['visual_candidates']:3d} excl={c['pages_excluded']} dup={dup} neardup={c['entries_near_duplicate_of_standard']} nocontent={c['pages_no_content']}")
    man.close()
    json.dump(report, open(os.path.join(REPO,'_meta','report.json'),'w'), indent=1)

if __name__ == '__main__':
    main(sys.argv[1:] or None)
