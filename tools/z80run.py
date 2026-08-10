#!/usr/bin/env python3
"""Εκτελεί ρουτίνες του src/*.asm σε προσομοιωτή Z80.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: ο emulator του Amstrad δεν τρέχει από εδώ, οπότε ο κώδικας σε
assembly ήταν ο μόνος που δεν δοκιμαζόταν ποτέ πριν φτάσει στον χρήστη. Το
parity harness συγκρίνει Python με JavaScript — δηλαδή δύο γλώσσες που δεν
έχουν καταχωρητές 8 bit — και γι' αυτό ΔΕΝ μπορεί να πιάσει την πιο συχνή
οικογένεια σφαλμάτων του Z80: υπερχείλιση σε 8 bit. Δύο τέτοια έχουν ήδη
φτάσει στον χρήστη (type*16 στο draw_tile, col*8 στο h_teleport).

Εδώ ο ΙΔΙΟΣ κώδικας που μπαίνει στη δισκέτα εκτελείται πραγματικά.

Χρήση:
    m = Z80Test()
    m.poke16(m.sym("HERO_X"), 0)
    m.call("HERO_TO_CELL", hl=addr_of_two_bytes)
    assert m.peek16(m.sym("HERO_X")) == 300
"""

import os
import re
import subprocess
import sys
import time

try:
    import z80
except ImportError:                                     # pragma: no cover
    z80 = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG = 0x4000

# Το firmware δεν υπάρχει εδώ. Κάθε κλήση σε jumpblock γίνεται RET, ώστε οι
# ρουτίνες που το αγγίζουν να τρέχουν χωρίς να κρεμάνε. Όποιος έλεγχος
# εξαρτάται από firmware δεν ανήκει σε αυτό το επίπεδο.
FIRMWARE_LO, FIRMWARE_HI = 0xB800, 0xBFFF

# Διεύθυνση-φρουρός: εκεί «επιστρέφει» η ρουτίνα που δοκιμάζουμε.
SENTINEL = 0x0038


class Z80Test:
    """Το χτισμένο main.bin φορτωμένο σε προσομοιωτή, με τα σύμβολα του rasm."""

    def __init__(self):
        if z80 is None:
            raise RuntimeError(
                "λείπει το πακέτο 'z80' (pip install z80) — τα τεστ Z80 "
                "παραλείπονται")
        self.syms = {}
        binary = self._build()
        self.m = z80.Z80Machine()
        for i, b in enumerate(binary):
            self.m.memory[ORG + i] = b
        # RET σε όλο το jumpblock του firmware.
        for a in range(FIRMWARE_LO, FIRMWARE_HI + 1):
            self.m.memory[a] = 0xC9
        self.m.memory[SENTINEL] = 0x76          # HALT: σταματά το run()

    # ---------------------------------------------------------------- build
    def _build(self):
        """Χτίζει το main.bin και διαβάζει τον πίνακα συμβόλων του rasm."""
        symfile = os.path.join(ROOT, "build", "symbols.txt")
        os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
        subprocess.run(["rasm", "src/main.asm", "-s", "-sa", "-os", symfile],
                       cwd=ROOT, check=True, capture_output=True)
        with open(symfile) as f:
            for line in f:
                m = re.match(r"(\S+)\s+#([0-9A-F]+)", line)
                if m:
                    self.syms[m.group(1).upper()] = int(m.group(2), 16)
        with open(os.path.join(ROOT, "build", "main.bin"), "rb") as f:
            return f.read()

    # ---------------------------------------------------------------- μνήμη
    def sym(self, name):
        key = name.upper()
        if key not in self.syms:
            raise KeyError(f"άγνωστο σύμβολο: {name}")
        return self.syms[key]

    def peek(self, addr, n=1):
        return bytes(self.m.memory[addr + i] for i in range(n))

    def peek16(self, addr):
        return self.m.memory[addr] | (self.m.memory[addr + 1] << 8)

    def poke(self, addr, data):
        for i, b in enumerate(bytes(data)):
            self.m.memory[addr + i] = b

    def poke16(self, addr, value):
        self.m.memory[addr] = value & 0xFF
        self.m.memory[addr + 1] = (value >> 8) & 0xFF

    # ------------------------------------------------------------- εκτέλεση
    def call(self, name, a=0, bc=0, de=0, hl=0, timeout=10.0):
        """Καλεί τη ρουτίνα και γυρίζει όταν κάνει RET.

        Η επιστροφή πιάνεται με μια διεύθυνση-φρουρό στη στοίβα που περιέχει
        HALT — έτσι δεν χρειάζεται να ξέρουμε πόσο θα τρέξει η ρουτίνα.
        """
        addr = self.sym(name) if isinstance(name, str) else name
        self.m.sp = 0xBFF0
        self.m.sp = (self.m.sp - 2) & 0xFFFF
        self.poke16(self.m.sp, SENTINEL)
        self.m.a, self.m.bc, self.m.de, self.m.hl = a, bc, de, hl
        self.m.pc = addr
        self.m.halted = False
        # Ο προσομοιωτής σταματά όποτε του πει το ticks_to_stop, όχι όταν
        # τελειώσει τη δουλειά του· το όριο μπαίνει σε πραγματικό χρόνο, γιατί
        # ένας ατέρμονος βρόχος δεν φαίνεται από τους κύκλους.
        deadline = time.time() + timeout
        while not self.m.halted:
            self.m.ticks_to_stop = 1_000_000
            self.m.run()
            if time.time() > deadline:
                raise RuntimeError(
                    f"η {name} δεν επέστρεψε σε {timeout}s — "
                    f"κόλλησε στο #{self.m.pc:04X} ({self.where(self.m.pc)})")
        return self

    def where(self, addr):
        """Το κοντινότερο σύμβολο πριν από τη διεύθυνση — για τα μηνύματα."""
        best = max((a, n) for n, a in self.syms.items() if a <= addr)
        return f"{best[1]}+{addr - best[0]}"

    def stub(self, name):
        """Κάνει μια ρουτίνα σκέτο RET.

        Χρησιμοποιείται για τη σχεδίαση: το render_room γράφει 960 πλακίδια και
        κυριαρχεί στον χρόνο του προσομοιωτή, ενώ δεν έχει τι να επαληθεύσει
        χωρίς οθόνη. Ό,τι ΕΛΕΓΧΕΤΑΙ εδώ είναι τα δεδομένα, όχι τα pixel.
        """
        self.m.memory[self.sym(name)] = 0xC9
        return self


if __name__ == "__main__":                              # pragma: no cover
    t = Z80Test()
    print(f"φορτώθηκαν {len(t.syms)} σύμβολα, main.bin στο #{ORG:04X}")
    sys.exit(0)
