#!/usr/bin/env python3
"""Μοντέλο φυσικής του GRAVASSIST — ΑΝΑΦΟΡΑ για την υλοποίηση σε Z80.

Εδώ δοκιμάζεται η μηχανική πριν γραφτεί σε assembly, γιατί ο Z80 κώδικας δεν
μπορεί να τρέξει από το περιβάλλον ανάπτυξης. Ό,τι αλλάζει εδώ πρέπει να
αλλάξει και στο src/hero.asm — και το αντίστροφο.

Οι δύο κανόνες που βγάζουν όλη τη συμπεριφορά:

  1. Ο ήρωας ΣΤΕΚΕΤΑΙ αν και τα ΔΥΟ πέλματα πατάνε σε στερεό.
     Ένα πέλμα -> ασταθής -> γλιστράει. Κανένα -> πέφτει.
     Από αυτόν τον κανόνα προκύπτει ΔΩΡΕΑΝ ότι η διαγώνια βαρύτητα σε
     επίπεδο πάτωμα γλιστράει, ενώ σε ράμπα 45 μοιρών στέκεται.

  2. Περπατώντας, αν κλείσει ο δρόμος -> στροφή ΑΝΤΙΘΕΤΑ (κοίλη γωνία).
     Αν χαθεί το έδαφος -> στροφή ΠΡΟΣ τη φορά (κυρτή γωνία).
     Οι ράμπες προκύπτουν από το ίδιο, με βήμα 45 αντί για 90.
"""

import math
import os
import re
import sys


def r(v):
    """Στρογγυλοποίηση όπως θα την κάνει ο Z80 (floor(v+0.5)).
    Η ενσωματωμένη r() είναι banker's rounding και δίνει άλλα αποτελέσματα."""
    return math.floor(v + 0.5)

CELL = 8
COLS, ROWS = 40, 24
GRID_Y0 = 8                     # η πρώτη scanline του grid (πάνω από αυτήν = HUD)
DEFAULT_START = (7, 4)          # αν λείπει ο δείκτης '@'
ROOM_RE = re.compile(r"room_(\d+)\.txt$", re.I)

# --- Τύποι κελιών -----------------------------------------------------
# Οι τιμές 0..5 (γεωμετρία) ΔΕΝ αλλάζουν ποτέ: πάνω τους στηρίζεται το
# solid_at και ο πίνακας ramp_grav. Τα στοιχεία παιχνιδιού μπαίνουν από το 6.
EMPTY, SOLID = 0, 1
RAMP_DR, RAMP_DL, RAMP_UR, RAMP_UL = 2, 3, 4, 5     # στερεό κάτω-δεξιά κ.λπ.

SPIKE_U, SPIKE_L, SPIKE_D, SPIKE_R = 6, 7, 8, 9     # η φορά που δείχνουν οι μύτες
ONEWAY_U, ONEWAY_L, ONEWAY_D, ONEWAY_R = 10, 11, 12, 13
GRAVLOCK = 14           # ζώνη: απαγορεύεται η αλλαγή βαρύτητας
CRUMBLE = 15            # στερεό που καταρρέει αφού το πατήσεις
EXIT = 16
ENERGY = 17
PARACHUTE = 18
KEY = 19
LOCK = 20               # στερεό μέχρι να έχεις κλειδί
GATE = 21               # στερεό όσο είναι κλειστό
SWITCH = 22
PLATE = 23              # πλάκα πίεσης
TELEPORT = 24
CRATE = 25
START = 26              # δείκτης εκκίνησης· δεν υπάρχει στο παιχνίδι
LOCK_OPEN = 27          # ξεκλειδωμένο: φαίνεται ακόμα, αλλά περνάς από μέσα
GATE_OPEN = 28          # ανοιγμένη πόρτα· ίδια λογική με το LOCK_OPEN

CHARS = {
    ".": EMPTY, "#": SOLID,
    "/": RAMP_DR, "\\": RAMP_DL, "7": RAMP_UR, "F": RAMP_UL,
    "^": SPIKE_U, "<": SPIKE_L, "v": SPIKE_D, ">": SPIKE_R,
    "-": ONEWAY_U, "[": ONEWAY_L, "_": ONEWAY_D, "]": ONEWAY_R,
    ":": GRAVLOCK, "%": CRUMBLE, "X": EXIT, "+": ENERGY, "P": PARACHUTE,
    "k": KEY, "K": LOCK, "G": GATE, "S": SWITCH, "p": PLATE,
    "T": TELEPORT, "B": CRATE, "@": START, "|": LOCK_OPEN, "g": GATE_OPEN,
}
NAMES = {v: k for k, v in CHARS.items()}
TYPE_NAMES = ["EMPTY", "SOLID", "RAMP_DR", "RAMP_DL", "RAMP_UR", "RAMP_UL",
              "SPIKE_U", "SPIKE_L", "SPIKE_D", "SPIKE_R",
              "ONEWAY_U", "ONEWAY_L", "ONEWAY_D", "ONEWAY_R",
              "GRAVLOCK", "CRUMBLE", "EXIT", "ENERGY", "PARACHUTE",
              "KEY", "LOCK", "GATE", "SWITCH", "PLATE", "TELEPORT", "CRATE",
              "START", "LOCK_OPEN", "GATE_OPEN"]
NTYPES = 29

# --- Ιδιότητες ανά τύπο (bit flags) ----------------------------------
# Ένας πίνακας αντί για σκόρπια if: ο ίδιος εξάγεται στο src/tables.asm και
# ο Z80 ρωτάει το ίδιο πράγμα με ένα AND.
F_SOLID   = 0x01        # μπλοκάρει την κίνηση
F_DEADLY  = 0x02        # αφαιρεί ενέργεια στην επαφή
F_PICKUP  = 0x04        # καταναλώνεται μόλις το αγγίξεις
F_NOFLIP  = 0x08        # μέσα του δεν αλλάζει η βαρύτητα
F_FRAGILE = 0x10        # καταρρέει αφού το πατήσεις
F_ONEWAY  = 0x20        # στερεό μόνο από τη μία πλευρά
F_TRIGGER = 0x40        # ενεργοποιεί κάτι (έξοδος, διακόπτης, τηλεμεταφορά)

PROPS = [0] * NTYPES
for _t in (SOLID, RAMP_DR, RAMP_DL, RAMP_UR, RAMP_UL, LOCK, GATE, CRATE):
    PROPS[_t] |= F_SOLID
for _t in (SPIKE_U, SPIKE_L, SPIKE_D, SPIKE_R):
    PROPS[_t] |= F_DEADLY | F_SOLID     # στερεά: πατάς πάνω τους, δεν τα περνάς
for _t in (ENERGY, PARACHUTE, KEY):
    PROPS[_t] |= F_PICKUP
for _t in (ONEWAY_U, ONEWAY_L, ONEWAY_D, ONEWAY_R):
    PROPS[_t] |= F_ONEWAY | F_SOLID
PROPS[GRAVLOCK] |= F_NOFLIP
PROPS[CRUMBLE] |= F_SOLID | F_FRAGILE
for _t in (EXIT, SWITCH, TELEPORT, PLATE):
    PROPS[_t] |= F_TRIGGER

# Η φορά που "κοιτάει" κάθε κατευθυντικός τύπος (κωδικός βαρύτητας 0..7).
# Αγκάθι: πονάει αν πέφτεις ΠΑΝΩ στις μύτες. Μονόδρομη: στερεή μόνο όταν
# την πλησιάζεις από αυτή την πλευρά.
FACING = {SPIKE_U: 4, SPIKE_L: 2, SPIKE_D: 0, SPIKE_R: 6,
          ONEWAY_U: 4, ONEWAY_L: 2, ONEWAY_D: 0, ONEWAY_R: 6}

# Για κάθε ράμπα: είναι στερεό το pixel (u,v) μέσα στο κελί 8x8;
RAMP_TEST = {
    RAMP_DR: lambda u, v: v >= 7 - u,     # υποτείνουσα κάτω-αριστερά -> πάνω-δεξιά
    RAMP_DL: lambda u, v: v >= u,         # υποτείνουσα πάνω-αριστερά -> κάτω-δεξιά
    RAMP_UR: lambda u, v: v <= u,
    RAMP_UL: lambda u, v: v <= 7 - u,
}

# Η φορά βαρύτητας ΠΑΝΩ σε κάθε ράμπα: το κάθετο στην επιφάνεια, προς το υλικό.
# Επειδή ο κόσμος είναι από tiles γνωστού σχήματος, η κλίση δεν χρειάζεται να
# εκτιμηθεί — διαβάζεται. Αυτό εξαφανίζει την ασάφεια στις συμβολές.
RAMP_GRAVITY = {RAMP_DR: 7, RAMP_DL: 1, RAMP_UR: 5, RAMP_UL: 3}

# --- Γεωμετρία βαρύτητας: ΜΟΝΟ ΑΚΕΡΑΙΟΙ, ΜΟΝΟ ΠΙΝΑΚΕΣ --------------
# Το μοντέλο δεν κάνει πράξεις κινητής υποδιαστολής πουθενά, ώστε ο Z80 να
# παράγει ΑΚΡΙΒΩΣ τα ίδια αποτελέσματα. Οι ίδιοι πίνακες εξάγονται στο
# src/tables.asm από το tools/gentables.py.
# ΠΡΟΣΟΧΗ: ο πίνακας βαρύτητας χρειάζεται και ΑΡΝΗΤΙΚΑ βάθη — το κεφάλι είναι
# στο b = -7. Χωρίς το offset η Python τα ερμηνεύει ως δείκτες από το τέλος και
# διαβάζει σιωπηλά λάθος τιμές.
GSPAN = 16          # βάθη -16..+16 κατά τη βαρύτητα
RSPAN = 4           # πλάγιες αποστάσεις -4..+4


def _unit(g):
    a = math.radians(g * 45)
    return (-math.sin(a), math.cos(a))


def _perp(g):
    gx, gy = _unit(g)
    return (gy, -gx)


# GTAB[g][k]  = μετατόπιση k pixel ΚΑΤΑ τη βαρύτητα
# RTAB[g][a]  = μετατόπιση a pixel ΚΑΘΕΤΑ στη βαρύτητα (a = -4..+4)
GTAB = [[(r(k * _unit(g)[0]), r(k * _unit(g)[1]))
         for k in range(-GSPAN, GSPAN + 1)] for g in range(8)]
RTAB = [[(r(a * _perp(g)[0]), r(a * _perp(g)[1]))
         for a in range(-RSPAN, RSPAN + 1)] for g in range(8)]

# Βήμα ενός pixel: η πρώτη μη μηδενική εγγραφή των παραπάνω.
GSTEP = [GTAB[g][GSPAN + 1] for g in range(8)]
RSTEP = [RTAB[g][RSPAN + 1] for g in range(8)]


def off(g, a, b):
    """Offset σε pixels για τοπικές συντεταγμένες (a = πλάγια, b = προς πόδια).

    ΠΡΟΣΟΧΗ: αθροίζονται δύο ΞΕΧΩΡΙΣΤΑ στρογγυλοποιημένες τιμές, όχι η
    στρογγυλοποίηση του αθροίσματος. Έτσι το κάνει και ο Z80 με lookup, και οι
    δύο υλοποιήσεις πρέπει να συμφωνούν στο pixel.
    """
    rx, ry = RTAB[g][a + RSPAN]
    gx, gy = GTAB[g][b + GSPAN]
    return rx + gx, ry + gy


class Room:
    def __init__(self, text):
        # Γραμμή πίστας = ακριβώς COLS έγκυροι χαρακτήρες. Τα σχόλια είναι ";"
        # (ΟΧΙ "#": το "#" είναι στερεό κελί).
        rows = [ln for ln in text.splitlines()
                if len(ln) == COLS and all(c in CHARS for c in ln)]
        assert len(rows) == ROWS, f"περίμενα {ROWS} γραμμές, βρήκα {len(rows)}"
        self.cells = [[CHARS[c] for c in ln] for ln in rows]
        self.probe_g = 0        # φορά βαρύτητας του ελέγχου (για τις μονόδρομες)

        # Ο δείκτης '@' δηλώνει πού ξεκινά ο παίκτης. Δεν είναι αντικείμενο του
        # παιχνιδιού: διαβάζεται και το κελί γίνεται κενό.
        self.start_col, self.start_row = DEFAULT_START
        for r, row in enumerate(self.cells):
            for c, v in enumerate(row):
                if v == START:
                    self.start_col, self.start_row = c, r
                    row[c] = EMPTY

        # Ρυθμίσεις δωματίου, ΜΕΤΑ το πλέγμα
        self.start_g = 0
        decl = {}                       # (col,row) -> αίθουσα προορισμού
        tpd = {}                        # (col,row) -> κελί προορισμού
        two = {}                        # (col,row) -> διπλής κατεύθυνσης;
        arr = {}                        # (col,row) -> κελί άφιξης της πόρτας
        arg = {}                        # (col,row) -> φορά βαρύτητας στην άφιξη
        # ΕΝΑΣ πίνακας ιδιοτήτων για όλα: κάθε κελί έχει ακριβώς έναν τύπο,
        # οπότε δεν υπάρχει ασάφεια. Ο διακόπτης και η πόρτα μοιράζονται
        # "κανάλι", το κλειδί και η κλειδαριά "ταυτότητα".
        attrs = {}                      # (col,row) -> τιμή 0..ATTR_MAX-1
        for ln in text.splitlines():
            m = re.match(r"\s*gravity\s+([0-7])\s*$", ln, re.I)
            if m:
                self.start_g = int(m.group(1))
            # Τα προαιρετικά πεδία είναι ΘΕΣΗΣ:
            #   exit <col> <row> <αίθουσα> [διπλή] [acol] [arow] [g]
            # Η φορά βαρύτητας της άφιξης έρχεται τελευταία, γιατί χωρίς κελί
            # άφιξης δεν έχει σε τι να εφαρμοστεί.
            m = re.match(r"\s*exit\s+(\d+)\s+(\d+)\s+(\d+)"
                         r"(?:\s+([01])(?:\s+(\d+)\s+(\d+)(?:\s+([0-7]))?)?)?\s*$",
                         ln, re.I)
            if m:
                key = (int(m.group(1)), int(m.group(2)))
                decl[key] = int(m.group(3))
                two[key] = m.group(4) == "1"
                if m.group(5):
                    arr[key] = (int(m.group(5)), int(m.group(6)))
                if m.group(7):
                    arg[key] = int(m.group(7))
            m = re.match(r"\s*tp\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", ln, re.I)
            if m:
                a, b, c, d = (int(x) for x in m.groups())
                tpd[(a, b)] = (c, d)
            m = re.match(r"\s*(sw|gate|lock|key)\s+(\d+)\s+(\d+)\s+(\d+)\s*$",
                         ln, re.I)
            if m:
                attrs[(int(m.group(2)), int(m.group(3)))] = int(m.group(4))
        self.exits = {k: (v or 0) for k, v in
                      self._link(EXIT, decl, "εξόδου").items()}
        self.teleports = self._link(TELEPORT, tpd, "τηλεμεταφοράς")
        self.exit_two = {k: bool(v) for k, v in
                         self._link(EXIT, two, "εξόδου (κατεύθυνση)").items()}
        self.exit_arrive = self._link(EXIT, arr, "εξόδου (άφιξη)")
        self.exit_arrive_g = self._link(EXIT, arg, "εξόδου (βαρύτητα άφιξης)")

        # Η ιδιότητα απλώνεται σε ΟΛΑ τα κελιά της ομάδας, όπως ο προορισμός
        # μιας εξόδου: μια ψηλή πόρτα δύο κελιών είναι ΕΝΑ αντικείμενο.
        self.attrs = {}
        for kind in (SWITCH, GATE, GATE_OPEN, LOCK, LOCK_OPEN, KEY):
            for cell, v in self._link(kind, attrs, "ιδιότητας").items():
                self.attrs[cell] = v or 0

    def _groups_of(self, kind):
        """Συνιστώσες γειτονικών κελιών τύπου `kind` (γειτνίαση 4).

        Επιστρέφει λίστα από λίστες κελιών, με πρώτο κάθε φορά το πάνω-αριστερό
        (σάρωση κατά γραμμές) — σταθερό αναγνωριστικό, ανεξάρτητο από τη σειρά
        σχεδίασης.
        """
        seen, out = set(), []
        for r in range(ROWS):
            for c in range(COLS):
                if self.cells[r][c] != kind or (c, r) in seen:
                    continue
                group, stack = [], [(c, r)]
                seen.add((c, r))
                while stack:
                    cc, rr = stack.pop()
                    group.append((cc, rr))
                    for nc, nr in ((cc+1, rr), (cc-1, rr), (cc, rr+1), (cc, rr-1)):
                        if (0 <= nc < COLS and 0 <= nr < ROWS
                                and (nc, nr) not in seen
                                and self.cells[nr][nc] == kind):
                            seen.add((nc, nr))
                            stack.append((nc, nr))
                out.append(sorted(group, key=lambda p: (p[1], p[0])))
        return out

    def _link(self, kind, decl, what):
        """Δίνει σε ΟΛΑ τα κελιά κάθε ομάδας τον ίδιο προορισμό.

        Γειτονικά κελιά είναι ΕΝΑ αντικείμενο: δεν έχει νόημα δύο που ακουμπάνε
        να βγάζουν αλλού. Ο κανόνας επιβάλλεται εδώ, ώστε ούτε ο editor ούτε ο
        σχεδιαστής να μπορούν να τον παραβιάσουν κατά λάθος.
        """
        out = {}
        for group in self._groups_of(kind):
            found = {decl[g] for g in group if g in decl}
            if len(found) > 1:
                raise ValueError(
                    f"γειτονικά κελιά {what} στο {group} δηλώνουν "
                    f"διαφορετικούς προορισμούς {sorted(found)}")
            dest = found.pop() if found else None
            for g in group:
                out[g] = dest
        return out

    def attr(self, col, row):
        """Κανάλι διακόπτη/πόρτας ή ταυτότητα κλειδιού/κλειδαριάς. 0 = προεπιλογή."""
        return self.attrs.get((col, row), 0)

    def gate_cells(self, channel):
        """Τα κελιά πόρτας του καναλιού — και ανοιχτά και κλειστά."""
        return [(c, r) for (c, r), v in self.attrs.items()
                if v == channel and self.cells[r][c] in (GATE, GATE_OPEN)]

    def exit_groups(self):
        """[(πάνω-αριστερό κελί, αίθουσα, διπλής;, [κελιά])] ανά ομάδα εξόδου."""
        return [(g[0], self.exits[g[0]], self.exit_two.get(g[0], False), g)
                for g in self._groups_of(EXIT)]

    def arrival_for(self, origin):
        """Πού εμφανίζεται ο παίκτης μπαίνοντας ΑΠΟ την αίθουσα `origin`.

        Στο σημείο άφιξης της πόρτας που γυρίζει πίσω εκεί — δηλαδή της πόρτας
        από την οποία ΒΓΑΙΝΕΙ. Το σημείο δηλώνεται στην ίδια γραμμή `exit` και
        είναι ιδιότητα της πόρτας, όχι της αίθουσας: κάθε πόρτα βγάζει αλλού.

        Χωρίς δήλωση πέφτουμε σε ένα ελεύθερο διπλανό κελί. ΠΟΤΕ πάνω στην ίδια
        την πόρτα: εκεί θα την ξαναπερνούσε αμέσως και θα πηγαινοερχόταν
        ατέρμονα — και το διπλανό κελί δεν αρκεί πάντα, γιατί ο ήρωας είναι 7
        pixel φαρδύς και ακουμπάει και το επόμενο κελί. Γι' αυτό υπάρχει η ρητή
        δήλωση.

        Η ΦΟΡΑ ΒΑΡΥΤΗΤΑΣ δηλώνεται κι αυτή στην ίδια γραμμή. Χωρίς δήλωση
        ισχύει η αρχική φορά της αίθουσας — που είναι λάθος όποτε μπαίνεις από
        πόρτα σε τοίχο ή σε ταβάνι, γιατί η αίθουσα «ξεκινάει» αλλού από εκεί
        που μπαίνεις. Επιστρέφεται πάντα λυμένη, ώστε ούτε ο Z80 ούτε η
        JavaScript να χρειάζεται να ξέρουν τον κανόνα.

        Επιστρέφει (col, row, g) ή None αν δεν υπάρχει πόρτα επιστροφής.
        """
        for cell, dest, two, cells in self.exit_groups():
            if dest != origin:
                continue
            g = self.exit_arrive_g.get(cell)
            if g is None:
                g = self.start_g
            declared = self.exit_arrive.get(cell)
            if declared is not None:
                return declared[0], declared[1], g
            if not two:
                # Η πόρτα δεν δηλώνει ούτε σημείο άφιξης ούτε «διπλή»: ο
                # παίκτης ξεκινά από το '@' της αίθουσας.
                #
                # Η ΣΥΝΘΗΚΗ ΚΡΙΝΕΤΑΙ ΕΔΩ, στην πόρτα από την οποία ΒΓΑΙΝΕΙΣ.
                # Παλιά την έκρινε η πόρτα από την οποία ΜΠΗΚΕΣ — που ζει σε
                # ΑΛΛΟ αρχείο. Έτσι το σημείο άφιξης που έβλεπες μπροστά σου
                # αγνοούνταν επειδή έλειπε μια σημαία σε άλλη αίθουσα: δύο
                # μισά της ίδιας απόφασης σε δύο μεριές.
                return None
            for c, r in cells:          # σταθερή σειρά -> προβλέψιμο σημείο
                for nc, nr in ((c-1, r), (c+1, r), (c, r-1), (c, r+1)):
                    if not (0 <= nc < COLS and 0 <= nr < ROWS):
                        continue
                    t = self.cells[nr][nc]
                    if t == EMPTY or not (PROPS[t] & (F_SOLID | F_DEADLY)):
                        if t != EXIT:
                            return nc, nr, g
        return None

    def teleport_groups(self):
        """[(πάνω-αριστερό κελί, κελί προορισμού ή None, [κελιά])] ανά ομάδα."""
        return [(g[0], self.teleports[g[0]], g) for g in self._groups_of(TELEPORT)]

    @property
    def start_x(self):
        """Κέντρο του κελιού εκκίνησης σε pixels."""
        return self.start_col * CELL + CELL // 2

    @property
    def start_y(self):
        return GRID_Y0 + self.start_row * CELL + CELL // 2

    def cell(self, col, row):
        if col < 0 or row < 0 or col >= COLS or row >= ROWS:
            return SOLID                    # έξω από το δωμάτιο = τοίχος
        return self.cells[row][col]

    def solid_at(self, px, py):
        """Είναι το pixel (px,py) μέσα σε υλικό; Χειρίζεται ράμπες και μονόδρομες."""
        py -= GRID_Y0
        if py < 0:
            return True
        t = self.cell(px // CELL, py // CELL)
        if t in RAMP_TEST:
            return RAMP_TEST[t](px % CELL, py % CELL)
        if PROPS[t] & F_ONEWAY:
            # Στερεή μόνο όταν την πλησιάζεις από τη σωστή πλευρά, δηλαδή όταν
            # η βαρύτητα δείχνει ΑΝΤΙΘΕΤΑ από την όψη της. Το ίδιο tile είναι
            # πάτωμα ή αέρας ανάλογα με το πού κοιτάς — εκεί είναι η αξία του.
            return (FACING[t] + 4) % 8 == self.probe_g
        return bool(PROPS[t] & F_SOLID)


# Το σώμα 7x12 μοντελοποιείται ΣΤΕΝΟ: μια κατακόρυφη ράβδος με δύο "πέλματα".
# Με πλατύ bounding box κάθε ράμπα μοιάζει με τοίχο.
FEET_B   = 6        # απόσταση πέλματος από το κέντρο, κατά τη βαρύτητα
FOOT_A   = 2        # μισό άνοιγμα ποδιών, κάθετα στη βαρύτητα
WALL_A   = 3        # μισό πλάτος κορμού
SCAN_MAX = 14       # πόσο βαθιά ψάχνουμε έδαφος
ENERGY_MAX = 8
SPIKE_DMG  = 2
# Τα αγκάθια χτυπούν ΑΝΑ SPIKE_TICKS frames, όχι σε κάθε frame. Με ζημιά σε
# κάθε frame η ενέργεια εξατμιζόταν σε κλάσμα δευτερολέπτου και το να πατήσεις
# αγκάθι ήταν πρακτικά θάνατος· τώρα προλαβαίνεις να φύγεις.
SPIKE_TICKS = 10
# Πόσα διαφορετικά κανάλια διακοπτών και ταυτότητες κλειδιών. Ένα byte θα
# χωρούσε 256, αλλά 8 φτάνουν για puzzle και κρατούν το inventory μικρό.
ATTR_MAX = 8
ENERGY_PICK = 2
WALK_V = 512        # 2.0 px/frame· το τρέξιμο είναι διπλάσιο -> 4.0
CRATE_TICKS = 4     # frames ανά κελί πτώσης κιβωτίου (8 px / 4 = 2 px/frame)
FALL_SAFE = 36      # 3 x ύψος ήρωα
TILT_45  = 3        # διαφορά ύψους (σε 2*FOOT_A pixels) που μετράει για 45 μοίρες

# --- Επιτάχυνση πτώσης (8.8 σταθερή υποδιαστολή: 256 = 1 pixel/frame) ---
# Μεγέθη για οθόνη 200 pixel στα 50 Hz:
#   αρχική 1.0 px/frame, επιτάχυνση ~0.1, τερματική 4.0 px/frame
# Πτώση όλης της οθόνης (192 px) ~59 frames = 1.2 δευτερόλεπτα.
# Το ασφαλές όριο των 36 px καλύπτεται σε ~19 frames με ταχύτητα 2.9 px/frame.
FALL_V0    = 256
FALL_ACCEL = 26
FALL_VMAX  = 1024
PARA_V     = 256        # με αλεξίπτωτο: 1.0 px/frame, χωρίς επιτάχυνση

# ΠΡΟΣΟΧΗ: η ταχύτητα ΔΕΝ γίνεται ποτέ βήμα πολλών pixel. Εκτελούνται πολλαπλά
# βήματα του ΕΝΟΣ pixel ανά frame, γιατί οι γωνίες, οι ακμές και οι ράμπες
# ανιχνεύονται ανά pixel — με βήμα 4 pixel ο ήρωας θα περνούσε μέσα από λεπτά
# πατώματα και θα προσπερνούσε τις γωνίες.


def gvec(g):
    a = math.radians(g * 45)
    return (-math.sin(a), math.cos(a))


def rvec(g):
    gx, gy = gvec(g)
    return (gy, -gx)


class Hero:
    """Θέση = ΚΕΝΤΡΟ του σώματος σε pixels.

    Η βαρύτητα δεν συμπεραίνεται από το τι εμποδίζει· η κλίση της επιφάνειας
    ΜΕΤΡΙΕΤΑΙ ψάχνοντας το έδαφος κάτω από το μπροστινό και το πίσω πέλμα. Έτσι
    μια ράμπα δεν μπερδεύεται ποτέ με τοίχο, όσο πλατύ κι αν είναι το σώμα.
    """

    def __init__(self, room, x, y, g=0):
        self.room, self.x, self.y, self.g = room, x, y, g
        self.fall_dist = 0
        self.state = "FALL"
        self.prev_support = EMPTY
        self.fall_v = FALL_V0
        self.fall_acc = 0
        self.energy = ENERGY_MAX
        # ΕΝΑΣ ΜΕΤΡΗΤΗΣ ΑΝΑ ΤΑΥΤΟΤΗΤΑ: το κλειδί 3 ανοίγει μόνο την κλειδαριά 3.
        # Χωρίς ταυτότητες, ένα κλειδί άνοιγε ό,τι έβρισκε και ο σχεδιαστής δεν
        # μπορούσε να επιβάλει σειρά — που είναι όλο το puzzle.
        self.keys = [0] * ATTR_MAX
        self.parachute = 0      # ΠΛΗΘΟΣ αλεξίπτωτων, όχι σημαία
        self.para_open = 0      # ανοιγμένο αυτή τη στιγμή
        self.won = False
        self.crate_tick = 0
        self.walk_acc = 0
        self.spike_tick = 0
        # Το κελί ΣΤΗΡΙΞΗΣ του προηγούμενου frame. Το εύθραυστο καταρρέει όταν
        # το ΑΦΗΝΕΙΣ, όχι όταν το πατάς: έτσι το περνάς ακριβώς μία φορά.
        self.prev_cell = None
        # Το κελί ΣΩΜΑΤΟΣ του προηγούμενου frame, για την ΑΚΜΗ του διακόπτη.
        # Χωρίς αυτό, στέκεσαι πάνω του και η πόρτα ανοιγοκλείνει 50 φορές
        # το δευτερόλεπτο.
        self.prev_body = None           # κλάσμα pixel που μεταφέρεται στο επόμενο frame
        self.moved_cells = []       # κελιά που πρέπει να ξαναζωγραφιστούν
        # Η φορά που ΟΡΙΣΕ Ο ΠΑΙΚΤΗΣ, όχι η τρέχουσα του ήρωα: η δική του
        # γυρίζει αυτόματα σε κάθε γωνία που περπατάει, ενώ η βαρύτητα του
        # κόσμου αλλάζει μόνο όταν το ζητήσει ο παίκτης. Τα κιβώτια ακολουθούν
        # τον κόσμο — αλλιώς θα άλλαζαν φορά κάθε φορά που ο ήρωας στρίβει.
        self.world_g = g
        # Τα κιβώτια ΔΕΝ κινούνται πριν ο παίκτης αλλάξει φορά έστω μία φορά:
        # αλλιώς θα έπεφταν μόλις φορτώσει η πίστα και η τοποθέτηση του
        # σχεδιαστή θα χανόταν πριν καν παίξει κανείς.
        self.crates_on = False
        self.face = 1           # τελευταία φορά βάδισης· ορίζει το "μπροστά"
        self.carry = 0          # κουβαλάει κιβώτιο

    # --- πρωτογενείς έλεγχοι --------------------------------------
    def at(self, a, b):
        """Στερεό στο σημείο (a = πλάγια, b = προς τα πόδια) του ήρωα;"""
        dx, dy = off(self.g, a, b)
        self.room.probe_g = self.g
        return self.room.solid_at(self.x + dx, self.y + dy)

    def ground_depth(self, a):
        """Σε πόσα pixels κατά τη βαρύτητα βρίσκεται έδαφος στη στήλη `a`;
        None αν δεν βρεθεί μέσα στο SCAN_MAX."""
        for k in range(0, SCAN_MAX):
            if self.at(a, k):
                return k
        return None

    def wall_ahead(self, d):
        """Εμπόδιο στο ύψος του ΚΟΡΜΟΥ (όχι των ποδιών) — αυτό είναι τοίχος."""
        return self.at(WALL_A * d, 0) or self.at(WALL_A * d, -4)

    def tilt(self, d):
        """Διαφορά ύψους εδάφους μπροστά-πίσω. Αρνητικό = ανηφόρα μπροστά.
        None αν λείπει έδαφος σε κάποια από τις δύο πλευρές."""
        f = self.ground_depth(FOOT_A * d)
        b = self.ground_depth(-FOOT_A * d)
        if f is None or b is None:
            return None
        return f - b

    def stable(self):
        """Στέκεται αν υπάρχει έδαφος ΚΑΙ η επιφάνεια είναι κάθετη στη βαρύτητα.
        Από εδώ βγαίνει δωρεάν το γλίστρημα: με διαγώνια βαρύτητα σε επίπεδο
        πάτωμα η κλίση βγαίνει μεγάλη -> ασταθής -> γλιστράει."""
        t = self.tilt(1)
        if t is None or abs(t) > 1:
            return False
        k = self.ground_depth(0)
        return k is not None and k <= FEET_B + 2

    def body_cell(self):
        """Το κελί στο κέντρο του σώματος — εκεί μαζεύονται τα αντικείμενα."""
        return self.room.cell(self.x // CELL, (self.y - GRID_Y0) // CELL)

    def crate_step(self):
        """Τα κιβώτια πέφτουν προς την ΤΡΕΧΟΥΣΑ φορά βαρύτητας του παίκτη.

        Κίνηση ανά ΚΕΛΙ, όχι ανά pixel: το κιβώτιο γεμίζει ακριβώς ένα κελί, και
        η κατά κελί κίνηση κρατά τα puzzles καθαρά (τύπου Sokoban) αντί να
        απαιτεί δεύτερο σώμα με δική του φυσική pixel.

        Η σειρά έχει σημασία: πρώτα κινούνται τα κιβώτια που είναι ΠΙΟ ΜΑΚΡΙΑ
        κατά τη βαρύτητα, αλλιώς μια στοίβα δεν θα ξεκολλούσε ποτέ — το από
        πάνω θα έβρισκε πάντα κατειλημμένο το κελί του από κάτω.
        """
        if not self.crates_on:
            return
        self.crate_tick += 1
        if self.crate_tick < CRATE_TICKS:
            return
        self.crate_tick = 0

        dx, dy = GSTEP[self.world_g]
        cells = [(c, r) for r in range(ROWS) for c in range(COLS)
                 if self.room.cells[r][c] == CRATE]
        cells.sort(key=lambda p: -(p[0] * dx + p[1] * dy))

        for c, r in cells:
            nc, nr = c + dx, r + dy
            if not (0 <= nc < COLS and 0 <= nr < ROWS):
                continue
            if self.room.cells[nr][nc] != EMPTY:
                continue
            self.room.cells[r][c] = EMPTY
            self.room.cells[nr][nc] = CRATE
            self.moved_cells += [(c, r), (nc, nr)]

    def set_gravity(self, g):
        """Η φορά που ΟΡΙΖΕΙ ο παίκτης. Ξεχωριστή από την αυτόματη στροφή του
        ήρωα στις γωνίες — μόνο αυτή κινεί τα κιβώτια."""
        self.world_g = g
        self.g = g
        self.crates_on = True

    def ahead_cell(self):
        """Το κελί ΜΠΡΟΣΤΑ του ήρωα, κατά τη φορά που κοιτάει."""
        rx, ry = RSTEP[self.g]
        return ((self.x + rx * self.face * CELL) // CELL,
                (self.y + ry * self.face * CELL - GRID_Y0) // CELL)

    def use(self):
        """Ενεργοποίηση αντικειμένου. ΜΙΑ φορά ανά πάτημα, όχι όσο κρατιέται.

        Όλα κρίνονται από το κελί που ΠΑΤΑΣ, όχι από αυτό που κοιτάς: με τον
        ήρωα να περπατά σε τοίχους και ταβάνια, το "μπροστά" είναι δύσκολο να
        το προβλέψει ο παίκτης ενώ το "από κάτω μου" όχι.

        Σειρά: λουκέτο -> τηλεμεταφορά -> άφημα -> σήκωμα. Το λουκέτο και η
        τηλεμεταφορά προηγούνται ώστε να μη χάνεις την ευκαιρία επειδή τυχαίνει
        να κουβαλάς κιβώτιο.
        """
        sc = self.support_cell()
        st = self.room.cell(*sc) if sc else EMPTY

        kid = self.room.attr(*sc) if sc else 0
        if st == LOCK and self.keys[kid]:
            self.keys[kid] -= 1
            # ΔΕΝ εξαφανίζεται: γίνεται ανοιγμένη πόρτα. Ο παίκτης βλέπει τι
            # ξεκλείδωσε και περνά από μέσα.
            self.room.cells[sc[1]][sc[0]] = LOCK_OPEN
            return True

        col, row = self.x // CELL, (self.y - GRID_Y0) // CELL
        if self.room.cell(col, row) == TELEPORT:
            return self.teleport(col, row)

        if self.carry:
            return self.drop()

        if st == CRATE:
            self.room.cells[sc[1]][sc[0]] = EMPTY
            self.carry = 1
            return True
        return False

    def toggle_gates(self, channel):
        """Γυρίζει ΟΛΕΣ τις πόρτες ενός καναλιού: κλειστή <-> ανοιχτή.

        Η ανοιχτή πόρτα δεν εξαφανίζεται — γίνεται GATE_OPEN και φαίνεται,
        όπως και η ξεκλείδωτη κλειδαριά. Ο παίκτης πρέπει να βλέπει τι άλλαξε
        ο διακόπτης, αλλιώς πατάει κάτι και δεν ξέρει τι έγινε.
        """
        for c, r in self.room.gate_cells(channel):
            self.room.cells[r][c] = (
                GATE_OPEN if self.room.cells[r][c] == GATE else GATE)
            self.moved_cells.append((c, r))

    def drop(self):
        fc, fr = self.ahead_cell()
        if not (0 <= fc < COLS and 0 <= fr < ROWS):
            return False
        if self.room.cells[fr][fc] != EMPTY:
            return False
        self.room.cells[fr][fc] = CRATE
        self.carry = 0
        return True

    def teleport(self, col, row):
        """Στο ΔΗΛΩΜΕΝΟ κελί προορισμού.

        Παλιά έψαχνε "τον άλλον teleporter στο δωμάτιο": δούλευε μόνο με
        ακριβώς δύο, και ο σχεδιαστής δεν είχε κανέναν έλεγχο. Τώρα ο
        προορισμός δηλώνεται ρητά· αδήλωτος teleporter δεν κάνει τίποτα.

        Η φορά βαρύτητας ΔΙΑΤΗΡΕΙΤΑΙ — αλλιώς η τηλεμεταφορά θα ήταν και κρυφό
        flip, και ο παίκτης δεν θα μπορούσε να προβλέψει πού θα βρεθεί.
        """
        dest = self.room.teleports.get((col, row))
        if dest is None:
            return False
        c, r = dest
        self.x = c * CELL + CELL // 2
        self.y = GRID_Y0 + r * CELL + CELL // 2
        self.warp = True
        return True

    def touch_objects(self):
        """Αντιδράσεις σε ό,τι ακουμπάει το σώμα. Καλείται μία φορά ανά frame."""
        col, row = self.x // CELL, (self.y - GRID_Y0) // CELL
        t = self.room.cell(col, row)
        pr = PROPS[t]

        if pr & F_PICKUP:
            self.room.cells[row][col] = EMPTY
            if t == ENERGY:
                self.energy = min(ENERGY_MAX, self.energy + ENERGY_PICK)
            elif t == PARACHUTE:
                self.parachute += 1
            elif t == KEY:
                self.keys[self.room.attr(col, row)] += 1
        elif t == EXIT:
            self.won = True
        elif t == SWITCH and (col, row) != self.prev_body:
            # ΤΟ ΠΑΤΑΣ, ΔΕΝ ΤΟ ΞΟΔΕΥΕΙΣ: ο διακόπτης γυρίζει κάθε πόρτα του
            # καναλιού του και μένει εκεί. Ένας διακόπτης μπορεί να οδηγεί
            # ΠΟΛΛΕΣ πόρτες — αυτό είναι το νόημα του καναλιού.
            self.toggle_gates(self.room.attr(col, row))
        self.prev_body = (col, row)

        # Τα αγκάθια πονάνε μόνο αν πέφτεις ΠΑΝΩ στις μύτες: η βαρύτητα πρέπει
        # να δείχνει αντίθετα από την όψη τους. Από πίσω είναι απλό πάτωμα.
        # ΕΥΘΡΑΥΣΤΟ: καταρρέει μόλις φύγεις από πάνω του.
        sc = self.support_cell()
        if self.prev_cell is not None and sc != self.prev_cell:
            pc, pr = self.prev_cell
            if PROPS[self.room.cell(pc, pr)] & F_FRAGILE:
                self.room.cells[pr][pc] = EMPTY
                self.moved_cells.append((pc, pr))
        self.prev_cell = sc

        st = self.support_type()
        if PROPS[st] & F_DEADLY and (FACING[st] + 4) % 8 == self.g:
            # Ο μετρητής μηδενίζεται όταν ΔΕΝ πατάς αγκάθι, ώστε το πρώτο
            # χτύπημα να είναι άμεσο και το επόμενο να αργεί.
            if self.spike_tick == 0:
                self.hurt(SPIKE_DMG)
            self.spike_tick = (self.spike_tick + 1) % SPIKE_TICKS
        else:
            self.spike_tick = 0

    def hurt(self, n):
        self.energy = max(0, self.energy - n)

    def noflip(self):
        """Είναι μέσα σε ζώνη όπου απαγορεύεται η αλλαγή βαρύτητας;"""
        return bool(PROPS[self.body_cell()] & F_NOFLIP)

    def slipping(self):
        """Γλιστράει; Ναι αν η βαρύτητα δεν είναι κάθετη στην επιφάνεια.

        Ακριβές, γιατί το κελί λέει μονοσήμαντα ποια φορά "στέκεται" πάνω του:
        σε ράμπα μόνο η διαγώνια της, σε στερεό μόνο οι τέσσερις ορθές. Από εδώ
        βγαίνει ο κανόνας "διαγώνια βαρύτητα σε επίπεδο πάτωμα -> γλιστράς".
        """
        st = self.support_type()
        if st == EMPTY:
            return False                      # δεν ακουμπάει: πτώση, όχι γλίστρημα
        if st in RAMP_GRAVITY:
            return self.g != RAMP_GRAVITY[st]
        return self.g % 2 == 1

    # --- κίνηση ---------------------------------------------------
    def rotate(self, steps):
        self.g = (self.g + steps) % 8

    def snap(self):
        """Κάθισε τα πέλματα ακριβώς πάνω στην επιφάνεια."""
        gx, gy = GSTEP[self.g]
        for _ in range(SCAN_MAX):
            k = self.ground_depth(0)
            if k is None:
                return False
            if abs(k - FEET_B) <= 1:
                return True
            step = 1 if k > FEET_B else -1
            self.x += gx * step
            self.y += gy * step
        return False

    def update(self, walk=0, run=False):
        """Η ΣΕΙΡΑ εδώ είναι ο πυρήνας του παιχνιδιού:

        Η βαρύτητα ευθυγραμμίζεται με την επιφάνεια ΜΟΝΟ μέσα από το περπάτημα
        (do_walk). Αν ο παίκτης βάλει βαρύτητα που δεν ταιριάζει με το πάτωμα,
        δεν "ισιώνει" μόνη της — ο ήρωας γλιστράει. Αν το κάναμε ανάποδα, το
        γλίστρημα δεν θα συνέβαινε ποτέ.
        """
        self.moved_cells = []
        self.crate_step()
        self.touch_objects()        # και στον αέρα: μαζεύεις πέφτοντας
        k = self.ground_depth(0)
        if k is None or k > FEET_B + 2:
            self.fall_step()
            return
        if self.state == "FALL":
            self.land()
        # Το ΠΕΡΠΑΤΗΜΑ ευθυγραμμίζει τη βαρύτητα με την επιφάνεια (§2.3). Ο
        # έλεγχος γλιστρήματος πρέπει να γίνει ΜΕΤΑ, αλλιώς ο ήρωας γλιστράει
        # στο πρώτο pixel κάθε ράμπας πριν προλάβει να κουμπώσει πάνω της.
        if walk:
            # Η ταχύτητα ΔΕΝ γίνεται μεγαλύτερο βήμα: εκτελούνται τόσα βήματα
            # του ενός pixel όσα λέει ο συσσωρευτής. Οι γωνίες και οι ράμπες
            # ανιχνεύονται ανά pixel — με βήμα 3 pixel θα προσπερνιόνταν.
            self.walk_acc += WALK_V * (2 if run else 1)
            steps = self.walk_acc >> 8
            self.walk_acc &= 0xFF
            for _ in range(steps):
                self.do_walk(walk)
        elif self.slipping():
            self.fall_step()
        else:
            self.state = "IDLE"
        self.prev_support = self.support_type()

    def fall_step(self):
        """Ένα frame πτώσης: επιταχύνει και εκτελεί τόσα βήματα του 1 pixel
        όσα λέει η ταχύτητα.

        Το γλίστρημα μένει σταθερό στο 1 pixel/frame — είναι κίνηση κατά μήκος
        επιφάνειας, όχι πτώση, και σε puzzle game η προβλεψιμότητά του μετράει
        περισσότερο από τη φυσική ακρίβεια.
        """
        if self.state != "FALL":
            self.fall_v = FALL_V0
            self.fall_acc = 0
        # Ανοίγει ΜΟΝΟ όταν η πτώση ξεπεράσει το ασφαλές όριο. Αν άνοιγε σε κάθε
        # πτώση, ένα σκαλοπάτι δύο pixel θα το κατανάλωνε.
        if self.parachute and not self.para_open and self.fall_dist >= FALL_SAFE:
            self.para_open = 1
        self.fall_v = min(self.fall_v + FALL_ACCEL, FALL_VMAX)
        if self.para_open:
            self.fall_v = PARA_V        # σταθερή, αργή κάθοδος· καμία ζημιά
        self.fall_acc += self.fall_v
        steps = self.fall_acc >> 8
        self.fall_acc &= 0xFF
        for _ in range(steps):
            if not self.do_fall():
                return                  # ακούμπησε ή γλίστρησε

    def do_fall(self):
        self.state = "FALL"
        gx, gy = GSTEP[self.g]
        if not self.at(0, FEET_B):                 # ελεύθερος -> πέφτε
            self.x += gx
            self.y += gy
            self.fall_dist += 1
            return True
        # ακουμπάει αλλά η επιφάνεια δεν είναι κάθετη -> γλίστρα κατά μήκος της
        t = self.tilt(1)
        slide = 0 if t is None else (1 if t > 0 else -1)
        if slide == 0:
            slide = 1 if not self.at(FOOT_A, FEET_B) else -1
        rx, ry = RSTEP[self.g]
        nx, ny = self.x + rx * slide, self.y + ry * slide
        if not self.room.solid_at(nx, ny):
            self.x, self.y = nx, ny
        self.snap()

    def land(self):
        self.state = "IDLE"
        if self.para_open:
            self.parachute -= 1         # καταναλώνεται ΕΝΑ, όχι όλα
            self.para_open = 0
        elif self.fall_dist > FALL_SAFE:
            self.hurt(1 + (self.fall_dist - FALL_SAFE) // 12)
        self.fall_dist = 0
        self.fall_v = FALL_V0
        self.fall_acc = 0

    def do_walk(self, d):
        """Ένα pixel. Τέσσερις περιπτώσεις, όλες στροφή γύρω από το ίδιο σημείο:
             τοίχος μπροστά   -> -2 βήματα (κοίλη γωνία, 90 μοίρες)
             ανηφόρα 45       -> -1 βήμα
             κατηφόρα 45      -> +1 βήμα
             χάθηκε το έδαφος -> +2 βήματα (κυρτή γωνία, 90 μοίρες)
        """
        self.state = "WALK"
        self.face = d
        ox, oy, og = self.x, self.y, self.g

        if self.wall_ahead(d):
            self.corner(-2 * d, d, ox, oy, og)   # ΚΟΙΛΗ: ανεβαίνει στον τοίχο
            return

        rx, ry = RSTEP[self.g]
        self.x += rx * d
        self.y += ry * d

        if self.ground_depth(0) is None:            # ΚΥΡΤΗ: τέλος πλατώματος
            self.x, self.y = ox, oy
            self.corner(2 * d, d, ox, oy, og)
            return

        self.snap()
        self.align(d)
        if self.slipping() and self.prev_support == self.support_type():
            self.do_fall()          # δεν κούμπωσε και δεν είναι μετάβαση

    def pivot_to(self, newg):
        """Αλλάζει φορά βαρύτητας περιστρέφοντας το σώμα ΓΥΡΩ ΑΠΟ ΤΟ ΣΗΜΕΙΟ
        ΕΠΑΦΗΣ των πελμάτων, όχι γύρω από το κέντρο του.

        Αυτό ήταν το βασικό σφάλμα του μοντέλου: με στροφή γύρω από το κέντρο,
        μετά από κάθε 45 μοίρες τα πέλματα βρίσκονταν 4-5 pixels στο πλάι από
        εκεί που πατούσαν, οπότε ο ήρωας "ξεκολλούσε" από τη ράμπα στη συμβολή
        της με το επίπεδο και γλιστρούσε.
        """
        k = self.ground_depth(0)
        if k is None:
            return False
        gx, gy = GTAB[self.g][k + GSPAN]
        cx, cy = self.x + gx, self.y + gy              # σημείο επαφής
        ngx, ngy = GTAB[newg][FEET_B + GSPAN]
        self.g = newg
        self.x = cx - ngx                              # ίδιο σημείο, νέα φορά
        self.y = cy - ngy
        return self.snap()

    def support_cell(self):
        """Οι συντεταγμένες του κελιού που στηρίζει τα πέλματα, ή None."""
        k = self.ground_depth(0)
        if k is None:
            return None
        gx, gy = GTAB[self.g][k + GSPAN]
        px, py = self.x + gx, self.y + gy
        return px // CELL, (py - GRID_Y0) // CELL

    def support_type(self):
        """Ο τύπος του κελιού που στηρίζει τα πέλματα."""
        k = self.ground_depth(0)
        if k is None:
            return EMPTY
        gx, gy = GTAB[self.g][k + GSPAN]      # ΤΟ ΜΕΤΡΗΜΕΝΟ βάθος επαφής, όχι σταθερό:
        px = self.x + gx              # ένα pixel πιο βαθιά και διαβάζεις το
        py = self.y + gy              # κελί από κάτω
        return self.room.cell(px // CELL, (py - GRID_Y0) // CELL)

    def align(self, d):
        """Ευθυγραμμίζει τη βαρύτητα με την επιφάνεια, ΔΙΑΒΑΖΟΝΤΑΣ το κελί.

        Προηγουμένως εκτιμούσαμε την κλίση από τη διαφορά βάθους των δύο
        πελμάτων. Στη συμβολή ράμπας με επίπεδο τα πέλματα πατάνε σε διαφορετικές
        γεωμετρίες, η μέτρηση έβγαινε ενδιάμεση, και ΚΑΜΙΑ φορά δεν ήταν ευσταθής
        — ο ήρωας κολλούσε στη βάση της ράμπας. Ο τύπος του κελιού είναι
        μονοσήμαντος και δεν έχει αυτό το πρόβλημα.
        """
        st = self.support_type()
        if st in RAMP_GRAVITY:
            if self.g == RAMP_GRAVITY[st]:
                return True
            save = (self.x, self.y, self.g)
            if self.pivot_to(RAMP_GRAVITY[st]) and not self.slipping():
                return True
            # Στο πρώτο pixel μιας ράμπας υπάρχει μόλις 1 pixel υλικού: η
            # περιστροφή γύρω από αυτό θα πετούσε το σώμα πίσω στο επίπεδο.
            # Μένουμε στην τρέχουσα φορά και ξαναδοκιμάζουμε το επόμενο pixel.
            self.x, self.y, self.g = save
            return False
        # ΟΠΟΙΟΣΔΗΠΟΤΕ επίπεδος στερεός τύπος, όχι μόνο ο SOLID: το εύθραυστο,
        # η κλειδαριά, η πόρτα και τα αγκάθια είναι επίσης έδρες που πατάς.
        flat_solid = (PROPS[st] & F_SOLID) and st not in RAMP_GRAVITY
        if flat_solid and self.g % 2 and self.prev_support in RAMP_GRAVITY:
            # βγαίνουμε από ράμπα σε επίπεδη έδρα: ποια από τις δύο γειτονικές
            # ορθές φορές είναι αυτή; Η επιφάνεια είναι επίπεδη, άρα αποφασίζει.
            for cand in ((self.g - 1) % 8, (self.g + 1) % 8):
                save = (self.x, self.y, self.g)
                # Κριτήριο: δεν γλιστράει ΚΑΙ το σώμα δεν είναι μέσα στο υλικό.
                # (Ο έλεγχος κλίσης που ήταν εδώ απέρριπτε τη σωστή λύση: στη
                #  βάση της ράμπας το μπροστινό πέλμα πατάει ακόμα στην κεκλιμένη
                #  επιφάνεια, οπότε η κλίση δεν έχει μηδενίσει.)
                if (self.pivot_to(cand) and not self.slipping()
                        and not self.at(0, 0) and not self.at(0, -FEET_B)):
                    return True
                self.x, self.y, self.g = save
        return False

    def corner(self, steps, d, ox, oy, og):
        """Στροφή 90 μοιρών σε γωνία, ΤΥΛΙΓΟΝΤΑΣ γύρω από την ακμή.

        Το σημείο περιστροφής είναι η ΑΚΜΗ (μπροστινή-κάτω γωνία του σώματος),
        όχι τα πέλματα: στην κοίλη γωνία είναι εκεί που ο τοίχος συναντά το
        πάτωμα, στην κυρτή εκεί που τελειώνει η πλατφόρμα. Και στις δύο, μετά τη
        στροφή η ίδια ακμή βρίσκεται πάλι στην μπροστινή-κάτω γωνία του σώματος —
        γι' αυτό ο τύπος είναι ένας:

            C          = κέντρο + WALL_A*d*R_παλιό + FEET_B*G_παλιό
            νέο κέντρο = C + WALL_A*d*R_νέο - FEET_B*G_νέο
        """
        ex, ey = off(self.g, WALL_A * d, FEET_B)
        cx, cy = self.x + ex, self.y + ey          # η ακμή

        newg = (self.g + steps) % 8
        nrx, nry = RTAB[newg][WALL_A * d + RSPAN]
        ngx, ngy = GTAB[newg][FEET_B + GSPAN]
        self.g = newg
        self.x = cx + nrx - ngx
        self.y = cy + nry - ngy

        if self.snap() and not self.slipping():
            return True
        self.x, self.y, self.g = ox, oy, og      # αδύνατη στροφή: μείνε ως έχεις
        return False


# --- Απεικόνιση για έλεγχο -------------------------------------------
GLYPH = {0: "↓", 1: "↙", 2: "←", 3: "↖",
         4: "↑", 5: "↗", 6: "→", 7: "↘"}
BACK = {EMPTY: " ", SOLID: "█", RAMP_DR: "◢", RAMP_DL: "◣",
        RAMP_UR: "◥", RAMP_UL: "◤"}
for _t in range(NTYPES):            # οι υπόλοιποι τύποι με τον χαρακτήρα τους
    BACK.setdefault(_t, NAMES.get(_t, "?"))


def render(room, hero, w=40, h=24):
    out = [[BACK[room.cell(c, r)] for c in range(w)] for r in range(h)]
    c, r = hero.x // CELL, (hero.y - GRID_Y0) // CELL
    if 0 <= c < w and 0 <= r < h:
        out[r][c] = GLYPH[hero.g]
    return "\n".join("".join(row) for row in out)


def load_room(path=None):
    path = path or os.path.join(LEVELS, "regress.txt")
    with open(path) as f:
        r = Room(f.read())
    m = ROOM_RE.search(os.path.basename(path))
    r.number = int(m.group(1)) if m else 0      # ο αριθμός είναι στο ΟΝΟΜΑ
    r.path = path
    return r


LEVELS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "levels")


def all_rooms():
    """Όλες οι αίθουσες levels/room_<N>.txt, ταξινομημένες ΑΡΙΘΜΗΤΙΚΑ."""
    out = []
    for fn in os.listdir(LEVELS):
        if ROOM_RE.search(fn):
            out.append(load_room(os.path.join(LEVELS, fn)))
    return sorted(out, key=lambda r: r.number)


if __name__ == "__main__":
    room = load_room()
    hero = Hero(room, 60, 40)
    walk = 1 if len(sys.argv) < 2 else int(sys.argv[1])
    for i in range(400):
        hero.update(walk)
    print(render(room, hero))
    print(f"θέση ({hero.x},{hero.y}) βαρύτητα {hero.g} κατάσταση {hero.state}")
