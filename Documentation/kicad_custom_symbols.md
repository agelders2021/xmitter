# KiCad Custom Symbols — xmitter library

Stock symbols for breakout boards and dev modules (Adafruit Metro
ESP32-S3, Adafruit Si5351A STEMMA QT, etc.) tend to show every pin with
every possible alternate-function name. The result is visually unreadable
at normal schematic zoom and clutters the sheet without adding
information this project actually needs.

This doc captures the pattern for building project-specific replacement
symbols in a local `xmitter` symbol library, and records the specific
custom symbols planned for this project.

## Why custom symbols

Three problems with the stock Metro_ESP32S3 symbol from the standard
KiCad library (visible in the current `arduino.kicad_sch` sheet):

- Each pin shows three or four alternate-function names stacked together
  (e.g. `D6 A4/SDA` for one physical pin). Labels overlap at any zoom
  level you would normally read a schematic at.
- The board has multiple physical header positions for the same logical
  signal (GND in three places, 5V in two, SCK on both the main header
  and the ICSP header). The stock symbol exposes ALL of them with
  disambiguating suffixes (`GND_R1`, `GND_R2`, `SCK_H`), so the symbol
  has ~30 pins when ~10 are in use.
- Most of those pins are unused in this project but still need a route
  on the schematic page (NC marker, label, or visible stub).

A custom symbol with only the pins this project uses, named with this
project's signal names, is far easier to read and review.

The same logic already drove the custom `Adafruit_Si5351A_STEMMA`
footprint in `KiCAD/xmitter.pretty/` — this doc extends the approach to
schematic symbols.

## Library location

All project-specific KiCad symbols live in:

    KiCAD/xmitter.kicad_sym

(matching the existing footprint library at `KiCAD/xmitter.pretty/`).

Registered in the project-local symbol library table:

    KiCAD/sym-lib-table

so it is available only to this project (does not pollute the global
KiCad library list on either dev machine).

## File-write caveat (KiCad 10 BOM gotcha)

Never write `.kicad_sym` files with PowerShell's
`Set-Content -Encoding UTF8` — it adds a UTF-8 BOM, and KiCad 10
silently treats BOM-prefixed symbol files as empty. Use
`[System.IO.File]::WriteAllBytes()` instead, or edit through the KiCad
Symbol Editor GUI (which writes the file correctly).

(This is the same rule that applies elsewhere in the KiCad tree — see
the project CLAUDE.md.)

## Workflow — building a custom symbol

The pattern below produces a symbol whose KiCad pin NUMBERS map onto the
existing footprint's pads (so wiring still connects to the right physical
location) but whose pin NAMES carry the project-specific signal label.

Done through the KiCad Symbol Editor GUI:

1. Open the Symbol Editor → File → New Library → name it `xmitter`,
   choose Project scope so it is registered in the project's
   `sym-lib-table`.
2. New Symbol in the `xmitter` library → name it after the part
   (`Metro_ESP32S3`, `MCP4921_DAC`, etc.).
3. Draw a simple rectangle body sized for the pin count.
4. Add pins one at a time. For each pin set:
   - Pin number: the actual footprint pad number for this signal on the
     module (look up against the existing footprint or the Adafruit
     pinout reference).
   - Pin name: a project-meaningful label (e.g. `D10/CS_DAC`, not
     `D10/SS`).
   - Electrical type: input / output / bidirectional / power_in /
     power_out / passive as appropriate. ERC uses this.
5. Save the library.
6. On the affected schematic sheet, right-click the existing stock
   symbol → Change Symbol → pick the new `xmitter:<name>`. Pin numbers
   stay aligned with the same footprint, so any existing wires remain
   attached.

Unused footprint pads do not need to appear in the symbol — KiCad does
not require schematic-to-footprint pad coverage to be 100 %. Unused
pads simply float on the PCB.

## Planned custom symbols for this project

### xmitter:Metro_ESP32S3

The big one. Project uses only these pins of the Metro ESP32-S3:

┌─────────────┬──────────────────┬────────┬───────────────────────────────┐
│ Pin name    │ Footprint pad    │ Type   │ Used for                      │
├─────────────┼──────────────────┼────────┼───────────────────────────────┤
│ GND         │ any GND header   │ pwr_in │ Ground reference              │
│ 3V3         │ 3.3V header pin  │ pwr_out│ Si5351 STEMMA breakout supply │
│ D2/SDA      │ D2               │ bidir  │ I2C data (Si5351, future LCD) │
│ D3/SCL      │ D3               │ output │ I2C clock                     │
│ D4/DIT      │ D4               │ input  │ Paddle dit (key input)        │
│ D5/DAH      │ D5               │ input  │ Paddle dah (key input)        │
│ D6/TX_LED   │ D6               │ output │ Optional TX-status indicator  │
│ D10/CS_DAC  │ D10              │ output │ SPI chip-select for MCP4921   │
│ D11/MOSI    │ D11              │ output │ SPI data to MCP4921           │
│ D13/SCK     │ D13              │ output │ SPI clock to MCP4921          │
└─────────────┴──────────────────┴────────┴───────────────────────────────┘

10 pins instead of ~30. Each pin shows its Arduino-header label plus a
project-specific function name. No `_R` / `_H` duplicate-pin suffixes.

NOT exposed (intentional):
- USB, EN, RST, BOOT — handled by the on-board USB-C / button, no need
  on the project schematic.
- Other analog pins (A0–A5 beyond what's reused as D-pins) — unused.
- Other digital pins (D7, D8, D9, D12) — unused.
- Second 5V / 3V3 / GND header positions — single logical net, single
  pin in the symbol.

Where on the Metro 5V comes from is decided externally: it enters the
control board via the J2 (+5V) terminal block on `buffer_keyer.kicad_sch`
and is wired into the Metro's 5V header pin off-schematic (jumper wire,
or via the same terminal block ground reference). The Metro symbol does
not need a 5V pin — the symbol just hosts the ESP32-S3 GPIO routes.

### xmitter:MCP4921_DAC  (optional, secondary priority)

The standard KiCad symbol for MCP4921 is already clean (eight pins, one
function each) — no obvious gain from a replacement. Defer unless the
standard symbol turns out to mislabel something.

### xmitter:MC1496  (optional, secondary priority)

The standard KiCad MC1496 symbol uses Motorola's original pin names
(`SIG_IN+`, `SIG_IN-`, `CARRIER_IN+`, `CARRIER_IN-`, `OUT+`, `OUT-`,
`BIAS`, `V_EE`, etc.). These are descriptive enough that a custom
relabel is mostly cosmetic. Defer unless a specific clarity problem
arises during PCB layout review.

## Verification checklist before placing a custom symbol

After building a custom symbol and before replacing the stock symbol on
a schematic sheet:

- [ ] Pin numbers match the footprint pad numbers (mismatched pin
  numbers will route signals to wrong pads — silent failure visible
  only at PCB layout).
- [ ] Electrical type is set on every pin (default is `passive`, which
  defeats ERC). Power pins must be `power_in` or `power_out` so the
  ERC's "no driver" check finds them correctly.
- [ ] The symbol value field defaults to the symbol name (so the BOM
  parts-list script picks it up correctly).
- [ ] The footprint association is set in the symbol properties
  (Symbol → Properties → Footprint), so dropping it on a sheet
  auto-links to the right footprint without a separate annotation pass.

## Reference — KiCad symbol file format

A `.kicad_sym` file is a single S-expression list. The minimal valid
empty library:

```
(kicad_symbol_lib
  (version 20240101)
  (generator "xmitter_manual")
)
```

Add symbols as additional `(symbol "name" ...)` blocks within the
top-level list. For most cases use the Symbol Editor GUI rather than
hand-editing the S-expression — easier to keep pin geometry and label
positions consistent.

## Related docs

- `control_board_BOM_and_wire_plan.md` — Bill of materials and inter-board
  wiring (terminal-block assignments, off-schematic Metro 5V routing).
- `construction.md` — Chassis, panel, and mechanical assembly notes
  (Front Panel Express, SendCutSend, Protocase contacts).
- `KiCAD/xmitter.pretty/Adafruit_Si5351A_STEMMA.kicad_mod` — Existing
  precedent for project-specific footprint customization.
