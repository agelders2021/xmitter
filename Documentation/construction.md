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
