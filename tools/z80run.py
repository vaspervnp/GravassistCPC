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

# --- Τράπεζες RAM του 6128 -------------------------------------------------
#
# Ο gate array αποκωδικοποιείται σε A15=0 και A14=1, δηλαδή θύρα #7Fxx. Μια
# τιμή με τα δύο πάνω bits 11 επιλέγει την ΟΡΓΑΝΩΣΗ μνήμης: #C0..#C7. Στο
# 6128 οι οργανώσεις 4..7 αντικαθιστούν ΜΟΝΟ το #4000..#7FFF με τα μπλοκ
# 4..7· τα υπόλοιπα τρία τέταρτα της μνήμης μένουν ως έχουν.
#
# ΓΙΑΤΙ ΕΔΩ: χωρίς μοντέλο τραπεζών, κάθε τεστ που θα γραφόταν για τον κώδικα
# banking θα ήταν ψεύτικο πράσινο — ο προσομοιωτής θα αγνοούσε το OUT και θα
# διάβαζε τη βασική μνήμη, δηλαδή ακριβώς ό,τι κάνει ένα μηχάνημα 64K.
GA_PORT_MASK, GA_PORT_SEL = 0xC000, 0x4000
BANK_LO, BANK_HI = 0x4000, 0x7FFF
BANK_SIZE = BANK_HI - BANK_LO + 1
FIRST_BANK = 4                  # οι οργανώσεις 4..7 -> μπλοκ 4..7


class Z80Test:
    """Το χτισμένο main.bin φορτωμένο σε προσομοιωτή, με τα σύμβολα του rasm."""

    def __init__(self, banking=False):
        """banking=False είναι ΜΗΧΑΝΗΜΑ 64K: το OUT στον gate array αγνοείται.

        Δεν είναι μόνο προεπιλογή για συμβατότητα — είναι και το σενάριο που
        πρέπει να δοκιμάζεται (464/664, ή 6128 σε προφίλ 64K στον emulator).
        Είναι επίσης ΓΡΗΓΟΡΟ: με banking=True κάθε ανάγνωση μνήμης περνά από
        callback της Python, που κοστίζει σε δοκιμές των 200 καρέ.
        """
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
        self.m.memory[SENTINEL] = 0x76
        self.traps = {}                 # διεύθυνση -> (bytes, carry)
        self.calls = []                 # τα μπλοκ που πέρασαν από τις παγίδες
        self.ram_org = 0                # οργάνωση μνήμης· 0 = καμία τράπεζα
        self.banks = [bytearray(BANK_SIZE) for _ in range(4)]   # μπλοκ 4..7
        self.banking = banking
        if banking:
            self._install_banking()

    # -------------------------------------------------------------- τράπεζες
    def _block_at(self, addr):
        """Ποιο μπλοκ βλέπει η διεύθυνση· None = η βασική μνήμη."""
        if self.ram_org < FIRST_BANK or not (BANK_LO <= addr <= BANK_HI):
            return None
        return self.banks[self.ram_org - FIRST_BANK]

    def _install_banking(self):
        mem = self.m.memory

        def rd(addr):
            blk = self._block_at(addr)
            return mem[addr] if blk is None else blk[addr - BANK_LO]

        def wr(addr, value):
            blk = self._block_at(addr)
            if blk is None:
                mem[addr] = value
            else:
                blk[addr - BANK_LO] = value

        def out(port, value):
            # ΣΤΑ BITS ΔΙΕΥΘΥΝΣΗΣ, όχι στο χαμηλό byte: το `out (c),c` με
            # BC=#7FC4 δίνει θύρα #7FC4 και το `out (#7F),a` δίνει #xx7F.
            # Σύγκριση με το #7F θα έχανε τη μία από τις δύο μορφές.
            if (port & GA_PORT_MASK) != GA_PORT_SEL or (value & 0xC0) != 0xC0:
                return
            org = value & 7
            # Οι οργανώσεις 1..3 είναι του CP/M Plus και μετακινούν και άλλα
            # μπλοκ. Δεν τις μοντελοποιούμε — σιωπηλή αγνόηση θα έδειχνε το
            # τεστ πράσινο ενώ το σίδερο θα έκανε κάτι εντελώς άλλο.
            if 1 <= org <= 3:
                raise RuntimeError(
                    f"οργάνωση μνήμης {org} (#{value:02X}): δεν μοντελοποιείται")
            self.ram_org = org

        self.m.set_read_callback(rd)
        self.m.set_write_callback(wr)
        self.m.set_output_callback(out)

    def bank_peek(self, block, addr, n=1):
        """Bytes από μπλοκ 4..7, με ΑΠΟΛΥΤΗ διεύθυνση μέσα στο #4000..#7FFF."""
        blk = self.banks[block - FIRST_BANK]
        return bytes(blk[addr - BANK_LO + i] for i in range(n))

    def bank_poke(self, block, addr, data):
        blk = self.banks[block - FIRST_BANK]
        for i, b in enumerate(bytes(data)):
            blk[addr - BANK_LO + i] = b

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
            event = self.m.run()
            if self.traps and (event & self.m._BREAKPOINT_HIT) \
                    and self.m.pc in self.traps:
                self._trapped()
                continue
            if time.time() > deadline:
                raise RuntimeError(
                    f"η {name} δεν επέστρεψε σε {timeout}s — "
                    f"κόλλησε στο #{self.m.pc:04X} ({self.where(self.m.pc)})")
        return self

    # ------------------------------------------------------------ παγίδες
    #
    # ΓΙΑΤΙ ΧΡΕΙΑΖΕΤΑΙ: όλο το jumpblock του firmware είναι σκέτο RET, οπότε
    # μια κλήση σε αυτό δεν αφήνει κανένα ίχνος. Για τον ήχο αυτό δεν φτάνει —
    # το ερώτημα δεν είναι «τι έγραψε στη μνήμη» αλλά «ΠΟΣΕΣ φορές κάλεσε την
    # ουρά και με τι». Ένας κοινός buffer κρατά μόνο το τελευταίο μπλοκ, άρα
    # δεν μπορεί να δείξει ούτε πλήθος ούτε σειρά.
    #
    # Η παγίδα σταματά ΠΡΙΝ εκτελεστεί η εντολή στη διεύθυνση, καταγράφει, και
    # μετά κάνει το RET με το χέρι.

    def trace(self, name, nbytes=9, carry=True):
        """Καταγράφει κάθε κλήση στη διεύθυνση: HL και το μπλοκ που δείχνει.

        carry=True σημαίνει «η ουρά δέχτηκε τον ήχο». Με False δοκιμάζουμε τι
        κάνει ο κώδικας σε γεμάτη ουρά.
        """
        addr = self.sym(name) if isinstance(name, str) else name
        self.traps[addr] = (nbytes, carry)
        self.m.set_breakpoint(addr)
        return self

    def _trapped(self):
        nbytes, carry = self.traps[self.m.pc]
        self.calls.append(self.peek(self.m.hl, nbytes))
        ret = self.peek16(self.m.sp)        # η CALL έχει ήδη σπρώξει τη διεύθυνση
        self.m.sp = (self.m.sp + 2) & 0xFFFF
        self.m.pc = ret
        self.m.f = (self.m.f | 0x01) if carry else (self.m.f & 0xFE)

    def where(self, addr):
        """Το κοντινότερο σύμβολο πριν από τη διεύθυνση — για τα μηνύματα."""
        best = max((a, n) for n, a in self.syms.items() if a <= addr)
        return f"{best[1]}+{addr - best[0]}"

    def fake_set_load(self):
        """Κάνει το set_load «scf / ret»: ο buffer γεμίζεται με το χέρι.

        ΓΙΑΤΙ ΧΡΕΙΑΖΕΤΑΙ: ο set_buf ζει στη μνήμη οθόνης, οπότε το room_load
        ξαναφορτώνει σε κάθε κλήση αντί να εμπιστεύεται το set_cur. Εδώ δεν
        υπάρχει δίσκος — όλο το jumpblock του firmware είναι RET — άρα κάθε
        room_load θα γύριζε άπρακτο. Επιστρέφει τα δύο αρχικά bytes, ώστε ο
        καλών να μπορεί να ξαναφέρει τον αληθινό δρόμο όταν τον δοκιμάζει.
        """
        addr = self.sym("SET_LOAD")
        before = self.peek(addr, 2)
        self.poke(addr, b"\x37\xC9")           # scf / ret
        return before

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
