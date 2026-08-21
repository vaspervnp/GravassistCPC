#!/usr/bin/env python3
"""Το κλειδί, η πύλη που ΚΟΙΤΑΣ, και το μήνυμα που το υπόσχεται.

ΤΟ ΣΦΑΛΜΑ ΠΟΥ ΤΟ ΓΕΝΝΗΣΕ: το hintFor έλεγε «Up or down to open with key» για
την πύλη μπροστά σου — η πύλη είναι στερεή, στέκεσαι μπροστά της, δεν την
πατάς — ενώ το use() ξεκλείδωνε μόνο το κελί που ΠΑΤΑΣ. Πάταγες και δεν
γινόταν τίποτα.

Ο έλεγχος δεν ρωτά χωριστά «τι λέει;» και «τι κάνει;» αλλά αν συμφωνούν: όποτε
η οθόνη υπόσχεται άνοιγμα με κλειδί, το πάτημα πρέπει να ανοίγει.
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


# Το hintFor ζει στο run.js, που θέλει DOM. Το φορτώνουμε με ψεύτικο έγγραφο
# και καλούμε ΜΟΝΟ τη συνάρτηση — η ίδια που τρέχει στο test run.
JS = """
const fs = require("fs");
const ctx = { imageSmoothingEnabled: false,
              createImageData: (w, h) => ({ data: new Uint8ClampedArray(w*h*4) }),
              putImageData(){}, drawImage(){}, save(){}, restore(){}, scale(){},
              fillRect(){}, clearRect(){}, fillText(){} };
const canvas = { width: 0, height: 0, getContext: () => ctx,
                 addEventListener(){}, getBoundingClientRect: () => ({}) };
// ΕΝΑ stub ΓΙΑ ΟΛΑ, καμβάς μαζί: το run.js ζητά το «screen» με getElementById
// και του κάνει getContext.
const stub = { addEventListener(){}, appendChild(){}, remove(){},
               style: {}, classList: { add(){}, remove(){} },
               textContent: "", value: "", options: [], focus(){},
               width: 0, height: 0, getContext: () => ctx,
               getBoundingClientRect: () => ({ width: 0, height: 0 }) };
global.document = { createElement: () => canvas, getElementById: () => stub,
                    addEventListener(){}, body: stub };
global.window = { addEventListener(){}, location: { search: "" },
                  requestAnimationFrame: () => 0, GRAV_TEST: {} };
global.location = { search: "" };   // το load() του run.js τη διαβάζει
global.requestAnimationFrame = () => 0;
global.addEventListener = () => {};
global.setInterval = () => 0;
global.AudioContext = function () {
  return { createOscillator: () => ({ connect(){}, start(){}, stop(){},
                                      frequency: { setValueAtTime(){} },
                                      type: "" }),
           createGain: () => ({ connect(){}, gain: { setValueAtTime(){},
                                exponentialRampToValueAtTime(){} } }),
           destination: {}, currentTime: 0, resume() {} };
};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ files: [] }) });
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
eval(fs.readFileSync(process.argv[4], "utf8"));
eval(fs.readFileSync(process.argv[5], "utf8"));

const D = window.GAME_DATA, G = window.GRAV;
const hintFor = window.GRAV_TEST.hintFor;
const spec = JSON.parse(fs.readFileSync(process.argv[6], "utf8"));
const out = [];
for (const keys of [1, 0]) {
  const room = new G.Room(spec.cells.map(r => r.slice()), {}, spec.attrs, {}, {});
  const h = new G.Hero(room, 12 * 8 + 4, D.GRID_Y0 + 21 * 8 + 4, 0);
  h.keys[1] = keys;
  for (let i = 0; i < 20; i++) h.update(0, false);
  for (let i = 0; i < 40; i++) {
    if (room.cell(...h.aheadCell()) === D.TYPE_NAMES.indexOf("GATE")) break;
    h.update(1, false);
  }
  const hint = hintFor ? hintFor(h) : "(χωρίς hintFor)";
  const opened = h.use();
  out.push({ keys, hint, opened,
             gate: D.TYPE_NAMES[room.cell(15, 22)], left: h.keys[1] });
}
console.log(JSON.stringify(out));
"""

KEY_HINT = "Up or down to open with key"


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΕ Η ΠΥΛΗ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for r in range(18, 23):
        rows[r][15] = "G"
    cells = [[P.CHARS[ch] for ch in row] for row in rows]
    attrs = {f"15,{r}": 1 for r in range(18, 23)}

    tmp = os.path.join(ROOT, "build", "keysjs")
    os.makedirs(tmp, exist_ok=True)
    blob = os.path.join(tmp, "room.json")
    with open(blob, "w") as f:
        json.dump({"cells": cells, "attrs": attrs}, f)
    js = os.path.join(tmp, "keys.js")
    with open(js, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"),
                        os.path.join(GAME, "render.js"),
                        os.path.join(GAME, "run.js"), blob],
                       capture_output=True, text=True)
    if r.returncode:
        print("  ΛΑΘΟΣ node: " + (r.stderr.strip().splitlines()[-1] if r.stderr else "?"))
        return 1
    got = {c["keys"]: c for c in json.loads(r.stdout)}

    with_key, without = got[1], got[0]
    check("με κλειδί, η οθόνη υπόσχεται άνοιγμα",
          with_key["hint"] == KEY_HINT, with_key["hint"])
    check("…και το πάτημα το κάνει",
          with_key["opened"] and with_key["gate"] == "GATE_OPEN",
          f"{with_key['opened']} / {with_key['gate']}")
    check("…ξοδεύοντας το κλειδί", with_key["left"] == 0, str(with_key["left"]))
    check("χωρίς κλειδί, δεν το υπόσχεται",
          without["hint"] != KEY_HINT, without["hint"])
    check("…ούτε το κάνει",
          not without["opened"] and without["gate"] == "GATE",
          f"{without['opened']} / {without['gate']}")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
