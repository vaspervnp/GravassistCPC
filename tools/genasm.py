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
import roomfile as RF

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
    P.GATE_OPEN: ("GATE", 0, True),   # ανοιγμένη: φαίνεται, αλλά περνάς
    P.KEY: ("KEY", 0), P.LOCK: ("LOCK", 0), P.GATE: ("GATE", 0),
    P.PLATE: ("PLATE", 0), P.TELEPORT: ("TELEPORT", 0),
    # Switches: four facings x two states, same turn numbers as the spikes.
    # The placeholder already leans the lever the other way when active, so
    # both states come from one drawing.
    P.SWITCH_U: ("SWITCH", 0), P.SWITCH_L: ("SWITCH", 3),
    P.SWITCH_D: ("SWITCH", 2), P.SWITCH_R: ("SWITCH", 1),
    P.SWITCH_U_ON: ("SWITCH", 0, True), P.SWITCH_L_ON: ("SWITCH", 3, True),
    P.SWITCH_D_ON: ("SWITCH", 2, True), P.SWITCH_R_ON: ("SWITCH", 1, True),
    P.CRATE: ("CRATE", 0), P.CRUMBLE: ("CRUMBLE", 0), P.GRAVLOCK: ("GRAVLOCK", 0),
    # Κινούμενη πλατφόρμα: ΕΝΑ σχήμα, δύο καταστάσεις. Τα κελιά της
    # σβήνονται στη φόρτωση — το πλακίδιο το ζωγραφίζει ο πίνακάς της.
    P.PLATFORM: ("PLATFORM", 0), P.PLATFORM_OFF: ("PLATFORM", 0, True),
    # Η ΒΑΣΗ ΚΑΘΕΤΑΙ ΑΠΕΝΑΝΤΙ ΑΠΟ ΤΙΣ ΜΥΤΕΣ. Το αριστερό και το δεξί ήταν
    # ανταλλαγμένα: το SPIKE_L (δείχνει αριστερά, FACING 2) ζωγραφιζόταν με τη
    # βάση ΑΡΙΣΤΕΡΑ, δηλαδή έδειχνε δεξιά — και το ανάποδο. Το σχήμα έλεγε
    # άλλα από τη φυσική, και ο παίκτης πάταγε τη «σίγουρη» πλευρά.
    P.SPIKE_U: ("SPIKES", 0), P.SPIKE_L: ("SPIKES", 3),
    P.SPIKE_D: ("SPIKES", 2), P.SPIKE_R: ("SPIKES", 1),
    # ΑΝΤΙΘΕΤΑ ΑΠΟ ΤΑ ΑΓΚΑΘΙΑ: εδώ η γεμάτη μπάρα κάθεται ΠΑΝΩ στη φορά —
    # είναι η πλευρά από την οποία ΔΕΝ περνάς. Το αριστερό και το δεξί ήταν
    # ανταλλαγμένα, όπως και στα αγκάθια, με την ίδια συνέπεια: το σχήμα
    # έδειχνε στέρεο εκεί που περνούσες και ανοιχτό εκεί που κολλούσες.
    P.ONEWAY_U: ("ONEWAY", 0), P.ONEWAY_L: ("ONEWAY", 3),
    P.ONEWAY_D: ("ONEWAY", 2), P.ONEWAY_R: ("ONEWAY", 1),
    # Πυργίσκοι: ΕΝΑ σχήμα, δύο στροφές. Ο οριζόντιος είναι ο κατακόρυφος
    # στραμμένος — ο άξονας βολής είναι όλη η διαφορά τους.
    P.TURRET_V: ("TURRET", 0), P.TURRET_H: ("TURRET", 1),
    # Σβηστοί: το ίδιο κουτί με κατεβασμένα καπάκια αντί για στόμια, ώστε να
    # φαίνεται ότι ο πυργίσκος είναι ΕΚΕΙ και απλώς δεν ρίχνει τώρα.
    P.TURRET_V_OFF: ("TURRET", 0, True), P.TURRET_H_OFF: ("TURRET", 1, True),
}

# Τραβηγμένα αγκάθια: ΘΗΚΗ, όχι πλάκα στον πάτο.
#
# ΤΟ ΚΕΛΙ ΕΙΝΑΙ ΣΤΕΡΕΟ ΟΛΟΚΛΗΡΟ (physics.py: «τραβηγμένα -> γίνονται πάτωμα»),
# άρα ο ήρωας πατάει στην ΚΟΡΥΦΗ του. Το σχήμα είχε τη μπάρα στις γραμμές 6-7
# και ό,τι από πάνω κενό, οπότε ο ήρωας στεκόταν έξι pixel ψηλότερα από
# οτιδήποτε ζωγραφιζόταν — μισό σώμα στον αέρα, μετρημένο με το μοντέλο. Τώρα
# η όψη από την οποία βγαίνουν οι ακίδες είναι επιφάνεια, με τις τρύπες τους
# πάνω της, και η κοιλότητα από κάτω λέει ότι οι ακίδες είναι μέσα.
#
# Η περιστροφή (SPIKE_OFF_TURNS) φέρνει αυτή την όψη στη σωστή πλευρά για κάθε
# φορά, ώστε να ισχύει το ίδιο με ανάποδη ή πλάγια βαρύτητα.
SPIKES_OFF = [
    "XX.XX.XX",
    "XXXXXXXX",
    "X......X",
    "X......X",
    "X......X",
    "X......X",
    "X......X",
    "XXXXXXXX",
]

SPIKE_OFF_TURNS = {P.SPIKE_U_OFF: 0, P.SPIKE_L_OFF: 3,
                   P.SPIKE_D_OFF: 2, P.SPIKE_R_OFF: 1}


# --- Σύμβολα του HUD --------------------------------------------------
# Κεραυνός για την ενέργεια, αστέρι για το σκορ. Το νόημα πρέπει να διαβάζεται
# χωρίς λεζάντα: ο κεραυνός είναι το καθιερωμένο σύμβολο για φόρτιση, και το
# αστέρι για πόντους — και τα δύο αναγνωρίσιμα σε 8x8.
HUD_BOLT = [
    "...XXX..",
    "..XXX...",
    ".XXX....",
    "XXXXXX..",
    "...XXX..",
    "..XXX...",
    ".XXX....",
    "XX......",
]

HUD_STAR = [
    "...XX...",
    "...XX...",
    "XXXXXXXX",
    ".XXXXXX.",
    "..XXXX..",
    ".XXXXXX.",
    ".XX..XX.",
    "XX....XX",
]


# --- Βελάκια βαρύτητας για το HUD -------------------------------------
# Ένα 8x8 ανά φορά. Σχεδιάζονται ΜΙΑ φορά (κάτω) και οι υπόλοιπες επτά
# προκύπτουν με περιστροφή, ώστε να μη διαφωνούν μεταξύ τους: αν διορθώσεις
# το σχήμα, διορθώνονται όλες.
ARROW_DOWN = [
    "..XX....",
    "..XX....",
    "..XX....",
    "XXXXXX..",
    ".XXXX...",
    "..XX....",
    "........",
    "........",
]


def arrow_pixels(g, pen):
    """8x8 βέλος που δείχνει προς τη φορά βαρύτητας `g`, σε χρώμα `pen`.

    Οι φορές 0,2,4,6 είναι ακριβείς περιστροφές 90. Οι διαγώνιες δεν είναι
    περιστροφή του ίδιου σχήματος — ζωγραφίζονται ξεχωριστά ως διαγώνια
    γραμμή με μύτη, γιατί μια περιστροφή 45 σε πλέγμα 8x8 βγάζει σκάλες.
    """
    grid = [[0] * 8 for _ in range(8)]
    if g % 2 == 0:
        src = rot90([[1 if c == "X" else 0 for c in row] for row in ARROW_DOWN],
                    {0: 0, 2: 1, 4: 2, 6: 3}[g])
        for v in range(8):
            for u in range(8):
                if src[v][u]:
                    grid[v][u] = pen
        return grid

    # Διαγώνια: ΣΦΗΝΑ στη γωνία και κοντός κορμός προς το κέντρο. Το βέλος
    # με γραμμή και μύτη, που δουλεύει στις ορθές φορές, γίνεται δυσανάγνωστο
    # στις 45 μοίρες σε πλέγμα 8x8 — η γεμάτη σφήνα διαβάζεται αμέσως.
    dx = -1 if g in (1, 3) else 1
    dy = 1 if g in (1, 7) else -1
    cu = 0 if dx < 0 else 7          # η γωνία προς την οποία δείχνει
    cv = 7 if dy > 0 else 0
    for v in range(8):
        for u in range(8):
            if (abs(u - cu) <= 3 and abs(v - cv) <= 3
                    and abs(u - cu) + abs(v - cv) <= 4):
                grid[v][u] = pen
    for k in range(2, 6):            # κορμός: από το κέντρο προς τη σφήνα
        u, v = cu - dx * k, cv - dy * k
        if 0 <= u < 8 and 0 <= v < 8:
            grid[v][u] = pen
            if 0 <= u + dx < 8:
                grid[v][u + dx] = pen
    return grid


# --- Γραμματοσειρά τίτλου ---------------------------------------------
# Μόνο τα γράμματα του GRAVASSIST. Ολόκληρο αλφάβητο θα κόστιζε μνήμη που
# αφαιρείται από τις αίθουσες, και δεν έχουμε άλλη χρήση για κείμενο σε
# pixels — το μενού γράφει τα υπόλοιπα με τη γραμματοσειρά του firmware.
TITLE_GLYPHS = {
    "G": ["..####..",
          ".######.",
          "##....##",
          "##......",
          "##......",
          "##..####",
          "##..####",
          "##....##",
          "##....##",
          ".######.",
          "..####..",
          "........"],
    "R": ["######..",
          "#######.",
          "##....##",
          "##....##",
          "#######.",
          "######..",
          "##..##..",
          "##...##.",
          "##....##",
          "##....##",
          "##....##",
          "........"],
    "A": ["..####..",
          ".######.",
          "##....##",
          "##....##",
          "##....##",
          "########",
          "########",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "........"],
    "V": ["##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          ".##..##.",
          ".##..##.",
          ".##..##.",
          "..####..",
          "..####..",
          "...##...",
          "........"],
    "S": ["..####..",
          ".######.",
          "##....##",
          "##......",
          ".#####..",
          "..#####.",
          "......##",
          "##....##",
          ".######.",
          "..####..",
          "........",
          "........"],
    "I": [".######.",
          ".######.",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          ".######.",
          ".######.",
          "........"],
    "T": ["########",
          "########",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "...##...",
          "........"],
    "M": ["##....##",
          "###..###",
          "########",
          "########",
          "##.##.##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "........"],
    "E": ["########",
          "########",
          "##......",
          "##......",
          "######..",
          "######..",
          "##......",
          "##......",
          "##......",
          "########",
          "########",
          "........"],
    "O": ["..####..",
          ".######.",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          ".######.",
          "..####..",
          "........"],
    "H": ["##....##",
          "##....##",
          "##....##",
          "##....##",
          "########",
          "########",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "........"],
    "N": ["##....##",
          "###...##",
          "####..##",
          "#####.##",
          "##.#####",
          "##..####",
          "##...###",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "........"],
    "D": ["######..",
          "#######.",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "##....##",
          "#######.",
          "######..",
          "........"],
    " ": ["........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........",
          "........"],
}

TITLE_TEXT = "GRAVASSIST"
# Τα μοναδικά γράμματα, σε σταθερή σειρά. Τα έξι τελευταία και το κενό
# μπήκαν για τις οθόνες «GAME OVER» και «THE END» — οι ίδιες φαρδιές
# γραμματοσειρές με τον τίτλο, ώστε το τέλος να μοιάζει με την αρχή.
TITLE_ORDER = "GRAVSIT" + "MEOHND" + " "
BANNERS = {"go_idx": "GAME OVER", "end_idx": "THE END"}


def expand4(bits, pen):
    """4 pixel μάσκας -> 2 bytes MODE 1, σε ΔΙΠΛΟ πλάτος (8 pixel οθόνης).

    Ο τίτλος ζωγραφίζεται 2x, όπως στο concept art. Η επέκταση γίνεται με
    πίνακα και όχι με ολισθήσεις στον Z80: 16 εγγραφές κοστίζουν λιγότερο από
    τον κώδικα που θα τις υπολόγιζε, και δεν μπορούν να βγουν λάθος.
    """
    row = []
    for i in range(4):
        v = pen if bits & (1 << (3 - i)) else 0
        row += [v, v]
    return pack_mode1(row)


def rot90(g, times):
    """Περιστροφή 8x8 κατά 90 δεξιόστροφα, `times` φορές. Ακριβής."""
    for _ in range(times % 4):
        g = [[g[7 - x][y] for x in range(8)] for y in range(8)]
    return g


def plate_down_pixels():
    """Πλάκα ΜΕ ΤΟ ΚΙΒΩΤΙΟ ΠΑΝΩ ΤΗΣ, σε ένα κελί 8x8.

    Δεν αρκεί «πατημένη πλάκα»: ο παίκτης πρέπει να βλέπει ΠΟΥ άφησε το
    κιβώτιο, αλλιώς ψάχνει στο δωμάτιο κάτι που κρατάει ήδη μια πύλη ανοιχτή.
    Το κιβώτιο στριμώχνεται σε έξι γραμμές (φεύγει η μεσαία διακόσμηση, μένει
    το περίγραμμα) και οι δύο τελευταίες γίνονται η πατημένη πλάκα.
    """
    import placeholders
    crate = placeholders._frame("CRATE", False)
    plate = placeholders._frame("PLATE", True)
    return [crate[0], crate[1], crate[3], crate[4], crate[6], crate[7],
            plate[6], plate[7]]


def tile_pixels(t):
    """8x8 pixels (pen ανά θέση) για κάθε τύπο κελιού."""
    g = [[0] * 8 for _ in range(8)]
    if t in (P.EMPTY, P.START):     # ο δείκτης εκκίνησης δεν ζωγραφίζεται ποτέ
        return g
    if t == P.PLATE_DOWN:
        return plate_down_pixels()
    if t in SPIKE_OFF_TURNS:
        base = [[PEN_EDGE if ch == "X" else 0 for ch in row] for row in SPIKES_OFF]
        return rot90(base, SPIKE_OFF_TURNS[t])
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
# Δισκέτα επίδειξης: γράφει DEMO κάτω από τον τίτλο και σε κάθε οθόνη. Είναι
# σημαία ΣΥΝΑΡΜΟΛΟΓΗΣΗΣ και όχι ρύθμιση: χωρίς αυτήν ο κώδικας δεν μπαίνει
# καν στο binary, και μια κανονική δισκέτα δεν πληρώνει τίποτα σε bytes.
DEMO = False


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
            "; --- σετ αιθουσών σε αρχείο (tools/roomfile.py) --------------",
            f"SET_ROOMS       equ {RF.SET_ROOMS}",
            f"SET_VERSION     equ {RF.VERSION}          ; ο φορτωτής απορρίπτει "
            "ό,τι άλλο",
            "; Οι θέσεις των σετ μέσα στις τράπεζες του 6128 (src/bank.asm).",
            "; Ο Z80 βρίσκει τη θέση με ολισθήσεις, οπότε τα δύο μεγέθη ΠΡΕΠΕΙ",
            "; να είναι δυνάμεις του 2 — το assert από κάτω το επιβάλλει.",
            f"SLOT_SHIFT      equ {RF.SLOT_SIZE.bit_length() - 1}"
            f"         ; 1 << {RF.SLOT_SIZE.bit_length() - 1} = {RF.SLOT_SIZE}"
            " bytes ανά θέση",
            f"SLOTS_SHIFT     equ {RF.SLOTS_PER_BANK.bit_length() - 1}"
            f"         ; 1 << {RF.SLOTS_PER_BANK.bit_length() - 1}"
            f" = {RF.SLOTS_PER_BANK} θέσεις ανά μπλοκ",
            f"MAX_SETS        equ {RF.MAX_SETS}         ; = "
            f"{RF.MAX_SETS * RF.SET_ROOMS} αίθουσες στη μνήμη",
            f"SET_COUNT       equ {RF.set_count()}          ; πόσα σετ ψάχνει "
            "η εκκίνηση",
            "; Πόσα bytes προχωράει η μπάρα φόρτωσης ανά σετ. Υπολογισμένο εδώ",
            "; ώστε η μπάρα να γεμίζει ακριβώς όσο και οι αίθουσες, όποιες κι",
            "; αν είναι — στον Z80 μια διαίρεση θα κόστιζε περισσότερο από όσο",
            "; αξίζει μια μπάρα.",
            f"BAR_STEP        equ {max(1, 64 // max(1, RF.set_count()))}",
            "",
            "; --- σκορ (tools/physics.py) ---------------------------------",
            f"SCORE_START     equ {P.SCORE_START}",
            f"SCORE_EXIT      equ {P.SCORE_EXIT}",
            f"SCORE_PLATE     equ {P.SCORE_PLATE}",
            f"SCORE_GATE      equ {P.SCORE_GATE}",
            f"SCORE_SWITCH    equ {P.SCORE_SWITCH}",
            f"SCORE_LOCK      equ {P.SCORE_LOCK}",
            f"SCORE_PARA_LAND equ {P.SCORE_PARA_LAND}",
            f"SCORE_PARA_KEEP equ {P.SCORE_PARA_KEEP}",
            f"SCORE_PICKUP    equ {P.SCORE_PICKUP}",
            "; Τα αρνητικά μπαίνουν ως ΣΥΜΠΛΗΡΩΜΑ 2 σε ένα byte: το score_add",
            "; επεκτείνει το πρόσημο μόνο του.",
            f"SCORE_STEP      equ {P.SCORE_STEP & 0xFF}         "
            f"; {P.SCORE_STEP}",
            f"SCORE_GRAV      equ {P.SCORE_GRAV & 0xFF}         "
            f"; {P.SCORE_GRAV}",
            f"HISCORE_MAX     equ {P.HISCORE_MAX}",
            f"HISCORE_NAME    equ {P.HISCORE_NAME}",
            "; Χάρτης επισκεμμένων αιθουσών: ένα bit ανά αίθουσα, όσες χωράνε",
            "; στις τράπεζες.",
            # ΔΥΝΑΜΗ ΤΟΥ 2: το visit_bit κόβει τον δείκτη με `and VISIT_BYTES-1`,
            # που είναι μάσκα μόνο αν το μέγεθος είναι δύναμη του 2. Με 13 bytes
            # η μάσκα θα ήταν 12 και οι μισές αίθουσες θα μοιράζονταν bit.
            f"VISIT_BYTES     equ {1 << (max(1, -(-RF.MAX_SETS * RF.SET_ROOMS // 8)) - 1).bit_length()}",
            f"SET_NUMBERS     equ {3 + 1 + 1}          ; offset του numbers[] "
            "στην κεφαλή",
            f"SET_OFFS        equ {3 + 1 + 1 + RF.SET_ROOMS}         ; offset "
            "του offs[]",
            f"LVL_CELLS       equ {P.COLS * P.ROWS}",
            "; Πόσες αλλαγές κελιών θυμάται το παιχνίδι συνολικά. Κάθε εγγραφή",
            "; είναι 4 bytes· γεμάτο ημερολόγιο σημαίνει ότι οι παλιότερες",
            "; αλλαγές δεν επιβιώνουν όταν ξαναμπείς στην αίθουσα.",
            "JOURNAL_MAX     equ 64",
            f"TRAIL_MAX       equ {P.TRAIL_MAX}    ; πόσα δωμάτια πίσω γυρνάς",
            "",
            "; Ταβάνι μνήμης με ενεργό AMSDOS — δες την assert στο main.asm.",
            "MEM_CEIL        equ #A67B",
            "",
            f"NTYPES          equ {P.NTYPES}",
            f"ATTR_MAX        equ {P.ATTR_MAX}   ; κανάλια διακοπτών / "
            "ταυτότητες κλειδιών",
            f"T_LOCK_AUTO     equ {P.LOCK_AUTO}    ; bit: η κλειδαριά ανοίγει "
            "μόλις την ακουμπήσεις",
            f"SPIKE_TICKS     equ {P.SPIKE_TICKS}",
            f"HURT_FRAMES     equ {P.HURT_FRAMES}",
            f"LAND_TICKS      equ {P.LAND_TICKS}",
            f"DEMO_MODE       equ {1 if DEMO else 0}"           "   ; 1 = δισκέτα επίδειξης",
            f"ENERGY_MAX      equ {P.ENERGY_MAX}",
            f"ENERGY_PICK     equ {P.ENERGY_PICK}",
            f"SPIKE_DMG       equ {P.SPIKE_DMG}",
            "",
            "; --- ΠΥΡΓΙΣΚΟΙ ---",
            f"TURRET_RANGE    equ {P.TURRET_RANGE}",
            f"ARROW_STEP      equ {P.ARROW_STEP}",
            f"TURRET_MAX      equ {P.TURRET_MAX}",
            "; Η φόρτιση σε παλμούς του ρολογιού του firmware (1/300 s), ΟΧΙ σε",
            "; περάσματα βρόχου: ένα πέρασμα είναι 3 ως 7 vsync ανάλογα με το τι",
            "; κάνει ο παίκτης, οπότε ένας μετρητής περασμάτων θα έδινε πέντε",
            "; δευτερόλεπτα ακίνητος και έντεκα τρέχοντας.",
            f"TURRET_RELOAD   equ {P.TURRET_RELOAD // 50 * 300}",
            "; Η προεπιλογή σε ΔΕΥΤΕΡΟΛΕΠΤΑ, για πυργίσκο που δεν δηλώνει τίποτα.",
            f"TURRET_COOL_DEF equ {P.TURRET_COOL}",
            f"ARROW_DMG_NEAR  equ {P.ARROW_DMG[0]}",
            f"ARROW_DMG_MID   equ {P.ARROW_DMG[1]}",
            f"ARROW_DMG_FAR   equ {P.ARROW_DMG[2]}",
            "; Πόσους πυργίσκους κρατά ο πίνακας μιας αίθουσας. Ό,τι περισσεύει",
            "; αγνοείται σιωπηλά — το tools/roomfile.py σπάει το build αντ' αυτού.",
            f"TURRET_SLOTS    equ {P.TURRET_SLOTS}",
            "; Κινούμενες πλατφόρμες: πόσες χωράνε, και οι δύο χρόνοι τους.",
            f"PLAT_MAX        equ {P.PLAT_MAX}",
            f"PLAT_SPEED_DEF  equ {P.PLAT_SPEED}",
            "; Η παύση στα άκρα, σε παλμούς του ρολογιού 1/300.",
            f"PLAT_PAUSE      equ {P.PLAT_PAUSE * 300}",
            "; Στερεή μόνο από πάνω: η βαρύτητα που την κάνει πάτωμα.",
            f"PLAT_GRAV       equ {(P.PLAT_FACING + 4) % 8}",
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
            "; A switch, any facing, either state — the eight numbers are not",
            "; contiguous, so a range check would break the first time a type",
            "; is inserted.",
            f"F_SWITCH        equ #{P.F_SWITCH:02X}",
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
           "",
           f"; Γραφικά: {P.NTYPES} τύποι x 8 γραμμές x 2 bytes (MODE 1)",
           "tile_gfx:"]
    for t in range(P.NTYPES):
        px = tile_pixels(t)
        out.append(f"                ; {t} {P.TYPE_NAMES[t]}")
        for v in range(8):
            a, b = pack_mode1(px[v])
            out.append(f"                db #{a:02X},#{b:02X}")

    # Δύο χρώματα: το ένα βελάκι είναι η βαρύτητα του ΚΟΣΜΟΥ (αυτή που όρισε
    # ο παίκτης, την ακολουθούν τα κιβώτια) και το άλλο η βαρύτητα του ΗΡΩΑ
    # (γυρίζει μόνη της σε κάθε γωνία). Είναι διαφορετικά πράγματα και ο
    # παίκτης δεν είχε τρόπο να τα ξεχωρίσει.
    for name, pen in (("grav_gfx_world", 3), ("grav_gfx_hero", 2)):
        out += ["", f"{name}:      ; 8 φορές x 8 γραμμές x 2 bytes"]
        for g in range(8):
            px = arrow_pixels(g, pen)
            out.append(f"                ; φορά {g}")
            for v in range(8):
                a, b = pack_mode1(px[v])
                out.append(f"                db #{a:02X},#{b:02X}")

    # --- Σύμβολα του HUD ----------------------------------------------
    # Δύο 8x8 γλυφές που λένε ΤΙ μετράει ο αριθμός δίπλα τους. Ίδια μορφή με
    # τα βελάκια (8 γραμμές x 2 bytes) ώστε να τις ζωγραφίζει η ΙΔΙΑ ρουτίνα,
    # draw_garrow με φορά 0 — καμία νέα διαδρομή σχεδίασης.
    for name, art, pen in (("hud_bolt", HUD_BOLT, 3),
                           ("hud_star", HUD_STAR, 2)):
        out += ["", f"{name}:        ; 8 γραμμές x 2 bytes"]
        for row in art:
            a, b = pack_mode1([pen if ch == "X" else 0 for ch in row])
            out.append(f"                db #{a:02X},#{b:02X}")

    # --- Τίτλος του μενού ---------------------------------------------
    out += ["",
            "; Γράμματα του τίτλου: 8x8 μάσκα, ένα bit ανά pixel. Ζωγραφίζονται",
            "; σε διπλό μέγεθος με τον πίνακα font_x2 από κάτω.",
            "TITLE_LEN       equ " + str(len(TITLE_TEXT)),
            "TITLE_H         equ " + str(len(TITLE_GLYPHS["G"])),
            "font_glyphs:"]
    for ch in TITLE_ORDER:
        rows = TITLE_GLYPHS[ch]
        bits = ",".join(
            "#%02X" % sum(1 << (7 - i) for i, c in enumerate(r) if c == "#")
            for r in rows)
        out.append(f"                db {bits}   ; {ch}")

    out += ["",
            "; Η σειρά των γραμμάτων του τίτλου, ως δείκτες μέσα στο font_glyphs.",
            "title_idx:      db " + ",".join(
                str(TITLE_ORDER.index(c)) for c in TITLE_TEXT),
            ""]
    for name, text in BANNERS.items():
        out += [f"{name.upper()}_LEN     equ {len(text)}",
                f"{name}:{' ' * max(1, 15 - len(name))}db " + ",".join(
                    str(TITLE_ORDER.index(c)) for c in text) + f"   ; {text}"]
    out += ["",
            "; 4 bits μάσκας -> 2 bytes MODE 1 σε διπλό πλάτος, ανά χρώμα.",
            ]
    for name, pen in (("font_x2_a", 3), ("font_x2_b", 2)):
        rows = []
        for bits in range(16):
            a, b = expand4(bits, pen)
            rows.append(f"#{a:02X},#{b:02X}")
        out.append(f"{name}:      db " + ",".join(rows))

    out += ["",
            "; Ιδιότητες ανά τύπο κελιού — ένα AND αντί για σκόρπιες συγκρίσεις",
            "tile_props:     db " + ",".join(f"#{v:02X}" for v in P.PROPS),
            "",
            "; Η φορά που 'κοιτάει' κάθε κατευθυντικός τύπος· #FF = άσχετο.",
            "tile_facing:    db " + ",".join(
                str(P.FACING.get(i, 255)) for i in range(P.NTYPES)),
            "",
            "; Οι ΑΙΘΟΥΣΕΣ δεν είναι πια εδώ. Ασυμπίεστες κόστιζαν 960 bytes",
            "; η καθεμία και χωρούσαν ~10 συνολικά· τώρα ζουν RLE μέσα στα",
            "; build/ROOMSnn.BIN, σετ των 40. Δες tools/roomfile.py.",
            ""]

    return "\n".join(out)


if __name__ == "__main__":
    if "--start" in sys.argv:
        START_ROOM = int(sys.argv[sys.argv.index("--start") + 1])
    DEMO = "--demo" in sys.argv
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

    # Τα δεδομένα των αιθουσών τα γράφει το tools/roomfile.py, με δικό του
    # κανόνα στο Makefile — ένας παραγωγός ανά αρχείο.
