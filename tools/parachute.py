#!/usr/bin/env python3
"""Γεννήτρια του αλεξίπτωτου: 4 φάσεις ανοίγματος.

Ίδια λογική με τον stickman: παραμετρικό σχήμα αντί για ζωγραφική pixel-pixel.
Το σχήμα κρατιέται ως λίστα ΕΥΘΥΓΡΑΜΜΩΝ ΤΜΗΜΑΤΩΝ, όχι ως εικόνα, ώστε η
έκδοση των 45 μοιρών να παράγεται περιστρέφοντας τα ΣΗΜΕΙΑ και
ξαναζωγραφίζοντας — καθαρά, χωρίς resampling.

Το αλεξίπτωτο πρέπει να είναι ΠΑΝΤΑ πάνω από το κεφάλι, άρα γυρίζει μαζί με
τη βαρύτητα και στις 8 φορές. Οι ζυγές βγαίνουν από την κανονική δέσμη, οι
μονές από τη δέσμη των 45 — ακριβώς όπως ο ήρωας (docs/sprites.md §2).
"""

import math

from cpcgfx import blank, line

# ΠΕΡΙΤΤΟ πλάτος επίτηδες: με άρτιο, το κέντρο του καμβά πέφτει στο 7.5 ενώ ο
# θόλος είναι στο 7, και το αλεξίπτωτο εμφανιζόταν μισό pixel αριστερά.
W, H = 15, 12
CX = 7                  # ΑΚΡΙΒΩΣ το κέντρο: (W-1)/2 = 7
PEN_CANOPY = 3          # πορτοκαλί: ξεχωρίζει από τον λευκό ήρωα
PEN_CORD = 1            # λευκό, όπως τα μέλη του ήρωα

# Ανά φάση: μισό πλάτος θόλου, βάθος θόλου, πόσο ψηλά ξεκινά.
PHASES = [
    (2, 2, 5),          # 0 δεμένος μπόγος
    (4, 3, 3),          # 1 αρχίζει να πιάνει αέρα
    (6, 4, 1),          # 2 μισάνοιχτο
    (7, 5, 0),          # 3 πλήρως ανοιγμένο
]

KNOT_Y = 11             # εκεί συγκλίνουν τα σχοινιά (προς το κεφάλι του ήρωα)


def shape(half, depth, top):
    """Γεωμετρία μιας φάσης ως τμήματα (x0,y0,x1,y1,pen), ανεξάρτητα από καμβά.

    Θόλος: y = top + depth*(1-cos), ώστε οι άκρες να κρέμονται προς τα κάτω.
    Μόνο δύο σχοινιά — σε αυτό το μέγεθος τα εσωτερικά περνούν μέσα από τον
    θόλο και η φιγούρα γίνεται δυσανάγνωστη.
    """
    segs, prev = [], None
    for i in range(-half, half + 1):
        y = top + depth * (1 - math.cos(i / half * math.pi / 2))
        pt = (CX + i, y)
        if prev is not None:
            segs.append((*prev, *pt, PEN_CANOPY))
        prev = pt
    edge = top + depth
    segs.append((CX - half, edge, CX, KNOT_Y, PEN_CORD))
    segs.append((CX + half, edge, CX, KNOT_Y, PEN_CORD))
    return segs


def rot45(segs):
    """Περιστροφή των ΣΗΜΕΙΩΝ κατά 45 μοίρες δεξιόστροφα, γύρω από το κέντρο."""
    k = math.sqrt(0.5)
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0

    def r(x, y):
        dx, dy = x - cx, y - cy
        return (cx + (dx - dy) * k, cy + (dx + dy) * k)

    return [(*r(x0, y0), *r(x1, y1), pen) for x0, y0, x1, y1, pen in segs]


# Καμβάς των 45 μοιρών: υπολογίζεται ΣΥΜΜΕΤΡΙΚΑ γύρω από το κέντρο
# περιστροφής, ώστε το κέντρο του sprite να παραμένει το ίδιο φυσικό σημείο.
# Αλλιώς το αλεξίπτωτο θα μετατοπιζόταν κάθε φορά που γυρίζει.
_PIVOT = ((W - 1) / 2.0, (H - 1) / 2.0)


def _radius(all_segs):
    rx = max(abs(v - _PIVOT[0]) for s in all_segs for v in (s[0], s[2]))
    ry = max(abs(v - _PIVOT[1]) for s in all_segs for v in (s[1], s[3]))
    return rx, ry


_ALL45 = [s for p in PHASES for s in rot45(shape(*p))]
_RX, _RY = _radius(_ALL45)
W45 = 2 * int(math.ceil(_RX)) + 1
H45 = 2 * int(math.ceil(_RY)) + 1
_DX45 = (W45 - 1) / 2.0 - _PIVOT[0]
_DY45 = (H45 - 1) / 2.0 - _PIVOT[1]


def _render(segs, w, h, dx, dy):
    f = blank(w, h)
    for x0, y0, x1, y1, pen in segs:
        line(f, x0 + dx, y0 + dy, x1 + dx, y1 + dy, pen)
    return f


def build_frames():
    """Οι 4 φάσεις στην κανονική φορά (16x12)."""
    return [_render(shape(*p), W, H, 0, 0) for p in PHASES]


def build_frames45():
    """Οι ίδιες 4 φάσεις γυρισμένες 45 μοίρες."""
    return [_render(rot45(shape(*p)), W45, H45, _DX45, _DY45) for p in PHASES]


FRAME_NAMES = [f"OPEN{i}" for i in range(len(PHASES))]


if __name__ == "__main__":
    import sys
    from cpcgfx import to_ascii
    which = sys.argv[1] if len(sys.argv) > 1 else "0"
    frames = build_frames45() if which == "45" else build_frames()
    print(f"καμβάς: {W}x{H} κανονικά, {W45}x{H45} στις 45 μοίρες")
    for name, fr in zip(FRAME_NAMES, frames):
        print(f"--- {name} ---")
        print(to_ascii(fr))
