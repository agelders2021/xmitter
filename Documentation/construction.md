# Construction Notes

Practical fabrication, assembly, and bench-build notes. Grows as
each phase of the build surfaces new techniques or sourcing
decisions worth remembering.

## Chassis and front-panel fabrication

### Custom CNC panel / chassis services

The clean answer for the panel and chassis cutouts on this build.
Three vendors handle one-off custom front panels and chassis
with CNC milling, laser cutting, or punching:

┌────────────────────────────┬────────────────────────────────────────────────────────────┐
│ Vendor                     │ Notes                                                      │
├────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Front Panel Express        │ German engineering (Schaeffer AG behind it). Free          │
│   (frontpanelexpress.com)  │ "Front Panel Designer" CAD tool that prices instantly      │
│                            │ as you draw. Best for engraved legends + bus-bar quality   │
│                            │ panels.                                                    │
│ SendCutSend                │ US, fast, cheap on flat sheet stock. Laser + waterjet +    │
│   (sendcutsend.com)        │ CNC. Best for chassis-style sheet metal.                   │
│ Protocase                  │ Canadian. Full enclosures, not just panels. Pricier but    │
│   (protocase.com)          │ delivers a finished metal box ready for guts.              │
└────────────────────────────┴────────────────────────────────────────────────────────────┘

What they'll machine from one drawing in a single job:

- Rectangular IEC inlet opening (mains entry)
- Round power-transformer hole (chassis mount)
- Octal / 9-pin / Magnoval tube socket holes
- Meter cutouts (round or rectangular)
- Switch / jack / encoder / display openings
- Mounting hole patterns for PCB standoffs
- Engraved or silkscreened legends (FPE only)

### Workflow advantages for this build

- Already in KiCad and documentation mode — dimensioned drawings
  are a deliverable not an extra step
- One-off pricing is often cheaper than expected (no setup fees
  on these vendors' workflows)
- Result looks **punched, not filed** — front panel quality
  matches the design effort

### Caveat — commit the layout first

You're committing the front-panel and chassis layout **before**
test-fitting the actual hardware. Implications:

- Measure tube sockets, transformer mounting hole patterns,
  meter bezels, and display bezels twice from real parts in
  hand before sending the drawing
- Build a cardboard or 3D-printed mockup of the panel and
  lay parts on it to verify clearance, ergonomics, and visual
  balance before paying for metal
- Order one panel to validate fit, **then** order a second
  identical one as production. Don't pay for two until you've
  proven the first one works.

### Open items

- [ ] Pick the vendor (Front Panel Express for the front panel,
      SendCutSend for the chassis if separating; or Protocase
      for an integrated enclosure)
- [ ] Decide on chassis material — aluminum sheet (lighter,
      easier to drill if anything needs adjusting) vs steel
      (more rigid, classic ham-shack look)
- [ ] Front-panel finish — brushed natural aluminum, anodized
      black, painted. Affects how engraved legends contrast
- [ ] Lock in the panel layout drawing before sending

## Electronics-in-a-separate-box strategy

Decision (2026-07-09): the control PCB (MC1496 keyer, MCP4921
envelope DAC, Si5351 VFO, MCP4728 quad DAC, PCF8575 expander,
Metro ESP32-S3) does **not** go inside the main chassis with the
high-power RF stages. It gets its own small metal box mounted on
top of the main chassis, and signals cross the gap through
bulkhead BNC connectors on both boxes.

### Why the two-box split

- Keeps the Metro's WiFi / BT, USB, and digital-switching noise
  out of the PA field
- Keeps the driver + PA harmonics out of the MCP4921 DAC and
  cathode monitor ADC path
- Keeps the Si5351 VFO out of PA proximity (RF pickup on the
  reference clock would show up as spurs at the transmitter
  output)
- Standard practice in commercial tube-transmitter design —
  the control section is always a separate compartment behind
  its own shielding
- Also better for service — the control box lifts off for firmware
  debugging without opening the HV compartment

### Signal chain from PCB to driver tubes

Push-pull modulated RF (MOD_RF_OUT+ / MOD_RF_OUT−) exits the
PCB near the MC1496 output and reaches the 12HG7 driver grids
via this path:

- PCB header pin at TP2 / TP3 area (replace the raw test-point
  posts with proper 0.025" square header pins or Keystone
  5000-series test-point sockets so the jumper wire has a
  mechanical anchor)
- Short (~5-10 cm) shielded twisted pair inside the control
  box to a bulkhead BNC on the control-box wall. Shield
  grounded at the PCB end.
- External BNC-BNC coax (RG-174 or RG-316, 15-30 cm) between
  the control-box bulkhead and a matching bulkhead BNC on the
  main-chassis wall. Shield grounded at **both** ends.
- Inside the main chassis: shielded twisted pair from the
  bulkhead BNC to the driver-grid resistors.

Signal amplitude out of the MC1496 is several volts p-p, so
connector losses and modest impedance mismatches are not
audible in the RF path. The mechanical and RF-shielding
integrity of the connectors matters more than their nominal
impedance rating.

### Why BNC (not RCA, SMA, or PL-259)

- BNC bayonet lock won't vibrate loose the way an RCA phono
  center pin can; a slightly loose RCA on one of the two
  push-pull channels flips the balance and puts carrier leakage
  through the MC1496
- BNC is defined-50-Ω where RCA is not — matters less at HF
  than it does at VHF+, but the discipline helps
- SMA is overkill at 14 MHz and its torque requirements make
  service harder
- PL-259 / SO-239 is too physically large for a low-level
  interconnect between two small compartments — save it for
  the antenna port

Suggested part: **Amphenol RF 112404** (right-angle PCB / panel
BNC, 4 GND posts + signal pin, ~$4-5 at Mouser / Digikey,
matches KiCad footprint
`Connector_Coaxial:BNC_Amphenol_112404_Horizontal`). Buy 6+
for two channels + spares.

### Balance and matching between the two push-pull channels

For CW carrier suppression through the MC1496 balanced mixer,
the two channels **must** be electrically matched:

- Identical cable length on MOD_RF_OUT+ and MOD_RF_OUT−
- Identical connector types on both channels
- Identical routing (same-side jumpers inside the control box,
  same-side runs inside the main chassis)

Amplitude or phase mismatch between the two channels shows up
as an audible carrier tone during key-down that should not be
there. Balance the channels physically before blaming the
mixer or trying to null it in firmware.

### Grounding scheme summary

- Control-box chassis and main chassis ground are bonded by the
  BNC shield of the interconnect cable at both bulkheads. The
  two enclosures become one continuous Faraday cage split by a
  small gap.
- Inside each box, all local grounds (PCB ground, tube-socket
  ground, transformer secondary center-tap, meter neutrals)
  return to the local chassis at a single star point per box.
- The two star points are connected through the coax shield,
  not through a separate heavy ground strap that would create a
  ground loop at 60 Hz.
- Safety earth (green wire from IEC inlet) bonds only to the
  main chassis (which holds the HV). The control box picks up
  safety earth through the coax shield and any DC-supply
  ground return.

### Open items — two-box construction

- [ ] Pick the control-box enclosure — small aluminum diecast
      (Hammond 1590-series) vs. sheet-metal card cage. Diecast
      wins on shielding, sheet metal wins on internal access
      and mounting flexibility.
- [ ] Confirm bulkhead-BNC panel-cut diameter and grounding
      washer / lock nut against the chosen enclosure metal
      thickness
- [ ] Verify TP2 / TP3 PCB footprints are compatible with 0.025"
      square header pins before assembly (may need to widen the
      drills on the current test-point pads or add a proper
      2-pin header on the next PCB revision)
- [ ] Route the external BNC-BNC coax so it's mechanically
      captive (cable tie or clamp to chassis) — the leverage
      arm on a floating cable + connector will fatigue the
      solder joints over time
