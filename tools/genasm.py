#!/usr/bin/env python3
"""Εξάγει σε assembly ό,τι πρέπει να είναι ΤΑΥΤΟΣΗΜΟ με το μοντέλο φυσικής.

    python3 tools/genasm.py

Παράγει:
    src/tables.asm      πίνακες γεωμετρίας βαρύτητας (GTAB/RTAB/βήματα)
    src/level_test.asm  το δοκιμαστικό δωμάτιο + γραφικά tiles σε MODE 1

Οι πίνακες ΔΕΝ ξαναϋπολογίζονται εδώ: διαβάζονται από το tools/physics.py, που
είναι το επαληθευμένο μοντέλο. Έτσι ο Z80 και η προσομοίωση δεν μπορούν να
αποκλίνουν — αν αλλάξει το μοντέλο, αρκεί να ξανατρέξει αυτό.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROW = 32            # εγγραφές ανά γραμμή πίνακα (64 bytes) — δύναμη του 2 ώστε
                    # ο δείκτης στον Z80 να είναι μόνο ολισθήσεις
RTAB_OFF = 16       # a  = -16..15
GTAB_OFF = 15       # b  = -15..16


def sb(v):
    """Προσημασμένο byte για db."""
    return v & 0xFF


def tables_asm():
    out = [";" + "=" * 69,
           ";  GRAVASSIST — πίνακες γεωμετρίας βαρύτητας",
           ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py — ΜΗΝ το επεξεργάζεσαι.",
           ";",
           ";  Το μοντέλο αναφοράς είναι tools/physics.py. Κάθε γραμμή είναι",
           f";  {ROW} ζεύγη (dx,dy) = {ROW*2} bytes, ώστε ο δείκτης να είναι g*{ROW*2}.",
           ";" + "=" * 69,
           "",
           f"TAB_ROW         equ {ROW*2}",
           f"RTAB_OFF        equ {RTAB_OFF}",
           f"GTAB_OFF        equ {GTAB_OFF}",
           ""]

    out.append("; RTAB[g][a+16] — μετατόπιση a pixel ΚΑΘΕΤΑ στη βαρύτητα")
    out.append("rtab:")
    for g in range(8):
        vals = []
        for i in range(ROW):
            a = i - RTAB_OFF
            if -P.RSPAN <= a <= P.RSPAN:
                dx, dy = P.RTAB[g][a + P.RSPAN]
            else:
                dx = dy = 0                       # εκτός εύρους: δεν χρησιμοποιείται
            vals += [dx, dy]
        out.append(f"                ; g={g}")
        for i in range(0, len(vals), 16):
            out.append("                db " + ",".join(str(sb(v)) for v in vals[i:i+16]))

    out.append("")
    out.append("; GTAB[g][b+15] — μετατόπιση b pixel ΚΑΤΑ τη βαρύτητα")
    out.append("gtab:")
    for g in range(8):
        vals = []
        for i in range(ROW):
            b = i - GTAB_OFF
            dx, dy = P.GTAB[g][b + P.GSPAN]
            vals += [dx, dy]
        out.append(f"                ; g={g}")
        for i in range(0, len(vals), 16):
            out.append("                db " + ",".join(str(sb(v)) for v in vals[i:i+16]))

    out.append("")
    out.append("; Βήμα ενός pixel κατά / κάθετα στη βαρύτητα")
    out.append("gstep:          db " + ",".join(
        f"{sb(P.GSTEP[g][0])},{sb(P.GSTEP[g][1])}" for g in range(8)))
    out.append("rstep:          db " + ",".join(
        f"{sb(P.RSTEP[g][0])},{sb(P.RSTEP[g][1])}" for g in range(8)))
    out.append("")
    out.append("; Η φορά βαρύτητας που 'στέκεται' πάνω σε κάθε τύπο κελιού.")
    out.append("; #FF = το κελί δεν επιβάλλει φορά (κενό ή επίπεδο στερεό).")
    rg = [255, 255] + [P.RAMP_GRAVITY[t] for t in
                       (P.RAMP_DR, P.RAMP_DL, P.RAMP_UR, P.RAMP_UL)]
    out.append("ramp_grav:      db " + ",".join(str(v) for v in rg))
    out.append("")
    return "\n".join(out)


# --- Γραφικά tiles σε MODE 1 -----------------------------------------
PEN_BODY, PEN_EDGE = 2, 3


def tile_pixels(t):
    """8x8 pixels (pen ανά θέση) για κάθε τύπο κελιού."""
    g = [[0] * 8 for _ in range(8)]
    if t == P.EMPTY:
        return g
    for v in range(8):
        for u in range(8):
            if t == P.SOLID:
                inside = True
            else:
                inside = P.RAMP_TEST[t](u, v)
            if not inside:
                continue
            # ακμή = pen3 όπου το γειτονικό pixel είναι έξω από το υλικό
            edge = False
            for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nu, nv = u + du, v + dv
                if not (0 <= nu < 8 and 0 <= nv < 8):
                    continue
                out = not (True if t == P.SOLID else P.RAMP_TEST[t](nu, nv))
                edge = edge or out
            if t == P.SOLID:
                edge = v == 0 or v == 7 or u == 0 or u == 7
            g[v][u] = PEN_EDGE if edge else PEN_BODY
    return g


def pack_mode1(row8):
    """8 pixels -> 2 bytes MODE 1 (bit 7-s = pen bit0, bit 3-s = pen bit1)."""
    out = []
    for half in (0, 4):
        b = 0
        for s in range(4):
            pen = row8[half + s]
            if pen & 1:
                b |= 1 << (7 - s)
            if pen & 2:
                b |= 1 << (3 - s)
        out.append(b)
    return out


def level_asm(room):
    out = [";" + "=" * 69,
           ";  GRAVASSIST — δοκιμαστικό δωμάτιο και γραφικά tiles",
           ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py (πηγή: levels/test.txt)",
           ";" + "=" * 69,
           "",
           f"LVL_COLS        equ {P.COLS}",
           f"LVL_ROWS        equ {P.ROWS}",
           f"LVL_CELL        equ {P.CELL}",
           f"LVL_Y0          equ {P.GRID_Y0}",
           "",
           "; Γραφικά: 6 τύποι x 8 γραμμές x 2 bytes = 96 bytes (MODE 1)",
           "tile_gfx:"]
    for t in range(6):
        px = tile_pixels(t)
        name = {0: "EMPTY", 1: "SOLID", 2: "RAMP_DR",
                3: "RAMP_DL", 4: "RAMP_UR", 5: "RAMP_UL"}[t]
        out.append(f"                ; {t} {name}")
        for v in range(8):
            a, b = pack_mode1(px[v])
            out.append(f"                db #{a:02X},#{b:02X}")

    out.append("")
    out.append(f"; Δωμάτιο: 1 byte ανά κελί, {P.COLS}x{P.ROWS} = {P.COLS*P.ROWS} bytes")
    out.append("level_data:")
    for r in range(P.ROWS):
        row = room.cells[r]
        out.append("                db " + ",".join(str(v) for v in row))
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    room = P.load_room()
    for name, text in (("src/tables.asm", tables_asm()),
                       ("src/level_test.asm", level_asm(room))):
        path = os.path.join(ROOT, name)
        with open(path, "w") as f:
            f.write(text)
        print(f"  {name}: {len(text.splitlines())} γραμμές")
