#!/usr/bin/env python3
"""The screenshot tool draws what the machine would draw — checked, not eyeballed.

The pictures in docs/screenshots come from the real main.bin, but the text
in them comes from a stand-in for the firmware in tools/screenshot.py. A
stand-in that put the score one cell to the left, or counted rows from 0,
would give convincing pictures of a game that does not exist. So the test
reads the text BACK out of the screen memory, glyph by glyph against the
CPC font, at the exact cells the game asked for.

The room message is the other thing the stand-in has to get right: the game
holds the screen until SPACE is released, pressed and released again, and
the tool's key schedule has to satisfy that or the run never returns.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cpcfont
import physics as P
import roomfile as RF

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def read_row(t, row, pen=1):
    """The 40 characters of text row `row` (1-based), read back from #C000.

    A cell whose pen-`pen` bits match no glyph reads as '?', so a shifted or
    garbled character shows up instead of vanishing into a space.
    """
    from screenshot import SCREEN
    inverse = {g: chr(c) for c, g in cpcfont.GLYPHS.items()}
    out = ""
    for col in range(40):
        rows = []
        for line in range(8):
            y = (row - 1) * 8 + line
            addr = SCREEN + (y % 8) * 0x800 + (y // 8) * 80 + col * 2
            bits = 0
            for half in range(2):
                b = t.m.memory[addr + half]
                for i in range(4):
                    p = ((b >> (7 - i)) & 1) | (((b >> (3 - i)) & 1) << 1)
                    if p == pen:
                        bits |= 0x80 >> (half * 4 + i)
            rows.append(bits)
        out += inverse.get(bytes(rows), "?")
    return out


def main():
    try:
        import z80  # noqa: F401
    except ImportError:
        print("  ΠΑΡΑΛΕΙΨΗ: λείπει το πακέτο z80")
        return 0
    import screenshot as S
    import re

    t = S.Shot()
    t.stub("BANK_BOOT")
    t.run("INIT_LINETAB")
    t.run("HS_LOAD")
    t.run("SET_PALETTE")
    check("η παλέτα του παιχνιδιού πέρασε από το SCR_SET_INK",
          t.inks == [1, 26, 18, 16], str(t.inks))

    # 1. The menu, then the first room, exactly as tools/screenshot.py does.
    t.press(S.K_SPACE, t.frame + 30)
    t.run("MENU_SHOW")
    check("το μενού γράφει «Press Space» στη γραμμή του",
          "Press Space to start game" in read_row(t, 22), repr(read_row(t, 22)))

    t.fw[S.SCR_SET_MODE]()
    t.run("SET_PALETTE")
    t.run("GAME_RESET")
    t.run("ROOM_LOAD", a=1)
    t.run("PREP_HERO")
    t.run("DRAW_HERO")
    t.press(S.K_ESC, t.frame + 40, frames=8)
    t.run("MAIN_LOOP")

    # The score: SCORE_COL and row 1 come from src/score.asm, and the text
    # must sit in those very cells.
    src = open(os.path.join(S.ROOT, "src", "score.asm")).read()
    score_col = int(re.search(r"^SCORE_COL\s+equ\s+(\d+)", src, re.M).group(1))
    hud = read_row(t, 1)
    field = hud[score_col - 1:score_col - 1 + 7]
    check("το σκορ κάθεται στη στήλη SCORE_COL της γραμμής 1",
          re.fullmatch(r"[ +-]?0*1000\s*", field) is not None,
          repr(hud))
    check("…και τίποτα δεν γράφτηκε δεξιά ή αριστερά του",
          hud[:score_col - 1].strip() == "" and hud[score_col - 1 + 7:].strip() == "",
          repr(hud))

    img = t.image()
    colours = {c for _, c in img.getcolors(64)}
    check("η εικόνα έχει μόνο τα τέσσερα χρώματα της παλέτας",
          colours <= {S.INK_RGB[i] for i in t.inks} and len(colours) == 4,
          str(len(colours)))

    # 2. A room with an entry message: the screen is held, the text is
    #    centred on ENTRY_ROW, and the run comes back.
    txt = open(os.path.join(S.ROOT, "levels", "room_1.txt")).read().rstrip("\n")
    msg = "GRAVITY IS A CHOICE"
    room = P.Room(txt + "\nmsg " + msg)
    room.number = 1
    t.sets[1] = RF.build_set([room])
    t.poke(t.sym("SET_CUR"), b"\x00")          # force the set to reload
    shots = []
    t.hooks[t.sym("RMS_WAIT")] = lambda: (shots.append(read_row(t, S.ENTRY_ROW)),
                                          t.press(S.K_SPACE, t.frame + 2))
    t.m.set_breakpoint(t.sym("RMS_WAIT"))
    t.run("ROOM_LOAD", a=1, limit=20)
    check("η αίθουσα με μήνυμα κράτησε την οθόνη και μετά συνέχισε",
          len(shots) == 1, str(len(shots)))
    want_col = (40 - len(msg)) // 2 + 1
    got = shots[0] if shots else ""
    check("το μήνυμα είναι κεντραρισμένο στη γραμμή ENTRY_ROW",
          got[want_col - 1:want_col - 1 + len(msg)] == msg and got.strip() == msg,
          repr(got))
    return 0


if __name__ == "__main__":
    rc = main()
    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else "ΑΠΕΤΥΧΑΝ: " + ", ".join(FAILS))
    sys.exit(1 if FAILS or rc else 0)
