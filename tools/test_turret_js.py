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
ROOM = [(10, 16, "I"), (4, 21, "=")]


def build_room():
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for c, r, ch in ROOM:
        rows[r][c] = ch
    return ";\n" + "\n".join("".join(x) for x in rows) + "\ngravity 0\n"


def python_trace():
    rm = P.Room(build_room())
    rm.number, rm.path = 1, ""
    h = P.Hero(rm, 10 * P.CELL + P.CELL // 2, P.GRID_Y0 + 18 * P.CELL)
    out = []
    for i in range(FRAMES):
        # Κινήσου λίγο, ώστε να αλλάζει και το κόστος του καρέ: εκεί κρύβεται
        # η διαφορά ανάμεσα σε «5 δευτερόλεπτα» και «τόσα περάσματα».
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
const room = new G.Room(JSON.parse(fs.readFileSync(process.argv[4], "utf8")));
// Η βαρύτητα ΡΗΤΑ: ο Hero της JavaScript δεν έχει προεπιλογή, ενώ το Python
// έχει g=0 — και χωρίς αυτήν το g βγαίνει undefined και σκάει στους πίνακες.
const h = new G.Hero(room, 10 * D.CELL + (D.CELL >> 1),
                     D.GRID_Y0 + 18 * D.CELL, 0);
const out = [];
for (let i = 0; i < __N__; i++) {
  const walk = ((i / 20) | 0) % 2 === 0 ? 1 : -1;
  h.update(walk, ((i / 40) | 0) % 2 === 0);
  out.push([h.clock, h.energy,
            h.arrows.map(a => [a.x, a.y, a.gone]).sort((p, q) =>
              p[0] - q[0] || p[1] - q[1] || p[2] - q[2])]);
}
console.log(JSON.stringify(out));
""".replace("__N__", str(FRAMES))


def js_trace(tmp):
    # Ο Room της JavaScript παίρνει ΠΛΕΓΜΑ, όχι κείμενο — το ίδιο κάνει και το
    # tools/parity.py. Το parsing είναι δουλειά του μοντέλου, μία φορά.
    rm = P.Room(build_room())
    room_path = os.path.join(tmp, "room.json")
    with open(room_path, "w") as f:
        json.dump(rm.cells, f)
    js_path = os.path.join(tmp, "run.js")
    with open(js_path, "w") as f:
        f.write(JS)
    r = subprocess.run(["node", js_path,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"), room_path],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("node: " + (r.stderr.strip() or "άγνωστο σφάλμα"))
    return json.loads(r.stdout)


def main():
    if shutil.which("node") is None:
        print("  ΠΑΡΑΛΕΙΨΗ ισοδυναμίας πυργίσκου: δεν βρέθηκε node")
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
