#!/usr/bin/env python3
"""Εξάγει το μοντέλο σε JavaScript, για το test run μέσα στον editor.

    python3 tools/genjs.py

Παράγει editor/wwwroot/game/data.js

ΓΙΑΤΙ: η φυσική υπάρχει πλέον σε ΤΡΕΙΣ υλοποιήσεις — tools/physics.py (αναφορά),
src/hero.asm (Amstrad) και το JS του editor. Τρία αντίγραφα των ίδιων κανόνων
αποκλίνουν αναπόφευκτα. Η άμυνα είναι η ίδια με τον Z80: ΚΑΝΕΝΑ από τα δύο
αντίγραφα δεν υπολογίζει γεωμετρία ή ιδιότητες — τα διαβάζει από πίνακες που
παράγονται εδώ, από το μοντέλο. Ό,τι μένει είναι μεταγραφή ροής, που ελέγχεται
από το tools/parity.py.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
from genasm import tile_pixels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "editor", "wwwroot", "game", "data.js")


def sprite_frames(frames):
    """Frames σε συμπαγή μορφή: μία συμβολοσειρά ψηφίων pen ανά γραμμή."""
    return ["".join("".join(str(v) for v in row) for row in f) for f in frames]


def build():
    import parachute
    import stickman

    return {
        "CELL": P.CELL, "COLS": P.COLS, "ROWS": P.ROWS, "GRID_Y0": P.GRID_Y0,
        "NTYPES": P.NTYPES,
        "TYPE_NAMES": P.TYPE_NAMES,
        "CHARS": P.CHARS,
        "PROPS": P.PROPS,
        "FACING": {str(k): v for k, v in P.FACING.items()},
        "RAMP_GRAVITY": {str(k): v for k, v in P.RAMP_GRAVITY.items()},
        "F": {"SOLID": P.F_SOLID, "DEADLY": P.F_DEADLY, "PICKUP": P.F_PICKUP,
              "NOFLIP": P.F_NOFLIP, "FRAGILE": P.F_FRAGILE,
              "ONEWAY": P.F_ONEWAY, "TRIGGER": P.F_TRIGGER},

        # Σχήμα των ραμπών ως μάσκα 8x8, ώστε το JS να μην ξαναγράψει τις
        # ανισότητες (u+v>=7 κ.λπ.) και να μην μπορεί να τις γράψει λάθος.
        "RAMP_MASK": {str(t): [[1 if P.RAMP_TEST[t](u, v) else 0
                                for u in range(P.CELL)] for v in range(P.CELL)]
                      for t in P.RAMP_TEST},

        # Γεωμετρία βαρύτητας — ΟΙ ΙΔΙΟΙ πίνακες με τον Z80.
        "GSPAN": P.GSPAN, "RSPAN": P.RSPAN,
        "GTAB": P.GTAB, "RTAB": P.RTAB,
        "GSTEP": P.GSTEP, "RSTEP": P.RSTEP,

        "K": {"FEET_B": P.FEET_B, "FOOT_A": P.FOOT_A, "WALL_A": P.WALL_A,
              "SCAN_MAX": P.SCAN_MAX, "FALL_SAFE": P.FALL_SAFE,
              "FALL_V0": P.FALL_V0, "FALL_ACCEL": P.FALL_ACCEL,
              "FALL_VMAX": P.FALL_VMAX, "PARA_V": P.PARA_V,
              "ENERGY_MAX": P.ENERGY_MAX, "ENERGY_PICK": P.ENERGY_PICK,
              "SPIKE_DMG": P.SPIKE_DMG, "CRATE_TICKS": P.CRATE_TICKS},

        # Γραφικά: τιμές pen ανά pixel, ίδια πηγή με τα tiles του Amstrad.
        "PALETTE": ["#000080", "#FFFFFF", "#00FF00", "#FF8000"],
        "TILE_PX": [tile_pixels(t) for t in range(P.NTYPES)],
        "HERO": {"w": stickman.W, "h": stickman.H,
                 "frames": sprite_frames(stickman.build_frames())},
        "HERO45": {"w": stickman.W45, "h": stickman.H45,
                   "frames": sprite_frames(stickman.build_frames45())},
        "PARA": {"w": parachute.W, "h": parachute.H,
                 "frames": sprite_frames(parachute.build_frames())},
        "PARA45": {"w": parachute.W45, "h": parachute.H45,
                   "frames": sprite_frames(parachute.build_frames45())},
    }


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = build()
    with open(OUT, "w") as f:
        f.write("// ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genjs.py — ΜΗΝ το επεξεργάζεσαι.\n")
        f.write("// Πηγή: tools/physics.py. Δες το docstring του genjs.py για το γιατί.\n")
        f.write("window.GAME_DATA = ")
        json.dump(data, f, separators=(",", ":"))
        f.write(";\n")
    print(f"  {os.path.relpath(OUT, ROOT)}: {os.path.getsize(OUT)} bytes")
