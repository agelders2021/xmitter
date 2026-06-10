"""Post-process QUCS-S grid_bias.cir to produce a working DC sweep.

Run between QUCS-S 'Save' and ngspice. Patches three problems QUCS-S
produces from the grid_bias.sch as currently drawn:

  1. If `XX1  OPA454_5PIN` has no nodes, fill in the inferred
     connections (rare now that the symbol uses 'auto' template).

  2. If R_F (170k feedback) is wired between _net0 (+ input) and _net4
     (output) -- which is positive feedback -- move it to _net1
     (- input).

  3. Rewrite the .control block to do a real DC sweep of V_DAC
     across 0..3.3V and write a spice4qucs.dc1.plot rawfile that
     gui_plot can read. (QUCS-S's .SW alone produces just `op`.)

Usage:
    python fix_grid_bias.py
    -> writes grid_bias_patched.cir alongside grid_bias.cir
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "grid_bias.cir"
DST = HERE / "grid_bias_patched.cir"

if not SRC.exists():
    sys.exit(f"Not found: {SRC}")

text = SRC.read_text()

# (1) Fill in XX1 nodes if missing.
text = re.sub(
    r'^XX1\s+OPA454_5PIN\s*$',
    'XX1 _net0 _net1 _net2 _net3 _net4 OPA454_5PIN',
    text,
    flags=re.MULTILINE,
)

# (2) Catch any 170k resistor wired between _net0 and _net4 (positive
# feedback) and move to _net1 (negative input).
text = re.sub(
    r'^(R\w+)\s+_net0\s+_net4\s+170K\b',
    r'\1 _net1 _net4 170K',
    text,
    flags=re.MULTILINE,
)
text = re.sub(
    r'^(R\w+)\s+_net4\s+_net0\s+170K\b',
    r'\1 _net4 _net1 170K',
    text,
    flags=re.MULTILINE,
)

# (3) Replace any .control block (and drop any preceding QUCS-S
# simulation directives we don't want) with a proper DC sweep that
# writes a rawfile. Sweep V_DAC if it's a parameter, otherwise sweep
# VDAC source directly.

is_parameterized = bool(re.search(r'\.PARAM\s+V_DAC\s*=', text, flags=re.IGNORECASE))

if is_parameterized:
    sweep_line = ".DC V_DAC 0 3.3 0.05"
else:
    sweep_line = ".DC VDAC 0 3.3 0.05"

control_block = f"""
{sweep_line}

.control
run
write spice4qucs.dc1.plot v(_net0) v(_net1) v(_net4)
destroy all
reset
exit
.endc
"""

# Strip any existing .control ... .endc and replace
text = re.sub(
    r'\.control[\s\S]*?\.endc\s*',
    '',
    text,
    flags=re.IGNORECASE,
)
# Also strip any pre-existing .DC / .AC / .TR directives outside .control
text = re.sub(r'^\.DC[^\n]*\n', '', text, flags=re.MULTILINE | re.IGNORECASE)

# Insert sweep + control block right before .END
text = re.sub(
    r'(\n\.END\s*$)',
    f'\n{control_block.strip()}\n\\1',
    text,
    flags=re.IGNORECASE,
)

DST.write_text(text)
print(f"Wrote {DST}")
print(f"V_DAC sweep: parameterized={is_parameterized}")
print(f"Sweep line:  {sweep_line}")
print(f"Run with: ngspice -b {DST.name}")
