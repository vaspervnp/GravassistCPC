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

PROPS_SOLID = P.F_SOLID

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
    h.keys[0] = 1
    check("κλειδαριά με κλειδί ανοίγει",
          h.use() and h.keys[0] == 0 and room.cells[22][5] == P.LOCK_OPEN,
          P.TYPE_NAMES[room.cells[22][5]])
    check("ανοιγμένη κλειδαριά δεν είναι στερεή",
          not (P.PROPS[P.LOCK_OPEN] & P.F_SOLID))
    h.state = "IDLE"
    y0 = h.y
    for _ in range(20):
        h.update(0)
    check("περνάς από μέσα της", h.y > y0, f"y {y0} -> {h.y}")

    # Ο προορισμός δηλώνεται ΡΗΤΑ· αδήλωτος teleporter δεν κάνει τίποτα.
    room = fresh()
    room.cells[10][5] = P.TELEPORT
    room.cells[12][30] = P.TELEPORT
    room.teleports = {(5, 10): None, (30, 12): None}
    h = P.Hero(room, 5 * 8 + 4, 8 + 10 * 8 + 4, 3)
    check("αδήλωτη τηλεμεταφορά δεν κάνει τίποτα", not h.use())

    room.teleports = {(5, 10): (30, 12), (30, 12): (5, 10)}
    h = P.Hero(room, 5 * 8 + 4, 8 + 10 * 8 + 4, 3)
    g0 = h.g
    check("τηλεμεταφορά στο δηλωμένο κελί",
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

    # 13. Αίθουσες και έξοδοι
    rooms = P.all_rooms()
    check("βρέθηκαν αίθουσες", len(rooms) >= 2, f"{[r.number for r in rooms]}")
    for r in rooms:
        for cell, dest, _two, cells in r.exit_groups():
            check(f"room_{r.number}: η έξοδος {cell} έχει προορισμό", dest != 0)
            check(f"room_{r.number}: ο προορισμός {dest} υπάρχει",
                  any(o.number == dest for o in rooms))
            # ΟΛΑ τα κελιά της ομάδας δείχνουν στο ίδιο σημείο
            check(f"room_{r.number}: η ομάδα {cell} είναι ενιαία",
                  all(r.exits[c] == dest for c in cells), f"{len(cells)} κελιά")

    for r in rooms:
        for cell, dest, cells in r.teleport_groups():
            check(f"room_{r.number}: η τηλεμεταφορά {cell} έχει προορισμό",
                  dest is not None, f"{dest}")
            if dest is None:
                continue
            # Προορισμός μέσα σε στερεό = ο παίκτης κολλάει ή πεθαίνει μόλις
            # πατήσει το πλήκτρο. Ελέγχεται εδώ ώστε να πιάνεται και όταν η
            # πίστα γράφεται με το χέρι, όχι μόνο από τον editor.
            dt = r.cell(*dest)
            check(f"room_{r.number}: ο προορισμός {dest} δεν είναι στερεός",
                  not (PROPS_SOLID & P.PROPS[dt]), P.TYPE_NAMES[dt])

    # 14. Πόρτες διπλής κατεύθυνσης: μπαίνοντας πίσω, ο παίκτης ΔΕΝ ξαναπερνά
    #     αμέσως την πόρτα. Δεν αρκεί να μην είναι ΠΑΝΩ της: με πλάγια βαρύτητα
    #     το διπλανό κελί γλιστράει μέσα της και ο παίκτης πηγαινοέρχεται
    #     ατέρμονα (αυτό ακριβώς έγινε στο room_1, όπου η βαρύτητα τραβάει
    #     ΔΕΞΙΑ και η πόρτα είναι στον δεξιό τοίχο). Ο μόνος έλεγχος που το
    #     πιάνει είναι να αφήσουμε τον ήρωα να τρέξει.
    # Αρκετά frames ώστε να πιαστεί και το ΑΡΓΟ γλίστρημα: μια άφιξη μπορεί
    # να φαίνεται σταθερή για δευτερόλεπτα και μετά να μπει στην πόρτα.
    SETTLE = 400
    for r in rooms:
        for cell, dest, two, cells in r.exit_groups():
            other = next((o for o in rooms if o.number == dest), None)
            if other is None:
                continue
            # Η συνθήκη κρίνεται στην πόρτα από την οποία ΒΓΑΙΝΕΙΣ, όχι σε
            # αυτή από την οποία μπήκες: το arrival_for() το ξέρει, εμείς όχι.
            a = other.arrival_for(r.number)
            if a is None:
                continue
            ac, ar, ag = a
            where = (ac, ar)
            check(f"room_{dest}: η άφιξη {where} ΔΕΝ είναι πάνω στην πόρτα",
                  other.cell(ac, ar) != P.EXIT, P.TYPE_NAMES[other.cell(ac, ar)])
            check(f"room_{dest}: η άφιξη {where} δεν είναι στερεή",
                  not (P.PROPS[other.cell(ac, ar)] & P.F_SOLID))

            # Με τη ΔΗΛΩΜΕΝΗ φορά βαρύτητας, όχι με την αρχική της αίθουσας:
            # αυτό ακριβώς επιτρέπει σε πόρτα σε τοίχο να έχει άφιξη που στέκει.
            fresh_room = P.load_room(other.path)
            h = P.Hero(fresh_room,
                       ac * P.CELL + P.CELL // 2,
                       P.GRID_Y0 + ar * P.CELL + P.CELL // 2,
                       ag)
            bounced = False
            for _ in range(SETTLE):
                h.update()
                if h.won:
                    bounced = True
                    break
            check(f"room_{dest}: η άφιξη {where} δεν ξαναπερνά την πόρτα",
                  not bounced, f"βαρύτητα {ag}")


    # 15. Διακόπτης -> ΠΟΛΛΕΣ πόρτες. Το κανάλι είναι ο σύνδεσμος: ό,τι έχει
    #     το ίδιο κανάλι γυρίζει μαζί, όσες πόρτες κι αν είναι.
    grid = ["#" * 40] + [
        "#" + ("S" if i == 5 else ".") * 1 + "." * 37 + "#" for i in range(1, 23)
    ] + ["#" * 40]
    rows = [list(r) for r in grid]
    rows[5][1] = "S"                    # διακόπτης, κανάλι 1
    rows[8][10] = "G"                   # τρεις ΞΕΧΩΡΙΣΤΕΣ πόρτες, ίδιο κανάλι
    rows[8][20] = "G"
    rows[8][30] = "G"
    rows[12][5] = "G"                   # τέταρτη, ΑΛΛΟ κανάλι
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join([
        "gravity 0", "sw 1 5 1",
        "gate 10 8 1", "gate 20 8 1", "gate 30 8 1", "gate 5 12 2"])
    room = P.Room(text)
    h = P.Hero(room, 1 * 8 + 4, P.GRID_Y0 + 5 * 8 + 4, 0)

    check("οι πόρτες ξεκινούν κλειστές",
          all(room.cell(c, r) == P.GATE for c, r in
              ((10, 8), (20, 8), (30, 8), (5, 12))))
    h.toggle_gates(1)
    check("ένας διακόπτης άνοιξε ΚΑΙ ΤΙΣ ΤΡΕΙΣ πόρτες του καναλιού",
          all(room.cell(c, r) == P.GATE_OPEN for c, r in
              ((10, 8), (20, 8), (30, 8))),
          str([P.TYPE_NAMES[room.cell(c, r)] for c, r in
               ((10, 8), (20, 8), (30, 8))]))
    check("η πόρτα άλλου καναλιού ΔΕΝ πειράχτηκε",
          room.cell(5, 12) == P.GATE)
    check("ανοιγμένη πόρτα δεν είναι στερεή",
          not (P.PROPS[P.GATE_OPEN] & P.F_SOLID))
    h.toggle_gates(1)
    check("ο διακόπτης ξανακλείνει (δεν είναι μιας χρήσης)",
          all(room.cell(c, r) == P.GATE for c, r in ((10, 8), (20, 8), (30, 8))))

    # Το πάτημα δεν επαναλαμβάνεται όσο μένεις πάνω του: αλλιώς η πόρτα
    # ανοιγοκλείνει 50 φορές το δευτερόλεπτο και δεν ελέγχεται.
    h.x, h.y = 1 * 8 + 4, P.GRID_Y0 + 5 * 8 + 4
    h.prev_body = None
    h.touch_objects()
    first = room.cell(10, 8)
    h.touch_objects()
    check("ο διακόπτης δεν ξαναπατιέται όσο στέκεσαι πάνω του",
          room.cell(10, 8) == first, P.TYPE_NAMES[room.cell(10, 8)])

    # 16. Το κλειδί ανοίγει ΤΗ ΔΙΚΗ ΤΟΥ κλειδαριά. Χωρίς ταυτότητες ο
    #     σχεδιαστής δεν μπορεί να επιβάλει σειρά, που είναι όλο το puzzle.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][5] = "K"                   # κλειδαριά ταυτότητας 2
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + \
        "\n".join(["gravity 0", "lock 5 22 2"])
    room = P.Room(text)
    h = P.Hero(room, 5 * 8 + 4, P.GRID_Y0 + 18 * 8, 0)
    for _ in range(80):
        h.update(0)
    h.keys[1] = 1
    check("λάθος κλειδί ΔΕΝ ανοίγει την κλειδαριά", not h.use(),
          P.TYPE_NAMES[room.cell(5, 22)])
    h.keys[2] = 1
    check("το σωστό κλειδί ανοίγει", h.use() and room.cell(5, 22) == P.LOCK_OPEN)
    check("καταναλώθηκε ΜΟΝΟ το σωστό κλειδί",
          h.keys[2] == 0 and h.keys[1] == 1)

    # 17. Εύθραυστο: το περνάς ΜΙΑ φορά. Το F_FRAGILE υπήρχε από την αρχή αλλά
    #     κανείς δεν το κοιτούσε — το πάτωμα δεν κατέρρεε ποτέ.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for c in range(4, 12):
        rows[22][c] = "%"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0"
    room = P.Room(text)
    h = P.Hero(room, 5 * 8 + 4, P.GRID_Y0 + 20 * 8, 0)
    for _ in range(40):
        h.update(0)
    check("το εύθραυστο κρατάει όσο πατάς πάνω του",
          room.cell(5, 22) == P.CRUMBLE, P.TYPE_NAMES[room.cell(5, 22)])
    start = h.support_cell()
    for _ in range(200):
        h.update(1)
        if h.support_cell() != start:
            h.update(1)         # η κατάρρευση κρίνεται στο ΕΠΟΜΕΝΟ frame
            break
    check("το εύθραυστο καταρρέει μόλις φύγεις",
          room.cell(*start) == P.EMPTY, P.TYPE_NAMES[room.cell(*start)])

    # 18. Αγκάθια: ζημιά ανά SPIKE_TICKS frames, όχι σε κάθε frame. Με ζημιά
    #     κάθε frame η ενέργεια εξατμιζόταν πριν προλάβεις να αντιδράσεις.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for c in range(2, 20):
        rows[22][c] = "^"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0"
    room = P.Room(text)
    h = P.Hero(room, 5 * 8 + 4, P.GRID_Y0 + 21 * 8 + 4, 0)
    h.energy = P.ENERGY_MAX
    h.state = "IDLE"
    for _ in range(P.SPIKE_TICKS):
        h.touch_objects()
    check(f"αγκάθια: ένα χτύπημα ανά {P.SPIKE_TICKS} frames",
          h.energy == P.ENERGY_MAX - P.SPIKE_DMG,
          f"ενέργεια {h.energy}/{P.ENERGY_MAX}")
    h.touch_objects()
    check("αγκάθια: δεύτερο χτύπημα στο επόμενο διάστημα",
          h.energy == P.ENERGY_MAX - 2 * P.SPIKE_DMG, f"ενέργεια {h.energy}")

    # 19. Ζημιά πτώσης: μόνο πάνω από FALL_SAFE, και ΠΟΤΕ με ανοιγμένο
    #     αλεξίπτωτο — αυτός είναι όλος ο λόγος ύπαρξής του.
    h = P.Hero(fresh(), 60, 100, 0)
    h.energy, h.fall_dist, h.state = P.ENERGY_MAX, P.FALL_SAFE, "FALL"
    h.land()
    check(f"πτώση ακριβώς {P.FALL_SAFE}px δεν πονάει", h.energy == P.ENERGY_MAX,
          f"ενέργεια {h.energy}")
    h.energy, h.fall_dist, h.state = P.ENERGY_MAX, P.FALL_SAFE + 1, "FALL"
    h.land()
    check(f"πτώση πάνω από {P.FALL_SAFE}px πονάει", h.energy < P.ENERGY_MAX,
          f"ενέργεια {h.energy}")
    h.energy, h.fall_dist, h.state = P.ENERGY_MAX, 180, "FALL"
    h.parachute, h.para_open = 1, 1
    h.land()
    check("με ανοιγμένο αλεξίπτωτο η πτώση ΔΕΝ πονάει",
          h.energy == P.ENERGY_MAX and h.parachute == 0,
          f"ενέργεια {h.energy}, αλεξίπτωτα {h.parachute}")

    # Γειτονικές έξοδοι με ΔΙΑΦΟΡΕΤΙΚΟΥΣ προορισμούς πρέπει να απορρίπτονται.
    bad = ";\n" + "\n".join(
        "#" * 40 if i in (0, 23) else "#" + ("X" * 2 if i == 5 else ".." ) + "." * 36 + "#"
        for i in range(24)) + "\nexit 1 5 1\nexit 2 5 2\n"
    try:
        P.Room(bad)
        check("γειτονικές έξοδοι με διαφορετικό προορισμό απορρίπτονται", False)
    except ValueError:
        check("γειτονικές έξοδοι με διαφορετικό προορισμό απορρίπτονται", True)

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
