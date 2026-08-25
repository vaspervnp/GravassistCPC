#!/usr/bin/env python3
"""Κανάλια «όλοι μαζί», στον browser όπως και στο μοντέλο.

Δύο διακόπτες ή δύο πλάκες στο ίδιο κανάλι, δηλωμένο με «all N»: η πύλη
ανοίγει μόνο όταν είναι ΚΑΙ ΟΙ ΔΥΟ ενεργοί. Χωρίς τη δήλωση ισχύει ο παλιός
κανόνας — ο ένας αρκεί.

Ο έλεγχος τρέχει το ΙΔΙΟ σενάριο σε Python και JavaScript και συγκρίνει την
πύλη ΚΑΡΕ ΠΡΟΣ ΚΑΡΕ: το επίμαχο δεν είναι «ανοίγει;» αλλά πότε ανοίγει.
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


def room_text(a, b, declare):
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    rows[22][10] = a
    rows[22][14] = b
    for r in range(18, 23):
        rows[r][25] = "G"
    kind = {"S": "sw", "p": "plate"}
    foot = ["gravity 0"] + (["all 3"] if declare else []) \
        + [f"{kind[a]} 10 22 3", f"{kind[b]} 14 22 3"] \
        + [f"gate 25 {r} 3" for r in range(18, 23)]
    return ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(foot)


JS = """
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
const G = window.GRAV, D = window.GAME_DATA;
const blob = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const out = {};
for (const key in blob.rooms) {
  const spec = blob.rooms[key];
  const room = new G.Room(spec.cells.map(r => r.slice()), {}, spec.attrs,
                          {}, {}, spec.allChan);
  const h = new G.Hero(room, 10 * D.CELL + 4, D.GRID_Y0 + 21 * D.CELL + 4, 0);
  const seen = [];
  for (let i = 0; i < 120; i++) {
    h.update(i < 30 ? 0 : 1, false);
    seen.push(room.cell(25, 22));
  }
  out[key] = seen;
}
console.log(JSON.stringify(out));
"""


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΑΝ ΤΑ ΚΑΝΑΛΙΑ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    cases = {"and": (True,), "plain": (False,)}
    rooms, want = {}, {}
    for key, (declare,) in cases.items():
        txt = room_text("S", "S", declare)
        rm = P.Room(txt)
        rooms[key] = {
            "cells": [[P.CHARS[ch] for ch in row]
                      for row in txt.split("\n")[1:1 + P.ROWS]],
            "attrs": {f"{c},{r}": v for (c, r), v in rm.attrs.items()},
            "allChan": rm.all_chan,
        }
        h = P.Hero(rm, 10 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)
        seen = []
        for i in range(120):
            h.update(0 if i < 30 else 1)
            seen.append(rm.cell(25, 22))
        want[key] = seen

    tmp = os.path.join(ROOT, "build", "andjs")
    os.makedirs(tmp, exist_ok=True)
    blob = os.path.join(tmp, "rooms.json")
    with open(blob, "w") as f:
        json.dump({"rooms": rooms}, f)
    js = os.path.join(tmp, "and.js")
    with open(js, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"), blob],
                       capture_output=True, text=True)
    if r.returncode:
        print("  ΛΑΘΟΣ node: " + (r.stderr.strip().splitlines()[-1] if r.stderr else "?"))
        return 1
    got = json.loads(r.stdout)

    # ΤΟ ΣΕΝΑΡΙΟ ΔΟΚΙΜΑΖΕΙ ΟΝΤΩΣ ΚΑΤΙ; Με δήλωση η πύλη πρέπει να μείνει
    # κλειστή στην αρχή και να ανοίξει αργότερα· χωρίς, να ανοίξει νωρίς.
    # ΤΟ ΚΑΡΕ 29 ΕΙΝΑΙ Η ΚΡΙΣΗ: ως εκεί ο ήρωας στέκεται πάνω στον ΠΡΩΤΟ
    # διακόπτη και δεν έχει κουνηθεί. Με δήλωση η πύλη πρέπει να είναι ακόμα
    # κλειστή, χωρίς δήλωση ήδη ανοιχτή — και αργότερα, με τον δεύτερο, να
    # ανοίγει και στις δύο περιπτώσεις.
    check("με «all», ο πρώτος διακόπτης ΔΕΝ αρκεί",
          want["and"][29] == P.GATE, P.TYPE_NAMES[want["and"][29]])
    check("…και ο δεύτερος την ανοίγει",
          P.GATE_OPEN in want["and"][30:],
          str(sorted({P.TYPE_NAMES[v] for v in want["and"]})))
    check("χωρίς «all», ο πρώτος αρκεί",
          want["plain"][29] == P.GATE_OPEN, P.TYPE_NAMES[want["plain"][29]])

    for key in cases:
        check(f"σενάριο «{key}»: η JavaScript συμφωνεί καρέ προς καρέ",
              got[key] == want[key],
              f"πρώτη διαφορά στο {next((i for i, (a, b) in enumerate(zip(got[key], want[key])) if a != b), None)}")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
