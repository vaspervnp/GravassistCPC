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
FOOTER = "turret 10 16 0 2 0\nturret 4 21 0 5 0\nturret 30 6 0 5 1\n"

# Ο ΔΙΑΚΟΠΤΗΣ ΜΕΣΑ ΣΤΗ ΣΥΓΚΡΙΣΗ. Ο ρυθμικός του (30,6) σβήνει στο καρέ 40 και
# ξανανάβει στο 80: ο πυργίσκος με ρυθμό δεν ρωτάει ούτε εμβέλεια ούτε οπτική
# επαφή, οπότε ο διακόπτης είναι το ΜΟΝΟ πράγμα που τον σταματά — και ήταν
# ακριβώς το μόνο που δεν συγκρινόταν ποτέ με το μοντέλο.
#
# Γράφεται ο τύπος του κελιού κατευθείαν, όπως κάνει ο διακόπτης και στις δύο
# υλοποιήσεις· η καλωδίωση δοκιμάζεται αλλού.
SWITCH_CELL = (30, 6)
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
        sc, sr = SWITCH_CELL
        if i == SWITCH_OFF:
            rm.cells[sr][sc] = P.TURRET_V_OFF
        elif i == SWITCH_ON:
            rm.cells[sr][sc] = P.TURRET_V
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
const room = new G.Room(blob.cells, {}, {}, blob.turretArg);
// Η βαρύτητα ΡΗΤΑ: ο Hero της JavaScript δεν έχει προεπιλογή, ενώ το Python
// έχει g=0 — και χωρίς αυτήν το g βγαίνει undefined και σκάει στους πίνακες.
const h = new G.Hero(room, 10 * D.CELL + (D.CELL >> 1),
                     D.GRID_Y0 + 18 * D.CELL, 0);
const out = [];
const [SC, SR] = blob.switchCell;
for (let i = 0; i < __N__; i++) {
  if (i === blob.switchOff) room.cells[SR][SC] = D.TYPE_NAMES.indexOf("TURRET_V_OFF");
  else if (i === blob.switchOn) room.cells[SR][SC] = D.TYPE_NAMES.indexOf("TURRET_V");
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
                   "switchCell": list(SWITCH_CELL),
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


def main():
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
        return 0
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
    print("ΟΛΑ ΣΩΣΤΑ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
