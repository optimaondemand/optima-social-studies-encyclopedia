# Social Studies Encyclopedia Editor

An editor for the Optima Academy Online social studies lesson library, [`optima-history`](https://github.com/optimaondemand/optima-history).
It reads the library's lessons, keeps an **entry** for each lesson (the lesson's narrative paragraphs plus tags and notes),
and lets an editor revise the text in a staging area before anything touches the lessons.

Lessons are organized purely by topic. A lesson's course and position in that course are metadata on its entry, never part of its name.

## What is here

| Folder / file | What it holds |
|---|---|
| `editor/index.html` | The editor (one page): a collapsible table of contents of the library, lesson preview, the entry editor, the Apply / Push screen |
| `entries/<topic>/` | One entry per lesson: front matter (tags, category, sources) and the lesson's paragraphs |
| `_original/` | The frozen extraction each entry started from. Used for before/after diffs and as a merge base |
| `visuals/` | Visual blocks pulled out of lessons |
| `index.json` | Generated index of all entries |
| `_meta/` | Vocabularies (`taxonomy.yml`, `topics.yml`, `texts.yml`), the folder order (`topic_order.yml`), the Ready list (`ready.json`), generated reports |
| `_build/` | `serve.py` (local server), `harvest.py`, `build_index.py`, `inventory.py`, `toc.py` |
| `NEXT-SESSION.md` | Working notes: decisions, current state, what is and is not built |

## Use it

Hosted editor (public, read-only unless you sign in with a token that can write to this repo): https://optimaondemand.github.io/optima-social-studies-encyclopedia/editor/

## Run it locally

You need Python 3 (with `bs4`, `lxml`, `PyYAML`) and a local clone of `optima-history` **next to** this folder:

```
Files for Claude/
  optima-history/                        <- clone of github.com/optimaondemand/optima-history
  optima-social-studies-encyclopedia/    <- this repo
```

```
python _build/serve.py
```

then open http://localhost:8765/editor/ . The server listens on 127.0.0.1 only.

## How it works

- **Refresh (Pull)** downloads new commits from GitHub into your local `optima-history` clone (fast-forward only, never overwrites your work) and reloads the lists.
- **Save** keeps a draft of an entry. **Apply** marks it finished and puts it on the Ready list; it is undoable.
- **Push** opens a cart-style review of every applied entry with before/after diffs.

## Status

The review screen is a **preview**: its two order steps (write to the lessons, send to GitHub) explain what they would do and
**change nothing yet**. Until they are connected, editing an entry never changes a lesson and nothing is sent to GitHub.
When they are connected, sending changes to the lessons will require the user to hold GitHub credentials with write access to `optima-history`.

Rebuilding generated files: `python _build/build_index.py` (index and checks), `python _build/inventory.py` (library scan),
`python _build/toc.py` (the contents list in the `optima-history` README).
`harvest.py` re-extracts every entry from the lessons and **replaces** existing entries, so do not run it casually.
