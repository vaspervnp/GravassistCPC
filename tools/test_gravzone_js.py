#!/usr/bin/env python3
"""Οι τέσσερις ζώνες βαρύτητας, στον browser όπως και στο μοντέλο.

Η ζώνη δεν παγώνει τη φορά που είχες: επιβάλλει τη ΔΙΚΗ της, και το πλακίδιο
τη δείχνει. Τέσσερις τύποι κελιού, ένας πίνακας (FACING) και ο ίδιος κανόνας
με τα αγκάθια — (FACING + 4) % 8.

Ο έλεγχος μπαίνει στη ζώνη με ΚΑΘΕ μία από τις οκτώ φορές: μια υλοποίηση που
απλώς κρατάει ό,τι βρήκε θα περνούσε αν δοκιμαζόταν μόνο η σωστή.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
from test_turret_js import GAME, ROOT, have_node, node_exe

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def room_text(ch):
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for r in range(10, 20):
        for c in range(10, 20):
            rows[r][c] = ch
    return ";\n" + "\n".join("".join(x) for x in rows) + "\ngravity 0"


JS = """
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
const G = window.GRAV, D = window.GAME_DATA;
const blob = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const out = {};
for (const key in blob.cells) {
  const room = new G.Room(blob.cells[key], {}, {}, {}, {});
  const seen = [];
  for (let g = 0; g < 8; g++) {
    const h = new G.Hero(room, 15 * D.CELL + 4, D.GRID_Y0 + 15 * D.CELL + 4, g);
    h.update(0, false);
    seen.push(h.g);
  }
  out[key] = seen;
}
console.log(JSON.stringify(out));
"""


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΑΝ ΟΙ ΖΩΝΕΣ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    zones = {":": P.GRAVLOCK, "8": P.GRAVLOCK_U,
             "4": P.GRAVLOCK_L, "6": P.GRAVLOCK_R}
    cells = {ch: [[P.CHARS[c] for c in row]
                  for row in room_text(ch).split("\n")[1:1 + P.ROWS]]
             for ch in zones}

    tmp = os.path.join(ROOT, "build", "zonejs")
    os.makedirs(tmp, exist_ok=True)
    blob = os.path.join(tmp, "zones.json")
    with open(blob, "w") as f:
        json.dump({"cells": cells}, f)
    js = os.path.join(tmp, "zones.js")
    with open(js, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"), blob],
                       capture_output=True, text=True)
    if r.returncode:
        print("  ΛΑΘΟΣ node: " + (r.stderr.strip() or "?"))
        return 1
    got = json.loads(r.stdout)

    for ch, t in zones.items():
        want = (P.FACING[t] + 4) % 8
        # Το μοντέλο πρώτα: αν αυτό αλλάξει, εδώ φαίνεται ότι άλλαξε ο κανόνας
        # και όχι ότι διαφωνεί ο browser.
        rm = P.Room(room_text(ch))
        model = []
        for g in range(8):
            h = P.Hero(rm, 15 * P.CELL + 4, P.GRID_Y0 + 15 * P.CELL + 4, g)
            h.update(0)
            model.append(h.g)
        check(f"ζώνη «{ch}»: το μοντέλο επιβάλλει {want} από κάθε φορά",
              set(model) == {want}, str(sorted(set(model))))
        check(f"ζώνη «{ch}»: η JavaScript λέει το ίδιο",
              got[ch] == model, f"{got[ch]} vs {model}")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
