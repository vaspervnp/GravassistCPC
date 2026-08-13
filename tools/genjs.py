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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
import genasm as GA
from genasm import arrow_pixels, tile_pixels

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
              "ONEWAY": P.F_ONEWAY, "TRIGGER": P.F_TRIGGER,
              "SWITCH": P.F_SWITCH},

        # Off <-> on for every switch facing. A table and not arithmetic: the
        # eight type numbers are not contiguous.
        "SWITCH_FLIP": {str(k): v for k, v in
                        list(P.SWITCH_ON_OF.items()) + list(P.SWITCH_OFF_OF.items())},

        # Σχήμα των ραμπών ως μάσκα 8x8, ώστε το JS να μην ξαναγράψει τις
        # ανισότητες (u+v>=7 κ.λπ.) και να μην μπορεί να τις γράψει λάθος.
        "RAMP_MASK": {str(t): [[1 if P.RAMP_TEST[t](u, v) else 0
                                for u in range(P.CELL)] for v in range(P.CELL)]
                      for t in P.RAMP_TEST},

        # Γεωμετρία βαρύτητας — ΟΙ ΙΔΙΟΙ πίνακες με τον Z80.
        "GSPAN": P.GSPAN, "RSPAN": P.RSPAN,
        "GTAB": P.GTAB, "RTAB": P.RTAB,
        "GSTEP": P.GSTEP, "RSTEP": P.RSTEP,

        "K": {"WALK_V": P.WALK_V,
              "FEET_B": P.FEET_B, "FOOT_A": P.FOOT_A, "WALL_A": P.WALL_A,
              "SCAN_MAX": P.SCAN_MAX, "FALL_SAFE": P.FALL_SAFE,
              "FALL_V0": P.FALL_V0, "FALL_ACCEL": P.FALL_ACCEL,
              "FALL_VMAX": P.FALL_VMAX, "PARA_V": P.PARA_V,
              "ENERGY_MAX": P.ENERGY_MAX, "ENERGY_PICK": P.ENERGY_PICK,
              "SPIKE_DMG": P.SPIKE_DMG, "CRATE_TICKS": P.CRATE_TICKS,
              "SPIKE_TICKS": P.SPIKE_TICKS, "HURT_FRAMES": P.HURT_FRAMES, "ATTR_MAX": P.ATTR_MAX,
              "LAND_TICKS": P.LAND_TICKS,
              "TRAIL_MAX": P.TRAIL_MAX, "LOCK_AUTO": P.LOCK_AUTO,
              # Το κόστος καρέ του Amstrad — το test run το χρειάζεται για να
              # τρέχει με τον ρυθμό του σιδήρου και όχι με τα ονομαστικά 50 Hz.
              "CPC_VSYNC_IDLE": P.CPC_VSYNC_IDLE,
              "CPC_VSYNC_WALK": P.CPC_VSYNC_WALK,
              "CPC_VSYNC_RUN": P.CPC_VSYNC_RUN,
              # Το σκορ. Οι ίδιες τιμές με τον Amstrad, από την ίδια πηγή —
              # ένα test run που βαθμολογεί αλλιώς είναι χειρότερο από ένα
              # που δεν βαθμολογεί καθόλου.
              "SCORE_START": P.SCORE_START, "SCORE_EXIT": P.SCORE_EXIT,
              "SCORE_PLATE": P.SCORE_PLATE, "SCORE_GATE": P.SCORE_GATE,
              "SCORE_SWITCH": P.SCORE_SWITCH, "SCORE_LOCK": P.SCORE_LOCK,
              "SCORE_PARA_LAND": P.SCORE_PARA_LAND,
              "SCORE_PARA_KEEP": P.SCORE_PARA_KEEP,
              "SCORE_PICKUP": P.SCORE_PICKUP,
              "SCORE_STEP": P.SCORE_STEP, "SCORE_GRAV": P.SCORE_GRAV,
              # Πυργίσκοι. Το ARROW_DMG είναι τριάδα και όχι αριθμός: η ζημιά
              # εξαρτάται από το πόσο ταξίδεψε το βέλος.
              "ARROW_STEP": P.ARROW_STEP, "TURRET_RANGE": P.TURRET_RANGE,
              "TURRET_RELOAD": P.TURRET_RELOAD, "TURRET_MAX": P.TURRET_MAX,
              "ARROW_DMG": list(P.ARROW_DMG)},

        # Γραφικά: τιμές pen ανά pixel, ίδια πηγή με τα tiles του Amstrad.
        "PALETTE": ["#000080", "#FFFFFF", "#00FF00", "#FF8000"],
        "TILE_PX": [tile_pixels(t) for t in range(P.NTYPES)],
        # Ο τίτλος του μενού: ΤΑ ΙΔΙΑ pixel με τον Amstrad. Ο browser τα
        # ζωγραφίζει μέσα από τον ίδιο buffer με τα πλακίδια, ώστε αυτό που
        # βλέπεις εδώ να είναι αυτό που θα δεις στην οθόνη του CPC.
        "TITLE": {
            "text": GA.TITLE_TEXT,
            "glyphs": {c: GA.TITLE_GLYPHS[c] for c in GA.TITLE_ORDER},
            "x": 80, "y": 14, "scale": 2, "split": 4,
            "pens": [3, 2],
            # Ίδιες τιμές με τα FRAME_* του src/menu.asm: x σε pixel (byte*4),
            # y σε scanlines. Το x1 είναι η ΑΡΙΣΤΕΡΗ ακμή του δεξιού byte.
            # Ίδιες τιμές με τα FRAME_* του src/menu.asm: x σε pixel (byte*4),
            # y σε scanlines. Το x1 είναι η ΑΡΙΣΤΕΡΗ ακμή του δεξιού byte, και
            # το mid το σημείο όπου αλλάζει χρώμα — όπως στο concept art.
            "frame": {"x0": 72, "x1": 244, "y0": 8, "y1": 43, "mid": 144},
        },
        # Βελάκια βαρύτητας του HUD — ίδια πηγή με τον Amstrad, ώστε η δοκιμή
        # στον browser να δείχνει ακριβώς ό,τι θα δεις στην οθόνη του CPC.
        "GRAV_PX": [[arrow_pixels(g, 3) for g in range(8)],
                    [arrow_pixels(g, 2) for g in range(8)]],
        # Τα δύο σταθερά σύμβολα, από το ίδιο σχέδιο με τον Amstrad.
        "HUD_BOLT_PX": [[3 if ch == "X" else 0 for ch in row]
                        for row in GA.HUD_BOLT],
        "HUD_STAR_PX": [[2 if ch == "X" else 0 for ch in row]
                        for row in GA.HUD_STAR],
        # ΟΙ ΘΕΣΕΙΣ ΤΟΥ HUD, σε στήλες byte, από ΜΙΑ πηγή. Ήταν γραμμένες με
        # το χέρι και στις δύο γλώσσες, και όταν μετακινήθηκαν τα βελάκια ο
        # editor έδειχνε άλλο HUD από το παιχνίδι.
        "HUD": {"bolt": 0, "energy": 2, "inv": 22,
                "star": 56, "score_col": 30,
                "grav_w": 76, "grav_h": 78, "score_digits": 6},
        "HERO": {"w": stickman.W, "h": stickman.H,
                 "frames": sprite_frames(stickman.build_frames())},
        "HERO45": {"w": stickman.W45, "h": stickman.H45,
                   "frames": sprite_frames(stickman.build_frames45())},
        "PARA": {"w": parachute.W, "h": parachute.H,
                 "frames": sprite_frames(parachute.build_frames())},
        "PARA45": {"w": parachute.W45, "h": parachute.H45,
                   "frames": sprite_frames(parachute.build_frames45())},
    }


def check_constants(data):
    """Κάθε K.ΚΑΤΙ που διαβάζει η JavaScript πρέπει να εξάγεται από εδώ.

    ΓΙΑΤΙ ΥΠΑΡΧΕΙ: το WALK_V έλειπε από το export και κανείς δεν το πήρε
    είδηση. Στη JavaScript το `undefined * 2` δίνει NaN, το `NaN >> 8` δίνει
    0, και ο ήρωας απλώς δεν περπατούσε — καμία εξαίρεση, κανένα μήνυμα, μόνο
    ένα παιχνίδι που δεν αντιδρούσε στα πλήκτρα. Ένα σκέτο grep το πιάνει.
    """
    used = set()
    game = os.path.join(ROOT, "editor", "wwwroot", "game")
    for name in sorted(os.listdir(game)):
        if not name.endswith(".js") or name == "data.js":
            continue
        with open(os.path.join(game, name)) as f:
            used |= set(re.findall(r"\bK\.([A-Z_0-9]+)", f.read()))
    missing = sorted(used - set(data["K"]))
    if missing:
        raise SystemExit(
            "λείπουν σταθερές από το export της JavaScript: "
            + ", ".join(missing))
    return len(used)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    data = build()
    n = check_constants(data)
    with open(OUT, "w") as f:
        f.write("// ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genjs.py — ΜΗΝ το επεξεργάζεσαι.\n")
        f.write("// Πηγή: tools/physics.py. Δες το docstring του genjs.py για το γιατί.\n")
        f.write("window.GAME_DATA = ")
        json.dump(data, f, separators=(",", ":"))
        f.write(";\n")
    print(f"  {os.path.relpath(OUT, ROOT)}: {os.path.getsize(OUT)} bytes, "
          f"{n} σταθερές σε χρήση")
