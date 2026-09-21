#!/usr/bin/env python3
"""Screenshots of the REAL game, taken from the Z80 simulator.

WHY IT EXISTS: the Amstrad emulator does not run from here, and the docs
wanted pictures. The only honest picture of the game is the one the game
draws itself, so this runs the built main.bin on the same simulator the
tests use and reads the MODE 1 screen back out of #C000.

The firmware is not there. Everything the game asks of it is answered by a
small Python stand-in at the jumpblock address: the screen calls clear
memory, the text calls draw the CPC character set (tools/cpcfont.py, the
matrix table of the 6128 lower ROM), the keyboard call answers from a
schedule, the clock counts flybacks. The tiles, the hero, the HUD bar, the
title banner and the arrows are all drawn by the Z80 code, untouched.

What comes out is what the hardware would show at that moment, minus the
border and the CRT. Text is the one thing rendered here rather than by the
machine, and the doc says so.

    python3 tools/screenshot.py            # docs/screenshots/*.png
    python3 tools/screenshot.py 3 7        # only those rooms (plus the menu)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image

import physics as P
import roomfile as RF
from z80run import Z80Test, SENTINEL
import cpcfont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")

SCREEN = 0xC000
SCALE = 2                       # 640x400: MODE 1 pixels are twice as tall

# The 27 firmware ink numbers as RGB (SOFT968 appendix V: each of R, G, B is
# off, half or full).
INK_RGB = [
    (0, 0, 0), (0, 0, 128), (0, 0, 255), (128, 0, 0), (128, 0, 128),
    (128, 0, 255), (255, 0, 0), (255, 0, 128), (255, 0, 255), (0, 128, 0),
    (0, 128, 128), (0, 128, 255), (128, 128, 0), (128, 128, 128),
    (128, 128, 255), (255, 128, 0), (255, 128, 128), (255, 128, 255),
    (0, 255, 0), (0, 255, 128), (0, 255, 255), (128, 255, 0),
    (128, 255, 128), (128, 255, 255), (255, 255, 0), (255, 255, 128),
    (255, 255, 255)]

# Firmware jumpblock entries the game uses (addresses as in src/*.asm).
SCR_SET_MODE, SCR_CLEAR, SCR_SET_INK, SCR_SET_BORDER = 0xBC0E, 0xBC14, 0xBC32, 0xBC38
TXT_OUTPUT, TXT_SET_CURSOR, TXT_SET_PEN = 0xBB5A, 0xBB75, 0xBB90
KM_TEST_KEY, KM_READ_CHAR = 0xBB1E, 0xBB09
MC_WAIT_FLYBACK, KL_TIME_PLEASE = 0xBD19, 0xBD0D
SOUND_QUEUE, SOUND_RESET = 0xBCAA, 0xBCA7
CAS_IN_OPEN = 0xBC77

K_SPACE, K_ESC = 47, 66
ENTRY_ROW = 12                  # src/main.asm: the room message's text row


class Shot(Z80Test):
    """The game with a firmware stand-in: screen, text, keys and clock."""

    def __init__(self):
        super().__init__()
        self.inks = [1, 24, 20, 6]      # firmware defaults until set_palette
        self.pen = 1
        self.cursor = (1, 1)
        self.frame = 0                  # flybacks so far: the clock
        self.pressed = {}               # key -> (from_frame, to_frame)
        self.on_frame = {}              # frame -> callback
        self.fw = {
            SCR_SET_MODE: self._clear, SCR_CLEAR: self._clear,
            SCR_SET_INK: self._ink, SCR_SET_BORDER: lambda: None,
            TXT_OUTPUT: self._txt, TXT_SET_CURSOR: self._cursor,
            TXT_SET_PEN: self._pen,
            KM_TEST_KEY: self._key, KM_READ_CHAR: lambda: self._carry(False),
            MC_WAIT_FLYBACK: self._flyback, KL_TIME_PLEASE: self._time,
            SOUND_QUEUE: lambda: self._carry(True), SOUND_RESET: lambda: None,
            CAS_IN_OPEN: lambda: self._carry(False),
        }
        for a in self.fw:
            self.m.set_breakpoint(a)
        # set_load: the disc is not here. Answer with the set from the build.
        self.sets = {i: d for i, _, d in RF.all_sets()}
        self.hooks = {self.sym("SET_LOAD"): self._set_load}
        for a in self.hooks:
            self.m.set_breakpoint(a)

    # ----------------------------------------------------------- firmware
    def _ret(self):
        self.m.pc = self.peek16(self.m.sp)
        self.m.sp = (self.m.sp + 2) & 0xFFFF

    def _carry(self, on):
        self.m.f = (self.m.f | 1) if on else (self.m.f & 0xFE)

    def _zero(self, on):
        self.m.f = (self.m.f | 0x40) if on else (self.m.f & 0xBF)

    def _clear(self):
        for a in range(SCREEN, 0x10000):
            self.m.memory[a] = 0

    def _ink(self):
        self.inks[self.m.a & 3] = self.m.b

    def _pen(self):
        self.pen = self.m.a & 3

    def _cursor(self):
        self.cursor = (self.m.h, self.m.l)        # 1-based, as the firmware

    def _txt(self):
        """One character at the cursor, pen on paper 0, then advance."""
        col, row = self.cursor
        ch = self.m.a
        glyph = cpcfont.glyph(ch)
        base = (col - 1) * 2
        for line in range(8):
            y = (row - 1) * 8 + line
            addr = SCREEN + (y % 8) * 0x800 + (y // 8) * 80 + base
            bits = glyph[line]
            for half in range(2):
                out = 0
                for i in range(4):
                    if bits & (0x80 >> (half * 4 + i)):
                        out |= ((self.pen & 1) << (7 - i)) | ((self.pen >> 1) << (3 - i))
                self.m.memory[addr + half] = out
        self.cursor = (col + 1, row)

    def _key(self):
        span = self.pressed.get(self.m.a)
        down = bool(span) and span[0] <= self.frame < span[1]
        self._zero(not down)

    def _flyback(self):
        self.frame += 1
        cb = self.on_frame.pop(self.frame, None)
        if cb:
            cb()

    def _time(self):
        t = self.frame * 6                          # 1/300 s per tick
        self.m.hl, self.m.de = t & 0xFFFF, t >> 16

    def _set_load(self):
        idx = self.m.a
        self.poke(self.sym("SET_BUF"), self.sets[idx])
        self.poke(self.sym("SET_CUR"), bytes((idx,)))
        self._carry(True)

    # ------------------------------------------------------------ running
    def run(self, name, a=0, limit=60.0):
        """Like Z80Test.call, but the jumpblock answers instead of RETurning."""
        import time
        self.m.sp = 0xBFF0 - 2
        self.poke16(self.m.sp, SENTINEL)
        self.m.a = a
        self.m.pc = self.sym(name)
        self.m.halted = False
        deadline = time.time() + limit
        while not self.m.halted:
            self.m.ticks_to_stop = 200_000
            ev = self.m.run()
            if ev & self.m._BREAKPOINT_HIT:
                pc = self.m.pc
                if pc in self.fw:
                    self.fw[pc]()
                    self._ret()
                elif pc in self.hooks:
                    self.hooks[pc]()
                    self._ret()
            if time.time() > deadline:
                raise RuntimeError(f"{name}: still running after {limit}s "
                                   f"at #{self.m.pc:04X} ({self.where(self.m.pc)})")
        return self

    def press(self, key, at, frames=3):
        self.pressed[key] = (at, at + frames)

    # -------------------------------------------------------------- image
    def image(self):
        img = Image.new("RGB", (320, 200))
        px = img.load()
        rgb = [INK_RGB[i] for i in self.inks]
        for y in range(200):
            row = SCREEN + (y % 8) * 0x800 + (y // 8) * 80
            for bx in range(80):
                b = self.m.memory[row + bx]
                for i in range(4):
                    pen = ((b >> (7 - i)) & 1) | (((b >> (3 - i)) & 1) << 1)
                    px[bx * 4 + i, y] = rgb[pen]
        return img.resize((320 * SCALE, 200 * SCALE), Image.NEAREST)

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        path = os.path.join(OUT, name)
        self.image().save(path)
        print(f"  {path}")
        return path


def main(argv):
    rooms = [int(a) for a in argv] or sorted(r.number for r in P.all_rooms())
    t = Shot()
    t.stub("BANK_BOOT")             # the banks are filled from disc; not here
    t.run("INIT_LINETAB")
    t.run("HS_LOAD")                # no SCORES.BIN: an empty table, as on a new disc
    t.m.a = 1
    t.run("SET_PALETTE")

    # The menu: the arena hero walks for a while, then SPACE.
    MENU_FRAMES = 240
    t.press(K_SPACE, t.frame + MENU_FRAMES)
    t.on_frame[t.frame + MENU_FRAMES - 1] = lambda: t.save("menu.png")
    t.run("MENU_SHOW")

    t.fw[SCR_SET_MODE]()
    t.run("SET_PALETTE")
    t.run("GAME_RESET")
    t.run("MUSIC_GAME")
    t.run("MUSIC_START")

    for n in rooms:
        # A room with a message holds the screen until SPACE: answer it, and
        # keep the picture of the message too.
        held = []

        def on_msg(n=n):
            t.save(f"room_{n}_message.png")
            t.press(K_SPACE, t.frame + 2)
            held.append(1)
        t.hooks[t.sym("RMS_WAIT")] = on_msg
        t.m.set_breakpoint(t.sym("RMS_WAIT"))
        t.run("ROOM_LOAD", a=n)
        t.hooks.pop(t.sym("RMS_WAIT"))
        t.m.clear_breakpoint(t.sym("RMS_WAIT"))
        t.run("PREP_HERO")
        t.run("DRAW_HERO")
        # A few passes of the real loop so the hero lands and the HUD is
        # drawn, then ESC ends it.
        t.press(K_ESC, t.frame + 40, frames=8)
        t.run("MAIN_LOOP")
        t.save(f"room_{n}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
