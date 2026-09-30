"""
serve.py -- local backend for the encyclopedia editor.

  python _build/serve.py            -> http://localhost:8765/editor/
Serves the repo folder read-only over HTTP and accepts writes ONLY under entries/, visuals/, _meta/:
  POST /api/save   {path, content}            write one file (entry .md, taxonomy/topics/texts/queue .yml)
  POST /api/rebuild                            re-run build_index.py; returns gate.json
  POST /api/git    {message}                   git add entries/ visuals/ _meta/ index.json + commit (if the repo has git)
  POST /api/pull                               Refresh: `git pull --ff-only` in optima-history (the only thing here that touches it)
  GET  /api/source?repo=&path=                 read-only: one .html lesson page from optima-history (sibling folder)
optima-history is the only repo this server reads lessons from, and it is never writable from here.
"""
import os, sys, json, subprocess, http.server, urllib.parse, posixpath
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath((os.path.join(HERE, '..', 'repo') if os.path.isdir(os.path.join(HERE, '..', 'repo')) else os.path.join(HERE, '..')))
SRC = os.path.normpath(os.path.join(HERE, '..', '..'))
SOURCE_REPOS = ('optima-history',)
WRITABLE = ('entries/', 'visuals/', '_meta/', 'queue/')
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=REPO, **k)
    def log_message(self, fmt, *args): pass
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != '/api/source': return super().do_GET()
        # read-only view of one lesson page in a source course repo (siblings of this folder); .html only, never writable
        q = urllib.parse.parse_qs(u.query); repo = (q.get('repo') or [''])[0]; rel = posixpath.normpath((q.get('path') or [''])[0])
        if repo not in SOURCE_REPOS or rel.startswith(('..', '/')) or not rel.lower().endswith(('.html', '.htm')):
            return self._json(403, {'error': 'refused: not a lesson page in a known source repo'})
        base = os.path.realpath(os.path.join(SRC, repo)); full = os.path.realpath(os.path.join(base, rel.replace('/', os.sep)))
        if not full.startswith(base + os.sep) or not os.path.isfile(full): return self._json(404, {'error': 'no such file'})
        b = open(full, 'rb').read(3_000_000)
        self.send_response(200); self.send_header('Content-Type', 'text/plain; charset=utf-8'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(n) or b'{}')
        if self.path == '/api/save':
            rel = posixpath.normpath(body.get('path', ''))
            if rel.startswith(('..', '/')) or not rel.startswith(WRITABLE):
                return self._json(403, {'error': f'refused: {rel} is outside the writable folders'})
            full = os.path.join(REPO, rel.replace('/', os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, 'w', encoding='utf-8', newline='\n') as f: f.write(body.get('content', ''))
            return self._json(200, {'ok': True, 'path': rel, 'bytes': len(body.get('content', '').encode('utf-8'))})
        if self.path == '/api/rebuild':
            r = subprocess.run([sys.executable, os.path.join(HERE, 'build_index.py')], capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            try: gate = json.load(open(os.path.join(REPO, '_meta', 'gate.json'), encoding='utf-8'))
            except Exception: gate = {}
            return self._json(200, {'ok': r.returncode == 0, 'gate': gate, 'log': (r.stdout + r.stderr)[-4000:]})
        if self.path == '/api/inventory':
            r = subprocess.run([sys.executable, os.path.join(HERE, 'inventory.py')], capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            return self._json(200, {'ok': r.returncode == 0, 'log': (r.stdout + r.stderr)[-2000:]})
        if self.path == '/api/pull':
            # Refresh: `git pull --ff-only` in optima-history. Fast-forward only, so it never merges over or discards local work;
            # if it cannot fast-forward (diverged history), it stops and says why. GIT_TERMINAL_PROMPT=0 so it never waits on a password.
            lib = os.path.join(SRC, SOURCE_REPOS[0]); env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
            def git(*a, t=90): return subprocess.run(['git', '-C', lib, *a], capture_output=True, text=True, env=env, timeout=t)
            try:
                if not os.path.isdir(os.path.join(lib, '.git')): return self._json(200, {'ok': False, 'message': 'optima-history is not a git clone on this computer.'})
                before = git('rev-parse', 'HEAD').stdout.strip(); r = git('pull', '--ff-only')
                if r.returncode != 0:
                    text = (r.stderr or '') + ' ' + (r.stdout or ''); lines = [l for l in text.strip().splitlines() if l.strip() and not l.startswith('hint:')]
                    if 'fast-forward' in text: msg = 'Your local copy and GitHub have each gained commits the other lacks, so a safe pull is not possible. Nothing was changed.'
                    elif 'would be overwritten' in text: msg = 'You have uncommitted changes to files that GitHub also changed. Commit or set those aside first. Nothing was changed.'
                    elif 'resolve host' in text or 'unable to access' in text or 'Could not read from remote' in text: msg = "Couldn't reach GitHub. Check your internet connection and try again."
                    else: msg = (' '.join(lines[-3:]) or 'git pull failed')[:400]
                    return self._json(200, {'ok': False, 'message': msg})
                after = git('rev-parse', 'HEAD').stdout.strip(); moved = before != after
                commits = int(git('rev-list', '--count', f'{before}..{after}').stdout.strip() or 0) if moved else 0
                files = len([l for l in git('diff', '--name-only', before, after).stdout.splitlines() if l]) if moved else 0
                subjects = git('log', '--format=%s', f'{before}..{after}').stdout.splitlines()[:6] if moved else []
                ahead = int(git('rev-list', '--count', '@{u}..HEAD').stdout.strip() or 0)
                dirty = len([l for l in git('status', '--porcelain').stdout.splitlines() if l])
                return self._json(200, {'ok': True, 'changed': moved, 'commits': commits, 'files': files, 'subjects': subjects, 'ahead': ahead, 'dirty': dirty})
            except subprocess.TimeoutExpired: return self._json(200, {'ok': False, 'message': 'GitHub did not respond in time. Check your connection and try again.'})
            except Exception as e: return self._json(200, {'ok': False, 'message': str(e)[:300]})
        if self.path == '/api/git':
            if not os.path.isdir(os.path.join(REPO, '.git')): return self._json(400, {'error': 'repo has no .git yet'})
            msg = body.get('message') or 'Edit entries'
            subprocess.run(['git', '-C', REPO, 'add', 'entries', 'visuals', '_meta', 'index.json', 'queue'], capture_output=True)
            r = subprocess.run(['git', '-C', REPO, 'commit', '-m', msg], capture_output=True, text=True)
            return self._json(200, {'ok': r.returncode == 0, 'out': (r.stdout + r.stderr)[-2000:]})
        return self._json(404, {'error': 'unknown endpoint'})

if __name__ == '__main__':
    print(f'Encyclopedia editor: http://localhost:{PORT}/editor/   (repo: {REPO})')
    http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
