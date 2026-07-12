# KiCad 10 PCB Routing Cheatsheet

Compact shortcut reference for hand-routing the xmitter analog board.
Habit worth building: hit `B` after every substantive routing change,
and glance at DRC every ~10 traces. Catching a clearance mistake
immediately is way faster than untangling it later.

## Routing

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ X                    │ Start routing a single track (from selected pad or cursor)   │
│ 6                    │ Route differential pair (rarely needed here)                 │
│ Esc or double-click  │ Finish current trace                                         │
│ /                    │ Toggle 45°/90° trace angle mode while routing                │
│ Enter                │ Finalize current trace to cursor position                    │
│ Backspace            │ Remove last placed segment while routing                     │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Layers & vias

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ V                    │ Drop a via at cursor and switch to next layer (mid-trace)    │
│ Ctrl+/               │ Toggle active layer without dropping a via                   │
│ Page Up / Page Down  │ Cycle through copper layers                                  │
│ + / −                │ Switch to next/previous copper layer                         │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Track width & router mode

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ W                    │ Increase track width to next preset                          │
│ Shift+W              │ Decrease track width to previous preset                      │
│ Ctrl+Shift+H         │ Toggle "highlight collisions" router mode                    │
│ Ctrl+Shift+B         │ Toggle "shove" (push and shove) router mode                  │
│ Ctrl+Shift+W         │ Toggle "walk around" router mode                             │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Edit & select

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ E                    │ Edit properties of selected item                             │
│ M                    │ Move (selection follows cursor until click)                  │
│ G                    │ Drag (keeps trace connections while moving)                  │
│ R                    │ Rotate selection                                             │
│ F                    │ Flip footprint to other side                                 │
│ Delete               │ Delete selected                                              │
│ Ctrl+Z / Ctrl+Y      │ Undo / Redo                                                  │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Zones (ground pour)

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ B                    │ Refill all zones                                             │
│ Ctrl+B               │ Refill only the selected zone                                │
│ Ctrl+Shift+B         │ Unfill all zones (shows outlines only, faster to edit)       │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## View & navigation

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ F1 / F2              │ Zoom in / out                                                │
│ Home                 │ Zoom to fit board                                            │
│ Space                │ Reset relative origin at cursor (for measuring)              │
│ Alt+3                │ Toggle ratsnest ("airwires") visibility                      │
│ Ctrl+F5              │ Toggle 3D viewer                                             │
│ ` (backtick)         │ Refresh screen                                               │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Measurement & info

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Ctrl+Shift+M         │ Measure tool (click two points, get distance/angle)          │
│ ?                    │ Show all shortcuts for the current tool                      │
│ Hover on trace       │ Status bar shows: net name, class, layer, length             │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## DRC & save

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ Ctrl+S               │ Save                                                         │
│ Tools menu → DRC     │ Run Design Rules Check                                       │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Grid & display

┌──────────────────────┬──────────────────────────────────────────────────────────────┐
│ Key                  │ Action                                                       │
├──────────────────────┼──────────────────────────────────────────────────────────────┤
│ 1 / 2 / 3            │ Switch between preset grid sizes                             │
│ Ctrl+Home            │ Recenter view at origin                                      │
└──────────────────────┴──────────────────────────────────────────────────────────────┘

## Cursor tricks

- Hold `Shift` to temporarily disable grid snap while moving
- 45°/90° constraint is automatic during routing; hold `Ctrl` in some
  editing modes to constrain motion to those angles

## Handy workflow

1. Set active layer in the layers panel (F.Cu / B.Cu).
2. Hover over a pad, press `X` — router snaps to that pad and follows
   the ratsnest airwire.
3. Click to place corners; `/` if you need a segment at a non-45° angle.
4. `V` mid-trace to drop a via and jump to the other side.
5. Click the destination pad to end.
6. `B` to refill the GND pour.
7. Repeat.
