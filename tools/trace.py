#!/usr/bin/env python3
"""Οπτικό ίχνος του μοντέλου φυσικής.

    python3 tools/trace.py [frames] [x] [y] [walkdir]

Τυπώνει το δωμάτιο με το μονοπάτι που έκανε ο ήρωας, όπου κάθε κελί δείχνει τη
φορά βαρύτητας που είχε εκεί. Έτσι φαίνεται με μια ματιά αν οι στροφές στις
γωνίες και στις ράμπες γίνονται όπως πρέπει.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P


def run(frames=800, x=60, y=40, d=1, room=None):
    room = room or P.load_room()
    h = P.Hero(room, x, y, 0)
    path, events = {}, []
    prev = (h.g, h.state)
    for i in range(frames):
        h.update(d)
        path[(h.x // P.CELL, (h.y - P.GRID_Y0) // P.CELL)] = h.g
        cur = (h.g, h.state)
        if cur != prev:
            events.append((i, h.x, h.y, h.g, h.state))
            prev = cur
    return room, h, path, events


def render(room, path):
    out = [[P.BACK[room.cell(c, r)] for c in range(P.COLS)]
           for r in range(P.ROWS)]
    for (c, r), g in path.items():
        if 0 <= c < P.COLS and 0 <= r < P.ROWS:
            out[r][c] = P.GLYPH[g]
    return "\n".join("".join(row) for row in out)


if __name__ == "__main__":
    a = sys.argv[1:]
    frames = int(a[0]) if len(a) > 0 else 800
    x = int(a[1]) if len(a) > 1 else 60
    y = int(a[2]) if len(a) > 2 else 40
    d = int(a[3]) if len(a) > 3 else 1

    room, h, path, events = run(frames, x, y, d)
    print(render(room, path))
    print(f"\n{len(path)} κελιά, {len(events)} αλλαγές κατάστασης")
    for i, ex, ey, g, st in events[:40]:
        print(f"  frame {i:4}  ({ex:3},{ey:3})  βαρύτητα {g} {P.GLYPH[g]}  {st}")
    print(f"τέλος: ({h.x},{h.y}) βαρύτητα {h.g} {P.GLYPH[h.g]} {h.state}")
