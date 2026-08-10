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
    # ΟΛΟΙ οι τύποι, όχι μόνο οι 6 της γεωμετρίας: το h_align δεικτοδοτεί
    # αυτόν τον πίνακα με τον τύπο κελιού, που πλέον φτάνει το 25.
    rg = [P.RAMP_GRAVITY.get(i, 255) for i in range(P.NTYPES)]
    out.append("ramp_grav:      db " + ",".join(str(v) for v in rg))
    out.append("")
    return "\n".join(out)


# --- Γραφικά tiles σε MODE 1 -----------------------------------------
PEN_BODY, PEN_EDGE = 2, 3


# Ο κάθε τύπος παιχνιδιού δανείζεται το placeholder γραφικό του. Οι τέσσερις
# στροφές των αγκαθιών και των μονόδρομων παράγονται με ακριβή περιστροφή 90.
PLACEHOLDER = {
    P.EXIT: ("EXIT", 0), P.ENERGY: ("ENERGY", 0), P.PARACHUTE: ("PARACHUTE", 0),
    P.LOCK_OPEN: ("LOCK", 0, True),   # η "ενεργή" εκδοχή του placeholder
    P.KEY: ("KEY", 0), P.LOCK: ("LOCK", 0), P.GATE: ("GATE", 0),
    P.SWITCH: ("SWITCH", 0), P.PLATE: ("PLATE", 0), P.TELEPORT: ("TELEPORT", 0),
    P.CRATE: ("CRATE", 0), P.CRUMBLE: ("CRUMBLE", 0), P.GRAVLOCK: ("GRAVLOCK", 0),
    P.SPIKE_U: ("SPIKES", 0), P.SPIKE_L: ("SPIKES", 1),
    P.SPIKE_D: ("SPIKES", 2), P.SPIKE_R: ("SPIKES", 3),
    P.ONEWAY_U: ("ONEWAY", 0), P.ONEWAY_L: ("ONEWAY", 1),
    P.ONEWAY_D: ("ONEWAY", 2), P.ONEWAY_R: ("ONEWAY", 3),
}


def rot90(g, times):
    """Περιστροφή 8x8 κατά 90 δεξιόστροφα, `times` φορές. Ακριβής."""
    for _ in range(times % 4):
        g = [[g[7 - x][y] for x in range(8)] for y in range(8)]
    return g


def tile_pixels(t):
    """8x8 pixels (pen ανά θέση) για κάθε τύπο κελιού."""
    g = [[0] * 8 for _ in range(8)]
    if t in (P.EMPTY, P.START):     # ο δείκτης εκκίνησης δεν ζωγραφίζεται ποτέ
        return g
    if t in PLACEHOLDER:
        import placeholders
        entry = PLACEHOLDER[t]
        name, turns = entry[0], entry[1]
        active = entry[2] if len(entry) > 2 else False
        return rot90(placeholders._frame(name, active), turns)
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


START_ROOM = None       # ορίζεται από --start· αλλιώς η πρώτη αίθουσα


def defs_asm(rooms=()):
    """Κωδικοί τύπων και μεγέθη παιχνιδιού.

    Χωριστό αρχείο επειδή πρέπει να μπει ΠΡΩΤΟ στο main.asm: το `ds` για τους
    buffers χρειάζεται τις τιμές ήδη από το πρώτο πέρασμα του assembler.
    """
    out = [";" + "=" * 69,
           ";  GRAVASSIST — κωδικοί τύπων κελιού και μεγέθη παιχνιδιού",
           ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py — ΜΗΝ το επεξεργάζεσαι.",
           ";  Μία πηγή αλήθειας με το tools/physics.py.",
           ";" + "=" * 69,
           ""]
    for i, n in enumerate(P.TYPE_NAMES):
        out.append(f"T_{n:<14} equ {i}")
    first = rooms[0].number if rooms else 1
    out += ["",
            "; Αίθουσα εκκίνησης. Ο editor τη γράφει με --start ώστε να δοκιμάζεις",
            "; οποιαδήποτε αίθουσα χωρίς να πειράζεις τα αρχεία των πιστών.",
            f"START_ROOM      equ {START_ROOM if START_ROOM is not None else first}",
            "",
            "; Γεωμετρία πινάκων — εδώ ώστε να είναι ορατή σε assert του main.asm",
            f"TAB_ROW         equ {ROW*2}",
            f"RTAB_OFF        equ {RTAB_OFF}",
            f"GTAB_OFF        equ {GTAB_OFF}",
            "",
            f"NTYPES          equ {P.NTYPES}",
            f"ENERGY_MAX      equ {P.ENERGY_MAX}",
            f"ENERGY_PICK     equ {P.ENERGY_PICK}",
            f"SPIKE_DMG       equ {P.SPIKE_DMG}",
            f"CRATE_TICKS     equ {P.CRATE_TICKS}",
            f"FALL_SAFE       equ {P.FALL_SAFE}",
            f"FALL_V0         equ {P.FALL_V0}",
            f"FALL_ACCEL      equ {P.FALL_ACCEL}",
            f"FALL_VMAX       equ {P.FALL_VMAX}",
            f"PARA_V          equ {P.PARA_V}",
            f"WALK_V          equ {P.WALK_V}",
            "",
            "; Ιδιότητες ανά τύπο — ένα AND αντί για σκόρπιες συγκρίσεις",
            "F_SOLID         equ #01",
            "F_DEADLY        equ #02",
            "F_PICKUP        equ #04",
            "F_NOFLIP        equ #08",
            "F_FRAGILE       equ #10",
            "F_ONEWAY        equ #20",
            "F_TRIGGER       equ #40",
            ""]
    return "\n".join(out)


def sprite_pair(px):
    """8x8 pixels -> ζεύγη (mask,data) ανά byte, όπως τα περιμένει το blit.

    Το pen 0 είναι ΔΙΑΦΑΝΟ: η μάσκα κρατά το φόντο εκεί. Χωρίς αυτό, το
    αλεξίπτωτο θα ζωγράφιζε ένα μαύρο τετράγωνο γύρω του.
    """
    out = []
    for v in range(8):
        for half in (0, 4):
            mask = data = 0
            for s in range(4):
                pen = px[v][half + s]
                bits = 0
                if pen & 1:
                    bits |= 1 << (7 - s)
                if pen & 2:
                    bits |= 1 << (3 - s)
                if pen:
                    data |= bits
                else:
                    mask |= (1 << (7 - s)) | (1 << (3 - s))
            out.append((mask, data))
    return out


def rooms_asm(rooms):
    """Όλες οι αίθουσες σε ένα αρχείο, με πίνακα ευρετηρίου.

    Οι αίθουσες μεταγλωττίζονται ΜΕΣΑ στο δυαδικό αντί να φορτώνονται από
    δισκέτα: 960 bytes η καθεμία, οπότε για λίγες αίθουσες η μνήμη είναι
    φθηνότερη από τη ρουτίνα φόρτωσης και τον χρόνο αναμονής.
    """
    out = [";" + "=" * 69,
           ";  GRAVASSIST — αίθουσες, γραφικά tiles και ιδιότητες",
           ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py (πηγή: levels/room_*.txt)",
           ";" + "=" * 69,
           "",
           f"LVL_COLS        equ {P.COLS}",
           f"LVL_ROWS        equ {P.ROWS}",
           f"LVL_CELL        equ {P.CELL}",
           f"LVL_Y0          equ {P.GRID_Y0}",
           f"ROOM_COUNT      equ {len(rooms)}",
           "",
           f"; Γραφικά: {P.NTYPES} τύποι x 8 γραμμές x 2 bytes (MODE 1)",
           "tile_gfx:"]
    for t in range(P.NTYPES):
        px = tile_pixels(t)
        out.append(f"                ; {t} {P.TYPE_NAMES[t]}")
        for v in range(8):
            a, b = pack_mode1(px[v])
            out.append(f"                db #{a:02X},#{b:02X}")

    out += ["",
            "; Ιδιότητες ανά τύπο κελιού — ένα AND αντί για σκόρπιες συγκρίσεις",
            "tile_props:     db " + ",".join(f"#{v:02X}" for v in P.PROPS),
            "",
            "; Η φορά που 'κοιτάει' κάθε κατευθυντικός τύπος· #FF = άσχετο.",
            "tile_facing:    db " + ",".join(
                str(P.FACING.get(i, 255)) for i in range(P.NTYPES)),
            "",
            "; --- Ευρετήριο αιθουσών (ταξινομημένο αριθμητικά) ---------------",
            "room_numbers:   db " + ",".join(str(r.number) for r in rooms),
            "room_index:     dw " + ",".join(f"room_{r.number}_rec" for r in rooms),
            ""]

    for r in rooms:
        out += [f"; --- αίθουσα {r.number} " + "-" * 45,
                f"room_{r.number}_rec:",
                f"                dw {r.start_x}          ; αρχικό X",
                f"                dw {r.start_y}          ; αρχικό Y",
                f"                db {r.start_g}           ; αρχική φορά βαρύτητας",
                f"                dw room_{r.number}_cells",
                f"                dw room_{r.number}_exits",
                f"                dw room_{r.number}_tps",
                f"                dw room_{r.number}_arr",
                "",
                f"room_{r.number}_exits:   ; col, row, αίθουσα, διπλής; ... #FF"]
        for (c, rr), dest, two, cells in r.exit_groups():
            for cc, cr in cells:
                out.append(f"                db {cc},{cr},{dest},{1 if two else 0}")
        out += ["                db #FF", "",
                f"room_{r.number}_arr:     ; αίθουσα προέλευσης, col, row, "
                f"βαρύτητα ... #FF",
                ]
        for other in rooms:
            a = r.arrival_for(other.number)
            if a:
                out.append(
                    f"                db {other.number},{a[0]},{a[1]},{a[2]}")
        out += ["                db #FF", "",
                f"room_{r.number}_tps:     ; col, row, dcol, drow ... #FF = τέλος"]
        for (c, rr), dest, cells in r.teleport_groups():
            if dest is None:
                continue        # αδήλωτη: δεν μπαίνει, άρα δεν κάνει τίποτα
            for cc, cr in cells:
                out.append(f"                db {cc},{cr},{dest[0]},{dest[1]}")
        out += ["                db #FF", "",
                f"room_{r.number}_cells:"]
        for row in r.cells:
            out.append("                db " + ",".join(str(v) for v in row))
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    if "--start" in sys.argv:
        START_ROOM = int(sys.argv[sys.argv.index("--start") + 1])
    rooms = P.all_rooms()
    if not rooms:
        sys.exit("δεν βρέθηκε καμία levels/room_<N>.txt")
    for name, text in (("src/gamedefs.asm", defs_asm(rooms)),
                       ("src/tables.asm", tables_asm()),
                       ("src/rooms.asm", rooms_asm(rooms))):
        path = os.path.join(ROOT, name)
        with open(path, "w") as f:
            f.write(text)
        print(f"  {name}: {len(text.splitlines())} γραμμές")
