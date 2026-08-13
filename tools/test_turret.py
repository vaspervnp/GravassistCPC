#!/usr/bin/env python3
"""Ο πυργίσκος, απαίτηση προς απαίτηση.

Κάθε έλεγχος εδώ αντιστοιχεί σε μία πρόταση της προδιαγραφής: ρίχνει προς τη
μεριά που είσαι, πιο γρήγορα από το βάδισμα και πιο αργά από το τρέξιμο,
ξαναρίχνει μετά από 5 δευτερόλεπτα, εμβέλεια 80 pixel, ζημιά μεγαλύτερη από
κοντά. Αν κάποια αλλάξει, εδώ φαίνεται ποια.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def room(cells, gravity=0):
    """Άδειο δωμάτιο με τοίχους, και ό,τι βάλεις: [(col, row, char), ...]"""
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for c, r, ch in cells:
        rows[r][c] = ch
    txt = ";\n" + "\n".join("".join(x) for x in rows) + f"\ngravity {gravity}\n"
    rm = P.Room(txt)
    rm.number, rm.path = 1, ""
    return rm


def settled(rm, col, row):
    """Ήρωας που έχει ήδη προσγειωθεί, με καθαρή κατάσταση πυργίσκων."""
    h = P.Hero(rm, col * P.CELL + P.CELL // 2, P.GRID_Y0 + row * P.CELL)
    for _ in range(40):
        h.update(0)
    h.arrows.clear()
    h.turret_ready.clear()
    h.energy = P.ENERGY_MAX
    h.hurt_left = 0
    return h


def cy_of(row):
    return P.GRID_Y0 + row * P.CELL + P.CELL // 2


print("--- ρίχνει προς τη μεριά που είμαι")
# Πυργίσκος στη μέση, ήρωας ΠΑΝΩ και ΚΑΤΩ: το βέλος πρέπει να αλλάζει φορά.
for row, want, label in ((21, +1, "κάτω"), (13, -1, "πάνω")):
    # Ο ήρωας στέκεται σε ράφι· ΚΑΘΑΡΗ ευθεία ως τον πυργίσκο, χωρίς τοίχο
    # ανάμεσα — ο προηγούμενος έλεγχος έβαζε τον τοίχο ο ίδιος και μετά
    # παραπονιόταν ότι ο πυργίσκος δεν βλέπει.
    # ΣΤΟΝ ΑΕΡΑ ΓΙΑ ΤΗΝ ΠΑΝΩ ΠΕΡΙΠΤΩΣΗ, επίτηδες: ένα ράφι για να σταθεί
    # πάνω από τον πυργίσκο θα ήταν το ίδιο εμπόδιο που κρύβει τον πυργίσκο.
    # Το turret_step τρέχει ΠΡΙΝ το fall_step, οπότε η πρώτη ενημέρωση τον
    # βρίσκει ακόμα εκεί που τον έβαλα.
    rm = room([(10, 16, "I")])
    if row == 21:
        h = settled(rm, 10, row - 1)
        h.arrows.clear()
        h.turret_ready.clear()
    else:
        h = P.Hero(rm, 10 * P.CELL + P.CELL // 2, cy_of(row))
    h.update(0)
    got = h.arrows[0]["dy"] if h.arrows else 0
    check(f"ήρωας {label} από τον πυργίσκο -> βέλος προς τα {label}",
          got == want, f"dy={got}")

rm = room([(16, 21, "=")])
h = settled(rm, 10, 21)
h.arrows.clear(); h.turret_ready.clear()
h.update(0)
check("οριζόντιος πυργίσκος ρίχνει προς τα αριστερά",
      bool(h.arrows) and h.arrows[0]["dx"] == -1,
      str(h.arrows[0] if h.arrows else None))

print("--- ταχύτητα: πιο γρήγορο από το βάδισμα, πιο αργό από το τρέξιμο")
check("το βέλος κάνει 6 pixel ανά ενημέρωση", P.ARROW_STEP == 6)
check("…το βάδισμα 4", (P.WALK_V >> 8) == 4)
check("…το τρέξιμο 8", ((P.WALK_V * 2) >> 8) == 8)
check("άρα βάδισμα < βέλος < τρέξιμο",
      (P.WALK_V >> 8) < P.ARROW_STEP < ((P.WALK_V * 2) >> 8))

# ΚΑΙ ΣΤΗΝ ΠΡΑΞΗ, όχι μόνο στις σταθερές: ο ήρωας φεύγει από τον άξονα με
# βάδισμα και με τρέξιμο, και μετράμε αν τον προλαβαίνει.
for run, escapes, label in ((False, False, "περπατώντας"), (True, True, "τρέχοντας")):
    rm = room([(6, 21, "=")])
    h = settled(rm, 8, 21)
    h.arrows.clear(); h.turret_ready.clear()
    h.update(0)                                     # ρίχνει προς τα δεξιά
    fired = bool(h.arrows)
    hit = False
    for _ in range(30):
        h.update(1, run)                            # φύγε μακριά από αυτόν
        if h.energy < P.ENERGY_MAX:
            hit = True
            break
    check(f"{label} {'ξεφεύγει' if escapes else 'ΔΕΝ ξεφεύγει'}",
          fired and (hit != escapes), f"ρίχτηκε={fired}, χτυπήθηκε={hit}")

print("--- εμβέλεια 80 pixel, και στα δύο")
rm = room([(10, 4, "I")])
h = settled(rm, 10, 21)                             # ~140 px κάτω, εκτός εμβέλειας
d = h.y - cy_of(4)
h.update(0)
check(f"εκτός εμβέλειας ({d} px) δεν ρίχνει", not h.arrows, f"{len(h.arrows)}")

rm = room([(10, 16, "I")])
h = settled(rm, 30, 21)                             # στο πάτωμα, ΑΛΛΗ στήλη
h.update(0)
check("εκτός άξονα δεν ρίχνει", not h.arrows)

# Το βέλος σβήνει μόλις διανύσει την εμβέλεια, χωρίς να βρει κανέναν.
rm = room([(10, 4, "I"), (10, 12, "#")])
h = settled(rm, 30, 21)
h.arrows.append({"x": 84, "y": cy_of(4) + 5, "dx": 0, "dy": 1, "gone": 0})
steps = 0
while h.arrows and steps < 100:
    h.arrows_step()
    steps += 1
check("το βέλος σβήνει μέσα στην εμβέλεια",
      steps * P.ARROW_STEP <= P.TURRET_RANGE + P.ARROW_STEP,
      f"{steps} βήματα x {P.ARROW_STEP} px")

print("--- σταματά σε τοίχο, και δεν ρίχνει μέσα από αυτόν")
rm = room([(10, 16, "I"), (10, 19, "#")])           # τοίχος ανάμεσα
h = settled(rm, 10, 21)
h.update(0)
check("τοίχος στη μέση: ο πυργίσκος δεν ρίχνει", not h.arrows)

rm = room([(10, 16, "I"), (10, 19, "#")])
h = settled(rm, 10, 21)
h.arrows.append({"x": 84, "y": cy_of(16) + 5, "dx": 0, "dy": 1, "gone": 0})
e = h.energy
for _ in range(20):
    h.arrows_step()
check("βέλος που ρίχτηκε σταματά στον τοίχο και δεν με βρίσκει",
      not h.arrows and h.energy == e, f"ενέργεια {h.energy}")

print("--- ζημιά: μεγαλύτερη από κοντά")
d_near = P.Hero(room([]), 0, 0)
vals = [d_near.arrow_damage(g) for g in (0, P.TURRET_RANGE // 2,
                                         P.TURRET_RANGE - 1)]
check("κοντά > μεσαία > μακριά", vals[0] > vals[1] > vals[2], str(vals))
check("και ταιριάζουν με το ARROW_DMG", tuple(vals) == P.ARROW_DMG, str(vals))

print("--- φόρτιση 5 δευτερολέπτων, μετρημένη σε ΧΡΟΝΟ")
rm = room([(10, 16, "I")])
h = settled(rm, 10, 21)
h.update(0)
check("ρίχνει αμέσως μόλις είναι φορτισμένος", len(h.arrows) == 1)
t0 = h.clock
h.arrows.clear()
gap = None
for _ in range(400):
    h.update(0)
    if h.arrows:
        gap = h.clock - t0
        break
check("ξαναρίχνει μετά από 5 δευτερόλεπτα",
      gap is not None and abs(gap - P.TURRET_RELOAD) <= P.CPC_VSYNC_RUN,
      f"{gap} vsync = {gap / 50:.2f}s" if gap else "δεν ξαναέριξε")

# ΤΟ ΚΡΙΣΙΜΟ: ο ίδιος χρόνος ΚΑΙ όταν ο παίκτης τρέχει. Ένας μετρητής
# περασμάτων θα έδινε 11 δευτερόλεπτα εδώ και 5 παραπάνω — ο πυργίσκος θα
# άραζε ακριβώς όταν τον αποφεύγεις.
# ΟΡΙΖΟΝΤΙΟΣ πυργίσκος: τρέχοντας πάνω στο πάτωμα ο ήρωας μένει στην ευθεία
# του, οπότε μετράμε καθαρά τον ΧΡΟΝΟ και όχι το αν βγήκε από τη γραμμή.
rm = room([(4, 21, "=")])
h = settled(rm, 12, 21)
h.arrows.clear(); h.turret_ready.clear()
h.update(0)
t0 = h.clock
h.arrows.clear()
gap_run = None
for _ in range(400):
    # ΜΕΣΑ ΣΤΗΝ ΕΜΒΕΛΕΙΑ όλη την ώρα: με μεγαλύτερη διαδρομή ο ήρωας έβγαινε
    # πέρα από τα 80 pixel και ο έλεγχος μετρούσε την απόσταση αντί για τον χρόνο.
    h.update(1 if (h.x < 11 * P.CELL) else -1, True)
    if h.arrows:
        gap_run = h.clock - t0
        break
check("…και ο ίδιος χρόνος ενώ ο παίκτης τρέχει",
      gap_run is not None and abs(gap_run - P.TURRET_RELOAD) <= 2 * P.CPC_VSYNC_RUN,
      f"{gap_run} vsync = {gap_run / 50:.2f}s" if gap_run else "δεν ξαναέριξε")

print("--- το πολύ δύο βέλη στον αέρα")
rm = room([(10, 16, "I"), (20, 16, "I"), (30, 16, "I")])
h = settled(rm, 10, 21)
h.x = 10 * P.CELL + P.CELL // 2
for _ in range(3):
    h.turret_ready.clear()
    h.turret_step()
check(f"δεν ξεπερνά τα {P.TURRET_MAX}", len(h.arrows) <= P.TURRET_MAX,
      str(len(h.arrows)))

print("--- ο πυργίσκος είναι εμπόδιο")
check("στερεός", bool(P.PROPS[P.TURRET_V] & P.F_SOLID))
check("…αλλά δεν πονάει με την αφή",
      not (P.PROPS[P.TURRET_V] & P.F_DEADLY))

print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"ΑΠΕΤΥΧΑΝ {len(FAILS)}")
sys.exit(1 if FAILS else 0)
