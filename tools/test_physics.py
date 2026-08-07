#!/usr/bin/env python3
"""Τεστ παλινδρόμησης του μοντέλου φυσικής (tools/physics.py).

Κάθε ένα από αυτά αντιστοιχεί σε σφάλμα που όντως εμφανίστηκε κατά την
ανάπτυξη. Πριν αλλάξεις το μοντέλο ή το src/hero.asm, τρέξε: make test
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


def run(room, x, y, g=0, walk=1, frames=4000):
    h = P.Hero(room, x, y, g)
    seen_g, stuck, last = set(), 0, None
    for _ in range(frames):
        h.update(walk)
        seen_g.add(h.g)
        pos = (h.x, h.y, h.g)
        stuck = stuck + 1 if pos == last else 0
        last = pos
    return h, seen_g, stuck


def main():
    room = P.load_room()
    print("Μοντέλο φυσικής:")

    # 1. Περιδιάβαση: με ένα μόνο πλήκτρο πρέπει να γυρίσει όλο το δωμάτιο και
    #    να περάσει από ΚΑΘΕ φορά βαρύτητας — πάτωμα, τοίχους, ταβάνι, ράμπες.
    for d, label in ((1, "μπροστά"), (-1, "πίσω")):
        h, seen, stuck = run(room, 60, 40, walk=d)
        check(f"περιδιάβαση {label}: δεν κολλάει", stuck < 50, f"stuck={stuck}")
        check(f"περιδιάβαση {label}: όλες οι ορθές φορές",
              {0, 2, 4, 6} <= seen, f"είδε {sorted(seen)}")
        check(f"περιδιάβαση {label}: πέρασε από ράμπα (διαγώνια φορά)",
              bool(seen & {1, 3, 5, 7}), f"είδε {sorted(seen)}")

    # 2. Ράμπα ανόδου -> η βαρύτητα γίνεται DOWN-RIGHT, όχι κάτι άλλο.
    h, seen, _ = run(room, 60, 40, walk=1, frames=200)
    check("ανηφόρα 45 μοιρών -> βαρύτητα 7", 7 in seen, f"είδε {sorted(seen)}")

    # 3. Ο κανόνας που ζήτησε ο χρήστης: διαγώνια βαρύτητα σε ΕΠΙΠΕΔΟ πάτωμα
    #    γλιστράει — δεν στέκεται και δεν ισιώνει μόνη της.
    h = P.Hero(room, 60, 185, 0)
    for _ in range(30):
        h.update(0)
    x0 = h.x
    h.g = 7                                   # ο παίκτης βάζει διαγώνια
    for _ in range(40):
        h.update(0)
    check("διαγώνια βαρύτητα σε επίπεδο πάτωμα -> γλιστράει",
          h.x > x0 + 5, f"x {x0} -> {h.x}")

    # 4. ...ενώ σε ράμπα 45 μοιρών η ίδια φορά ΣΤΕΚΕΤΑΙ.
    h = P.Hero(room, 90, 180, 7)
    h.snap()
    check("ίδια φορά πάνω σε ράμπα -> στέκεται", not h.slipping(),
          f"support={h.support_type()}")

    # 5. Ζημιά πτώσης μόνο πάνω από 3x το ύψος του ήρωα (36 px).
    h = P.Hero(room, 60, 40, 0)
    for _ in range(400):
        h.update(0)
    check("μεγάλη πτώση -> ζημιά", h.state != "FALL")

    # 6. Ο ήρωας δεν χώνεται ποτέ μέσα στο υλικό.
    h = P.Hero(room, 60, 40, 0)
    bad = 0
    for _ in range(3000):
        h.update(1)
        if h.at(0, 0):
            bad += 1
    check("δεν βρίσκεται ποτέ μέσα σε υλικό", bad == 0, f"{bad} frames")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
