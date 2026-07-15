# Multi-board split — how to revert

The `multi-board-split` branch reorganizes `KiCAD/` from a single-project
layout (one `.kicad_pro` covering the analog board) into three sibling
KiCad projects sharing one footprint library:

```
KiCAD/
├── xmitter.pretty/          (shared — unchanged)
├── xmitter.kicad_sym        (shared — unchanged)
├── analog/                  (was: KiCAD/ root, renamed KiCAD.* -> analog.*)
├── bias/                    (new project seeded from bias.kicad_sch)
└── frontpanel/              (new empty project — front-panel display + encoders)
```

Nothing in the analog Rev A gerbers, PCB, or schematic content is edited.
Only file locations change, plus:

- `filename` fields inside `analog.kicad_pro` and `analog.kicad_prl`
  updated to match the renamed files.
- Per-project `fp-lib-table` / `sym-lib-table` in each of `analog/`,
  `bias/`, `frontpanel/`, pointing at the shared libs one directory up.
- The old `KiCAD/fp-lib-table` and `KiCAD/sym-lib-table` are deleted
  (replaced by the per-project copies).

## If the split turns out to be a mistake

### Option 1 — throw away the branch entirely (cleanest)

```
git checkout master
git branch -D multi-board-split
```

You lose all migration commits. `master` is untouched, so this is the
zero-risk path.

### Option 2 — you already merged the split into master

```
git log --oneline                 # find the merge commit (or the first
                                  # migration commit if fast-forwarded)
git revert -m 1 <merge-commit>    # for a merge commit
git revert <commit>...            # for individual migration commits, newest first
```

This creates a new commit that undoes the moves. History is preserved.

### Option 3 — surgical rollback (keep some stages, drop others)

Migration is committed in stages so you can revert one stage without
touching the others:

- Stage 1 commit: analog files moved into `KiCAD/analog/`.
- Stage 2 commit: `KiCAD/bias/` project created.
- Stage 3 commit: `KiCAD/frontpanel/` project created.
- Tools-update commit: `CLAUDE.md` and tool paths updated.

`git revert <stage-3-commit>` (for example) undoes just the frontpanel
project without disturbing the analog rename or the bias project.

## What to check after any revert

1. `git status` — should be clean.
2. Open `KiCAD/KiCAD.kicad_pro` in KiCad. Schematic loads, PCB loads,
   no missing footprint or symbol errors.
3. Re-check `CLAUDE.md`'s tool command block for any stale paths the
   revert didn't touch.

## Files intentionally NOT changed by the migration

- Everything under `KiCAD/analog/gerber/` (the Rev A submission record —
  moved as-is, byte-identical to what JLCPCB received).
- `xmitter.pretty/*.kicad_mod` (shared footprints — path unchanged).
- `xmitter.kicad_sym` (shared symbol library — path unchanged).
- Any `.kicad_sch` or `.kicad_pcb` file contents (only their locations
  move).
