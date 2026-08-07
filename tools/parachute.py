#!/usr/bin/env python3
"""Γεννήτρια του αλεξίπτωτου: 4 φάσεις ανοίγματος, 16x12.

Ίδια λογική με τον stickman: παραμετρικό σχήμα αντί για ζωγραφική pixel-pixel,
ώστε το άνοιγμα να ρυθμίζεται με αριθμούς. Το PNG μένει η τελική αυθεντία.

Οι 4 φάσεις παίζουν ΜΙΑ φορά όταν ανοίγει και μετά κρατάνε την τελευταία.
"""

import math

from cpcgfx import blank, line, put

W, H = 16, 12
CX = 7                  # κέντρο σε x (0..15)
PEN_CANOPY = 3          # πορτοκαλί: ξεχωρίζει από τον λευκό ήρωα
PEN_CORD = 1            # λευκό, όπως τα μέλη του ήρωα

# Ανά φάση: μισό πλάτος θόλου, βάθος θόλου, πόσο ψηλά ξεκινά.
PHASES = [
    (2, 2, 5),          # 0 δεμένο μπόγος
    (4, 3, 3),          # 1 αρχίζει να πιάνει αέρα
    (6, 4, 1),          # 2 μισάνοιχτο
    (7, 5, 0),          # 3 πλήρως ανοιγμένο
]

KNOT_Y = 11             # εκεί συγκλίνουν τα σχοινιά (πάνω από το κεφάλι)


def arc(f, half, depth, top):
    """Ημιελλειπτικός θόλος: από (cx-half, top+depth) ως (cx+half, top+depth)."""
    prev = None
    for i in range(-half, half + 1):
        # y = top + depth * (1 - cos) ώστε οι άκρες να κρέμονται προς τα κάτω
        y = top + depth * (1 - math.cos(i / max(1, half) * math.pi / 2))
        pt = (CX + i, round(y))
        if prev:
            line(f, *prev, *pt, PEN_CANOPY)
        else:
            put(f, *pt, PEN_CANOPY)
        prev = pt
    return prev


def build_frames():
    frames = []
    for half, depth, top in PHASES:
        f = blank(W, H)
        arc(f, half, depth, top)
        # σχοινιά: από τις δύο άκρες του θόλου στον κόμπο
        edge_y = top + depth
        line(f, CX - half, edge_y, CX, KNOT_Y, PEN_CORD)
        line(f, CX + half, edge_y, CX, KNOT_Y, PEN_CORD)
        # ΜΟΝΟ δύο σχοινιά: σε 16x12 τα εσωτερικά περνούν μέσα από τον θόλο
        # και η φιγούρα γίνεται δυσανάγνωστη.
        frames.append(f)
    return frames


FRAME_NAMES = [f"OPEN{i}" for i in range(len(PHASES))]


if __name__ == "__main__":
    from cpcgfx import to_ascii
    for name, fr in zip(FRAME_NAMES, build_frames()):
        print(f"--- {name} ---")
        print(to_ascii(fr))
