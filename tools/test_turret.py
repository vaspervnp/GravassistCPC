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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def room(cells, gravity=0, footer=""):
    """Άδειο δωμάτιο με τοίχους, και ό,τι βάλεις: [(col, row, char), ...]"""
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for c, r, ch in cells:
        rows[r][c] = ch
    txt = ";\n" + "\n".join("".join(x) for x in rows) \
        + f"\ngravity {gravity}\n" + footer
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

print("--- η φόρτιση είναι παράμετρος του κάθε πυργίσκου")


def reload_gap(footer, col=10, trow=16):
    """Πόσος χρόνος περνά ανάμεσα σε δύο βολές, σε vsync."""
    rm = room([(col, trow, "I")], footer=footer)
    h = settled(rm, col, 21)
    h.arrows.clear()
    h.turret_ready.clear()
    h.update(0)
    if not h.arrows:
        return None
    t0 = h.clock
    h.arrows.clear()
    for _ in range(900):
        h.update(0)
        if h.arrows:
            return h.clock - t0
    return None


base = reload_gap("")
check("χωρίς δήλωση: η προεπιλογή των 5 δευτερολέπτων",
      base is not None and abs(base - 5 * 50) <= P.CPC_VSYNC_RUN,
      f"{base} vsync = {base / 50:.2f}s" if base else "δεν ξαναέριξε")
fast = reload_gap("turret 10 16 0 2 0\n")
check("φόρτιση 2: ξαναρίχνει σε 2 δευτερόλεπτα",
      fast is not None and abs(fast - 2 * 50) <= P.CPC_VSYNC_RUN,
      f"{fast} vsync = {fast / 50:.2f}s" if fast else "δεν ξαναέριξε")
slow = reload_gap("turret 10 16 0 7 0\n")
check("φόρτιση 7: ξαναρίχνει σε 7 δευτερόλεπτα",
      slow is not None and abs(slow - 7 * 50) <= P.CPC_VSYNC_RUN,
      f"{slow} vsync = {slow / 50:.2f}s" if slow else "δεν ξαναέριξε")

print("--- αυτόματη βολή: ρυθμός αντί για αντίδραση")
# Ο ήρωας ΜΑΚΡΙΑ και εκτός εμβέλειας: με 0 δεν ρίχνει ποτέ, με ρυθμό ρίχνει.
rm = room([(10, 4, "I")])
h = settled(rm, 30, 21)
for _ in range(200):
    h.update(0)
check("αυτόματα=0 και μακριά: σιωπή", not h.arrows, str(len(h.arrows)))

rm = room([(10, 4, "I")], footer="turret 10 4 0 5 1\n")
h = settled(rm, 30, 21)
h.arrows.clear()
h.turret_ready.clear()
fired = 0
for _ in range(200):
    h.update(0)
    if h.arrows:
        fired += 1
        h.arrows.clear()
check("αυτόματα=1: ρίχνει χωρίς να με βλέπει και χωρίς εμβέλεια",
      fired >= 3, f"{fired} βολές")

# Και ο ρυθμός είναι όντως το δηλωμένο διάστημα.
rm = room([(10, 4, "I")], footer="turret 10 4 0 5 2\n")
h = settled(rm, 30, 21)
h.arrows.clear()
h.turret_ready.clear()
h.update(0)
t0 = h.clock
h.arrows.clear()
gap = None
for _ in range(400):
    h.update(0)
    if h.arrows:
        gap = h.clock - t0
        break
check("αυτόματα=2: ένα βέλος κάθε 2 δευτερόλεπτα",
      gap is not None and abs(gap - 2 * 50) <= P.CPC_VSYNC_RUN,
      f"{gap} vsync = {gap / 50:.2f}s" if gap else "δεν ξαναέριξε")

print("--- ο ρυθμικός δεν ρίχνει με το που μπαίνεις")
#
# ΜΠΑΙΝΕΙΣ ΑΠΟ ΤΗΝ ΠΟΡΤΑ ΚΑΙ ΣΕ ΒΡΙΣΚΕΙ ΒΕΛΟΣ. Με ρολόι 0 και turret_ready 0 ο
# ρυθμικός ήταν φορτισμένος από την πρώτη στιγμή και έριχνε στο πρώτο κιόλας
# πέρασμα — πριν προλάβεις να δεις πού είσαι. Η πρώτη βολή έρχεται τώρα ένα
# ΔΙΑΣΤΗΜΑ μετά την είσοδο.
# ΦΡΕΣΚΟΣ ΗΡΩΑΣ, ΧΩΡΙΣ settled(): εκείνο καθαρίζει το turret_ready και θα
# έσβηνε ακριβώς ό,τι ελέγχεται εδώ — τη φόρτιση που βάζει ο constructor.
rm = room([(10, 4, "I")], footer="turret 10 4 0 5 2\n")
h = P.Hero(rm, 30 * P.CELL + P.CELL // 2, P.GRID_Y0 + 21 * P.CELL)
check("ο ρυθμικός ξεκινά ΑΦΟΡΤΙΣΤΟΣ", h.turret_ready.get((10, 4)) == 2 * 50,
      str(h.turret_ready))
first = None
for _ in range(400):
    h.update(0)
    if h.arrows:
        first = h.clock
        break
check("ρυθμός 2: η πρώτη βολή έρχεται μετά από 2 δευτερόλεπτα",
      first is not None and abs(first - 2 * 50) <= P.CPC_VSYNC_RUN,
      f"{first} vsync = {first / 50:.2f}s" if first else "δεν έριξε ποτέ")

# Ο πυργίσκος «σε βλέπω» ΔΕΝ περιμένει: ρίχνει όταν μπεις στην ευθεία του, που
# είναι δική σου κίνηση και όχι έκπληξη της εισόδου.
rm = room([(10, 16, "I")], footer="turret 10 16 0 5 0\n")
h = P.Hero(rm, 10 * P.CELL + P.CELL // 2, P.GRID_Y0 + 21 * P.CELL)
check("χωρίς ρυθμό: κανένας χρόνος αναμονής", (10, 16) not in h.turret_ready,
      str(h.turret_ready))
h.update(0)
check("…και ρίχνει αμέσως μόλις σε δει", bool(h.arrows), str(len(h.arrows)))

print("--- το πολύ δύο βέλη στον αέρα")
rm = room([(10, 16, "I"), (20, 16, "I"), (30, 16, "I")])
h = settled(rm, 10, 21)
h.x = 10 * P.CELL + P.CELL // 2
for _ in range(3):
    h.turret_ready.clear()
    h.turret_step()
check(f"δεν ξεπερνά τα {P.TURRET_MAX}", len(h.arrows) <= P.TURRET_MAX,
      str(len(h.arrows)))

print("--- ο διακόπτης τον κλείνει")
rm = room([(10, 16, "I")], footer="turret 10 16 3 5 0\n")
h = settled(rm, 10, 21)
h.arrows.clear()
h.turret_ready.clear()
h.update(0)
check("πριν τον διακόπτη ρίχνει", bool(h.arrows), str(len(h.arrows)))

# «Ανοιχτό» σημαίνει ΑΚΙΝΔΥΝΟ σε όλο το σύστημα: η πύλη ανοίγει, τα αγκάθια
# τραβιούνται, ο πυργίσκος σβήνει. Ένας διακόπτης, ένα νόημα.
h.set_targets(3, True)
check("ο διακόπτης άλλαξε τον τύπο του κελιού",
      rm.cells[16][10] == P.TURRET_V_OFF, P.TYPE_NAMES[rm.cells[16][10]])
h.arrows.clear()
h.turret_ready.clear()
for _ in range(60):
    h.update(0)
check("σβηστός: δεν ρίχνει καθόλου", not h.arrows, str(len(h.arrows)))

h.set_targets(3, False)
check("και ξαναανάβει", rm.cells[16][10] == P.TURRET_V,
      P.TYPE_NAMES[rm.cells[16][10]])
h.turret_ready.clear()
h.update(0)
check("…και ξαναρίχνει", bool(h.arrows), str(len(h.arrows)))

# Ο πυργίσκος που ΞΕΚΙΝΑ σβηστός πρέπει να μπορεί να ανάψει: η λίστα βολής
# χτίζεται μία φορά στη φόρτωση, οπότε αν κρατούσε μόνο τους αναμμένους δεν θα
# τον έβρισκε ποτέ.
rm = room([(10, 16, "i")], footer="turret 10 16 3 5 0\n")
h = settled(rm, 10, 21)
h.set_targets(3, False)
h.arrows.clear()
h.turret_ready.clear()
h.update(0)
check("πυργίσκος που ξεκινά σβηστός ανάβει και ρίχνει", bool(h.arrows),
      str(len(h.arrows)))


def rhythm_shots(hero, passes=400):
    """Πόσες φορές έριξε σε τόσα περάσματα, χωρίς να μαζεύονται τα βέλη."""
    hero.arrows.clear()
    hero.turret_ready.clear()
    n = 0
    for _ in range(passes):
        hero.update(0)
        n += len(hero.arrows)
        hero.arrows.clear()
    return n


# Ο ΔΙΑΚΟΠΤΗΣ ΚΑΙ ΣΤΟΝ ΡΥΘΜΙΚΟ. Ο πυργίσκος με ρυθμό δεν ρωτάει ούτε εμβέλεια
# ούτε οπτική επαφή — ρίχνει στην ώρα του, ΜΕΧΡΙ να τον κλείσει ο διακόπτης.
# Ο έλεγχος «σβηστός;» είναι ΞΕΧΩΡΙΣΤΟΣ από τα δύο φίλτρα, και ένα λάθος που θα
# τον έβαζε μέσα τους θα άφηνε τον ρυθμικό να ρίχνει για πάντα: το μόνο πράγμα
# που τον σταματά θα είχε φύγει μαζί τους. Ο ήρωας στέκεται μακριά και εκτός
# ευθείας επίτηδες — αν κάποιο φίλτρο τρέξει κατά λάθος, οι βολές μηδενίζονται.
rm = room([(10, 4, "I")], footer="turret 10 4 3 5 2\n")
h = settled(rm, 30, 21)
check("με ρυθμό: ρίχνει ξανά και ξανά", rhythm_shots(h) >= 3,
      f"{rhythm_shots(h)} βολές")
h.set_targets(3, True)
check("…ο διακόπτης τον σβήνει", rm.cells[4][10] == P.TURRET_V_OFF,
      P.TYPE_NAMES[rm.cells[4][10]])
check("…και τότε σταματά εντελώς", rhythm_shots(h) == 0,
      f"{rhythm_shots(h)} βολές")
h.set_targets(3, False)
check("…και με τον διακόπτη ξανά ρίχνει", rhythm_shots(h) >= 3,
      f"{rhythm_shots(h)} βολές")

print("--- ο πυργίσκος ΔΕΝ είναι εμπόδιο")
check("περνάς από μέσα του", not (P.PROPS[P.TURRET_V] & P.F_SOLID))
check("…και δεν πονάει με την αφή", not (P.PROPS[P.TURRET_V] & P.F_DEADLY))

# Και στην πράξη: ο ήρωας πρέπει να διασχίζει το κελί χωρίς να σταματά.
rm = room([(12, 21, "I")])
h = settled(rm, 9, 21)
x0 = h.x
for _ in range(60):
    h.update(1)
check("περπατάει μέσα από πυργίσκο χωρίς να κολλήσει",
      h.x > 13 * P.CELL, f"ξεκίνησε {x0}, έφτασε {h.x}")


# =====================================================================
#  ΚΑΙ ΣΤΟΝ Z80 — άλλη υλοποίηση, ίδια προδιαγραφή
#
#  Το μοντέλο παραπάνω δεν λέει τίποτα για τον Amstrad: εκεί ο πίνακας
#  πυργίσκων χτίζεται με σάρωση του cell_buf, η φόρτιση διαβάζει το ρολόι του
#  firmware, και η αριθμητική είναι 8 και 16 bit με το χέρι. Ό,τι μπορεί να
#  αποκλίνει, αποκλίνει — γι' αυτό τρέχει εδώ ο ΠΡΑΓΜΑΤΙΚΟΣ κώδικας.
# =====================================================================
print("--- ο ίδιος πυργίσκος, στον Z80")

CLK = 0xB7FE                    # ελεύθερη μνήμη κάτω από το jumpblock


TARG = 0xB700           # ελεύθερη μνήμη για τον πέμπτο πίνακα, στα τεστ


def z80_room(cells, targ=()):
    """main.bin με πλέγμα, ρολόι και πίνακα χρόνων πυργίσκων."""
    from z80run import Z80Test
    t = Z80Test()
    # ΤΟ ΡΟΛΟΙ ΤΟΥ FIRMWARE, σε 11 bytes: χωρίς αυτό το KL_TIME_PLEASE γυρίζει
    # ό,τι έτυχε να έχει το HL και η φόρτιση δεν σημαίνει τίποτα.
    code = bytes([0x2A, CLK & 0xFF, CLK >> 8,
                  0x11, 30, 0, 0x19,
                  0x22, CLK & 0xFF, CLK >> 8, 0xC9])
    for i, b in enumerate(code):
        t.m.memory[0xBD0D + i] = b
    t.poke16(CLK, 0)

    grid = [[P.EMPTY] * P.COLS for _ in range(P.ROWS)]
    for c in range(P.COLS):
        grid[0][c] = grid[P.ROWS - 1][c] = P.SOLID
    for r in range(P.ROWS):
        grid[r][0] = grid[r][P.COLS - 1] = P.SOLID
    for c, r, ch in cells:
        grid[r][c] = P.CHARS[ch]
    t.poke(t.sym("CELL_BUF"), bytes(v for row in grid for v in row))
    t.poke16(t.sym("LEVEL_PTR"), t.sym("CELL_BUF"))
    t.poke(t.sym("HERO_ENERGY"), bytes([P.ENERGY_MAX]))
    t.poke(t.sym("HERO_HURT"), b"\x00")
    t.poke(t.sym("HERO_G"), b"\x00")
    # Ο πέμπτος πίνακας του αρχείου αίθουσας: τετράδες, τέλος με #FF.
    blob = b"".join(bytes(q) for q in targ) + b"\xFF"
    t.poke(TARG, blob)
    t.poke16(t.sym("ROOM_TARG"), TARG)
    return t


t = z80_room([(10, 16, "I"), (4, 21, "=")])
t.call("TURRET_LOAD")
check("ο πίνακας βρίσκει τους δύο πυργίσκους",
      t.peek(t.sym("TURRET_N"))[0] == 2, str(t.peek(t.sym("TURRET_N"))[0]))
# ΤΟ ΒΗΜΑ ΑΠΟ ΤΟΝ ΚΩΔΙΚΑ: η εγγραφή μεγάλωσε από 5 σε 7 bytes όταν μπήκαν οι
# δύο χρόνοι, και ένα καρφωμένο 5 εδώ διάβαζε τη μέση της επόμενης.
TS = t.sym("TS_SIZE")
tab = t.peek(t.sym("TURRET_TAB"), 2 * TS)
check("…με τη σωστή στήλη, γραμμή και τύπο",
      tuple(tab[0:3]) == (10, 16, P.TURRET_V)
      and tuple(tab[TS:TS + 3]) == (4, 21, P.TURRET_H),
      f"{list(tab[0:3])} {list(tab[TS:TS + 3])}")

# --- ρίχνει προς τον ήρωα και το βέλος κάνει 6 pixel ανά κλήση
t = z80_room([(10, 16, "I")])
t.call("TURRET_LOAD")
t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
AR = t.sym("ARROW_TAB")
t.call("TURRET_STEP")
on = t.peek(AR)[0]
y0 = t.peek(AR + 3)[0]
check("ρίχνει προς τα κάτω", on == 1 and t.peek(AR + 5)[0] == 1,
      f"on={on} dy={t.peek(AR + 5)[0]}")
t.call("TURRET_STEP")
y1 = t.peek(AR + 3)[0]
check(f"το βέλος κάνει {P.ARROW_STEP} pixel ανά καρέ",
      y1 - y0 == P.ARROW_STEP, f"{y0} -> {y1}")

# --- χτυπάει, και πονάει περισσότερο από κοντά
# Οι ζώνες μετρώνται σε ΔΙΑΝΥΘΕΙΣΑ απόσταση, όχι σε γραμμές: από πυργίσκο στη
# γραμμή 16 ο ήρωας στο πάτωμα απέχει μόλις 33 pixel, δηλαδή μεσαία ζώνη. Για
# τη μακρινή χρειάζεται πυργίσκος ψηλά και ήρωας χαμηλά.
for trow, row, want, label in ((16, 18, P.ARROW_DMG[0], "κοντά"),
                               (16, 22, P.ARROW_DMG[1], "μεσαία"),
                               (8, 18, P.ARROW_DMG[2], "μακριά")):
    t = z80_room([(10, trow, "I")])
    t.call("TURRET_LOAD")
    t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
    t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + row * P.CELL]))
    for _ in range(30):
        t.call("TURRET_STEP")
        if t.peek(t.sym("HERO_ENERGY"))[0] != P.ENERGY_MAX:
            break
    got = P.ENERGY_MAX - t.peek(t.sym("HERO_ENERGY"))[0]
    check(f"χτύπημα από {label}: ζημιά {want}", got == want, f"{got}")

# --- η φόρτιση μετριέται στο ΡΟΛΟΙ
t = z80_room([(10, 16, "I")])
t.call("TURRET_LOAD")
t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
t.call("TURRET_STEP")
ready = t.peek16(t.sym("TURRET_TAB") + 3)
now = t.peek16(CLK)
check("μετά τη βολή ξαναφορτίζει σε 5 δευτερόλεπτα",
      abs((ready - now) - 1500) <= 60,
      f"ready {ready}, ρολόι {now}, διαφορά {ready - now} παλμοί = "
      f"{(ready - now) / 300:.2f}s")

# --- τοίχος στη μέση: ούτε ρίχνει ούτε περνάει
t = z80_room([(10, 16, "I"), (10, 19, "#")])
t.call("TURRET_LOAD")
t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
for _ in range(10):
    t.call("TURRET_STEP")
check("τοίχος ανάμεσα: δεν ρίχνει και δεν πονάει",
      t.peek(AR)[0] == 0 and t.peek(t.sym("HERO_ENERGY"))[0] == P.ENERGY_MAX,
      f"on={t.peek(AR)[0]} ενέργεια={t.peek(t.sym('HERO_ENERGY'))[0]}")

# --- οι δύο χρόνοι, στον Z80 -----------------------------------------
print("--- οι παράμετροι φτάνουν στον Z80")
t = z80_room([(10, 16, "I")], targ=[(10, 16, 2, 0)])
t.call("TURRET_LOAD")
tab = t.peek(t.sym("TURRET_TAB"), 7)
check("ο πίνακας κρατά φόρτιση και ρυθμό", (tab[5], tab[6]) == (2, 0),
      f"cool={tab[5]} auto={tab[6]}")
t = z80_room([(10, 16, "I")])
t.call("TURRET_LOAD")
tab = t.peek(t.sym("TURRET_TAB"), 7)
check("αδήλωτος: η προεπιλογή των 5 δευτερολέπτων", tab[5] == 5, str(tab[5]))

# ΚΑΙ Η ΑΡΧΙΚΗ ΦΟΡΤΙΣΗ, ΣΤΟΝ Z80. Το ρολόι εδώ είναι το ψεύτικο των τεστ και
# προχωράει 30 παλμούς ανά κλήση του firmware, οπότε συγκρίνουμε με αυτό.
t = z80_room([(10, 16, "I")], targ=[(10, 16, 5, 2)])
t.call("TURRET_LOAD")
ready = t.peek16(t.sym("TURRET_TAB") + 3)
check("ρυθμικός: φορτώνεται με 2 δευτερόλεπτα μπροστά",
      abs(ready - (t.peek16(CLK) + 2 * 300)) <= 60, f"ready={ready}")
t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
t.call("TURRET_STEP")
check("…και ΔΕΝ ρίχνει στο πρώτο πέρασμα της αίθουσας",
      t.peek(t.sym("ARROW_TAB"))[0] == 0,
      f"on={t.peek(t.sym('ARROW_TAB'))[0]}")

t = z80_room([(10, 16, "I")], targ=[(10, 16, 5, 0)])
t.call("TURRET_LOAD")
check("χωρίς ρυθμό: φορτισμένος από την πρώτη στιγμή",
      t.peek16(t.sym("TURRET_TAB") + 3) == 0,
      str(t.peek16(t.sym("TURRET_TAB") + 3)))


def z80_gap(targ):
    """Πόσοι παλμοί ανάμεσα σε δύο βολές, στον Z80.

    ΜΕΤΑ ΤΗΝ ΑΡΧΙΚΗ ΦΟΡΤΙΣΗ: ο ρυθμικός φορτώνεται πια άδειος και η πρώτη του
    βολή έρχεται ένα διάστημα αργότερα. Χωρίς το μηδένισμα εδώ, το τεστ θα
    μετρούσε την ΑΡΧΙΚΗ φόρτιση αντί για το διάστημα ανάμεσα σε δύο βολές —
    ίδιος αριθμός, εντελώς άλλο πράγμα.
    """
    t = z80_room([(10, 16, "I")], targ=targ)
    t.call("TURRET_LOAD")
    t.poke16(t.sym("TURRET_TAB") + 3, 0)        # TS_READY: φορτισμένος τώρα
    t.poke16(t.sym("HERO_X"), 10 * P.CELL + P.CELL // 2)
    t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
    t.call("TURRET_STEP")
    return t.peek16(t.sym("TURRET_TAB") + 3) - t.peek16(CLK)


check("φόρτιση 2 -> 600 παλμοί", abs(z80_gap([(10, 16, 2, 0)]) - 600) <= 60,
      str(z80_gap([(10, 16, 2, 0)])))
check("φόρτιση 7 -> 2100 παλμοί", abs(z80_gap([(10, 16, 7, 0)]) - 2100) <= 60,
      str(z80_gap([(10, 16, 7, 0)])))
check("ρυθμός 3 -> 900 παλμοί (η φόρτιση αγνοείται)",
      abs(z80_gap([(10, 16, 7, 3)]) - 900) <= 60,
      str(z80_gap([(10, 16, 7, 3)])))

# ΡΥΘΜΟΣ: ρίχνει χωρίς εμβέλεια και χωρίς οπτική επαφή.
t = z80_room([(10, 4, "I"), (10, 12, "#")], targ=[(10, 4, 5, 1)])
t.call("TURRET_LOAD")
t.poke16(t.sym("TURRET_TAB") + 3, 0)        # η αρχική φόρτιση πέρασε
t.poke16(t.sym("HERO_X"), 30 * P.CELL)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
t.call("TURRET_STEP")
check("με ρυθμό ρίχνει και πίσω από τοίχο, και μακριά",
      t.peek(t.sym("ARROW_TAB"))[0] == 1,
      f"on={t.peek(t.sym('ARROW_TAB'))[0]}")

t = z80_room([(10, 4, "I"), (10, 12, "#")])
t.call("TURRET_LOAD")
t.poke16(t.sym("HERO_X"), 30 * P.CELL)
t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 21 * P.CELL]))
t.call("TURRET_STEP")
check("χωρίς ρυθμό, στην ίδια θέση, σιωπή",
      t.peek(t.sym("ARROW_TAB"))[0] == 0,
      f"on={t.peek(t.sym('ARROW_TAB'))[0]}")

# --- ο διακόπτης, στον Z80 -------------------------------------------
#
# ΤΟ ΜΟΝΤΕΛΟ ΤΟ ΕΛΕΓΧΕΙ ΗΔΗ, Ο Z80 ΔΕΝ ΤΟ ΕΛΕΓΧΕ ΚΑΘΟΛΟΥ. Και είναι άλλος
# κώδικας: εκεί το «σβηστός;» δεν είναι μια σύγκριση σε λίστα τύπων αλλά δύο
# `cp` πάνω στο κελί, ΠΡΙΝ από τη διακλάδωση των δύο τρόπων. Αν έμπαινε μετά,
# ο ρυθμικός θα συνέχιζε να ρίχνει σβηστός.
#
# Ο διακόπτης γράφει τον ΤΥΠΟ ΤΟΥ ΚΕΛΙΟΥ — αυτό κάνει και το tgt_want — οπότε
# εδώ γράφεται κατευθείαν: το ζητούμενο είναι τι κάνει ο πυργίσκος όταν το
# κελί αλλάξει, όχι πώς έφτασε να αλλάξει.
#
# ΟΡΙΖΟΝΤΙΟΣ ΠΥΡΓΙΣΚΟΣ, ΚΑΙ ΟΧΙ ΚΑΘΕΤΟΣ, ΓΙΑ ΣΥΓΚΕΚΡΙΜΕΝΟ ΛΟΓΟ. Με κάθετο, το
# τεστ έμενε ΠΡΑΣΙΝΟ ακόμα και με σβησμένο τον έλεγχο «σβηστός;»: το TS_TYPE
# γινόταν TURRET_V_OFF, το `cp T_TURRET_V` αποτύγχανε, ο κώδικας έπαιρνε τον
# ΟΡΙΖΟΝΤΙΟ κλάδο και έβρισκε d = hero_x - cx = 0, οπότε δεν έριχνε — για
# εντελώς άλλον λόγο από αυτόν που υποτίθεται ότι έλεγχε. Ο οριζόντιος παίρνει
# τον ίδιο κλάδο αναμμένος και σβηστός, οπότε η ΜΟΝΗ διαφορά μένει ο έλεγχος.
print("--- ο διακόπτης τον κλείνει, στον Z80")


def z80_fires(t, cell_addr, value):
    """Ρίχνει ο πυργίσκος με αυτόν τον τύπο κελιού; Καθαρή αφετηρία κάθε φορά."""
    t.poke(cell_addr, bytes([value]))
    t.poke16(t.sym("TURRET_TAB") + 3, 0)         # TS_READY: φορτισμένος
    for i in range(P.TURRET_MAX):                # καμία θέση βέλους πιασμένη
        t.poke(t.sym("ARROW_TAB") + i * t.sym("AR_SIZE"), b"\x00")
    t.call("TURRET_STEP")
    return t.peek(t.sym("ARROW_TAB"))[0] == 1


for cool, auto, what in ((5, 0, "χωρίς ρυθμό"), (5, 2, "με ρυθμό")):
    t = z80_room([(10, 16, "=")], targ=[(10, 16, cool, auto)])
    t.call("TURRET_LOAD")
    t.poke16(t.sym("HERO_X"), 16 * P.CELL + P.CELL // 2)
    t.poke(t.sym("HERO_Y"), bytes([P.GRID_Y0 + 16 * P.CELL + P.CELL // 2]))
    cell = t.sym("CELL_BUF") + 16 * P.COLS + 10
    check(f"{what}: ρίχνει όσο είναι αναμμένος",
          z80_fires(t, cell, P.TURRET_H))
    check(f"{what}: σβηστός δεν ρίχνει καθόλου",
          not z80_fires(t, cell, P.TURRET_H_OFF))
    check(f"{what}: και ξαναρίχνει μόλις ανάψει",
          z80_fires(t, cell, P.TURRET_H))

# --- Η ΣΦΑΙΡΑ ΣΤΗΝ ΟΘΟΝΗ ---------------------------------------------
#
# Ως εδώ κανένα τεστ δεν ακούμπησε pixel: το βέλος μπορούσε να δουλεύει τέλεια
# και να είναι αόρατο, που είναι ακριβώς η κατάσταση που παρέδωσα πριν.
print("--- και φαίνεται;")
t = z80_room([(10, 16, "I")])
t.call("INIT_LINETAB")
t.call("TURRET_LOAD")
AR = t.sym("ARROW_TAB")
t.poke(AR, bytes([1]))                      # ένα βέλος στο χέρι, προς τα κάτω
t.poke16(AR + 1, 84)
t.poke(AR + 3, bytes([150]))
t.poke(AR + 4, bytes([0, 1, 0]))            # dx=0, dy=1, gone=0

before = bytes(t.m.memory[a] for a in range(0xC000, 0x10000))
t.call("ARROW_DRAW")
after = bytes(t.m.memory[a] for a in range(0xC000, 0x10000))
changed = [i for i in range(len(before)) if before[i] != after[i]]
check("το arrow_draw γράφει στην οθόνη",
      len(changed) > 0, f"{len(changed)} bytes")
check("…και μόνο γύρω από το βέλος (11 pixel -> το πολύ 11 bytes)",
      0 < len(changed) <= 11, f"{len(changed)}")
# Pen 3 στο MODE 1 = bits και στα δύο επίπεδα· ο πίνακας είναι ο spr_pixtab.
check("…με αναμμένα bits (pen 1 ουρά, pen 3 μύτη)",
      all(after[i] & 0x88 or after[i] & 0x44 or after[i] & 0x22
          or after[i] & 0x11 for i in changed))

# ΚΑΙ ΤΟ ΣΒΗΣΙΜΟ ΑΚΟΛΟΥΘΕΙ ΤΗΝ ΠΑΛΙΑ ΘΕΣΗ, ΟΧΙ ΤΗ ΝΕΑ.
#
# Το σβήσιμο έφυγε από το hero_update και κόλλησε δίπλα στη σχεδίαση, μετά το
# flyback — αλλιώς το βέλος έλειπε από την οθόνη σχεδόν όλο το πέρασμα και
# τρεμόπαιζε. Τη στιγμή που τρέχει τώρα, τα βέλη έχουν ΗΔΗ κουνηθεί, οπότε το
# arrow_erase διαβάζει το αντίγραφο που κράτησε το arrow_save. Αν το ξαναδιάβαζε
# από τον ζωντανό πίνακα, θα καθάριζε ένα ορθογώνιο έξι pixel παρακάτω και θα
# άφηνε πίσω του το βέλος — μια ουρά από φαντάσματα σε κάθε βολή.
t.call("ARROW_SAVE")
t.call("AR_MOVE")
t.call("ARROW_ERASE")
back = bytes(t.m.memory[a] for a in range(0xC000, 0x10000))
check("το arrow_erase ξαναφέρνει το φόντο ΕΚΕΙ ΠΟΥ ΗΤΑΝ", back == before,
      f"{sum(1 for i in range(len(back)) if back[i] != before[i])} bytes διαφορά")

print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"ΑΠΕΤΥΧΑΝ {len(FAILS)}")
sys.exit(1 if FAILS else 0)
