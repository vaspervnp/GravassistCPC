#!/usr/bin/env python3
"""GRAVASSIST — sprite pipeline: PNG <-> assembly.

    python3 tools/sprites.py init [--force]   φτιάχνει τα PNG από τις γεννήτριες
    python3 tools/sprites.py build            PNG  -> src/gfx_*.asm
    python3 tools/sprites.py export           asm  -> PNG (round-trip / ανάκτηση)
    python3 tools/sprites.py show hero 5      τυπώνει ένα frame ως ASCII

Ο κύκλος δουλειάς: `init` μία φορά, μετά ζωγραφίζεις ελεύθερα στα assets/*.png
και τρέχεις `build`. Το PNG είναι πάντα η αυθεντία — δες docs/sprites.md §5.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cpcgfx
import parachute
import placeholders
import stickman

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Sheet:
    def __init__(self, key, png, asm, label, w, h, count, cols, gen, names, title):
        self.key, self.png, self.asm, self.label = key, png, asm, label
        self.w, self.h, self.count, self.cols = w, h, count, cols
        self.gen, self.names, self.title = gen, names, title

    def path_png(self):
        return os.path.join(ROOT, self.png)

    def path_asm(self):
        return os.path.join(ROOT, self.asm)


SHEETS = [
    Sheet("hero", "assets/hero.png", "src/gfx_hero.asm", "hero_gfx",
          stickman.W, stickman.H, 32, 8,
          stickman.build_frames, stickman.FRAME_NAMES,
          "GRAVASSIST - sprites ήρωα"),
    Sheet("hero45", "assets/hero45.png", "src/gfx_hero45.asm", "hero45_gfx",
          stickman.W45, stickman.H45, 32, 8,
          stickman.build_frames45, stickman.FRAME_NAMES,
          "GRAVASSIST - sprites ήρωα στις 45 μοίρες"),
    Sheet("para", "assets/parachute.png", "src/gfx_para.asm", "para_gfx",
          parachute.W, parachute.H, len(parachute.FRAME_NAMES), 4,
          parachute.build_frames, parachute.FRAME_NAMES,
          "GRAVASSIST - αλεξίπτωτο, 4 φάσεις ανοίγματος"),
    Sheet("objects", "assets/objects.png", "src/gfx_objects.asm", "obj_gfx",
          placeholders.S, placeholders.S, len(placeholders.FRAME_NAMES), 8,
          placeholders.build_frames, placeholders.FRAME_NAMES,
          "GRAVASSIST - sprites αντικειμένων (PLACEHOLDERS)"),
]


def _sheet(key):
    for s in SHEETS:
        if s.key == key:
            return s
    sys.exit(f"άγνωστο sheet '{key}' (διάθεσιμα: {', '.join(s.key for s in SHEETS)})")


def cmd_init(argv):
    force = "--force" in argv
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    for s in SHEETS:
        if os.path.exists(s.path_png()) and not force:
            print(f"  παραλείπω {s.png} (υπάρχει· --force για overwrite)")
            continue
        frames = s.gen()
        W, H = cpcgfx.write_sheet(s.path_png(), frames, s.w, s.h, s.cols)
        print(f"  {s.png}: {len(frames)} frames {s.w}x{s.h} -> εικόνα {W}x{H}")


def cmd_build(argv):
    for s in SHEETS:
        if not os.path.exists(s.path_png()):
            sys.exit(f"λείπει το {s.png} — τρέξε πρώτα: python3 tools/sprites.py init")
        frames = cpcgfx.read_sheet(s.path_png(), s.w, s.h, s.cols, s.count)
        asm = cpcgfx.to_asm(s.label, frames, s.w, s.h, s.title)
        # ονόματα frames ως equ, για να διαβάζεται ο κώδικας παιχνιδιού
        eq = ["", f"; --- δείκτες frame του {s.label} ---"]
        for i, n in enumerate(s.names):
            eq.append(f"{s.label}_{n:<10} equ {i}")
        os.makedirs(os.path.dirname(s.path_asm()), exist_ok=True)
        with open(s.path_asm(), "w") as f:
            f.write(asm + "\n".join(eq) + "\n")
        print(f"  {s.png} -> {s.asm} ({len(frames)} frames, "
              f"{len(frames) * s.w * s.h} bytes δεδομένων)")


def cmd_export(argv):
    """Ανακατασκευάζει το PNG από το .asm — έλεγχος ότι το round-trip κλείνει."""
    for s in SHEETS:
        if not os.path.exists(s.path_asm()):
            print(f"  παραλείπω {s.asm} (δεν υπάρχει)")
            continue
        rows = []
        with open(s.path_asm()) as f:
            for ln in f:
                m = re.match(r"\s*db\s+([0-9,\s]+)$", ln)
                if m:
                    rows.append([int(v) for v in m.group(1).split(",")])
        frames = [rows[i:i + s.h] for i in range(0, len(rows), s.h)]
        out = s.path_png().replace(".png", "-export.png")
        cpcgfx.write_sheet(out, frames, s.w, s.h, s.cols)
        print(f"  {s.asm} -> {os.path.relpath(out, ROOT)} ({len(frames)} frames)")


def cmd_show(argv):
    if len(argv) < 1:
        sys.exit("χρήση: sprites.py show <hero|objects> [frame]")
    s = _sheet(argv[0])
    frames = (cpcgfx.read_sheet(s.path_png(), s.w, s.h, s.cols, s.count)
              if os.path.exists(s.path_png()) else s.gen())
    idx = range(s.count) if len(argv) < 2 else [int(argv[1])]
    for i in idx:
        print(f"--- {i}: {s.names[i]} ---")
        print(cpcgfx.to_ascii(frames[i]))


CMDS = {"init": cmd_init, "build": cmd_build, "export": cmd_export, "show": cmd_show}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        sys.exit(__doc__)
    CMDS[sys.argv[1]](sys.argv[2:])
