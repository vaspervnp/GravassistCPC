#!/usr/bin/env python3
"""Επαλήθευση του αλγορίθμου του src/rotate.asm.

Δεν προσομοιώνει Z80. Υλοποιεί ΤΟΝ ΙΔΙΟ αλγόριθμο (τους ίδιους πίνακες
start/dx/dy και packing) και τον συγκρίνει με μια αφελή, προφανώς σωστή
"περίστρεψε και μετά πάκαρε" υλοποίηση. Έτσι πιάνονται τα λάθη που είναι
πιθανότερα: λάθος offset, λάθος πρόσημο, λάθος bits του MODE 1.

    python3 tools/verify_rotate.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stickman
from cpcgfx import blank

PIXTAB = [
    [0x00, 0x00, 0x00, 0x00],
    [0x80, 0x40, 0x20, 0x10],
    [0x08, 0x04, 0x02, 0x01],
    [0x88, 0x44, 0x22, 0x11],
]
ANDTAB = [0x77, 0xBB, 0xDD, 0xEE]

DOWN, LEFT, UP, RIGHT = 0, 1, 2, 3


def setup(orient, W, H):
    """Ο πίνακας του docs/sprites.md §2 / spr_set0..3."""
    if orient == DOWN:
        return 0, 1, W, W, H
    if orient == LEFT:
        return (H - 1) * W, -W, 1, H, W
    if orient == UP:
        return W * H - 1, -1, -W, W, H
    return W - 1, W, -1, H, W        # RIGHT


def table_driven(frame, orient, shift):
    """Αντίγραφο του spr_transform: μία πέραση, μόνο με start/dx/dy."""
    H, W = len(frame), len(frame[0])
    flat = [p for row in frame for p in row]
    start, dx, dy, dw, dh = setup(orient, W, H)
    bw = (dw + shift + 3) // 4

    buf = [[0xFF, 0x00] for _ in range(bw * dh)]
    row_ptr = start
    for y in range(dh):
        p = row_ptr
        slot = shift
        byte = 0
        for x in range(dw):
            pen = flat[p]
            if pen:
                i = y * bw + byte
                buf[i][0] &= ANDTAB[slot]
                buf[i][1] |= PIXTAB[pen][slot]
            slot += 1
            if slot == 4:
                slot = 0
                byte += 1
            p += dx
        row_ptr += dy
    return bw, dh, buf


def naive(frame, orient, shift):
    """Αφελής αναφορά: πρώτα περιστροφή σε νέο πίνακα, μετά packing."""
    H, W = len(frame), len(frame[0])
    if orient == DOWN:
        rot = [row[:] for row in frame]
    elif orient == LEFT:                       # 90 δεξιόστροφα
        rot = [[frame[H - 1 - x][y] for x in range(H)] for y in range(W)]
    elif orient == UP:                         # 180
        rot = [row[::-1] for row in frame[::-1]]
    else:                                      # 90 αριστερόστροφα
        rot = [[frame[x][W - 1 - y] for x in range(H)] for y in range(W)]

    dh, dw = len(rot), len(rot[0])
    bw = (dw + shift + 3) // 4
    buf = [[0xFF, 0x00] for _ in range(bw * dh)]
    for y in range(dh):
        for x in range(dw):
            pen = rot[y][x]
            if pen:
                pos = x + shift
                i = y * bw + (pos // 4)
                buf[i][0] &= ANDTAB[pos % 4]
                buf[i][1] |= PIXTAB[pen][pos % 4]
    return bw, dh, buf


def check(frames, label):
    bad = 0
    for fi, fr in enumerate(frames):
        for orient in range(4):
            for shift in range(4):
                a = table_driven(fr, orient, shift)
                b = naive(fr, orient, shift)
                if a != b:
                    bad += 1
                    if bad <= 3:
                        print(f"  ΔΙΑΦΟΡΑ: {label} frame {fi}, "
                              f"orient {orient}, shift {shift}")
    n = len(frames) * 16
    print(f"  {label}: {n - bad}/{n} συνδυασμοί σωστοί")
    return bad


def rot90_pt(pt, W, H, times):
    """Πού καταλήγει ένα σημείο μετά από `times` περιστροφές 90 δεξιόστροφα.
    Ίδια αντιστοίχιση με τη naive(): (x,y) -> (H-1-y, x)."""
    x, y = pt
    for _ in range(times % 4):
        x, y, W, H = H - 1 - y, x, H, W
    return x, y


def check_gravity_dirs():
    """Ελέγχει ότι για κάθε φορά βαρύτητας 0..7 τα πόδια δείχνουν όντως εκεί.

    Πιάνει το λάθος που είναι πιο εύκολο να γίνει και πιο δύσκολο να δεις:
    αν η rot45 γυρίζει αριστερόστροφα ενώ ο πίνακας των 90 δεξιόστροφα, οι
    μονές φορές βγαίνουν καθρεφτισμένες και μόνο ο emulator θα το δείξει.
    """
    import math
    base = stickman.BASE
    bad = 0
    for g in range(8):
        if g % 2 == 0:
            p, W, H = base, stickman.W, stickman.H
        else:
            p, W, H = stickman.rot45(base), stickman.W45, stickman.H45
        times = g // 2

        head = rot90_pt(p["head"], W, H, times)
        feet = rot90_pt(((p["foot_l"][0] + p["foot_r"][0]) / 2,
                         (p["foot_l"][1] + p["foot_r"][1]) / 2), W, H, times)
        vx, vy = feet[0] - head[0], feet[1] - head[1]

        # αναμενόμενη φορά: το (0,+1) γυρισμένο g*45 δεξιόστροφα
        a = math.radians(g * 45)
        ex, ey = -math.sin(a), math.cos(a)
        cos = (vx * ex + vy * ey) / math.hypot(vx, vy)
        ok = cos > 0.97                     # < 14 μοίρες απόκλιση
        if not ok:
            bad += 1
            err = math.degrees(math.acos(max(-1, min(1, cos))))
            print(f"  ΛΑΘΟΣ ΦΟΡΑ: gravity {g} ({g*45} μοίρες), "
                  f"απόκλιση {err:.0f} μοίρες")
    print(f"  φορές βαρύτητας: {8 - bad}/8 δείχνουν σωστά")
    return bad


if __name__ == "__main__":
    print("Επαλήθευση αλγορίθμου περιστροφής (src/rotate.asm):")
    bad = check(stickman.build_frames(), "ήρωας 7x12")
    bad += check(stickman.build_frames45(), "ήρωας 13x13 @45")
    bad += check_gravity_dirs()

    # Μη τετράγωνο μέγεθος: πιάνει λάθη όπου μπερδεύονται W και H.
    odd = [blank(5, 9) for _ in range(1)]
    for y in range(9):
        for x in range(5):
            odd[0][y][x] = (x + y) % 4
    bad += check(odd, "δοκιμαστικό 5x9")

    print("ΟΛΑ ΣΩΣΤΑ" if bad == 0 else f"{bad} ΑΠΟΤΥΧΙΕΣ")
    sys.exit(1 if bad else 0)
