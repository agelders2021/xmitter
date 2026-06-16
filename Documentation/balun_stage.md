# Balun Stage — Current State

A 6:1 impedance ratio balun converts the PA's 300 Ω balanced
output to a 50 Ω unbalanced output for the output LPF, coax run,
and external ATU.

Source of truth: `xmitter_prj/Balun_6to1_subcircuit.sch`.

## Block diagram

```
PA link winding (L6)                            Output LPF input
                                                (50 Ω)
[PA OUT_HOT ] ────┐                       ┌──── [out]
                  │  primary      secondary
                  │  LP 14 µH     LS 2.33 µH
                  │  k ≈ 0.95
[PA OUT_COLD] ────┴── R1 (0.5 Ω) ──── GND ─┐
                       (sim convenience;    │
                       omit in hardware)    │
                                            └── GND
```

Two-winding voltage step-down transformer. Primary is the
differential PA output (driven push-pull from the PA link
winding L6); secondary is single-ended to the LPF input. Turns
ratio for 6:1 impedance is √6 ≈ 2.45 (voltage ratio).

## Component values

┌──────┬─────────┬──────────────────────────────────────────────┐
│ Ref  │ Value   │ Role                                         │
├──────┼─────────┼──────────────────────────────────────────────┤
│ LP   │ 14 µH   │ Primary winding (differential PA load)       │
│ LS   │ 2.33 µH │ Secondary winding (50 Ω to LPF)              │
│ R1   │ 0.5 Ω   │ Series stability resistor — sim only         │
└──────┴─────────┴──────────────────────────────────────────────┘

R1 is a simulation convenience that breaks the singular-matrix
between LP and the PA's L6 (both inductors between the same
two nodes at DC). Omit in hardware; the transformer's own
resistive losses cover the same role.

LP / LS inductance ratio = 14 / 2.33 = 6.01, confirming the
6:1 impedance ratio.

## Core: FT82-43 with 5+2 turns

**Core**: FT82-43 (Fair-Rite type 43 NiZn ferrite, 0.82" OD,
AL ≈ 510 nH/t²).

**Windings**:

┌──────────────┬─────────────┬────────────────────────────────┐
│ Winding      │ Turns       │ Resulting L                    │
├──────────────┼─────────────┼────────────────────────────────┤
│ Primary LP   │ 5 turns     │ 5² × 510 = 12.75 µH (target 14)│
│ Secondary LS │ 2 turns     │ 2² × 510 = 2.04 µH (target 2.33)│
└──────────────┴─────────────┴────────────────────────────────┘

The slight inductance shortfall (~10 %) is within the bandpass
tolerance for a broadband transformer at 14.2 MHz; no retune
needed. If bench measurement of insertion loss is high, add
one more turn to each winding and recheck.

**Winding technique**:

- Wind primary as a bifilar pair: 5 turns of two parallel wires
  spread evenly around the core. Connect the end of wire A to
  the start of wire B for the center tap. Start and finish of
  the pair are the two PA output connections.
- Wind secondary as 2 turns single, overlaid on the primary.
- Single-end the secondary by tying one end to GND, taking
  output from the other end.

The larger FT114-43 core was considered but doesn't land cleanly
on these inductance targets at integer turn counts. FT82-43 is
the right choice.

## Wire gauge

The balun carries ~1 A RMS at 50 W output into 50 Ω. The
project's single-gauge #22 AWG plan handles this with margin,
but for the balun specifically, **#18-20 AWG** is preferable:

- Lower I²R losses (efficiency)
- Better thermal headroom for extended key-down
- Standard practice for QRO balun construction

This is the one place in the project where a third wire gauge
is worth keeping in inventory. A few feet of #18 enameled
covers the balun and the PA-board parasitic-suppressor coils.

## Power dissipation

At 50 W RF into the balun primary, with FT82-43 ferrite at
14 MHz:

┌──────────────────────────┬──────────────────────────────────────┐
│ Loss mechanism           │ Estimate                             │
├──────────────────────────┼──────────────────────────────────────┤
│ Wire I²R (primary)       │ ~150 mW at 1 A RMS × short R         │
│ Wire I²R (secondary)     │ ~250 mW at 1 A × short secondary R   │
│ Core hysteresis loss     │ ~500 mW for FT82-43 at 14 MHz / 50 W │
│ Total                    │ ~1 W                                 │
└──────────────────────────┴──────────────────────────────────────┘

Efficiency: ~98 % (50 W in, ~49 W out). Comfortable for sustained
key-down operation; no auxiliary cooling needed.

## Open question

### Common-mode choking on the antenna coax

A separate 1:1 current choke (often called a "line isolator")
on the coax run between the balun output and the external ATU
prevents common-mode RF on the coax shield from flowing back
into the shack. Standard practice but not strictly part of
this stage's build. Defer to RF-bench tuning to decide if
needed; typical solution is a clip-on ferrite (Mix 31 or 43)
on the coax, or a few turns of coax through a large toroid.

## What is NOT in this stage

- The PA's plate tank and link winding L6 are upstream — see
  `PA_stage.md`
- The 5-pole LPF is downstream — see `LPF_stage.md`
- The external ATU is downstream of the LPF and is not part of
  the project build
- An optional common-mode choke on the antenna coax (see open
  question above) is not in the simulation

## References

- `xmitter_prj/Balun_6to1_subcircuit.sch` — current simulation
- `Documentation/PA_stage.md` — upstream PA and tank circuit
- `Documentation/LPF_stage.md` — downstream output filter
