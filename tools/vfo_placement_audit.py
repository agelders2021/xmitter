"""VFO placement deep-dive audit."""
import io
import math
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PCB = r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\KiCAD.kicad_pcb"
SCH = r"C:\Users\AlAnd\Git Backed Projects\xmitter\KiCAD\KiCAD.kicad_sch"


def find_balanced(text, i0):
    depth = 0
    i = i0
    BS = chr(92)
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == BS:
                    i += 2
                else:
                    i += 1
            i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i0, i + 1
        i += 1


def rotate(lx, ly, deg):
    th = math.radians(deg)
    return (lx * math.cos(th) - ly * math.sin(th),
            lx * math.sin(th) + ly * math.cos(th))


with open(PCB, "r", encoding="utf-8") as f:
    pcb = f.read()
with open(SCH, "r", encoding="utf-8") as f:
    sch = f.read()

vfo_uuid = None
for m in re.finditer(r"\(sheet\s+(.*?)\n\t\)\n", sch, re.DOTALL):
    if re.search(r'\(property\s+"Sheetname"\s+"VFO"', m.group(1)):
        vfo_uuid = re.search(r'\(uuid\s+"([^"]+)"', m.group(1)).group(1)

edge_xs, edge_ys = [], []
for m in re.finditer(
    r'\(gr_(?:line|rect)\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)(?:.*?)\(layer\s+"Edge\.Cuts"\)',
    pcb, re.DOTALL,
):
    edge_xs += [float(m.group(1)), float(m.group(3))]
    edge_ys += [float(m.group(2)), float(m.group(4))]
bx0, bx1, by0, by1 = min(edge_xs), max(edge_xs), min(edge_ys), max(edge_ys)

foots = {}
foot_pads = {}
i = 0
while True:
    j = pcb.find("(footprint ", i)
    if j < 0:
        break
    s, e = find_balanced(pcb, j)
    block = pcb[s:e]
    rm = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    am = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", block)
    pm = re.search(r'\(path\s+"([^"]+)"', block)
    if rm and am and pm and vfo_uuid in pm.group(1):
        ref = rm.group(1)
        foots[ref] = {
            "x": float(am.group(1)),
            "y": float(am.group(2)),
            "rot": float(am.group(3)) if am.group(3) else 0.0,
        }
        pads = []
        for pd in re.finditer(
            r'\(pad\s+"([^"]*)"\s+(\S+)\s+\S+\s+\(at\s+([-\d.]+)\s+([-\d.]+)', block
        ):
            pads.append((pd.group(1), pd.group(2), float(pd.group(3)), float(pd.group(4))))
        foot_pads[ref] = pads
    i = e

print(f"Board outline: X=[{bx0:.2f}, {bx1:.2f}]  Y=[{by0:.2f}, {by1:.2f}]")
print(f"VFO components: {len(foots)}\n")

# ---- pads on-board ----
print("=== 1. All pads on-board ===")
offboard = []
for ref, f in foots.items():
    for name, ptype, lx, ly in foot_pads[ref]:
        rx, ry = rotate(lx, ly, f["rot"])
        gx, gy = f["x"] + rx, f["y"] + ry
        on = bx0 <= gx <= bx1 and by0 <= gy <= by1
        if not on:
            offboard.append((ref, name, gx, gy))
if offboard:
    for r, n, gx, gy in offboard:
        print(f"    {r} pad '{n}' at ({gx:.2f}, {gy:.2f}) OFF BOARD")
else:
    print("    All VFO pads on-board")

# ---- positions ----
print(f"\n=== 2. Placement ===")
for ref in sorted(foots.keys()):
    f = foots[ref]
    print(f"  {ref:8s} @ ({f['x']:7.2f}, {f['y']:7.2f}) rot={f['rot']:6.1f}")

# ---- U1 pad positions ----
u1 = foots.get("U1")
if u1:
    print(f"\n=== 3. U1 named pad positions ===")
    for pad_name in ("VIN", "GND", "SDA", "SCL", "CLK0", "CLK1", "CLK2"):
        for name, ptype, lx, ly in foot_pads["U1"]:
            if name == pad_name:
                rx, ry = rotate(lx, ly, u1["rot"])
                print(f"  U1 {pad_name:5s} @ ({u1['x']+rx:7.2f}, {u1['y']+ry:7.2f})")
                break

# ---- toroids ----
print("\n=== 4. Toroids ===")
if all(k in foots for k in ("L2", "L4", "L6")):
    for L in ("L2", "L4", "L6"):
        f = foots[L]
        print(f"  {L}: ({f['x']:.2f}, {f['y']:.2f}) rot={f['rot']:.0f} deg")
    d12 = math.sqrt((foots["L4"]["x"] - foots["L2"]["x"]) ** 2 + (foots["L4"]["y"] - foots["L2"]["y"]) ** 2)
    d46 = math.sqrt((foots["L6"]["x"] - foots["L4"]["x"]) ** 2 + (foots["L6"]["y"] - foots["L4"]["y"]) ** 2)
    print(f"  L2-L4 c-c: {d12:.1f} mm  (edge-edge {d12-17.3:.1f} mm)")
    print(f"  L4-L6 c-c: {d46:.1f} mm  (edge-edge {d46-17.3:.1f} mm)")

# ---- routing counts ----
print("\n=== 5. Trace segments per net ===")
nets = {}
for m in re.finditer(r'\(net\s+(\d+)\s+"([^"]*)"', pcb):
    nets[m.group(1)] = m.group(2)

segs = {}
for m in re.finditer(r"\(segment\b(?:[^()]*|\([^()]*\))*\)", pcb):
    seg = m.group(0)
    nm = re.search(r"\(net\s+(\d+)\)", seg)
    if nm:
        segs[nm.group(1)] = segs.get(nm.group(1), 0) + 1

vias = 0
for m in re.finditer(r"\(via\b", pcb):
    vias += 1
print(f"  Total vias in PCB: {vias}")

vfo_related = ("CLK0", "CLK2", "RAW_RF", "3V3", "GND", "RAW_RF_OUT")
for nn, name in nets.items():
    if any(k in name for k in vfo_related):
        n_segs = segs.get(nn, 0)
        print(f"  net #{nn} '{name}': {n_segs} routed segments")

# ---- signal chain (CLK2 -> ... -> TP1) ----
print("\n=== 6. Signal chain distances (CLK2 based) ===")
clk2 = None
clk0 = None
for name, ptype, lx, ly in foot_pads.get("U1", []):
    if name == "CLK2":
        rx, ry = rotate(lx, ly, u1["rot"])
        clk2 = (u1["x"] + rx, u1["y"] + ry)
    elif name == "CLK0":
        rx, ry = rotate(lx, ly, u1["rot"])
        clk0 = (u1["x"] + rx, u1["y"] + ry)

def refpos(r):
    if r in foots:
        return (foots[r]["x"], foots[r]["y"])
    return None

chain = [
    ("U1 CLK2", clk2),
    ("RS1", refpos("RS1")),
    ("C_IN1", refpos("C_IN1")),
    ("RP1", refpos("RP1")),
    ("RP2", refpos("RP2")),
    ("RP3", refpos("RP3")),
    ("CF1", refpos("CF1")),
    ("L2", refpos("L2")),
    ("CF3", refpos("CF3")),
    ("L4", refpos("L4")),
    ("CF5", refpos("CF5")),
    ("L6", refpos("L6")),
    ("CF7", refpos("CF7")),
    ("Q1", refpos("Q1")),
    ("CC1", refpos("CC1")),
    ("RT1", refpos("RT1")),
    ("TP1", refpos("TP1")),
]
total = 0
prev_name, prev_p = None, None
for name, p in chain:
    if prev_p and p:
        d = math.sqrt((p[0]-prev_p[0])**2 + (p[1]-prev_p[1])**2)
        total += d
        marker = "" if d < 20 else "  *long*"
        print(f"  {prev_name:12s} -> {name:12s}  d = {d:6.2f} mm {marker}")
    prev_name, prev_p = name, p
print(f"  Total chain: {total:.1f} mm")

# ---- CLK0 vs CLK2 short trace comparison ----
print("\n=== 7. CLK0 vs CLK2 to nearest downstream ===")
if clk2 and clk0:
    print(f"  CLK2 pad @ ({clk2[0]:.2f}, {clk2[1]:.2f})")
    print(f"  CLK0 pad @ ({clk0[0]:.2f}, {clk0[1]:.2f})")
    for tgt in ("RS1", "C_IN1"):
        p = refpos(tgt)
        if p:
            d2 = math.sqrt((clk2[0]-p[0])**2 + (clk2[1]-p[1])**2)
            d0 = math.sqrt((clk0[0]-p[0])**2 + (clk0[1]-p[1])**2)
            print(f"    CLK2 -> {tgt}: {d2:5.2f} mm    CLK0 -> {tgt}: {d0:5.2f} mm    (saved {d0-d2:.2f} mm)")
