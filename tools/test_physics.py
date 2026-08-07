#!/usr/bin/env python3
"""Τεστ παλινδρόμησης του μοντέλου φυσικής (tools/physics.py).

Κάθε ένα από αυτά αντιστοιχεί σε σφάλμα που όντως εμφανίστηκε κατά την
ανάπτυξη. Πριν αλλάξεις το μοντέλο ή το src/hero.asm, τρέξε: make test
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

# Τα τεστ ΔΕΝ τρέχουν στο levels/test.txt: εκείνο ανήκει στον σχεδιαστή και
# αλλάζει. Ένα σταθερό δωμάτιο κρατά τα τεστ ουσιαστικά.
REGRESS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "levels", "regress.txt")

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def fresh(strip=()):
    """Καθαρό δωμάτιο: τα pickups ΣΒΗΝΟΝΤΑΙ όταν μαζευτούν και τα κιβώτια
    μετακινούνται, οπότε τα τεστ δεν μπορούν να μοιράζονται το ίδιο Room.

    Το `strip` βγάζει τύπους από το δωμάτιο: τα τεστ γεωμετρίας ελέγχουν
    περπάτημα, γωνίες και ράμπες, και δεν πρέπει να αποτυγχάνουν επειδή ένα
    κιβώτιο έπεσε στον διάδρομο — αυτό είναι σωστή συμπεριφορά, όχι σφάλμα.
    """
    r = P.load_room(REGRESS)
    for row in r.cells:
        for i, v in enumerate(row):
            if v in strip:
                row[i] = P.EMPTY
    return r


def run(room, x, y, g=0, walk=1, frames=4000):
    """Τρέχει τον ήρωα και επιστρέφει (ήρωας, φορές που είδε, μέγιστο κόλλημα).

    Το φτάσιμο στην έξοδο ΔΕΝ είναι κόλλημα: εκεί το παιχνίδι τελειώνει, οπότε
    σταματάμε αντί να μετράμε τα ακίνητα frames που ακολουθούν.
    """
    h = P.Hero(room, x, y, g)
    seen_g, stuck, last = set(), 0, None
    for _ in range(frames):
        h.update(walk)
        if h.won:
            break
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
        h, seen, stuck = run(fresh(strip=(P.CRATE,)), 60, 40, walk=d)
        check(f"περιδιάβαση {label}: δεν κολλάει", stuck < 50, f"stuck={stuck}")
        check(f"περιδιάβαση {label}: όλες οι ορθές φορές",
              {0, 2, 4, 6} <= seen, f"είδε {sorted(seen)}")
        check(f"περιδιάβαση {label}: πέρασε από ράμπα (διαγώνια φορά)",
              bool(seen & {1, 3, 5, 7}), f"είδε {sorted(seen)}")

    # 2. Ράμπα ανόδου -> η βαρύτητα γίνεται DOWN-RIGHT, όχι κάτι άλλο.
    h, seen, _ = run(fresh(strip=(P.CRATE,)), 60, 40, walk=1, frames=200)
    check("ανηφόρα 45 μοιρών -> βαρύτητα 7", 7 in seen, f"είδε {sorted(seen)}")

    # 3. Ο κανόνας που ζήτησε ο χρήστης: διαγώνια βαρύτητα σε ΕΠΙΠΕΔΟ πάτωμα
    #    γλιστράει — δεν στέκεται και δεν ισιώνει μόνη της.
    h = P.Hero(fresh(), 60, 185, 0)
    for _ in range(30):
        h.update(0)
    x0 = h.x
    h.g = 7                                   # ο παίκτης βάζει διαγώνια
    for _ in range(40):
        h.update(0)
    check("διαγώνια βαρύτητα σε επίπεδο πάτωμα -> γλιστράει",
          h.x > x0 + 5, f"x {x0} -> {h.x}")

    # 4. ...ενώ σε ράμπα 45 μοιρών η ίδια φορά ΣΤΕΚΕΤΑΙ.
    h = P.Hero(fresh(), 90, 180, 7)
    h.snap()
    check("ίδια φορά πάνω σε ράμπα -> στέκεται", not h.slipping(),
          f"support={h.support_type()}")

    # 5. Ζημιά πτώσης μόνο πάνω από 3x το ύψος του ήρωα (36 px).
    h = P.Hero(fresh(), 60, 40, 0)
    for _ in range(400):
        h.update(0)
    check("μεγάλη πτώση -> ζημιά", h.state != "FALL")

    # 6. Επιτάχυνση πτώσης: φτάνει την τερματική ταχύτητα και δεν την ξεπερνά,
    #    και η πτώση όλης της οθόνης κρατάει λογικό χρόνο.
    h = P.Hero(fresh(), 60, 16, 0)
    fr, vmax = 0, 0
    while h.state != "IDLE" and fr < 300:
        h.update(0)
        vmax = max(vmax, h.fall_v)
        fr += 1
    check("πτώση οθόνης σε λογικό χρόνο", 40 <= fr <= 80, f"{fr} frames")
    check("δεν ξεπερνά την τερματική ταχύτητα", vmax <= P.FALL_VMAX,
          f"{vmax/256:.2f} px/frame")

    # 7. Με επιτάχυνση, ο ήρωας ΔΕΝ περνάει μέσα από λεπτά πατώματα: η ταχύτητα
    #    εκτελείται ως πολλαπλά βήματα του ενός pixel, όχι ως ένα μεγάλο άλμα.
    h = P.Hero(fresh(), 60, 16, 0)
    inside = 0
    for _ in range(300):
        h.update(0)
        if h.at(0, 0):
            inside += 1
    check("η επιτάχυνση δεν περνά μέσα από πατώματα", inside == 0,
          f"{inside} frames μέσα σε υλικό")

    # 8. Ο ήρωας δεν χώνεται ποτέ μέσα στο υλικό.
    h = P.Hero(fresh(), 60, 40, 0)
    bad = 0
    for _ in range(3000):
        h.update(1)
        if h.at(0, 0):
            bad += 1
    check("δεν βρίσκεται ποτέ μέσα σε υλικό", bad == 0, f"{bad} frames")

    # 9. Αντικείμενα: μάζεμα, αγκάθια, ζώνη κλειδώματος.
    h = P.Hero(fresh(), 52, 185, 0)        # πάνω από την ενέργεια (στήλη 6)
    h.energy = 3
    for _ in range(40):
        h.update(0)
    check("ενέργεια: μάζεμα αυξάνει", h.energy > 3, f"energy={h.energy}")

    h = P.Hero(fresh(), 28, 185, 0)        # πάνω από το αλεξίπτωτο (στήλη 3)
    for _ in range(40):
        h.update(0)
    check("αλεξίπτωτο: μαζεύεται", h.parachute == 1)

    # Με αλεξίπτωτο, μεγάλη πτώση ΔΕΝ κοστίζει ενέργεια και καταναλώνεται.
    h = P.Hero(fresh(), 60, 16, 0)
    h.parachute = 1
    for _ in range(400):
        h.update(0)
        if h.state == "IDLE":
            break
    check("αλεξίπτωτο: μηδενική ζημιά σε μεγάλη πτώση", h.energy == P.ENERGY_MAX,
          f"energy={h.energy}")
    check("αλεξίπτωτο: μία χρήση", h.parachute == 0)

    # Χωρίς αυτό, η ίδια πτώση πονάει.
    h = P.Hero(fresh(), 60, 16, 0)
    for _ in range(400):
        h.update(0)
        if h.state == "IDLE":
            break
    check("χωρίς αλεξίπτωτο: η ίδια πτώση πονάει", h.energy < P.ENERGY_MAX,
          f"energy={h.energy}")

    # Αγκάθια: πονάνε από τη μύτη, ασφαλή από πίσω.
    h = P.Hero(fresh(), 250, 180, 0)       # πάνω από τα αγκάθια (στήλες 30-34)
    e0 = h.energy
    for _ in range(40):
        h.update(0)
    check("αγκάθια: πονάνε από τη μύτη", h.energy < e0, f"energy={h.energy}")

    # Ζώνη κλειδώματος βαρύτητας
    h = P.Hero(fresh(), 176, 132, 0)       # μέσα στη ζώνη (στήλες 20-24, γραμμές 15-17)
    check("ζώνη κλειδώματος: εντοπίζεται", h.noflip(),
          f"cell={h.body_cell()}")

    # 10. Κιβώτια: πέφτουν προς τη φορά που ΟΡΙΣΕ Ο ΠΑΙΚΤΗΣ, όχι προς την
    #     τρέχουσα φορά του ήρωα (που γυρίζει μόνη της στις γωνίες).
    for g, (dx, dy) in ((0, (0, 1)), (6, (1, 0)), (4, (0, -1)), (1, (-1, 1))):
        room = fresh(strip=(P.CRATE,))
        room.cells[10][20] = P.CRATE
        h = P.Hero(room, 60, 44, 0)
        h.set_gravity(g)
        h.g = 2                              # ο ήρωας κοιτάει αλλού επίτηδες
        for _ in range(P.CRATE_TICKS):
            h.crate_step()
        found = [(c, r) for r in range(P.ROWS) for c in range(P.COLS)
                 if room.cells[r][c] == P.CRATE]
        check(f"κιβώτιο πέφτει προς τη φορά {g}", found == [(20 + dx, 10 + dy)],
              f"{found}")

    # Σταματά όταν βρει στερεό.
    room = fresh(strip=(P.CRATE,))
    room.cells[21][2] = P.CRATE              # ακριβώς πάνω από το πάτωμα
    h = P.Hero(room, 60, 44, 0)
    h.set_gravity(0)
    for _ in range(P.CRATE_TICKS * 6):
        h.crate_step()
    check("κιβώτιο σταματά σε στερεό", room.cells[22][2] == P.CRATE,
          f"γραμμή 22 = {room.cells[22][2]}")

    # 11. Πλήκτρο ενεργοποίησης: κλειδαριά, τηλεμεταφορά, σήκωμα/άφημα κιβωτίου
    # Το κιβώτιο σηκώνεται όταν το ΠΑΤΑΣ, όχι όταν το κοιτάς.
    room = fresh(strip=(P.CRATE,))
    room.cells[22][5] = P.CRATE          # ελεύθερο σημείο στο πάτωμα
    h = P.Hero(room, 5 * 8 + 4, 8 + 18 * 8, 0)
    for _ in range(80):                  # άφησέ τον να προσγειωθεί πάνω του
        h.update(0)
    check("στέκεται πάνω στο κιβώτιο", h.support_type() == P.CRATE,
          P.TYPE_NAMES[h.support_type()])
    check("σήκωμα κιβωτίου από κάτω",
          h.use() and h.carry == 1 and room.cells[22][5] == P.EMPTY)
    check("άφημα κιβωτίου", h.use() and h.carry == 0)

    # Το ίδιο για την κλειδαριά: την πατάς.
    room = fresh(strip=(P.CRATE,))
    room.cells[22][5] = P.LOCK
    h = P.Hero(room, 5 * 8 + 4, 8 + 18 * 8, 0)
    for _ in range(80):
        h.update(0)
    check("κλειδαριά χωρίς κλειδί δεν ανοίγει", not h.use())
    h.keys = 1
    check("κλειδαριά με κλειδί ανοίγει",
          h.use() and h.keys == 0 and room.cells[22][5] == P.EMPTY)

    room = fresh()
    room.cells[10][5] = P.TELEPORT
    room.cells[12][30] = P.TELEPORT
    h = P.Hero(room, 5 * 8 + 4, 8 + 10 * 8 + 4, 3)
    g0 = h.g
    check("τηλεμεταφορά στο ταίρι",
          h.use() and (h.x // 8, (h.y - 8) // 8) == (30, 12), f"({h.x},{h.y})")
    check("τηλεμεταφορά διατηρεί τη φορά βαρύτητας", h.g == g0)

    # 12. Στο φόρτωμα τα κιβώτια ΔΕΝ κινούνται: μόνο αφού ο παίκτης αλλάξει φορά.
    room = fresh(strip=(P.CRATE,))
    room.cells[10][20] = P.CRATE
    h = P.Hero(room, 60, 44, 0)
    for _ in range(P.CRATE_TICKS * 5):
        h.crate_step()
    check("κιβώτια ακίνητα στο φόρτωμα", room.cells[10][20] == P.CRATE,
          f"γραμμή 10 = {room.cells[10][20]}")
    h.set_gravity(0)
    for _ in range(P.CRATE_TICKS):
        h.crate_step()
    check("κινούνται μόλις ο παίκτης αλλάξει φορά",
          room.cells[11][20] == P.CRATE)

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
