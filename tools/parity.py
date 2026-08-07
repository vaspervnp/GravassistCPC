#!/usr/bin/env python3
"""Σενάριο ισοδυναμίας: το μοντέλο έναντι της JavaScript του editor.

    python3 tools/parity.py

Γράφει editor/wwwroot/game/parity-expected.json με το σενάριο και την τροχιά
που παράγει το tools/physics.py. Η σελίδα /game/parity.html τρέχει το ΙΔΙΟ
σενάριο στη JavaScript και συγκρίνει frame προς frame.

ΓΙΑΤΙ: η φυσική υπάρχει σε τρεις υλοποιήσεις. Οι πίνακες παράγονται από μία
πηγή, οπότε δεν μπορούν να αποκλίνουν αριθμητικά — αλλά η ΡΟΗ ΕΛΕΓΧΟΥ γράφεται
με το χέρι σε καθεμία, και εκεί κρύβονται τα λάθη: μια σειρά ανάποδα, ένας
πρόωρος τερματισμός, ένα πρόσημο. Αυτό το σενάριο τα πιάνει.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "editor", "wwwroot", "game", "parity-expected.json")

# (frame, ενέργεια) — τι κάνει ο "παίκτης". Διαλεγμένο ώστε να περάσει από
# πτώση, βάδισμα, ράμπα, γωνίες, αλλαγή βαρύτητας και γλίστρημα.
SCRIPT = [
    (0,   {"walk": 0}),
    (40,  {"walk": 1}),          # περπάτα δεξιά: πάτωμα -> ράμπα -> πλάτωμα
    (260, {"walk": 0, "grav": 6}),   # ρίξε τη βαρύτητα δεξιά
    (300, {"walk": 1}),
    (420, {"walk": 0, "grav": 4}),   # ανάποδα
    (460, {"walk": -1}),
    (560, {"walk": 0, "grav": 3}),   # διαγώνια -> γλίστρημα
    (620, {"walk": 1}),
]
FRAMES = 800


def run():
    room = P.load_room(os.path.join(P.LEVELS, "regress.txt"))
    h = P.Hero(room, room.start_x, room.start_y, room.start_g)
    script = dict(SCRIPT)
    walk, trace = 0, []
    for f in range(FRAMES):
        act = script.get(f)
        if act:
            if "grav" in act:
                h.set_gravity(act["grav"])
            walk = act.get("walk", walk)
        h.update(walk)
        trace.append([h.x, h.y, h.g, h.state, h.energy, h.fall_dist])
    return room, trace


if __name__ == "__main__":
    room, trace = run()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({
            "room": room.cells,
            "start": [room.start_x, room.start_y, room.start_g],
            "script": SCRIPT,
            "frames": FRAMES,
            "trace": trace,
        }, f, separators=(",", ":"))
    print(f"  {os.path.relpath(OUT, ROOT)}: {FRAMES} frames, "
          f"{os.path.getsize(OUT)} bytes")
