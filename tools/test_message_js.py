#!/usr/bin/env python3
"""Το μήνυμα εισόδου της αίθουσας: ο browser το διαβάζει όπως το μοντέλο.

Η ουρά της πίστας είναι κείμενο που γράφει ο σχεδιαστής, και τη διαβάζουν
ΤΡΕΙΣ υλοποιήσεις. Το μήνυμα είναι ελεύθερο κείμενο — κενά, σημεία στίξης,
τυχόν «msg» μέσα στο ίδιο το μήνυμα — οπότε η ερμηνεία του είναι ακριβώς εκεί
που δύο parser αποκλίνουν σιωπηλά.

Καλείται η ΙΔΙΑ συνάρτηση που τρέχει στο test run, όχι αντίγραφό της.
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


CASES = [
    "msg MIND THE SPIKES",
    "msg TWO  SPACES",
    "gravity 0",
    "msg " + "X" * 60,
    "msg   leading and trailing   ",
    "gravity 0\nmsg SECOND LINE\ntp 1 2 3 4",
    "msg msg IS A WORD TOO",
]

JS = """
const fs = require("fs");
const ctx = { imageSmoothingEnabled: false,
              createImageData: (w, h) => ({ data: new Uint8ClampedArray(w*h*4) }),
              putImageData(){}, drawImage(){}, save(){}, restore(){}, scale(){},
              fillRect(){}, clearRect(){}, fillText(){} };
const stub = { addEventListener(){}, appendChild(){}, remove(){}, style: {},
               classList: { add(){}, remove(){} }, textContent: "", value: "",
               options: [], focus(){}, width: 0, height: 0,
               getContext: () => ctx,
               getBoundingClientRect: () => ({ width: 0, height: 0 }) };
global.document = { createElement: () => stub, getElementById: () => stub,
                    addEventListener(){}, body: stub };
global.window = { addEventListener(){}, location: { search: "" },
                  requestAnimationFrame: () => 0, GRAV_TEST: {} };
global.location = { search: "" };
global.requestAnimationFrame = () => 0;
global.addEventListener = () => {};
global.setInterval = () => 0;
global.AudioContext = function () {
  return { createOscillator: () => ({ connect(){}, start(){}, stop(){},
                                      frequency: { setValueAtTime(){} }, type: "" }),
           createGain: () => ({ connect(){}, gain: { setValueAtTime(){},
                                exponentialRampToValueAtTime(){} } }),
           destination: {}, currentTime: 0, resume() {} };
};
global.fetch = () => Promise.resolve({ json: () => Promise.resolve({ files: [] }) });
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
eval(fs.readFileSync(process.argv[4], "utf8"));
eval(fs.readFileSync(process.argv[5], "utf8"));
const cases = JSON.parse(fs.readFileSync(process.argv[6], "utf8"));
console.log(JSON.stringify(cases.map(window.GRAV_TEST.parseMessage)));
"""


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΕ ΤΟ ΜΗΝΥΜΑ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    grid = ";\n" + "\n".join("".join(r) for r in rows) + "\n"
    want = [P.Room(grid + c).message for c in CASES]

    tmp = os.path.join(ROOT, "build", "msgjs")
    os.makedirs(tmp, exist_ok=True)
    blob = os.path.join(tmp, "cases.json")
    with open(blob, "w") as f:
        json.dump(CASES, f)
    js = os.path.join(tmp, "msg.js")
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
    got = json.loads(r.stdout)

    # ΤΟ ΣΕΝΑΡΙΟ ΔΟΚΙΜΑΖΕΙ ΟΝΤΩΣ ΚΑΤΙ; Χωρίς μήνυμα σε τουλάχιστον μία
    # περίπτωση και με μήνυμα σε άλλη, η σύγκριση θα ήταν «κενό ίσον κενό».
    check("το σενάριο έχει και μηνύματα και σιωπή",
          any(want) and not all(want), str(want))
    for c, w, g in zip(CASES, want, got):
        check(f"«{c.splitlines()[0][:28]}…»" if len(c) > 28 else f"«{c}»",
              g == w, f"JS «{g}» vs μοντέλο «{w}»")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
