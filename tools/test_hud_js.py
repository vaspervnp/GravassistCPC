#!/usr/bin/env python3
"""Πού γράφει κείμενο ο browser — και πού ο Amstrad.

ΤΟ ΣΦΑΛΜΑ ΠΟΥ ΤΟ ΓΕΝΝΗΣΕ: το firmware μετράει χαρακτήρες ΑΠΟ ΤΟ 1 (H = στήλη,
L = γραμμή στο TXT_SET_CURSOR) και ο browser τα διάβαζε από το 0. Όλα έπεφταν
οκτώ pixel δεξιά, και το σκορ — που το src/score.asm το βάζει στη γραμμή 1,
δηλαδή στο HUD — έμπαινε μέσα στο πλέγμα.

Η θέση δεν ελέγχεται με το μάτι: διαβάζεται από το src/score.asm και
συγκρίνεται με το τι ζωγραφίζει ο browser σε ψεύτικο canvas.
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_turret_js import GAME, ROOT, have_node, node_exe

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def amstrad_score_pos():
    """Στήλη και γραμμή κειμένου του σκορ, ΑΠΟ ΤΟ src/score.asm."""
    src = open(os.path.join(ROOT, "src", "score.asm")).read()
    col = re.search(r"^SCORE_COL\s+equ\s+(\d+)", src, re.M)
    row = re.search(r"ld\s+h,SCORE_COL\s*\n\s*ld\s+l,(\d+)", src)
    if not col or not row:
        raise SystemExit("το SCORE_COL ή η γραμμή του δεν βρέθηκαν στο score.asm")
    return int(col.group(1)), int(row.group(1))


# Ψεύτικο canvas που ΚΑΤΑΓΡΑΦΕΙ αντί να ζωγραφίζει: το ερώτημα δεν είναι «πώς
# φαίνεται» αλλά «σε ποιο pixel γράφτηκε».
JS = """
const fs = require("fs");
const calls = [];
const ctx = { imageSmoothingEnabled: false, font: "", textBaseline: "",
              fillStyle: "",
              createImageData: (w, h) => ({ data: new Uint8ClampedArray(w*h*4) }),
              putImageData(){}, drawImage(){}, save(){}, restore(){}, scale(){},
              clearRect(){},
              fillRect(x, y, w, h) { calls.push(["rect", x, y, w, h]); },
              fillText(s, x, y) { calls.push(["text", s, x, y]); } };
const canvas = { width: 0, height: 0, getContext: () => ctx };
global.document = { createElement: () => canvas, getElementById: () => null };
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
eval(fs.readFileSync(process.argv[4], "utf8"));
const D = window.GAME_DATA;
const s = new window.GRAV_RENDER.Screen(canvas, 1);
const out = {};
s.text("-123456", Number(process.argv[5]), Number(process.argv[6]));
out.score = calls.slice();
calls.length = 0;
s.text("hint", D.K.MSG_ROW_LO + 2, 10);
out.hint = calls.slice();
console.log(JSON.stringify(out));
"""


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΕ Η ΘΕΣΗ ΤΟΥ ΣΚΟΡ: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    col, row = amstrad_score_pos()
    print(f"--- ο Amstrad γράφει το σκορ στη στήλη {col}, γραμμή {row}")

    tmp = os.path.join(ROOT, "build", "hudjs")
    os.makedirs(tmp, exist_ok=True)
    js = os.path.join(tmp, "hud.js")
    with open(js, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"),
                        os.path.join(GAME, "render.js"),
                        str(row), str(col)],
                       capture_output=True, text=True)
    if r.returncode:
        print("  ΛΑΘΟΣ η σχεδίαση έσκασε: " + (r.stderr.strip() or "?"))
        return 1
    got = json.loads(r.stdout)

    # Το firmware: στήλη H και γραμμή L μετρημένες ΑΠΟ ΤΟ 1.
    want_x, want_y = (col - 1) * 8, (row - 1) * 8
    text = [c for c in got["score"] if c[0] == "text"]
    rect = [c for c in got["score"] if c[0] == "rect"]
    check("το σκορ ξεκινά στη σωστή στήλη",
          bool(text) and text[0][2] == want_x,
          f"x={text[0][2] if text else '-'} αντί για {want_x}")
    check("…και στη γραμμή του HUD, όχι μέσα στο πλέγμα",
          bool(rect) and rect[0][2] == want_y,
          f"y={rect[0][2] if rect else '-'} αντί για {want_y}")
    check("το φόντο του καλύπτει ακριβώς το κελί του χαρακτήρα",
          bool(rect) and rect[0][4] == 8 and rect[0][1] == want_x,
          str(rect[0] if rect else None))

    # Το μήνυμα: γραμμή πλέγματος r -> γραμμή κειμένου r + 2, δηλαδή pixel
    # GRID_Y0 + r*8. Η ίδια μετατροπή με το add a,2 του hint_draw.
    grid_row = 16
    hint_rect = [c for c in got["hint"] if c[0] == "rect"]
    check("το μήνυμα κάθεται στη γραμμή του πλέγματος που ζητήθηκε",
          bool(hint_rect) and hint_rect[0][2] == 8 + grid_row * 8,
          f"y={hint_rect[0][2] if hint_rect else '-'} αντί για {8 + grid_row * 8}")

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
