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

## 1. Custom footprint verification

All four project-specific footprints were drafted from datasheet text or
partial drawings. Signal-pin arrays are exact; other features are
best-guess and need verification against the physical part or the
datasheet drawing at proper zoom before fab.

### RJE1D-188 shielded RJ45 socket

`KiCAD/xmitter.pretty/Amphenol_RJE1D-188_Horizontal_Shielded.kicad_mod`.
Detailed items in `front_panel_interface.md` "RJE1D-188 footprint
verification" section.

- [x] Signal pins P1-P8 (staggered 2×4, 8.89 mm span, 1.27 mm offset,
      2.54 mm in-row pitch) — exact from datasheet.
- [ ] Shield mount post X-spacing (used 10.00 mm).
- [ ] Shield mount post Y-offset from pin array (used +3.96 mm) —
      *least confident dimension*.
- [ ] Alignment peg X-spacing (used 8.80 mm).
- [ ] Alignment peg Y-offset from pin array (used −3.96 mm).
- [ ] Four shield-tail hole positions (guessed at ±6.50, ±2.54).

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

- [ ] Instantiate the **RJE1D-188 RJ45 jack symbol** (currently only a
      text note). Symbol `Connector:8P8C_Shielded` is already in the
      sheet's `lib_symbols` block (linter-injected). Wire pins 1/2 to
      SDA/SCL, 3/6 to MBL_A_P/N, 4/5 to +5V/GND, 7/8 to MBL_B_P/N,
      shell tabs to GND.
- [ ] Place the **RS-422 differential receiver**. Pick between
      AM26LS32ACN (DIP-16, familiar) and 74LVC2G17 (SOT-23-6, tiny SMT
      — probably ruled out by the builder's hand tremor). Default:
      AM26LS32ACN in a DIP-16 socket. See front_panel_interface.md
      "Schematic — Interface sheet is not yet complete" for the wiring
      plan.
- [ ] Add hierarchical labels `MBL_A_QUAD` and `MBL_B_QUAD`
      (single-ended 3.3 V TTL outputs of the receiver) routing up to
      the Arduino sheet.
- [~] Filament / HV / T/R relay drivers. Deferred — will populate the
      Interface sheet in a later revision. Not required for this fab
      pass. Text-note placeholder stays; leave board area clear for a
      later daughtercard or hand-wire.

### Arduino sheet — `KiCAD/arduino.kicad_sch`

- [ ] Add **SDA** and **SCL** as bidirectional hierarchical labels
      (present on VFO, buffer_keyer, Interface sheets but not here).
      Even though the Metro I²C physically exits via STEMMA QT
      off-board, the schematic must show the electrical net for ERC to
      pass.
- [ ] Add **GRID_BLOCK_CRASH** as an input hierarchical label (already
      exposed by the Bias sheet). Enables firmware ADC-based fault
      logging.
- [ ] Wire the **MCP4728 LDAC** signal (from the buffer_keyer sheet)
      to a spare Metro GPIO. Required for the one-time I²C EEPROM
      address reprogram (0x60 → 0x62) — see build_checklist.md Phase 1
      and `project_i2c_bus.md` memory.

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
- [ ] Once SDA/SCL labels are added to the Arduino sheet, wire the new
      root sheet pin to the shared SDA/SCL net.

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

- [ ] **Board dimensions** — decided on paper but not yet in
      `KiCAD.kicad_pcb`. Draw the board outline on Edge.Cuts before
      routing.
- [ ] **Layer stack** — 2-layer FR4, 1 oz outer copper for the control
      board (per supply-strategy doc). Confirm in
      `KiCAD.kicad_pro` → Board Setup → Physical Stackup.
- [ ] **Mounting-hole plan** — 4 corner NPTH holes minimum, M3 clearance
      (ø3.2 mm hole). Add them to Edge.Cuts.
- [ ] **RJE1D-188 panel cutout** — 16.44 × 14.42 mm (datasheet page 1)
      if the RJ45 is intended to protrude through a panel. If it's
      internal only, skip.
- [ ] **Board-to-front-panel mounting** — how the analog board mounts
      relative to the front panel and how the RJ45 socket aligns with
      any panel cutout. Not yet on any drawing.

---

## 6. Design rules (DRC) — set before routing

- [ ] **Net classes** — the supply-strategy doc calls for HV_BIAS
      (2 mm creepage), HV_SCREEN (3 mm), HV_PLATE (6 mm). None of
      these are set up in `KiCAD.kicad_pro` yet. On the *control
      board* only, HV_BIAS matters (the −90 V rail); the higher-voltage
      classes apply to the PA module. Set at least HV_BIAS before
      routing bias tracks.
- [ ] **Minimum track width and clearance** — fab-house-specific;
      confirm with the chosen manufacturer (JLCPCB or PCBWay) before
      setting. Default 6 mil / 6 mil is safe for JLCPCB standard 2-layer.
- [ ] **Minimum drill and annular ring** — 0.3 mm drill / 0.15 mm
      annular is the JLCPCB standard 2-layer minimum. Confirm before
      running DRC.
- [ ] **Copper edge clearance** — 0.3 mm typical.
- [ ] **Silk over pads / silk clearance** — set to warning, resolve on
      a per-case basis.

---

## 7. Two-board directory split — decision needed

Current KiCad project structure is flat: everything under `KiCAD/`. The
supply-strategy doc calls for a two-board split (`control_board/` +
`pa_module/`).

- [ ] Decide **now** whether to split the project before this fab pass
      or after. Splitting after means the current sheet UUIDs stay
      stable; splitting before means the sheets get new instance paths.
      Recommendation: **defer the split until the PA module design
      starts** (Phase 3-5). The control board can ship as a
      single-project fab on the current flat structure.

If deferred: no action needed here, just don't accidentally place PA
components on the control-board sheets.

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
