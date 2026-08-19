#!/usr/bin/env python3
"""Η κινούμενη πλατφόρμα σε Python και σε JavaScript, καρέ προς καρέ.

ΓΙΑΤΙ ΞΕΧΩΡΙΣΤΟ ΑΡΧΕΙΟ, όπως και του πυργίσκου: το tools/parity.py τρέχει πάνω
στο levels/regress.txt, που είναι σταθερό και δεν αποκτά καινούργια αντικείμενα.
Χωρίς αυτό εδώ, ο κώδικας των πλατφορμών στη JavaScript δεν συγκρίνεται ποτέ με
το μοντέλο — θα μπορούσε να μην τρέχει καθόλου και όλα να είναι πράσινα.

ΤΙ ΣΥΓΚΡΙΝΕΤΑΙ: θέση και φορά της πλατφόρμας, και θέση του ήρωα που την πατάει.
Η μεταφορά είναι το μισό χαρακτηριστικό — πλατφόρμα που φεύγει από κάτω σου δεν
είναι πλατφόρμα, είναι παγίδα.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
from test_turret_js import GAME, ROOT, have_node, node_exe

FRAMES = 160
SWITCH_OFF, SWITCH_ON = 60, 100
CHANNEL = 1
RIDER_CHAN = 2
SPEED = 40


def build_rows():
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for i in range(3):                  # πλατφόρμα ΤΡΙΩΝ κελιών
        rows[14][10 + i] = "M"
    rows[13][11] = "S"                  # ΕΠΙΒΑΤΗΣ: διακόπτης πάνω της
    rows[18][25] = "G"                  # η πύλη που ανοίγει ο επιβάτης
    rows[22][30] = "S"                  # και ο δικός της διακόπτης, μακριά
    return rows


def room_text():
    return (";\n" + "\n".join("".join(r) for r in build_rows())
            + f"\ngravity 0\nplat 10 14 20 14 {CHANNEL} {SPEED}\n"
            + f"sw 30 22 {CHANNEL}\n"
            + f"sw 11 13 {RIDER_CHAN}\ngate 25 18 {RIDER_CHAN}\n")


def python_trace():
    rm = P.Room(room_text())
    rm.number, rm.path = 1, ""
    pl = rm.platforms[0]
    pl["moving"] = False                # άσε τον ήρωα να προσγειωθεί πρώτα
    h = P.Hero(rm, 10 * P.CELL + 2, P.GRID_Y0 + 12 * P.CELL)
    for _ in range(40):
        h.update(0)
    pl["moving"] = True
    out = []
    for i in range(FRAMES):
        if i == SWITCH_OFF:
            h.set_targets(CHANNEL, True)        # «ανοιχτό» = ακίνητη
        elif i == SWITCH_ON:
            h.set_targets(CHANNEL, False)
        # ΠΕΡΠΑΤΑΕΙ στην αρχή: έτσι ΔΙΑΣΧΙΖΕΙ τον επιβάτη μέσα στην καταγραφή
        # και το πάτημα μπαίνει στη σύγκριση. Ακίνητος, ο διακόπτης θα είχε
        # πατηθεί στην προσγείωση — δηλαδή πριν αρχίσει να μετράει.
        h.update(1 if i < 20 else 0)
        out.append([pl["x"], pl["y"], pl["dir"], h.x, h.y,
                    pl["rider"], rm.cells[18][25]])
    return out


JS = """
const fs = require("fs");
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
const G = window.GRAV, D = window.GAME_DATA;
const blob = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const room = new G.Room(blob.cells, {}, blob.attrs, {}, blob.platSpec);
const pl = room.platforms[0];
pl.moving = false;
const h = new G.Hero(room, 10 * D.CELL + 2, D.GRID_Y0 + 12 * D.CELL, 0);
for (let i = 0; i < 40; i++) h.update(0, false);
pl.moving = true;
const out = [];
for (let i = 0; i < __N__; i++) {
  if (i === blob.off) h.setTargets(blob.chan, true);
  else if (i === blob.on) h.setTargets(blob.chan, false);
  h.update(i < 20 ? 1 : 0, false);
  out.push([pl.x, pl.y, pl.dir, h.x, h.y, pl.rider, room.cells[18][25]]);
}
console.log(JSON.stringify(out));
""".replace("__N__", str(FRAMES))


def js_trace(tmp):
    # ΤΟ ΑΚΑΤΕΡΓΑΣΤΟ ΠΛΕΓΜΑ, όχι του Room: εκείνο σβήνει τα κελιά της
    # πλατφόρμας στη φόρτωση, και το run.js δίνει στον Room ό,τι διάβασε από το
    # αρχείο. Με το καθαρισμένο πλέγμα η JavaScript δεν θα έβρισκε πλατφόρμα
    # καθόλου και η σύγκριση θα έσκαγε αντί να συγκρίνει.
    cells = [[P.CHARS[ch] for ch in row] for row in build_rows()]
    # ΟΛΕΣ οι ιδιότητες, απλωμένες όπως τις παράγει το run.js. Με μόνο το ένα
    # κανάλι, ο επιβάτης δεν είχε πύλη να ανοίξει και η σύγκριση κοκκίνιζε για
    # λάθος λόγο — έλεγε «διαφωνούν» ενώ έλειπαν τα δεδομένα.
    rm = P.Room(room_text())
    path = os.path.join(tmp, "room.json")
    with open(path, "w") as f:
        json.dump({"cells": cells,
                   "attrs": {f"{c},{r}": v for (c, r), v in rm.attrs.items()},
                   "platSpec": {"10,14": [20, 14, CHANNEL, SPEED]},
                   "chan": CHANNEL, "off": SWITCH_OFF, "on": SWITCH_ON}, f)
    js = os.path.join(tmp, "run.js")
    with open(js, "w") as f:
        f.write(JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"), path],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("node: " + (r.stderr.strip() or "άγνωστο σφάλμα"))
    return json.loads(r.stdout)


# Η ΣΧΕΔΙΑΣΗ, ΞΕΧΩΡΙΣΤΑ ΑΠΟ ΤΗ ΦΥΣΙΚΗ.
#
# ΓΙΑΤΙ ΧΡΕΙΑΖΕΤΑΙ: η σύγκριση καρέ-προς-καρέ ελέγχει ΘΕΣΕΙΣ, όχι pixel. Ο
# επιβάτης-διακόπτης δούλευε τέλεια και ήταν ΑΟΡΑΤΟΣ, επειδή ένα script που
# πρόσθετε πάτημα και σχεδίαση μαζί σταμάτησε στη μέση: το πάτημα μπήκε, η
# σχεδίαση όχι, και κανένα τεστ δεν κοιτούσε την οθόνη.
DRAW_JS = """
const fs = require("fs");
const ctx = { imageSmoothingEnabled: false,
              createImageData: (w, h) => ({ data: new Uint8ClampedArray(w*h*4) }),
              putImageData(){}, drawImage(){}, save(){}, restore(){},
              scale(){}, fillRect(){}, clearRect(){} };
const canvas = { width: 0, height: 0, getContext: () => ctx };
global.document = { createElement: () => canvas, getElementById: () => null };
global.window = {};
eval(fs.readFileSync(process.argv[2], "utf8"));
eval(fs.readFileSync(process.argv[3], "utf8"));
eval(fs.readFileSync(process.argv[4], "utf8"));
const D = window.GAME_DATA;
const s = new window.GRAV_RENDER.Screen(canvas, 1);
function box(y0, y1) {
  let n = 0, x0 = 999, x1 = -1;
  for (let y = y0; y <= y1; y++) for (let x = 0; x < 320; x++)
    if (s.buf[y*320+x]) { n++; x0 = Math.min(x0, x); x1 = Math.max(x1, x); }
  return [n, x0, x1];
}
// ΜΗ στοιχισμένη στο πλέγμα θέση: εκεί κρίνεται η λεία κίνηση.
const p = { x: 85, y: 121, w: 24, h: 8, moving: true,
            rider: D.TYPE_NAMES.indexOf("SWITCH_U"), rdx: 8 };
s.clear(); s.platform(p);
const withRider = [box(121, 128), box(113, 120)];
p.rider = null;
s.clear(); s.platform(p);
console.log(JSON.stringify({ withRider, without: box(113, 120) }));
"""


def draw_check(tmp, fail):
    """Η πλατφόρμα και ο επιβάτης της στα σωστά pixel."""
    js = os.path.join(tmp, "draw.js")
    with open(js, "w") as f:
        f.write(DRAW_JS)
    r = subprocess.run([node_exe(), js,
                        os.path.join(GAME, "data.js"),
                        os.path.join(GAME, "physics.js"),
                        os.path.join(GAME, "render.js")],
                       capture_output=True, text=True)
    if r.returncode:
        return fail("η σχεδίαση έσκασε: " + (r.stderr.strip() or "?"))
    got = json.loads(r.stdout)
    (pn, px0, px1), (rn, rx0, rx1) = got["withRider"]
    if not pn or (px0, px1) != (85, 108):
        return fail(f"η πλατφόρμα ζωγραφίστηκε στο x {px0}..{px1}, περίμενα 85..108")
    if not rn or not (93 <= rx0 and rx1 <= 100):
        return fail(f"ο επιβάτης ζωγραφίστηκε στο x {rx0}..{rx1}, "
                    f"περίμενα μέσα στο 93..100")
    if got["without"][0]:
        return fail("χωρίς επιβάτη ζωγραφίζεται κάτι πάνω από την πλατφόρμα")
    print(f"  ΟΚ   η πλατφόρμα και ο επιβάτης της ζωγραφίζονται σε θέση pixel "
          f"({pn} + {rn} pixel)")
    return None


def main():
    if not have_node():
        print("  " + "!" * 66)
        print("  !! ΔΕΝ ΕΛΕΓΧΘΗΚΕ Η ΠΛΑΤΦΟΡΜΑ ΤΟΥ BROWSER: δεν βρέθηκε node.")
        print("  " + "!" * 66)
        return 0

    tmp = os.path.join(ROOT, "build", "platjs")
    os.makedirs(tmp, exist_ok=True)

    bad = []
    draw_check(tmp, lambda m: (print(f"  ΛΑΘΟΣ {m}"), bad.append(m)))
    if bad:
        return 1

    py, js = python_trace(), js_trace(tmp)

    moved = len({tuple(f[:2]) for f in py})
    if moved < 5:
        print(f"  ΛΑΘΟΣ η πλατφόρμα δεν κουνήθηκε ({moved} θέσεις) — "
              "το σενάριο δεν δοκιμάζει τίποτα")
        return 1
    # Η ΜΕΤΑΦΟΡΑ ΔΟΚΙΜΑΖΕΤΑΙ ΟΝΤΩΣ; Η συνολική μετατόπιση δεν το λέει: με την
    # παύση στα άκρα και τον διακόπτη η πλατφόρμα μπορεί να καταλήξει σχεδόν
    # εκεί που ξεκίνησε, και ένας έλεγχος «κουνήθηκε ο ήρωας» θα περνούσε με
    # δύο pixel. Μετράμε πόσα καρέ κινήθηκαν ΜΑΖΙ, βήμα προς βήμα.
    together = sum(1 for a, b in zip(py, py[1:])
                   if b[0] - a[0] and b[3] - a[3] == b[0] - a[0])
    if together < 10:
        print(f"  ΛΑΘΟΣ ο ήρωας κινήθηκε μαζί της μόνο σε {together} καρέ — "
              "η μεταφορά δεν δοκιμάζεται")
        return 1

    # Ο ΕΠΙΒΑΤΗΣ ΔΟΚΙΜΑΖΕΤΑΙ ΟΝΤΩΣ; Αν δεν πατηθεί ποτέ, ο κώδικάς του θα
    # μπορούσε να μην τρέχει καθόλου και η σύγκριση να μένει πράσινη.
    if len({f[5] for f in py}) < 2 or len({f[6] for f in py}) < 2:
        print("  ΛΑΘΟΣ ο επιβάτης-διακόπτης δεν πατήθηκε ποτέ")
        return 1

    for i, (a, b) in enumerate(zip(py, js)):
        if a != b:
            print(f"  ΛΑΘΟΣ απόκλιση στο καρέ {i}")
            print(f"        Python:     πλατφόρμα {a[:3]} ήρωας {a[3:5]} "
                  f"επιβάτης {a[5]} πύλη {a[6]}")
            print(f"        JavaScript: πλατφόρμα {b[:3]} ήρωας {b[3:5]} "
                  f"επιβάτης {b[5]} πύλη {b[6]}")
            return 1

    print(f"  ΟΚ   {FRAMES} καρέ ίδια σε Python και JavaScript "
          f"({moved} θέσεις, {together} καρέ με τον ήρωα πάνω της)")
    print("ΟΛΑ ΣΩΣΤΑ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
