#!/usr/bin/env python3
"""Ο πυργίσκος σε Python και σε JavaScript, βήμα προς βήμα.

ΓΙΑΤΙ ΞΕΧΩΡΙΣΤΟ ΑΡΧΕΙΟ: το tools/parity.py συγκρίνει τα δύο αντίγραφα πάνω στο
levels/regress.txt, που είναι σταθερό και ΔΕΝ επιτρέπεται να πειραχτεί — άρα δεν
έχει και δεν θα αποκτήσει πυργίσκο. Χωρίς αυτό εδώ, ο κώδικας των βελών στη
JavaScript δεν συγκρινόταν ποτέ με το μοντέλο: θα μπορούσε να μην τρέχει καθόλου
και όλα τα τεστ θα ήταν πράσινα.

Τρέχει το ΠΡΑΓΜΑΤΙΚΟ physics.js σε node, με το ίδιο data.js που φορτώνει ο
browser, και συγκρίνει καρέ προς καρέ: θέση κάθε βέλους, ενέργεια, ρολόι.
"""

import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "editor", "wwwroot", "game")
FRAMES = 120

# Πυργίσκος με καθαρή ευθεία προς τον ήρωα, και ένας οριζόντιος για να μπουν
# και οι δύο άξονες στη σύγκριση.
ROOM = [(10, 16, "I"), (4, 21, "="), (30, 6, "I")]
# ΜΕ ΠΑΡΑΜΕΤΡΟΥΣ, αλλιώς η σύγκριση δοκιμάζει μόνο τις προεπιλογές: ένας
# πυργίσκος με γρήγορη φόρτιση, ένας με ρυθμό που ρίχνει χωρίς να βλέπει.
CHANNEL = 5
FOOTER = ("turret 10 16 0 2 0\nturret 4 21 0 5 0\n"
          f"turret 30 6 {CHANNEL} 5 1\n")

# Ο ΔΙΑΚΟΠΤΗΣ ΜΕΣΑ ΣΤΗ ΣΥΓΚΡΙΣΗ. Ο ρυθμικός του (30,6) σβήνει στο καρέ 40 και
# ξανανάβει στο 80: δεν ρωτάει ούτε εμβέλεια ούτε οπτική επαφή, οπότε ο
# διακόπτης είναι το ΜΟΝΟ πράγμα που τον σταματά.
#
# ΜΕΣΑ ΑΠΟ ΤΟ set_targets, ΟΧΙ ΓΡΑΦΟΝΤΑΣ ΤΟ ΚΕΛΙ. Η πρώτη μορφή αυτού του τεστ
# άλλαζε τον τύπο του κελιού με το χέρι «γιατί αυτό κάνει ο διακόπτης», και
# έτσι πηδούσε ακριβώς το κομμάτι που ήταν σπασμένο: το OPEN_OF της JavaScript
# δεν είχε καθόλου πυργίσκους, οπότε το targetCells δεν επέστρεφε ποτέ κανέναν
# και ο διακόπτης δεν έσβηνε τίποτα στον browser. 120 από 120 καρέ ίδια, και το
# παιχνίδι χαλασμένο. Η σύγκριση περνάει τώρα από τον ΙΔΙΟ δρόμο με τον παίκτη.
SWITCH_OFF, SWITCH_ON = 40, 80


def build_room():
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for c, r, ch in ROOM:
        rows[r][c] = ch
    return (";\n" + "\n".join("".join(x) for x in rows)
            + "\ngravity 0\n" + FOOTER)


def python_trace():
    rm = P.Room(build_room())
    rm.number, rm.path = 1, ""
    h = P.Hero(rm, 10 * P.CELL + P.CELL // 2, P.GRID_Y0 + 18 * P.CELL)
    out = []
    for i in range(FRAMES):
        # Κινήσου λίγο, ώστε να αλλάζει και το κόστος του καρέ: εκεί κρύβεται
        # η διαφορά ανάμεσα σε «5 δευτερόλεπτα» και «τόσα περάσματα».
        if i == SWITCH_OFF:
            h.set_targets(CHANNEL, True)        # «ανοιχτό» = ακίνδυνο
        elif i == SWITCH_ON:
            h.set_targets(CHANNEL, False)
        walk = 1 if (i // 20) % 2 == 0 else -1
        h.update(walk, (i // 40) % 2 == 0)
        out.append([h.clock, h.energy,
                    sorted([a["x"], a["y"], a["gone"]] for a in h.arrows)])
    return out


JS = """
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));      // data.js -> window.GAME_DATA
eval(fs.readFileSync(process.argv[3], "utf8"));      // physics.js -> window.GRAV
const G = window.GRAV, D = window.GAME_DATA;
const blob = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const room = new G.Room(blob.cells, {}, blob.attrs, blob.turretArg);
// Η βαρύτητα ΡΗΤΑ: ο Hero της JavaScript δεν έχει προεπιλογή, ενώ το Python
// έχει g=0 — και χωρίς αυτήν το g βγαίνει undefined και σκάει στους πίνακες.
const h = new G.Hero(room, 10 * D.CELL + (D.CELL >> 1),
                     D.GRID_Y0 + 18 * D.CELL, 0);
const out = [];
for (let i = 0; i < __N__; i++) {
  if (i === blob.switchOff) h.setTargets(blob.channel, true);
  else if (i === blob.switchOn) h.setTargets(blob.channel, false);
  const walk = ((i / 20) | 0) % 2 === 0 ? 1 : -1;
  h.update(walk, ((i / 40) | 0) % 2 === 0);
  out.push([h.clock, h.energy,
            h.arrows.map(a => [a.x, a.y, a.gone]).sort((p, q) =>
              p[0] - q[0] || p[1] - q[1] || p[2] - q[2])]);
}
console.log(JSON.stringify(out));
""".replace("__N__", str(FRAMES))


def node_exe():
    """Ο node όπως τον δηλώνει το toolchain.json, ή ό,τι βρει το PATH.

    Ο node δεν είναι εργαλείο του CPC και σπάνια είναι στο PATH· η διαδρομή του
    δηλώνεται στο toolchain.json όπως των rasm/iDSK.
    """
    import toolchain
    return toolchain.resolve("node")


def have_node():
    exe = node_exe()
    return shutil.which(exe) is not None or os.access(exe, os.X_OK)


def js_trace(tmp):
    # Ο Room της JavaScript παίρνει ΠΛΕΓΜΑ, όχι κείμενο — το ίδιο κάνει και το
    # tools/parity.py. Το parsing είναι δουλειά του μοντέλου, μία φορά.
    rm = P.Room(build_room())
    room_path = os.path.join(tmp, "room.json")
    with open(room_path, "w") as f:
        json.dump({"cells": rm.cells,
                   "turretArg": {f"{c},{r}": list(v)
                                 for (c, r), v in rm.turret_arg.items()},
                   # ΚΑΙ ΟΙ ΙΔΙΟΤΗΤΕΣ: χωρίς αυτές το targetCells δεν έχει πού
                   # να ψάξει και ο διακόπτης δεν αγγίζει τίποτα — και στις δύο
                   # πλευρές, οπότε η σύγκριση θα έμενε πράσινη χωρίς λόγο.
                   "attrs": {f"{c},{r}": v for (c, r), v in rm.attrs.items()},
                   "channel": CHANNEL,
                   "switchOff": SWITCH_OFF, "switchOn": SWITCH_ON}, f)
    js_path = os.path.join(tmp, "run.js")
    with open(js_path, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js_path,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"), room_path],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("node: " + (r.stderr.strip() or "άγνωστο σφάλμα"))
    return json.loads(r.stdout)


def check_room_wiring(fail):
    """Ο,τι διαβάζει το run.js από την ουρά πρέπει να ΦΤΑΝΕΙ στο δωμάτιο.

    ΤΟ ΣΦΑΛΜΑ ΠΟΥ ΕΦΤΑΣΕ ΣΤΟΝ ΧΡΗΣΤΗ: το run.js διάβαζε τους δύο χρόνους κάθε
    πυργίσκου, τους κρατούσε στο rooms[name].turretArg — και μετά έφτιαχνε το
    δωμάτιο με ΤΡΙΑ από τα τέσσερα ορίσματα. Το turretArg έμενε undefined, ο
    Room έπεφτε στο {}, και κάθε πυργίσκος έπαιζε με τις προεπιλογές: ο ρυθμός
    απλώς δεν υπήρχε μέσα στο παιχνίδι.

    Η σύγκριση με το μοντέλο ΔΕΝ μπορεί να το πιάσει, γιατί φτιάχνει μόνη της
    το δωμάτιο και παρακάμπτει ακριβώς αυτή τη γραμμή. Ο έλεγχος είναι λοιπόν
    στο κείμενο: κάθε παράμετρος του constructor πρέπει να αναφέρεται στην
    κλήση του start(). Προσθέτεις έκτο πεδίο στο Room; Κοκκινίζει ώσπου να το
    περάσεις κι εδώ.
    """
    with open(os.path.join(GAME, "physics.js"), encoding="utf-8") as f:
        physics = f.read()
    with open(os.path.join(GAME, "run.js"), encoding="utf-8") as f:
        run = f.read()

    m = re.search(r"class Room\b.*?constructor\s*\(([^)]*)\)", physics, re.S)
    if not m:
        return fail("δεν βρέθηκε ο constructor του Room στο physics.js")
    params = [p.strip() for p in m.group(1).split(",") if p.strip()]

    body = re.search(r"function start\s*\(.*?\n  \}", run, re.S)
    if not body:
        return fail("δεν βρέθηκε η start() στο run.js")
    call = re.search(r"new G\.Room\((.*?)\);", body.group(0), re.S)
    if not call:
        return fail("η start() δεν φτιάχνει δωμάτιο;")

    missing = [p for p in params[1:] if p not in call.group(1)]
    if missing:
        return fail(f"η start() του run.js δεν περνά: {', '.join(missing)}")

    # ΚΑΙ Η ΛΙΣΤΑ ΤΩΝ ΚΑΛΩΔΙΩΜΕΝΩΝ ΤΥΠΩΝ ΑΠΟ ΤΟ ΜΟΝΤΕΛΟ.
    #
    # Ήταν γραμμένη με το χέρι στο run.js και δύο τύποι είχαν πέσει έξω: η
    # ΑΝΟΙΓΜΕΝΗ πύλη και η ΞΕΚΛΕΙΔΩΤΗ κλειδαριά. Το κανάλι απλώνεται σε όλα τα
    # κελιά της ομάδας, οπότε πύλη τριών κελιών ζωγραφισμένη ήδη ανοιχτή είχε
    # κανάλι μόνο στο κελί που ονόμαζε η ουρά — ο διακόπτης έκλεινε το ένα
    # κομμάτι και άφηνε τα άλλα δύο ανοιχτά. Οι κλειστές πύλες δούλευαν, γιατί
    # ο τύπος GATE ήταν στη λίστα.
    if "D.WIRED" not in run:
        return fail("το run.js δεν απλώνει τα κανάλια από το D.WIRED του "
                    "μοντέλου — χειρόγραφη λίστα ξεχνάει τύπους")
    hand = re.findall(r"spreadKind\([^)]*TYPE_NAMES\.indexOf", run)
    return fail(f"{len(hand)} χειρόγραφες κλήσεις spreadKind στο run.js") \
        if hand else None


def main():
    ok = True

    def fail(msg):
        nonlocal ok
        print(f"  ΛΑΘΟΣ {msg}")
        ok = False

    check_room_wiring(fail)
    if ok:
        print("  ΟΚ   το run.js περνά ΟΛΑ τα πεδία του δωματίου στο Room")

    if not have_node():
        # ΔΥΝΑΤΑ, ΟΧΙ ΜΙΑ ΓΡΑΜΜΗ. Χωρίς node αυτό το αρχείο δεν ελέγχει
        # ΤΙΠΟΤΑ, και μια διακριτική «ΠΑΡΑΛΕΙΨΗ» ανάμεσα σε εκατοντάδες ΟΚ
        # διαβάζεται ως «όλα καλά». Ο πυργίσκος του browser μένει τότε εντελώς
        # ανεπιβεβαίωτος — δες τη λίστα παγίδων στο CLAUDE.md.
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΕ Ο ΠΥΡΓΙΣΚΟΣ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  !! Το editor/wwwroot/game/physics.js ΔΕΝ συγκρίθηκε με το "
              "μοντέλο.")
        print("  " + "!" * 66)
        return 0 if ok else 1
    tmp = os.path.join(ROOT, "build", "turretjs")
    os.makedirs(tmp, exist_ok=True)
    py, js = python_trace(), js_trace(tmp)

    fired = sum(1 for f in py if f[2])
    if not fired:
        print("  ΛΑΘΟΣ το σενάριο δεν έριξε ούτε ένα βέλος — δεν δοκιμάζει τίποτα")
        return 1

    for i, (a, b) in enumerate(zip(py, js)):
        if a != b:
            print(f"  ΛΑΘΟΣ απόκλιση στο καρέ {i}")
            print(f"        Python:     ρολόι {a[0]} ενέργεια {a[1]} βέλη {a[2]}")
            print(f"        JavaScript: ρολόι {b[0]} ενέργεια {b[1]} βέλη {b[2]}")
            return 1
    print(f"  ΟΚ   {FRAMES} καρέ ίδια σε Python και JavaScript "
          f"({fired} με βέλος στον αέρα)")
    if not ok:
        return 1
    print("ΟΛΑ ΣΩΣΤΑ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
