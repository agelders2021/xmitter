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

### "B doesn't fill my pour" — troubleshooting

Failure symptoms usually mean one of these five things.  Walk them in
order; each takes ten seconds to check.

1. **No zone exists yet.**  `B` refills what's already there — it does
   not draw a new pour.  If you're on a freshly-started board and
   haven't drawn a GND pour outline, `B` is a silent no-op.  Fix:
   right toolbar → "Add filled zone" (solid-square icon) → click to
   draw an outline just inside the board edge → first click pops the
   Zone Properties dialog, set **Net = GND**, Layer = F.Cu (repeat
   for B.Cu), OK → double-click to close the polygon.  Then `B`.

2. **Zone exists but has no net assigned.**  If the Zone Properties
   dialog was dismissed with Net = `<no net>` or blank, KiCad refuses
   to fill because it doesn't know what net to attach the pour to.
   Fix: click the zone outline (or its edge) → `E` → set Net to GND
   in the "Net" field → OK → `B`.

3. **Zone is a keepout / rule area, not a fillable zone.**  Keepouts
   are drawn with the same "Add filled zone" tool but the "Keepout"
   checkbox in the properties dialog was checked and "Allow copper
   pour" was unchecked.  They will never fill — that's the point.
   Fix: if you meant a real pour, `E` on the zone → uncheck Keepout →
   OK → `B`.  Or delete and redraw as a normal zone.

4. **Display setting is showing outlines only.**  If `B` completes
   silently and you still see just hatched borders, the display mode
   is set to "outline only."  Fix: right-side Appearance panel →
   Objects tab → "Zones" section → set the display mode to
   **Filled**.  (Alternate quick fix: press `Ctrl+Shift+B` to unfill
   everything, then `B` again — sometimes forces a redraw.)

5. **The shortcut got re-bound or is going to the wrong window.**
   Uncommon but possible after a KiCad reinstall or preference reset.
   Fix: `Preferences → Preferences → Hotkeys → PCB Editor` → search
   for "Fill" → confirm `B` is bound to `Fill All Zones`.  If the
   PCB canvas doesn't have focus, `B` may be eaten by whatever panel
   does — click once on the canvas first, then `B`.

If none of those describe the failure, from the menu use
**Edit → Fill All Zones** instead of the shortcut.  That path always
runs regardless of hotkey / focus state, so it's the ground-truth
test.  If the menu action does nothing either, the problem is that
there are no fillable zones in the file — go back to point 1 or 2.

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
