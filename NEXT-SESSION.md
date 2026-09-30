# Next Session — Social Studies Encyclopedia Experiment

Status as of this handoff (updated 2026-09-30): **editor built, published as its own GitHub repo, and hosted on GitHub Pages (public)** (`optimaondemand/optima-social-studies-encyclopedia`, created at the user's direction as "the final stage of the
experiment"). The repo starts from a single fresh commit of the current state; the older local history (which predates the
clean break and names the old course repos) was deliberately NOT published and stays only in the local `master` branch. The
encyclopedia draws **only** on the `optima-history` lesson library (a clean break; see below). A demo for the author of the ELA
editor is pending.

## Progress log: 2026-09-30 (end of day) — read this first

**Published and public.** The repo `optimaondemand/optima-social-studies-encyclopedia` was made **public** (the user: everything
is already public, so no loss) and the editor is hosted on GitHub Pages:
**https://optimaondemand.github.io/optima-social-studies-encyclopedia/editor/** (Pages serves `main`, root; `.nojekyll` added).
The user tried it and confirmed it works.

What was done today, in order:
- Copied, sorted and renamed Texas History and World History lessons into `optima-history` topical folders (72 lessons, 12 widgets),
  cleaned course text (banners, week references), enabled Pages there; all pushed. Source course repos untouched (0 changes).
- Clean break: the encyclopedia reads only `optima-history`; entry ids are `<topic-folder>-<lesson-slug>`; course is metadata only
  (`course`, `module`, `_meta/lesson_map.json`). No file mentions the old course repos (scanned).
- Editor: Lessons view with collapsible chronological table of contents (`_meta/topic_order.yml`), Refresh (Pull, fast-forward
  only), Ulysses-style writing surface, Apply / Undo / Push cart screen (preview only).
- Published the repo from one clean commit; older local history stays on the local `master` branch only.
- **Read-only view for the hosted page:** on the sign-in screen, "Just look around (read-only)" lets anyone browse without a
  token (reads the site's own files; lesson previews load from `optimaondemand.github.io/optima-history/`). Saving still needs a
  GitHub token with write access to this repo. Implemented as `S.viewOnly` in `editor/index.html` (`readText`, `writeText`,
  `selectLesson`, `boot`, `#siView`).

Where the user works from now on: this folder (`optima-social-studies-encyclopedia`). Commit/push only when asked; never force-push.

Still true and unbuilt: Place order steps 1 and 2 change nothing; Refresh, Re-scan and Place order work only with the local server
(`python _build/serve.py`); the hosted page has had one manual look-around only, no automated test; topic tags on entries were seeded
from old text and not re-verified; the hard part of writing edits back into lesson HTML without losing glossary tooltips/widgets
is not started. The earlier "Open items" list below still stands.

## What this is

An experiment applying the finished ELA atomized-encyclopedia build (`optimaondemand/optima-ela-encyclopedia`,
via its own `PROMPT-new-subject.md`) to social studies lessons, deliberately mixing two state standards frameworks:

- **World History** (course slug `wh6`, CPALMS 2109010, FL framework) — 36 lessons
- **Texas History** (course slug `txhist7`, TEKS 113.19(b), TX framework) — 36 lessons

**Single source: `optima-history`.** Every lesson here was harvested from, and every source reference now points at,
the `optima-history` library (a sibling folder of this one; `github.com/optimaondemand/optima-history`), where lessons
live in topic folders (e.g. `ancient-mesopotamia/`, `spanish-republic-texas/`). Each lesson file is named for the
lesson itself (a slug of its title, e.g. `ancient-egypt/egypt-divided-and-a-king-from-the-south.html`) and never for a
course or a place in a course sequence; that name is the lesson's permanent address for future Canvas embeds, and the
matching entry id is `<topic folder>-<that slug>`. Which course a lesson fits, and where it sits in that course, is
metadata only: it is recorded per lesson in `_meta/lesson_map.json` and on each entry (`course`, `module`). This folder
only reads `optima-history`. Nothing else feeds the encyclopedia.

**State of `optima-history` (as of this note):** the 72 lessons are renamed (topical names), cleaned of all course framing
(banners, week/lesson/quarter references, Canvas and quiz pointers, capstone/exam tasks), and their 12 widgets are copied into
`<topic>/widgets/` and embedded from there. GitHub Pages is **on**
(`https://optimaondemand.github.io/optima-history/`). All of this was **pushed at the user's direction** through commit
`187dad3`. Three later local commits are **not yet pushed**: `53d9098` (two page `<title>`s), `1884a82` (README contents) and the
commit that orders that contents list chronologically. Folder order (earliest first, approximate by design) and each
folder's date hint live in `_meta/topic_order.yml`, which both the editor (via `_build/inventory.py`) and `_build/toc.py`
read; folders not listed there sort after the listed ones, A-Z. The
course repos were only ever read. The library README now has a collapsible table of contents (`<details>` per topic folder,
16 empty folders grouped together), generated by `python _build/toc.py` from the pages' own titles; re-run it after the
library changes and review the README diff before committing in `optima-history`.

This folder's GitHub repo (`origin`, branch `main`, private) is independent of every other repo, including the sibling
`optima-ela-encyclopedia` (the reference implementation, only ever read) and `optima-history`.

## The clean break (2026-09-30)

All provenance was re-pointed at `optima-history`: each entry's and each frozen original's `sources:` block
(repo, topic-folder path, the commit that added the file, and a GitHub blob URL), the visuals' source comments, the
manifest, `skip_sample.md`, `report.json`, the index, gate and tracker. `_build/harvest.py` and `_build/inventory.py`
read `optima-history` directly (set `ENC_SRC` to the folder that contains it if this folder is ever moved).

- **Entries re-synced to the cleaned lessons:** after the lessons were cleaned, every entry's text was regenerated from
  the current `optima-history` pages and merged over the existing entries. Harvest-owned fields (text, paragraph and word
  counts, `sources`, `lesson_title`, visuals) were refreshed; seeded fields (category, scope, topics, etc.) were kept.
  `_original/`, the manifest, report and skip sample were regenerated. No entry had been hand-edited, so nothing was lost.
- **Verified:** a fresh harvest from `optima-history` reproduces all 72 frozen originals (`_original/`) byte for byte, and
  every entry's text equals its frozen original. The gate passes with 72 entries and 647 paragraphs.
- **Removed:** the 3 entries whose source pages were not copied into the library (the glossary, the Olmec standards
  supplement, and the course review lesson), with their originals and manifest lines. They remain in this repo's git
  history (last commit before the break: `834af77`).
- **Do not casually re-run `harvest.py`.** A fresh run replaces each course's entries wholesale, discarding all tags,
  categories, topics and edits layered on top of the extraction.

## Topical organization (2026-09-30, an essential part of the experiment)

The user's rule: **lessons are not tied to courses; organization is purely topical.** Course is only metadata
recording which course an entry naturally fits.

- **Topic area** = the `optima-history` topic folder the lesson lives in (`ancient-egypt`, `spanish-republic-texas`,
  ...). Each entry has an `area:` field. Entries are filed `entries/<area>/<id>.md` (frozen originals at
  `_original/<area>/`), and the index gate fails if `area` disagrees with the lesson's topic folder.
- **Entry ids are topical:** `<area>-<slug of the lesson's own title>`, e.g.
  `ancient-egypt-egypt-divided-and-a-king-from-the-south`. No course or week in the id. A rerun of `harvest.py`
  produces the same ids; collisions get `-2`, `-3`.
- **Course is metadata:** `course:` (`wh6`, `txhist7`), `course_code`, `grade` and `module:` (`quarter-1-week-01`) stay
  as "fits course / position in that course" fields. A future `courses: [...]` list would let one entry fit several
  courses; not built. The editor shows them as "Fits course"; it groups, sorts and filters by topic area.
- **Titles fixed:** all 36 World History entries had the title "WORLD HISTORY" (the page banner). The harvest now takes the
  lesson's own "Topic" line, so every entry has a real, distinct title.
- **New topics** started in the editor pick a topic area and are filed under it with `course: ''`.
- Goal values (word goals) are stored in browser localStorage under the old ids, so any goal set before the rename is gone.
- Ran as a verified migration: a fresh harvest on a throwaway copy reproduces all 72 frozen originals byte for byte.

## Save / Apply / Push: UI BUILT as a preview (the user is moving slowly and carefully)

**What is real:** the entry editor has **Apply** (saves, refuses if the entry has no text changes from its lesson, records the
entry in `_meta/ready.json` with a hash of its text, then closes the editor), **Undo apply** (in the entry or via Remove in the
cart), and **Re-apply** if the entry is edited after applying (the cart flags it stale and blocks it until re-applied). The
header has **⇪ Push (n)**, which opens the cart screen: each applied entry with its lesson file, paragraphs changed/added/
removed, a View changes word diff, Open entry, Remove, per-item checkboxes, Select all/none, and a sticky totals bar with
**1 · Write to lessons** and **2 · Send to GitHub**. The Entries table shows "ready to push" and has a filter for it.

**What is NOT connected:** the two order steps only open a "Preview only" dialog describing what they would do. Nothing is
written to the lessons in `optima-history` and nothing is sent to GitHub. Writing the changes back into the page HTML
(keeping glossary tooltips, widgets and styling) is the unbuilt hard part. Tested end to end in a headless page on a throwaway
copy: apply, cart, diff, order preview, stale flag, remove, undo.

### Design as agreed (original notes)

Goal: the editor will ultimately change the lessons themselves, through a staging area. Three places: (1) GitHub
`optima-history`, (2) the local clone of it, (3) this encyclopedia folder. Today: Pull is (1)->(2) only; entries in (3) are
a separate extracted copy and are never written back; the editor never pushes.

```
(1) --Pull--> (2) --Update entries--> (3) edit --Apply--> [Ready list] --Push--> (2) --> (1)
```

- **Save** keeps a draft of an entry in (3). **Apply** finishes the entry and marks it *ready*; nothing outside (3) changes.
  Apply must be **undoable**, including later, from a Ready list in the main menu.
- **Push** (main menu) opens a new screen like a shopping cart just before purchase: every applied entry listed with the
  lesson and a before/after view, a Remove button per item (= un-apply), per-item checkboxes, a totals line. "Place order" is
  two steps: write the ready entries into the lessons in (2) as a local commit, then send to GitHub (1). The lessons stay
  untouched until Push. Never force-push; stop with a plain message if GitHub has moved ahead.
- **Update entries** (after a Pull): entries go stale when lessons change. `_original/` is the merge base, so a change on
  both sides can be merged three ways, with conflicts put to the user. A Refresh banner like "3 lessons changed since their
  entries were extracted" with an Update entries button was proposed first, as the low-risk first step.
- **Hard part:** writing an edited paragraph back into the page HTML without losing glossary tooltips, widgets or styling
  (patch only the changed paragraph in place; entries only support bold/italic).
- (3) now has its own GitHub repo (see the status line). `optima-history` stays the only home of the lessons. The user
  expects the app to eventually edit lessons on GitHub for anyone who holds credentials; that power is NOT built: the Push
  screen's two steps are still preview-only.

## Standing rules for this build (don't relitigate)

- **Pushing from this folder to GitHub is now allowed, but only when the user asks**, exactly like `optima-history`. The earlier
  "never push" rule was lifted by the user on 2026-09-30 when they asked for this repo. Never force-push; never publish the
  pre-clean-break history (it names the old course repos).
- **Harvest scope: narrative lesson prose only.** Reading Quizzes, Critical Questions, Primary Source
  Exercises, and VR write-ups are excluded — same ruling ELA made on instruction-shaped content.
- **Call-out boxes are IN SCOPE** — deliberate deviation from the ELA reference (which skips them
  wholesale). Turned out to need no code change: the classifier's skip-list never matched either course's
  actual call-out label text ("HELPFUL TO KNOW").
- **`teacher-homepages` is deliberately untouched.** The editor runs locally via `python _build/serve.py` at
  `localhost:8765`. It has not been deployed anywhere (no hosted copy).
- Categories (controlled, 7): `historical-concept, historic-context, primary-source, geography,
  civic-concept, biography, economics-concept`.

## Build order progress (per `optima-ela-encyclopedia/PROMPT-new-subject.md`)

| Step | Status |
|---|---|
| 0. Estimate | Done |
| 1. Inventory | Done |
| 2. Harvest | Done, including seeding — see below |
| 3. Taxonomy & gate | Done — `_meta/taxonomy.yml` written, `build_index.py` passes clean |
| 4. Editor | **Built and working locally** — see "Editor" below |
| 5. GitHub-mode test | Not started (needs a remote, which the no-push rule forbids for now) |
| 6. Standards audit | **Blocked**, see below |
| 7. Handback | Not started |

## Current counts

- World History: 36 entries, 446 paragraphs harvested, 31 voice-flagged
- Texas History: 36 entries, 201 paragraphs harvested, 10 voice-flagged
- Total: 72 entries, 647 paragraphs (the drop from 668 is the sequence-pointer sentences removed from the lessons). Categories: historic-context 20, biography 14, primary-source 12,
  civic-concept 9, historical-concept 8, geography 8, economics-concept 1 (real judgment-based categorization, not
  placeholder; borderline calls are logged with reasoning in `_meta/_categories.json`).

`_meta/topics.yml`: 32 concept-level topics seeded from bolded terms, duplicates consolidated. `_meta/texts.yml`
was built before the clean break and has not been re-verified against the 72 remaining entries.

## Editor (built 2026-09-30)

Run it: `python _build/serve.py` from this folder, then open `http://localhost:8765/editor/`. The server binds to
127.0.0.1 only, is a foreground process (stops at logout/restart), and writes only under `entries/`, `visuals/`,
`_meta/`, `queue/`. `optima-history` is the only repo it reads lessons from, and the editor never writes lesson files there. The one exception
is the header's **↻ Refresh (Pull)** button, which runs `git pull --ff-only` in `optima-history` (POST `/api/pull`) and then
re-scans and redraws the lists: it fast-forwards only, refuses diverged history or conflicting local edits with a plain-language
message, never creates merge commits, and reports commits/files pulled plus any local commits not yet pushed.

Files added or changed (**still untracked in this repo's git — nothing committed, by the user's choice**):
`editor/index.html`, `_build/serve.py`, `_build/inventory.py`, `_meta/source_inventory.json`, `_meta/queue.yml`, plus
the clean-break changes above.

- **Entries table / Library pane** are organized by topic area (filter by area, "Fits course" is a column and filter).
- **Lessons view (default).** Two panes: left is a **collapsible table of contents** of `optima-history`: one row per topical
  folder in repo order (counts, "no lessons yet" for empty ones), collapsed by default; click a folder to reveal or hide
  its lessons and widgets, Expand all / Collapse all for the whole picture or just the outline, open folders remembered in
  this browser, filter auto-opens matching folders, arrow keys move through open lessons (filter box, checkbox to include
  non-HTML files, green dot = has an entry); right previews the top of the selected
  lesson (text only, first 20 blocks, "show more/all"). A navy "Edit this entry" tab hangs from the header and opens the
  entry. Up/Down arrows move through the list. The user explicitly wants a plain, objective view of what is in the repo,
  not only curated/filtered views — keep it the default. Header buttons: Lessons / Entries (the curated table) /
  File table.
- **Backend.** `inventory.py` builds `_meta/source_inventory.json` (decodes HTML entities in titles). `serve.py` has a
  read-only `GET /api/source?repo=&path=` (.html only, `optima-history` only) plus `POST /api/inventory` for Re-scan.
- **Entry editor, Ulysses-style.** Library pane (all entries in repo order, filterable); Focus mode
  (Ctrl+Shift+F, Esc leaves; dims other paragraphs, hides chrome); typewriter scrolling; live word/char/
  reading-time counts with a per-entry word goal (goal stored in browser localStorage, not in the entry file);
  Enter splits a paragraph at the cursor, Backspace at the start joins to the one above (same role and section
  only); selection toolbar and Ctrl+B / Ctrl+I (bold and italic only — the entry format allows nothing else);
  Paper / Sepia / Dark themes; collapsible Library and Details panes (prefs in localStorage). Leaving an entry with
  unsaved edits asks first; the header is sticky.
- **How saving works locally.** Save writes the entry `.md` on disk and re-runs `build_index.py`. The page never
  calls the server's `/api/git` endpoint, so saves are **not** git commits. A "Commit" button in local mode was
  offered and not built.
- **Not verified in a browser by Claude:** only syntax-checked and endpoint-tested. The user has since looked at
  it and said it looks good. Split/join creates new paragraph ordinals flagged `added` — worth checking that
  Save and the diffs behave as expected with real edits.
- **The page's GitHub mode is untested.** Its preset repo, `optimaondemand/optima-social-studies-encyclopedia`, now exists
  (private). Signing in with a token and saving through the GitHub API has not been tried, and the page would need hosting
  (not set up) to be used without the local server.

The repo is fully independent of the ELA editor it was based on (the page here is a copy; the ELA repo was only read).

## Two real bugs found and fixed along the way (harvest)

1. World History mixes CSS-class kickers (`class="callout-label"`, styled only via `<style>` block) with
   inline-styled ones. The harvester's section-tracking only read inline styles, so class-based kickers
   didn't reset the tracked section name, causing some paragraphs to inherit a stale/wrong section label.
   Fixed by synthesizing `fs=11.0` when `class="callout-label"` is present with no inline font-size.
2. World History's closing wrap-up is labeled "KEEP THIS IN MIND" (Texas History's is "CARRY THIS
   FORWARD") — the former wasn't in `SKIP_SECTION`, so wrap-up paragraphs were slipping through as
   harvested content. Added to the skip list.

## Open items if this continues

1. **Topics schema gap, flagged not resolved:** `topics.yml` deliberately holds only institutional/
   conceptual terms (matching the ELA reference), not proper nouns (Hammurabi, Sargon, document titles,
   etc. — about 120 of them exist as bolded terms). If "every entry touching Hammurabi" needs to be a real
   query later, that needs a new figures/places field this schema doesn't have. Real design decision,
   not yet made.
2. **Standards citation is blocked, not just deferred.** Rule 7's "cited" standards class needs a real
   per-lesson teacher crosswalk. What exists: World History has only quarter-level standards lists (not
   per-lesson); Texas History's planning document has scattered, non-comprehensive TEKS citations. Attaching codes
   to specific entries without real per-lesson source data risks fabricating a citation — do not attempt
   this without either the actual Course Map PDFs parsed for per-lesson detail, or a real crosswalk
   supplied by the user.
3. **Entry-level `texts: []` tagging** — `_meta/texts.yml` (the vocabulary file) exists, but individual
   entries' `texts:` frontmatter fields were never populated (out of scope for what was asked).
4. **The 3 removed entries** (glossary, Olmec supplement, course review) would need their pages added to
   `optima-history` first if they should come back.
5. Steps 5-7 (GitHub-mode test, standards audit, handback) haven't started.

## Where things are on disk

- This repo: `C:\Users\Patrick\Desktop\Files for Claude\optima-social-studies-encyclopedia\` (local only)
- The lesson library it reads: `...\Files for Claude\optima-history\` (read-only from here)
- Reference implementation: `...\Files for Claude\optima-ela-encyclopedia\` (never modified)
- The build prompt this whole experiment follows: `optima-ela-encyclopedia\PROMPT-new-subject.md`
