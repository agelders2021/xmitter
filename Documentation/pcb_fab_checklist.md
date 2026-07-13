# PCB Fabrication Pre-Flight Checklist

The single gate before submitting gerbers. Every `- [ ]` here must become
`- [x]` before ordering the PCB. Once ordered, changes cost a full fab
cycle.

Scope: **analog control board only** (bias + cathode monitor + VFO +
buffer/keyer + Arduino carrier + Interface). The PA module is a separate
board and gets its own pre-flight later (Phase 4-5). Sheets that are
still empty stubs — `pa`, `driver`, `balun`, `lpf_output` — are
intentionally deferred and NOT part of this fab pass.

Related docs:

- `Documentation/front_panel_interface.md` — has the deep dive on RJ45,
  PCF8575, and I²C QT rotary encoder verification items. This doc is the
  index; that doc is the detail.
- `Documentation/build_checklist.md` — phase-by-phase build status. This
  doc references items there but does not duplicate them.
- `Documentation/2026-06-16-supply-and-pcb-strategy.md` — decisions on
  board partition, layer stack, and creepage net classes.

Status legend:

- `- [x]` — done, no further action.
- `- [ ]` — must resolve before fab.
- `- [~]` — deferred by explicit decision (with reason).

---

## Current status snapshot (2026-07-13)

Analog control board is functionally fab-ready. Board: 130 × 170 mm,
2-layer FR4, all copper routed, GND pours filled, 4 corner M3 mounting
holes at (11, 10), (131, 10), (11, 170), (131, 170).

DRC clean of functional errors: 0 unconnected, 0 clearance, 0 hole-to-hole,
0 starved-thermal, 0 track-dangling. 5 remaining warnings are all
cosmetic silk (4 silk_over_copper auto-clipped by fab, 1 silk_overlap).

Remaining pre-fab gates (small, listed under sections below):

- 3 custom footprints still need physical verification when parts arrive
  (PCF8575, QT rotary encoder, Si5351 breakout mounting holes)
- RJE1D-188 panel cutout dimensions on a User.Drawings layer
- BOM regeneration + Mouser cart cross-check
- Fab-house-specific gerber / drill / stackup form-fill

None are blockers for routing; they're just the last-mile items before
gerber export.

---

## 1. Custom footprint verification

All four project-specific footprints were drafted from datasheet text or
partial drawings. Signal-pin arrays are exact; other features are
best-guess and need verification against the physical part or the
datasheet drawing at proper zoom before fab.

### RJE1D-188 shielded RJ45 socket

`KiCAD/xmitter.pretty/Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`.
Detailed items in `front_panel_interface.md` "RJE1D-188 footprint
verification" section.

**Reworked 2026-07-12 against Amphenol datasheet `p-rje1d-188-x1x01.pdf`
after builder read the drawing dimensions directly.** All coordinates
now match the datasheet callouts.

- [x] Signal pins P1-P8 (staggered 2×4, 8.89 mm span, 1.27 mm offset,
      2.54 mm in-row pitch) — exact from datasheet.
- [x] Shield mount post X-spacing = 10.00 mm (Ø3.00 NPTH plastic
      locating posts at ±5.0). Verified 2026-07-12.
- [x] Shield mount post Y-offset = 0 (origin datum). Reinterpreted:
      Ø3.00 holes are NOT shield ground, they're plastic locating
      posts. Shield ground is via the small Ø1.57 plated tails.
- [x] Alignment peg / shield-tail X-spacing = 14.85 mm (Ø1.57 plated,
      at ±7.425). Verified 2026-07-12.
- [x] Shield-tail Y-offset = −6.79 mm (6.79 mm toward PCB edge from
      Ø3.00 locating posts). Verified 2026-07-12.
- [x] ~~Four shield-tail hole positions~~ — verified there are only 2
      shield tails (Ø1.57 plated), not 4. Original guesses removed.

### PCF8575 breakout

`KiCAD/xmitter.pretty/Adafruit_PCF8575_Breakout.kicad_mod`.

- [x] Board outline, mounting holes (0.90 × 0.50 in spacing), pin count
      and X spacing (24 pins on 2.54 mm centers) — exact from datasheet.
- [ ] Pin row Y offset from board edge (assumed same Y as mounting
      holes, ±6.35 mm). Verify from physical breakout when it arrives.

### I²C QT rotary encoder

`KiCAD/xmitter.pretty/Adafruit_I2C_QT_Rotary_Encoder.kicad_mod`.

- [x] Board outline (25.4 × 25.4 mm) and 4 corner mounting holes on
      0.90 in spacing — exact from datasheet.
- [ ] 6-pin header pin order (assumed VIN, GND, SCL, SDA, INT, 3Vo
      left-to-right). Verify against physical breakout silkscreen; a
      swap here would put +5V on the wrong pad.
- [ ] Header row Y offset from board edge (used +10.16 mm, same Y as
      the bottom mounting holes).
- [ ] Encoder body 45° clearance and M7 shaft nut diameter for the
      panel cutout.

### Si5351A STEMMA breakout

`KiCAD/xmitter.pretty/Adafruit_Si5351A_STEMMA.kicad_mod`.

- [x] Descr already states "VERIFY mounting hole positions with
      calipers before fabricating" — flagged from the start.
- [ ] Confirm the four M2.5 mounting hole positions against the
      physical breakout with calipers.
- [ ] Confirm the 7 jumper-wire landing pad positions and pin order
      (VIN, GND, SDA, SCL, CLK0, CLK1, CLK2) against the physical
      breakout's header.

---

## 2. Schematic completeness

The analog board can only be routed once every symbol that will occupy
copper is on the schematic. Text-note placeholders don't count.

### Interface sheet — `KiCAD/interface.kicad_sch`

- [x] Instantiate the **RJE1D-188 RJ45 jack symbol** — J4 placed with
      `Connector:8P8C_Shielded` symbol and `xmitter:Amphenol_RJE1D-188_Horizontal_Shielded`
      footprint. Wired per T568B: SDA/SCL, MBL_A_P/N, +5V/GND,
      MBL_B_P/N, shell tabs to GND.
- [x] **RS-422 differential receiver placed** — U16 = AM26LS32ACN in a
      DIP-16 socket. Terminations R100/R101 (120 Ω) + 2.2k/10k level-
      shift dividers R26–R29 all present. Enable pins tied to GND.
- [x] MBL_A_QUAD / MBL_B_QUAD labels present (implemented as global
      labels `MBL600_A` / `MBL600_B` — functionally equivalent to
      hierarchical, resolves cross-sheet at the root).
- [~] Filament / HV / T/R relay drivers. Deferred — will populate the
      Interface sheet in a later revision. Not required for this fab
      pass. Text-note placeholder stays; leave board area clear for a
      later daughtercard or hand-wire.

### Arduino sheet — `KiCAD/arduino.kicad_sch`

- [x] **SDA** and **SCL** labels present (global labels — same
      cross-sheet resolution as hierarchical).
- [x] **GRID_BLOCK_CRASH** label present.
- [x] **MCP4728 LDAC** signal wired to spare Metro GPIO (global label
      `LDAC_4728` reaches Metro from buffer_keyer sheet).

### Front_Panel sheet — `KiCAD/front_panel.kicad_sch`

- [~] Component population deferred. Front-panel electronics live on
      the vector board off-PCB; nothing on this sheet will occupy
      copper on the analog board. Empty stub + text note is
      acceptable. Populate at leisure with PCF8575 and 2× QT encoder
      symbols marked `exclude_from_board = yes` if you want the BOM to
      include them.

### Root — `KiCAD/KiCAD.kicad_sch`

- [x] Interface, Front_Panel sheets registered.
- [x] SDA/SCL bidirectional shape on all sheet pins.
- [x] SDA/SCL fully wired across the hierarchy (Arduino, VFO,
      buffer_keyer, Interface all carry the same SDA/SCL globals).
- [x] Bias sheet unlinked from root (moving to separate PCB —
      2026-07-11).

---

## 3. Electrical rules check (ERC)

Run ERC across the whole hierarchy. Rules that are currently set to
`error` in `KiCAD.kicad_pro`:

- [ ] `hier_label_mismatch` — passes (SDA/SCL bidirectional fix done
      2026-07-02, but re-run after Arduino sheet gains labels).
- [ ] `pin_not_driven` — every power net must have a driving power
      symbol somewhere in the hierarchy. Verify +5V, +3.3V, +12V,
      +150V, +200V, +600V, −90V rails.
- [ ] `power_pin_not_driven` — pass on the analog board's power inputs.
- [ ] `label_dangling` — no dangling hierarchical labels.
- [ ] `unresolved_variable` — no `${...}` variables left unresolved.
- [ ] `unannotated` — every component has a real reference, no `R?`,
      `C?`, `U?` left.

Any warnings left unresolved (not just errors) should be captured in a
"warnings I know about and accept" list in git-tracked form (e.g., in
`.kicad_pro` `erc_exclusions`) so a fresh reviewer knows what was
intentional.

---

## 4. Component footprint coverage

Every symbol that will end up on copper must have a Footprint property
that resolves in the installed libraries.

- [x] All resistors, capacitors, and IC symbols in bias, buffer_keyer,
      vfo, arduino, interface sheets have non-empty Footprint values
      (verified 2026-07-02 by grep for `(property "Footprint" ""`).
- [x] Custom symbols `Adafruit_PCF8575_Breakout` and
      `Adafruit_I2C_QT_Rotary_Encoder` are pre-linked to their custom
      footprints.
- [ ] Any component added between now and fab (RS-422 receiver, RJ45
      jack instance, etc.) must have its Footprint set before fab.
      Re-run the grep after every schematic change.
- [ ] Re-run `python tools/assign_cap_footprints.py` on all active
      sheets to catch any cap values added since the last pass.

---

## 5. Physical / mechanical

Decisions from `2026-06-16-supply-and-pcb-strategy.md` that need to be
committed to the project before routing.

- [x] **Board dimensions** — Edge.Cuts drawn as 130 × 170 mm rectangle
      (final size after 2026-07-13 expansion to make room for corner
      mounting holes without conflicting with U1 Si5351 or L6 toroid).
- [x] **Layer stack** — 2-layer FR4, 1.6 mm thickness, 1 oz outer
      copper. Confirmed in `KiCAD.kicad_pcb` general.thickness = 1.6.
- [x] **Mounting-hole plan** — 4 corner Ø3.2 mm NPTH holes placed at
      (11, 10), (131, 10), (11, 170), (131, 170), 5 mm inset from
      each edge. All have 8+ mm clearance to nearest component.
      `MountingHole:MountingHole_3.2mm_M3` footprint.
- [ ] **RJE1D-188 panel cutout** — 16.44 × 14.42 mm (datasheet page 1)
      if the RJ45 is intended to protrude through a panel. If it's
      internal only, skip.
- [ ] **Board-to-front-panel mounting** — how the analog board mounts
      relative to the front panel and how the RJ45 socket aligns with
      any panel cutout. Not yet on any drawing.

---

## 6. Design rules (DRC) — set before routing

- [x] **Net classes** — Default (0.2 mm / 0.2 mm), Power (0.5 mm),
      RF (0.4 mm), HIZ (0.3 mm) all set up in `KiCAD.kicad_pro` with
      color coding and pattern-based net assignments.
- [~] **HV_BIAS class** — no longer needed on this board. The bias
      circuit was moved to a separate PCB on 2026-07-11 (bias sheet
      unlinked from root schematic). HV_BIAS class will be set up on
      the bias PCB project when that starts.
- [x] **Minimum track width and clearance** — Default 0.2 mm / 0.2 mm
      meets JLCPCB standard 2-layer (0.127 mm minimum).
- [x] **Minimum drill and annular ring** — `min_through_hole_diameter`
      = 0.3 mm, `min_via_annular_width` = 0.1 mm. Meets JLCPCB standard.
- [x] **Copper edge clearance** — `min_copper_edge_clearance` = 0.5 mm.
      Better than typical 0.3 mm requirement.
- [x] **Silk over pads / silk clearance** — set to warning.
      `min_text_height` reduced 0.8 → 0.5 mm on 2026-07-13 to accommodate
      external breakout silk (U8 MCP4728, U17 PCF8575, J5, U1 Si5351)
      whose vendor-supplied text is intentionally smaller.

---

## 7. Two-board directory split — decided (deferred)

Current KiCad project structure is flat: everything under `KiCAD/`. The
supply-strategy doc calls for a two-board split (`control_board/` +
`pa_module/`).

- [~] **Decision: defer the split** until the PA module design starts
      (Phase 3-5). The control board ships as a single-project fab on
      the current flat structure. Bias sheet (going to its own PCB) has
      already been unlinked from the root schematic on 2026-07-11.
- [ ] Don't accidentally place PA components on the control-board
      sheets while working. (Ongoing discipline check, not a fab gate.)

---

## 8. Ordering / BOM alignment

Before submitting gerbers, confirm the BOM matches the schematic and the
Mouser cart matches the BOM.

- [ ] Run `python tools/gen_parts_list_xlsx.py` to regenerate
      `Documentation/Parts_List.xlsx`. Diff against the current Mouser
      cart PDF to catch drift.
- [ ] Confirm parts on the current Mouser cart (2026-07-02) match the
      schematic:
    - [x] Amphenol RJE1D18821401 shielded RJ45 (×2)
    - [x] KEMET C330C105K2R5TA 1 µF 200 V (×8)
    - [x] Panasonic ECA-1EM100 10 µF 25 V (×5)
    - [x] Taiwan Semi 1N5817 Schottky (×4)
    - [x] Adam Tech ICS-308-T DIP-8 socket (×5)
    - [x] AVX/KEMET small caps (100 pF, 0.33 µF, 1000 pF) — check qty
          against schematic instance count.
- [ ] Still to order (all in front_panel_interface.md open items):
    - [ ] Adafruit PCF8575 breakout (PID 5904, ×1)
    - [ ] Adafruit I²C QT Rotary Encoder (PID 4991, ×2)
    - [ ] Bourns PEC11-4 mechanical encoder with switch (×2)
    - [ ] AM26LS32ACN RS-422 receiver (×1) or chosen alternate
    - [ ] DIP-16 socket for AM26LS32ACN

---

## 9. Fab-house-specific pre-flight

Once everything above is `- [x]`, do this last sanity check against the
chosen fab house (default: JLCPCB).

- [ ] **Gerber format** — RS-274X, individual layer files. KiCad's
      default export is fine.
- [ ] **Drill file format** — Excellon 2, imperial or metric per fab
      house preference.
- [ ] **Silkscreen colours** — chosen (default white on green).
- [ ] **Surface finish** — HASL is fine (per supply-strategy doc);
      ENIG only if RF pads need it (not for this analog board).
- [ ] **Design-for-manufacturing (DFM) check** — run KiCad's DRC one
      final time on the final PCB with routing complete.
- [ ] **Layer stack matches order form** — 2 layers ordered = 2 layers
      in the file.
- [ ] **Panelization** — decide whether to panelize (multiple boards
      per fab lot) or single up. For a prototype 1-of-1 build, single
      up is fine.
- [ ] **Order quantity** — minimum 5 boards from JLCPCB. Budget for
      spares and rework.

---

## Sign-off

When every item above is `- [x]` or `- [~]` (deferred by explicit
decision, with reason noted), export gerbers and submit. Record the
order date, fab house, order number, and expected ship date in
`build_checklist.md` under Phase 2 "Verify before declaring done".
