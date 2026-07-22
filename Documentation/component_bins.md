# xmitter component bins  —  24-bin allocation

Total: **152 components across 42 unique part numbers, 24 bins.**

**Sources:**  `KiCAD/analog` (+ `arduino`, `buffer_keyer`, `vfo`, `interface`),
`KiCAD/bias`, `KiCAD/frontpanel`.

**Excludes:**  Adafruit breakouts, Metro carrier, LCD module, encoders.

**Companion CSVs:**
  - `Documentation/component_inventory.csv`  —  full detail, 42 rows
  - `Documentation/component_bins.csv`       —  bin allocation, 24 rows


## Resistors  (8 bins)

┌─────┬────────────────────────────────────────────────────────────────────────┬─────┐
│ Bin │ Contents                                                               │ Qty │
├─────┼────────────────────────────────────────────────────────────────────────┼─────┤
│  1  │ R < 100 Ω  —  0R×1, 10R×1, 50R×1, 51R×3, 62R×2                         │  8  │
│  2  │ R 100 – 999 Ω  —  120R×4, 200R×1, 240R×1, 270R×1                       │  7  │
│  3  │ R 1 k – 3.3 kΩ  —  1k×2, 1.5k×1, 2k×1, 2.2k×3, 2.7k×2                  │  9  │
│  4  │ R 3.3 k – 10 kΩ (excl 10k)  —  3.9k×2, 4.7k×2, 6.8k×1, 7.5k×2, 8.2k×4  │ 11  │
│  5  │ R 10 kΩ  (dedicated)                                                   │ 10  │
│  6  │ R 10.1 k – 100 kΩ  —  22k×4, 27k×1, 30k×2                              │  7  │
│  7  │ R > 100 kΩ  —  100k×3, 170k×2, 330k×2, 470k×3                          │ 10  │
│  8  │ R potentiometer  —  10 k trim                                          │  1  │
└─────┴────────────────────────────────────────────────────────────────────────┴─────┘


## Capacitors  (6 bins)

┌─────┬────────────────────────────────────────────────────────────────────────┬─────┐
│ Bin │ Contents                                                               │ Qty │
├─────┼────────────────────────────────────────────────────────────────────────┼─────┤
│  9  │ C ceramic  ≤ 1 nF (pF range)  —  220pF×2, 330pF×1, 390pF×2             │  5  │
│ 10  │ C ceramic  1 nF – 100 nF (excl 100n)  —  1nF×2, 10nF×2                 │  4  │
│ 11  │ C ceramic  100 nF (0.1 µF, dedicated)                                  │ 39  │
│ 12  │ C ceramic  > 100 nF (0.33 µF – 1 µF)  —  330nF×4, 680nF×1, 1µF×4       │  9  │
│ 13  │ C electrolytic  ≤ 1 µF  —  1µF×2                                       │  2  │
│ 14  │ C electrolytic  ≥ 10 µF  —  10µF×19, 100µF×1                           │ 20  │
└─────┴────────────────────────────────────────────────────────────────────────┴─────┘


## Semiconductors  —  bagged & labeled  (2 bins)

┌─────┬────────────────────────────────────────────────────────────────────────┬─────┐
│ Bin │ Contents                                                               │ Qty │
├─────┼────────────────────────────────────────────────────────────────────────┼─────┤
│ 15  │ Q transistors + FETs (bagged)  —  2N7000×9, J310×1                     │ 10  │
│ 16  │ U op-amps + LM393 (bagged)  —  LM393×3, LM7171×2, OPA1641×2, OPA454×4  │ 11  │
└─────┴────────────────────────────────────────────────────────────────────────┴─────┘


## Individual ICs  —  one bin each  (8 bins)

┌─────┬──────────────┬──────────────────────────────────────────────┬─────┐
│ Bin │ Part         │ Description                                  │ Qty │
├─────┼──────────────┼──────────────────────────────────────────────┼─────┤
│ 17  │ AM26LS32ACN  │ RS-422 quad differential receiver            │  1  │
│ 18  │ CD14538B     │ dual monostable multivibrator                │  1  │
│ 19  │ ICL7660S     │ charge-pump voltage inverter                 │  1  │
│ 20  │ L79L08       │ −8 V linear regulator (TO-92)                │  1  │
│ 21  │ LM4040LP-5   │ 5 V shunt voltage reference                  │  1  │
│ 22  │ LM7805       │ +5 V linear regulator (TO-220)               │  2  │
│ 23  │ MC1496       │ double-balanced modulator / keyer            │  1  │
│ 24  │ MCP4921      │ 12-bit SPI DAC (envelope keyer)              │  1  │
└─────┴──────────────┴──────────────────────────────────────────────┴─────┘


## Summary

┌──────────────────────────┬─────────┬────────────┐
│ Category                 │   Bins  │  Total pcs │
├──────────────────────────┼─────────┼────────────┤
│ Resistors                │  1 – 8  │         63 │
│ Capacitors               │  9 – 14 │         79 │
│ Semiconductors (bag)     │ 15 – 16 │         21 │
│ Individual ICs           │ 17 – 24 │          9 │
│ Grand total              │    24   │        152 │
└──────────────────────────┴─────────┴────────────┘


## Notes

  - Dedicated bins for the four highest-count values (100 nF ceramic,
    10 µF electrolytic, 10 kΩ resistor, 2N7000 FET) so the most-grabbed
    parts have their own home.

  - Bins 15 and 16 hold anti-static bags with per-part labels *inside*
    a single bin; the bag label tells you which part in the group you have.

  - **100 nF ceramic count is high (39 pcs)**  —  order 50+ to have
    working spares.  Same for 10 µF electrolytic (19 pcs, order 25+) and
    10 kΩ resistor (10 pcs, order 20+).

  - The following `Value` fields leaked their footprint/pin info into
    the value string and could be cleaned up in the schematics (cosmetic,
    does not affect the bin sort):
       - `LM7171_xIN`   →  `LM7171`
       - `L79L08_TO92`  →  `L79L08`     (put TO-92 in the Footprint field)
       - `LM7805_TO220` →  `LM7805`     (put TO-220 in the Footprint field)
