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
    #
    # ΤΟ ΚΙΒΩΤΙΟ ΔΕΝ ΕΙΝΑΙ ΣΤΕΡΕΟ: περνάς από μέσα, όπως στον teleporter. Δεν
    # στέκεσαι πάνω του — στέκεσαι ΜΕΣΑ του, και από εκεί το σηκώνεις.
    check("το κιβώτιο δεν είναι στερεό", not (P.PROPS[P.CRATE] & P.F_SOLID))
    room = fresh(strip=(P.CRATE,))
    room.cells[21][5] = P.CRATE          # στη γραμμή πάνω από το πάτωμα
    h = P.Hero(room, 5 * 8 + 4, 8 + 18 * 8, 0)
    for _ in range(80):                  # πέφτει ΜΕΣΑ από το κιβώτιο, ως το πάτωμα
        h.update(0)
    check("ο ήρωας περνά από μέσα και φτάνει στο πάτωμα",
          h.support_type() == P.SOLID, P.TYPE_NAMES[h.support_type()])

    room = fresh(strip=(P.CRATE,))
    room.cells[22][5] = P.CRATE          # στο ίδιο κελί με το σώμα του
    h = P.Hero(room, 5 * 8 + 4, P.GRID_Y0 + 22 * 8 + 4, 0)
    h.update(0)
    check("σήκωμα κιβωτίου από το κελί που στέκεσαι",
          h.use() and h.carry == 1 and room.cells[22][5] == P.EMPTY)
    check("άφημα κιβωτίου ΕΚΕΙ ΠΟΥ ΣΤΕΚΕΣΑΙ",
          h.use() and h.carry == 0 and room.cells[22][5] == P.CRATE)

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
            # Το 255 ΔΕΝ είναι αίθουσα: είναι η πόρτα που τελειώνει το
            # παιχνίδι (ROOM_END στο src/endings.asm). Χωρίς αυτή την
            # εξαίρεση ο έλεγχος ζητούσε αρχείο room_255.txt.
            if dest == 255:
                continue
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
    h.toggle_targets(1)
    check("ένας διακόπτης άνοιξε ΚΑΙ ΤΙΣ ΤΡΕΙΣ πόρτες του καναλιού",
          all(room.cell(c, r) == P.GATE_OPEN for c, r in
              ((10, 8), (20, 8), (30, 8))),
          str([P.TYPE_NAMES[room.cell(c, r)] for c, r in
               ((10, 8), (20, 8), (30, 8))]))
    check("η πόρτα άλλου καναλιού ΔΕΝ πειράχτηκε",
          room.cell(5, 12) == P.GATE)
    check("ανοιγμένη πόρτα δεν είναι στερεή",
          not (P.PROPS[P.GATE_OPEN] & P.F_SOLID))
    h.toggle_targets(1)
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

    # Ένα κλειδί ανοίγει ΟΛΕΣ τις κλειδαριές της ταυτότητάς του — αλλά μόνο
    # τις ΚΑΛΩΔΙΩΜΕΝΕΣ. Η ταυτότητα 0 σημαίνει «ακαλωδίωτη» και ανοίγει μόνη
    # της, αλλιώς πίστα με πολλές απλές κλειδαριές θα ξεκλείδωνε ολόκληρη.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for c in (5, 12, 20):
        rows[22][c] = "K"
    rows[22][30] = "K"
    rows[22][35] = "K"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "lock 5 22 2", "lock 12 22 2", "lock 20 22 2",
         "lock 30 22 3"])
    room = P.Room(text)
    h = P.Hero(room, 5 * 8 + 4, P.GRID_Y0 + 18 * 8, 0)
    for _ in range(80):
        h.update(0)
    h.keys[2] = 1
    check("ένα κλειδί ανοίγει ΟΛΕΣ τις κλειδαριές της ταυτότητάς του",
          h.use() and all(room.cell(c, 22) == P.LOCK_OPEN
                          for c in (5, 12, 20)),
          str([P.TYPE_NAMES[room.cell(c, 22)] for c in (5, 12, 20)]))
    check("άλλη ταυτότητα δεν πειράζεται", room.cell(30, 22) == P.LOCK)
    check("ακαλωδίωτη κλειδαριά δεν πειράζεται", room.cell(35, 22) == P.LOCK)
    check("καταναλώθηκε ΕΝΑ κλειδί, όχι ένα ανά κλειδαριά", h.keys[2] == 0)

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
    # Η ΑΤΡΩΣΙΑ ΥΠΕΡΙΣΧΥΕΙ ΤΟΥ SPIKE_TICKS. Το τεστ καλεί touch_objects()
    # απευθείας, που ΔΕΝ μετράει τα καρέ ατρωσίας — αυτό το κάνει η update().
    # Χωρίς αυτό, το δεύτερο χτύπημα δεν θα ερχόταν ποτέ.
    h.hurt_left = 0
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


    # 20. Η πόρτα ΔΕΝ ανοίγει με την επαφή — μόνο με ενεργοποίηση (ΠΑΝΩ/ΚΑΤΩ).
    #     Με αυτόματο πέρασμα κάθε άφιξη ήταν λεπτή ισορροπία: το σημείο
    #     άφιξης είναι αναγκαστικά κοντά στην πόρτα επιστροφής και ένα
    #     γλίστρημα λίγων pixel σε ξανάβαζε μέσα.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][30] = "X"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0\nexit 30 22 2"
    room = P.Room(text)

    h = P.Hero(room, 20 * 8 + 4, P.GRID_Y0 + 21 * 8 + 4, 0)
    for _ in range(200):                    # περπάτα ΠΑΝΩ στην πόρτα
        h.update(1)
        if h.body_cell() == P.EXIT:
            break
    check("ο ήρωας φτάνει πάνω στην πόρτα", h.body_cell() == P.EXIT,
          P.TYPE_NAMES[h.body_cell()])
    for _ in range(60):                     # …και μένει εκεί
        h.update(0)
    check("η πόρτα ΔΕΝ ανοίγει με την επαφή", not h.won)
    check("το πάτημα την ανοίγει", h.use() and h.won)

    # 21. Στοίβα διαδρομής: γυρνάς πίσω ως TRAIL_MAX δωμάτια.
    tr = P.Trail()
    for a, b in [(1, 2), (2, 3), (3, 4), (4, 5)]:
        tr.enter(a, b)
    check(f"στοίβα {P.TRAIL_MAX} δωματίων χωρίς σφράγιση",
          tr.rooms == [4, 3, 2, 1] and not tr.sealed, f"{tr.rooms}")
    tr.enter(5, 6)
    check("το πέμπτο δωμάτιο σφραγίζει το πρώτο",
          tr.rooms == [5, 4, 3, 2] and tr.sealed == {1}, f"{tr.rooms} {tr.sealed}")

    # Γυρνώντας πίσω, το δωμάτιο που άφησες είναι ΜΠΡΟΣΤΑ σου και ΔΕΝ
    # σφραγίζεται — αλλιώς δύο δωμάτια θα κλείδωναν το ένα το άλλο μόλις
    # πηγαινοερχόσουν.
    tr.enter(6, 5)
    check("το γύρισμα πίσω δεν σφραγίζει ό,τι άφησες",
          not tr.is_sealed(6), f"{tr.rooms} {tr.sealed}")
    check("η σφράγιση του πρώτου παραμένει", tr.is_sealed(1))
    tr.enter(5, 6)
    check("και ξαναμπροστά, χωρίς νέα σφράγιση",
          tr.rooms == [5, 4, 3, 2] and tr.sealed == {1}, f"{tr.rooms} {tr.sealed}")

    # Σφραγισμένος προορισμός -> τα κελιά της πόρτας γίνονται στερεά.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[10][5] = "X"
    rows[11][5] = "X"
    rows[10][30] = "X"
    text = ";\n" + "\n".join("".join(r) for r in rows) + \
        "\ngravity 0\nexit 5 10 1\nexit 30 10 9"
    room = P.Room(text)
    cells = tr.sealed_cells(room)
    check("σφραγίζονται τα κελιά ΜΟΝΟ της σφραγισμένης πόρτας",
          sorted(cells) == [(5, 10), (5, 11)], str(sorted(cells)))

    # 22. Ζώνη κλειδώματος: η βαρύτητα γίνεται ΚΑΤΩ και ΔΕΝ στρίβει σε γωνίες.
    #     Είναι νησίδα «κανονικού» παιχνιδιού — ο παίκτης ξέρει τι θα βρει
    #     μπαίνοντας, χωρίς να εξαρτάται από το πώς έτυχε να μπει.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for r in range(14, 23):
        rows[r][20] = "#"                       # κατακόρυφος τοίχος
    for r in range(10, 23):
        for c in range(12, 20):
            rows[r][c] = ":"                    # ζώνη γύρω από τη γωνία
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0"
    room = P.Room(text)
    h = P.Hero(room, 14 * 8 + 4, P.GRID_Y0 + 21 * 8 + 4, 0)
    seen = set()
    for _ in range(300):
        h.update(1)
        seen.add(h.g)
    check("μέσα στη ζώνη η βαρύτητα μένει ΚΑΤΩ", seen == {0}, str(sorted(seen)))

    # Μπαίνοντας με άλλη φορά, η ζώνη την επαναφέρει σε κάτω.
    h = P.Hero(room, 14 * 8 + 4, P.GRID_Y0 + 21 * 8 + 4, 6)
    h.update(0)
    check("μπαίνοντας με πλάγια φορά, γίνεται κάτω", h.g == 0, str(h.g))

    # Εκτός ζώνης, η γωνία εξακολουθεί να γυρίζει κανονικά.
    rows2 = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for r in range(14, 23):
        rows2[r][20] = "#"
    room2 = P.Room(";\n" + "\n".join("".join(r) for r in rows2) + "\ngravity 0")
    h2 = P.Hero(room2, 14 * 8 + 4, P.GRID_Y0 + 21 * 8 + 4, 0)
    seen2 = set()
    for _ in range(300):
        h2.update(1)
        seen2.add(h2.g)
    check("ΕΚΤΟΣ ζώνης η γωνία γυρίζει κανονικά", len(seen2) > 1,
          str(sorted(seen2)))

    # Γειτονικές έξοδοι με ΔΙΑΦΟΡΕΤΙΚΟΥΣ προορισμούς πρέπει να απορρίπτονται.
    bad = ";\n" + "\n".join(
        "#" * 40 if i in (0, 23) else "#" + ("X" * 2 if i == 5 else ".." ) + "." * 36 + "#"
        for i in range(24)) + "\nexit 1 5 1\nexit 2 5 2\n"
    try:
        P.Room(bad)
        check("γειτονικές έξοδοι με διαφορετικό προορισμό απορρίπτονται", False)
    except ValueError:
        check("γειτονικές έξοδοι με διαφορετικό προορισμό απορρίπτονται", True)

    # --- ΕΝΑΣ κόσμος αριθμών: κάθε ενεργοποιητής σε κάθε στόχο.
    #     Ήταν δύο χωριστοί κόσμοι (κανάλια / ταυτότητες), οπότε αυτοί οι
    #     συνδυασμοί ΔΕΝ γίνονταν καν να εκφραστούν.
    def wroom(cells, footer):
        rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
            + [list("#" * 40)]
        for (c, r, ch) in cells:
            rows[r][c] = ch
        return P.Room(";\n" + "\n".join("".join(r) for r in rows) + "\n"
                      + "\n".join(["gravity 0"] + footer))

    def whero(rm):
        return P.Hero(rm, 5 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)

    rm = wroom([(10, 22, "S"), (20, 22, "K")], ["sw 10 22 3", "lock 20 22 3"])
    whero(rm).toggle_targets(3)
    check("ο διακόπτης ανοίγει ΚΛΕΙΔΑΡΙΑ", rm.cells[22][20] == P.LOCK_OPEN,
          P.TYPE_NAMES[rm.cells[22][20]])

    rm = wroom([(10, 22, "k"), (20, 22, "G")], ["key 10 22 4", "gate 20 22 4"])
    h = whero(rm)
    h.keys[4] = 1
    h.open_locks((10, 22), 4)
    check("το κλειδί ανοίγει ΠΥΛΗ, μόνιμα", rm.cells[22][20] == P.GATE_OPEN,
          P.TYPE_NAMES[rm.cells[22][20]])

    for ch, on, off in (("^", P.SPIKE_U, P.SPIKE_U_OFF),
                        ("v", P.SPIKE_D, P.SPIKE_D_OFF),
                        ("<", P.SPIKE_L, P.SPIKE_L_OFF),
                        (">", P.SPIKE_R, P.SPIKE_R_OFF)):
        rm = wroom([(20, 22, ch)], ["spikes 20 22 1"])
        h = whero(rm)
        h.set_targets(1, True)
        a = rm.cells[22][20]
        h.set_targets(1, False)
        b = rm.cells[22][20]
        # Η ΦΟΡΑ ΠΡΕΠΕΙ ΝΑ ΕΠΙΒΙΩΝΕΙ: γι' αυτό υπάρχουν τέσσερις τραβηγμένοι
        # τύποι και όχι ένας — ο πίνακας κελιών δεν έχει πού αλλού να την
        # κρατήσει, και ένα αγκάθι που ξαναβγαίνει αλλού είναι άλλη παγίδα.
        check(f"αγκάθι '{ch}': τραβιέται και ξαναβγαίνει ΙΔΙΟ",
              a == off and b == on,
              f"{P.TYPE_NAMES[a]} -> {P.TYPE_NAMES[b]}")

    # ΚΑΙ ΜΕ ΤΟΝ ΗΡΩΑ ΠΑΝΩ ΣΤΟΝ ΔΙΑΚΟΠΤΗ, ΟΧΙ ΜΕ ΚΛΗΣΗ ΤΟΥ set_targets.
    #
    # Ό,τι παραπάνω καλεί κατευθείαν το set_targets/toggle_targets παρακάμπτει
    # ακριβώς το κομμάτι που μπορεί να λείπει: την αφή, το κανάλι, τη σάρωση
    # στόχων. Σφάλμα αυτού του σχήματος έζησε στη JavaScript ενώ 120 καρέ
    # έβγαιναν ίδια, γιατί και η σύγκριση έγραφε το κελί με το χέρι.
    #
    # Οι τέσσερις περιπτώσεις καρφώνουν και ΠΟΙΑ επιφάνεια θέλει κάθε φορά — το
    # 'Q' κοιτάζει αριστερά, άρα πατιέται από τον ΔΕΞΙΟ τοίχο.
    for ch, g, (sc, sr), (hc, hr), spike, where in (
            ("S", 0, (10, 22), (10, 21), "^", "δαπέδου"),
            ("A", 4, (10,  1), (10,  2), "v", "ταβανιού"),
            ("Q", 6, (38, 12), (37, 12), "<", "δεξιού τοίχου"),
            ("E", 2, ( 1, 12), ( 2, 12), ">", "αριστερού τοίχου")):
        rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
            + [list("#" * 40)]
        rows[sr][sc] = ch
        rows[12][20] = spike
        rm = P.Room(";\n" + "\n".join("".join(r) for r in rows)
                    + f"\ngravity {g}\nsw {sc} {sr} 1\nspikes 20 12 1\n")
        h = P.Hero(rm, hc * P.CELL + P.CELL // 2,
                   P.GRID_Y0 + hr * P.CELL + P.CELL // 2, g)
        before = rm.cells[12][20]
        for _ in range(60):
            h.update(0)
            if rm.cells[12][20] != before:
                break
        check(f"ο διακόπτης {where} τραβάει τα αγκάθια του",
              rm.cells[12][20] == P.SPIKE_OFF[before],
              f"{P.TYPE_NAMES[before]} -> {P.TYPE_NAMES[rm.cells[12][20]]}")

    check("τα τραβηγμένα αγκάθια είναι στερεά αλλά ΑΚΙΝΔΥΝΑ",
          not (P.PROPS[P.SPIKE_U_OFF] & P.F_DEADLY)
          and (P.PROPS[P.SPIKE_U_OFF] & P.F_SOLID))

    rm = wroom([(20, 22, "G")], [])
    whero(rm).set_targets(0, True)
    check("το κανάλι 0 είναι ακαλωδίωτο και δεν το ελέγχει κανείς",
          rm.cells[22][20] == P.GATE)

    # ΟΛΟΚΛΗΡΗ Η ΟΜΑΔΑ ΥΠΑΚΟΥΕΙ, ΚΑΙ ΣΤΙΣ ΔΥΟ ΚΑΤΑΣΤΑΣΕΙΣ. Το κανάλι απλώνεται
    # σε κάθε κελί της ομάδας, αλλιώς ο διακόπτης πιάνει μόνο το κελί που
    # ονομάζει η ουρά. Ο browser το είχε αυτό ακριβώς για τις ΗΔΗ ΑΝΟΙΧΤΕΣ
    # πύλες: έκλεινε το ένα κομμάτι και άφηνε τα υπόλοιπα ανοιχτά.
    for ch, shut, opened in (("G", P.GATE, P.GATE_OPEN),
                             ("g", P.GATE_OPEN, P.GATE),
                             ("K", P.LOCK, P.LOCK_OPEN),
                             ("|", P.LOCK_OPEN, P.LOCK)):
        rm = wroom([(20, 12, ch), (20, 13, ch), (20, 14, ch)],
                   [f"gate 20 12 1" if ch in "Gg" else "lock 20 12 1"])
        h = whero(rm)
        h.set_targets(1, ch in "Gg" and ch == "G" or ch == "K")
        got = [rm.cells[r][20] for r in (12, 13, 14)]
        check(f"«{ch}»: και τα τρία κελιά της ομάδας υπακούν",
              len(set(got)) == 1 and got[0] != shut,
              ", ".join(P.TYPE_NAMES[v] for v in got))

    # ================= ΚΙΝΟΥΜΕΝΕΣ ΠΛΑΤΦΟΡΜΕΣ =================
    #
    # Το μόνο υλικό που δεν ζει στο πλέγμα. Ό,τι ελέγχεται εδώ είναι ακριβώς τα
    # σημεία όπου αυτό το κάνει να διαφέρει από κάθε άλλο αντικείμενο.
    print("--- κινούμενες πλατφόρμες")

    def proom(path, speed=50, chan=1, ch="M", cells=2):
        rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
            + [list("#" * 40)]
        for i in range(cells):
            rows[14][10 + i] = ch
        return P.Room(";\n" + "\n".join("".join(r) for r in rows)
                      + f"\ngravity 0\nplat 10 14 {path} {chan} {speed}\n")

    rm = proom("24 14")
    pl = rm.platforms[0]
    check("το μέγεθος βγαίνει από το ΠΛΕΓΜΑ, όχι από αριθμό",
          (pl["w"], pl["h"]) == (2 * P.CELL, P.CELL), f'{pl["w"]}x{pl["h"]}')
    check("τα κελιά της σβήνονται — δείχνουν πού ξεκινάει, δεν είναι υλικό",
          rm.cells[14][10] == P.EMPTY and rm.cells[14][11] == P.EMPTY)
    check("…αλλά ΕΙΝΑΙ στερεή εκεί που στέκεται",
          rm.solid_at(pl["x"] + 4, pl["y"] + 4)
          and not rm.solid_at(pl["x"] - 4, pl["y"] + 4))

    # ΟΙ ΤΡΕΙΣ ΔΙΑΔΡΟΜΕΣ, ΚΑΙ Ο ΗΡΩΑΣ ΠΑΝΩ ΤΟΥΣ. Η μεταφορά είναι όλο το νόημα:
    # πλατφόρμα που φεύγει από κάτω σου δεν είναι πλατφόρμα, είναι παγίδα.
    for path, label in (("24 14", "οριζόντια"), ("10 20", "κατακόρυφα"),
                        ("16 20", "διαγώνια")):
        rm = proom(path, cells=3)
        pl = rm.platforms[0]
        pl["moving"] = False                    # άσε τον να προσγειωθεί πρώτα
        h = P.Hero(rm, 11 * P.CELL + 4, P.GRID_Y0 + 13 * P.CELL)
        for _ in range(40):
            h.update(0)
        pl["moving"] = True
        p0, h0 = (pl["x"], pl["y"]), (h.x, h.y)
        for _ in range(10):
            h.update(0)
        moved = (pl["x"] - p0[0], pl["y"] - p0[1])
        check(f"{label}: ο ήρωας ταξιδεύει ΜΑΖΙ της",
              moved == (h.x - h0[0], h.y - h0[1]) and moved != (0, 0),
              f'πλατφόρμα {moved}, ήρωας {(h.x - h0[0], h.y - h0[1])}')

    # Η ΤΑΧΥΤΗΤΑ ΕΙΝΑΙ ΣΕ PIXEL/ΔΕΥΤΕΡΟΛΕΠΤΟ, ΟΧΙ ΑΝΑ ΠΕΡΑΣΜΑ. Ένα πέρασμα
    # κοστίζει 3 vsync ακίνητος και 7 τρέχοντας· με μέτρημα περασμάτων η
    # πλατφόρμα θα διπλασίαζε ταχύτητα μόλις έτρεχε ο παίκτης, δηλαδή ο γρίφος
    # θα άλλαζε ανάλογα με το πώς περπατάς.
    #
    # ΔΙΑΝΥΘΕΙΣΑ ΑΠΟΣΤΑΣΗ ΚΑΙ ΟΧΙ ΜΕΤΑΤΟΠΙΣΗ: η πλατφόρμα γυρίζει στα άκρα, οπότε
    # το «πού είναι» δεν λέει πόσο ταξίδεψε. Η πρώτη μορφή του τεστ κοκκίνιζε
    # ενώ ο κώδικας ήταν σωστός — μετρούσε δύο διαφορετικές φάσεις της διαδρομής.
    #
    # ΜΕΣΑ ΣΤΟ ΠΡΩΤΟ ΣΚΕΛΟΣ, ΠΡΙΝ ΦΤΑΣΕΙ ΣΤΟ ΑΚΡΟ. Με την παύση των δύο
    # δευτερολέπτων, ένα παράθυρο που περιλαμβάνει άκρο μετράει και τον χρόνο
    # ακινησίας — και οι δύο δρόμοι φτάνουν εκεί σε διαφορετική στιγμή, οπότε
    # το τεστ κοκκίνιζε ενώ η ταχύτητα ήταν ίδια.
    dist = {}
    for running, label in ((False, "ακίνητος"), (True, "τρέχοντας")):
        rm = proom("30 14", speed=25)
        pl = rm.platforms[0]
        h = P.Hero(rm, 30 * P.CELL, P.GRID_Y0 + 21 * P.CELL)
        travelled, last = 0, pl["x"]
        for _ in range(40):
            h.update(1 if running else 0, running)
            travelled += abs(pl["x"] - last)
            last = pl["x"]
        assert pl["wait"] == 0 and pl["dir"] == 1, "το παράθυρο έφτασε στο άκρο"
        dist[label] = travelled / h.clock       # pixel ανά vsync
    check("η ταχύτητα δεν εξαρτάται από το τι κάνει ο παίκτης",
          abs(dist["ακίνητος"] - dist["τρέχοντας"]) < 0.02,
          f'{dist["ακίνητος"]:.3f} vs {dist["τρέχοντας"]:.3f} px/vsync')

    # Στα άκρα γυρίζει: πάει κι έρχεται για πάντα.
    rm = proom("14 14", speed=100)
    pl = rm.platforms[0]
    h = P.Hero(rm, 30 * P.CELL, P.GRID_Y0 + 21 * P.CELL)
    seen = set()
    for _ in range(120):
        h.update(0)
        seen.add(pl["x"])
    check("φτάνει και στα δύο άκρα και γυρίζει",
          min(seen) == 10 * P.CELL and max(seen) == 14 * P.CELL,
          f"{min(seen)}..{max(seen)}")

    # Ο ΔΙΑΚΟΠΤΗΣ ΤΗ ΣΤΑΜΑΤΑΕΙ, μέσα από τον ΠΙΝΑΚΑ. Το target_cells σαρώνει
    # κελιά και η πλατφόρμα έχει φύγει από το δικό της με το πρώτο βήμα.
    rm = proom("24 14")
    pl = rm.platforms[0]
    h = P.Hero(rm, 30 * P.CELL, P.GRID_Y0 + 21 * P.CELL)
    for _ in range(10):
        h.update(0)
    h.set_targets(1, True)
    stopped = pl["x"]
    for _ in range(20):
        h.update(0)
    check("ο διακόπτης τη σταματάει ΑΦΟΥ έχει φύγει από το κελί της",
          pl["x"] == stopped and stopped != pl["ax"], f'x={pl["x"]}')
    h.set_targets(1, False)
    for _ in range(10):
        h.update(0)
    check("…και την ξαναξεκινάει", pl["x"] != stopped, f'x={pl["x"]}')

    # ΣΤΕΡΕΗ ΜΟΝΟ ΑΠΟ ΠΑΝΩ. Είναι ανελκυστήρας, όχι κουτί: από κάτω περνάς.
    # Ο κανόνας είναι ο ΙΔΙΟΣ με τις μονόδρομες πλατφόρμες, γι' αυτό και
    # ελέγχεται με τις τέσσερις ορθές φορές — μία ξεχασμένη θα ήταν πλατφόρμα
    # που σε σταματά από το πλάι, δηλαδή αόρατος τοίχος.
    rm = proom("24 14")
    pl = rm.platforms[0]
    mid = (pl["x"] + 4, pl["y"] + 4)
    for g, want in ((0, True), (4, False), (2, False), (6, False)):
        rm.probe_g = g
        check(f"βαρύτητα {g}: στερεή = {want}", rm.solid_at(*mid) == want)

    # Και στην πράξη: με βαρύτητα ΠΑΝΩ ο ήρωας τη διασχίζει και δεν κολλάει.
    rm = proom("24 14", cells=3)
    pl = rm.platforms[0]
    h = P.Hero(rm, 11 * P.CELL + 4, P.GRID_Y0 + 17 * P.CELL, 4)
    for _ in range(60):
        h.update(0)
    check("από κάτω, με βαρύτητα πάνω, περνάει από μέσα της",
          h.y < pl["y"], f'ήρωας y={h.y}, πλατφόρμα y={pl["y"]}')

    # ΠΑΥΣΗ ΣΤΑ ΑΚΡΑ. Χωρίς αυτήν γύριζε ακαριαία και το παράθυρο για να
    # ανέβεις ή να κατέβεις ήταν ένα καρέ.
    rm = proom("14 14", speed=100)
    pl = rm.platforms[0]
    h = P.Hero(rm, 30 * P.CELL, P.GRID_Y0 + 21 * P.CELL)
    still, worst, prev = 0, 0, pl["x"]
    for _ in range(200):
        h.update(0)
        if pl["x"] == prev:
            still += P.CPC_VSYNC_IDLE
            worst = max(worst, still)
        else:
            still = 0
        prev = pl["x"]
    check(f"στα άκρα περιμένει {P.PLAT_PAUSE} δευτερόλεπτα",
          abs(worst - P.PLAT_PAUSE * 50) <= 2 * P.CPC_VSYNC_RUN,
          f"{worst} vsync = {worst / 50:.2f}s")

    # Ο ΕΠΙΒΑΤΗΣ: διακόπτης ζωγραφισμένος ΠΑΝΩ της, που ταξιδεύει μαζί της.
    # Χωρίς αυτό θα έμενε καρφωμένος στο κελί του ενώ η πλατφόρμα φεύγει.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for i in range(3):
        rows[14][10 + i] = "M"
    rows[13][11] = "S"
    rows[18][25] = "G"
    rm = P.Room(";\n" + "\n".join("".join(r) for r in rows)
                + "\ngravity 0\nplat 10 14 20 14 0 40\nsw 11 13 2\ngate 25 18 2\n")
    pl = rm.platforms[0]
    check("ο διακόπτης από πάνω γίνεται επιβάτης",
          pl["rider"] == P.SWITCH_U and pl["rchan"] == 2 and pl["rdx"] == P.CELL,
          f'rider={pl["rider"]} chan={pl["rchan"]} dx={pl["rdx"]}')
    check("…και το κελί του αδειάζει", rm.cells[13][11] == P.EMPTY)

    x0 = rm.rider_box(pl)[0]
    h = P.Hero(rm, 30 * P.CELL, P.GRID_Y0 + 21 * P.CELL)
    for _ in range(20):
        h.update(0)
    check("ο επιβάτης ταξιδεύει ΜΑΖΙ της",
          rm.rider_box(pl)[0] - x0 == pl["x"] - pl["ax"],
          f'επιβάτης +{rm.rider_box(pl)[0] - x0}, πλατφόρμα +{pl["x"] - pl["ax"]}')

    # Και πατιέται: ο ήρωας στέκεται πάνω του και η πύλη του ανοίγει.
    rm = P.Room(";\n" + "\n".join("".join(r) for r in rows)
                + "\ngravity 0\nplat 10 14 20 14 0 40\nsw 11 13 2\ngate 25 18 2\n")
    pl = rm.platforms[0]
    pl["moving"] = False
    h = P.Hero(rm, 11 * P.CELL + 4, P.GRID_Y0 + 13 * P.CELL)
    for _ in range(30):
        h.update(0)
    check("πατώντας τον επιβάτη ανοίγει η πύλη του",
          rm.cells[18][25] == P.GATE_OPEN and pl["rider"] == P.SWITCH_U_ON,
          P.TYPE_NAMES[rm.cells[18][25]])

    # Το 'm' ξεκινά ακίνητη: ο παίκτης πρέπει να τη βρει και να την ανάψει.
    rm = proom("24 14", ch="m")
    check("το «m» ξεκινά σταματημένη", not rm.platforms[0]["moving"])

    # Διαδρομή που δεν είναι ούτε ίσια ούτε στις 45 μοίρες δεν παρακολουθείται
    # με το μάτι — και σιωπηλά στραβή θα ήταν χειρότερη από άκυρη.
    try:
        proom("17 20")
        check("λοξή διαδρομή απορρίπτεται", False, "δεν πέταξε σφάλμα")
    except ValueError:
        check("λοξή διαδρομή απορρίπτεται", True)

    # --- ΤΟ ΣΧΗΜΑ ΠΡΕΠΕΙ ΝΑ ΣΥΜΦΩΝΕΙ ΜΕ ΤΗ ΦΥΣΙΚΗ.
    #     Το αγκάθι είναι θανατηφόρο από τη μεριά των ΜΥΤΩΝ και ακίνδυνο από
    #     τη ΒΑΣΗ. Αν το γραφικό δείχνει ανάποδα, ο παίκτης πατάει με
    #     εμπιστοσύνη τη μεριά που τον σκοτώνει. Το αριστερό και το δεξί ήταν
    #     όντως ανταλλαγμένα.
    import genasm as GA
    face_side = {4: "top", 2: "left", 0: "bottom", 6: "right"}
    opposite = {"top": "bottom", "bottom": "top",
                "left": "right", "right": "left"}
    for st in (P.SPIKE_U, P.SPIKE_L, P.SPIKE_D, P.SPIKE_R):
        px = GA.tile_pixels(st)
        sides = {"top": sum(1 for u in range(8) if px[0][u]),
                 "bottom": sum(1 for u in range(8) if px[7][u]),
                 "left": sum(1 for v in range(8) if px[v][0]),
                 "right": sum(1 for v in range(8) if px[v][7])}
        base = max(sides, key=sides.get)
        want = opposite[face_side[P.FACING[st]]]
        check(f"{P.TYPE_NAMES[st]}: η βάση απέναντι από τις μύτες",
              base == want, f"βάση {base}, περίμενα {want}")

    # Τα one-way έχουν τον ΑΝΤΙΘΕΤΟ κανόνα από τα αγκάθια: η γεμάτη μπάρα
    # κάθεται ΠΑΝΩ στη φορά, γιατί από εκεί δεν περνάς. Ίδια συνέπεια αν
    # ζωγραφιστεί ανάποδα: το σχήμα δείχνει στέρεο εκεί που περνάς.
    for ow in (P.ONEWAY_U, P.ONEWAY_L, P.ONEWAY_D, P.ONEWAY_R):
        px = GA.tile_pixels(ow)
        sides = {"top": sum(1 for u in range(8) if px[0][u]),
                 "bottom": sum(1 for u in range(8) if px[7][u]),
                 "left": sum(1 for v in range(8) if px[v][0]),
                 "right": sum(1 for v in range(8) if px[v][7])}
        solid = max(sides, key=sides.get)
        want = face_side[P.FACING[ow]]
        check(f"{P.TYPE_NAMES[ow]}: η μπάρα ΠΑΝΩ στη φορά",
              solid == want, f"μπάρα {solid}, περίμενα {want}")

    # ΤΑ ΤΡΑΒΗΓΜΕΝΑ ΕΙΝΑΙ ΠΑΤΩΜΑ, ΚΑΙ ΤΟ ΠΑΤΩΜΑ ΠΡΕΠΕΙ ΝΑ ΥΠΑΡΧΕΙ ΕΚΕΙ ΠΟΥ
    # ΠΑΤΑΣ. Το κελί είναι στερεό ολόκληρο, άρα ο ήρωας στέκεται στην ΑΚΡΗ του
    # — και το σχήμα είχε τη μπάρα στον πάτο και τα υπόλοιπα κενά, οπότε ο
    # ήρωας αιωρούνταν έξι pixel, μισό σώμα, πάνω από ό,τι φαινόταν.
    #
    # Ο παλιός έλεγχος έψαχνε «τη βάση» ως την πλευρά με τα περισσότερα pixel.
    # Σε θήκη με περίγραμμα όλες οι πλευρές είναι γεμάτες, οπότε η μέτρηση
    # έδειχνε όποια τύχαινε πρώτη. Αυτό που έχει σημασία είναι δύο πράγματα:
    for on, off in P.SPIKE_OFF.items():
        pon, poff = GA.tile_pixels(on), GA.tile_pixels(off)
        sides = lambda px: {"top": sum(1 for u in range(8) if px[0][u]),
                            "bottom": sum(1 for u in range(8) if px[7][u]),
                            "left": sum(1 for v in range(8) if px[v][0]),
                            "right": sum(1 for v in range(8) if px[v][7])}

        # 1. ΚΑΜΙΑ πλευρά κενή: όποια κι αν είναι η βαρύτητα, ο ήρωας πατάει
        #    πάνω σε κάτι ζωγραφισμένο και όχι στον αέρα.
        s = sides(poff)
        check(f"{P.TYPE_NAMES[off]}: κάθε πλευρά είναι επιφάνεια",
              min(s.values()) >= 6, f"λιγότερα pixel: {min(s, key=s.get)} "
              f"{min(s.values())}")

        # 2. Οι τρύπες κοιτούν εκεί που δείχνουν οι μύτες — δηλαδή απέναντι
        #    από τη βάση του βγαλμένου. Έτσι διαβάζεται ΠΟΙΑ παγίδα είναι.
        holes = min(s, key=s.get)
        base = max(sides(pon), key=sides(pon).get)
        check(f"{P.TYPE_NAMES[off]}: οι τρύπες απέναντι από τη βάση του "
              f"{P.TYPE_NAMES[on]}",
              holes == opposite[base], f"τρύπες {holes}, βάση {base}")

    # --- Κιβώτιο που ΠΕΦΤΕΙ πάνω σε πλάκα την πατάει.
    #     Σταματούσε ένα κελί πιο πάνω και η πλάκα έμενε ελεύθερη: έστηνες
    #     τη μηχανή σωστά και η πύλη δεν άνοιγε, χωρίς να φαίνεται γιατί.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "p"          # πλάκα στο πάτωμα
    rows[14][10] = "B"          # κιβώτιο οκτώ κελιά ψηλότερα
    rows[22][30] = "G"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "plate 10 22 1", "gate 30 22 1"])
    rm = P.Room(text)
    h = P.Hero(rm, 5 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)
    h.crates_on = True
    for _ in range(200):
        h.update(0)
    check("το κιβώτιο που πέφτει ΠΑΤΑΕΙ την πλάκα",
          rm.cells[22][10] == P.PLATE_DOWN, P.TYPE_NAMES[rm.cells[22][10]])
    check("…και η πύλη του καναλιού ανοίγει",
          rm.cells[22][30] == P.GATE_OPEN, P.TYPE_NAMES[rm.cells[22][30]])

    # --- Ατρωσία μετά από χτύπημα.
    #     Χωρίς αυτή, στα αγκάθια η ζημιά ερχόταν κάθε SPIKE_TICKS καρέ όσο
    #     ακουμπούσες: ένα λάθος ισοδυναμούσε με θάνατο.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "^"
    hrm = P.Room(";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0")
    h = P.Hero(hrm, 10 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)
    full = h.energy
    h.update(0)
    check("το πρώτο άγγιγμα αγκαθιού πονάει", h.energy < full,
          f"{full} -> {h.energy}")
    after = h.energy
    check("…ο μετρητής ξεκινά γεμάτος", h.hurt_left == P.HURT_FRAMES,
          str(h.hurt_left))
    # HURT_FRAMES-1: ο μετρητής μπήκε ΜΕΣΑ στο καρέ της ζημιάς και μειώνεται
    # στην ΑΡΧΗ κάθε επόμενου, οπότε στο τελευταίο από αυτά είναι ακόμα 1.
    for _ in range(P.HURT_FRAMES - 1):
        h.update(0)
    check("…και σε ΟΛΑ τα καρέ ατρωσίας δεν ξαναπονάει",
          h.energy == after, f"{after} -> {h.energy}")
    for _ in range(P.SPIKE_TICKS + 1):
        h.update(0)
    check("…και μετά ξαναπονάει", h.energy < after, f"{after} -> {h.energy}")

    # --- Το κλειδί ανοίγει και ΠΥΛΗ που πατάς.
    rm = wroom([(10, 22, "G"), (30, 22, "K")],
               ["gate 10 22 3", "lock 30 22 3"])
    h = P.Hero(rm, 10 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)
    h.use()
    check("χωρίς κλειδί η πύλη μένει κλειστή", rm.cells[22][10] == P.GATE,
          P.TYPE_NAMES[rm.cells[22][10]])
    h.keys[3] = 1
    h.use()
    # Η ανοιχτή μορφή ΤΟΥ ΤΥΠΟΥ: καρφωμένο LOCK_OPEN θα μεταμόρφωνε την πύλη
    # σε λουκέτο, που είναι άλλο αντικείμενο και ανοίγει με άλλον τρόπο.
    check("με το κλειδί της, η πύλη που πατάς ανοίγει ΩΣ ΠΥΛΗ",
          rm.cells[22][10] == P.GATE_OPEN, P.TYPE_NAMES[rm.cells[22][10]])
    check("…και ανοίγει και το λουκέτο του ίδιου καναλιού",
          rm.cells[22][30] == P.LOCK_OPEN, P.TYPE_NAMES[rm.cells[22][30]])
    check("…και ξοδεύτηκε ένα κλειδί", h.keys[3] == 0)

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
