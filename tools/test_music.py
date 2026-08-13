#!/usr/bin/env python3
"""Το MUSIC.BIN σε προσομοιωτή Z80 — με τη στοίβα εκεί που είναι στ' αλήθεια.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: ο player βγήκε δύο φορές στον χρήστη και δύο φορές ακούστηκε
συνεχής θόρυβος, ενώ κάθε έλεγχος εδώ ήταν πράσινος. Ο λόγος ήταν ότι το
tools/z80run.py καλεί τις ρουτίνες με SP=#BFF0, πάνω από το παράθυρο των
τραπεζών, ενώ ο loader κάνει MEMORY &7FFF και η στοίβα της BASIC κάθεται στο
#7FFx — ΜΕΣΑ στο παράθυρο. Το `pop bc` του bank_put διάβαζε τότε την τράπεζα
αντί για τη στοίβα, το LDIR έπαιρνε μήκος #FFFF και έγραφε 64 KB πάνω στο ίδιο
το πρόγραμμα. Το τεστ τρέχει και τις δύο θέσεις στοίβας, και με σκουπίδια στην
τράπεζα, γιατί η άδεια RAM δεν είναι μηδενικά σε πραγματικό μηχάνημα.

Δύο επίπεδα:
  1. bank_load με τη στοίβα μέσα στο παράθυρο — το αντίγραφο πρέπει να είναι
     ακριβές, όχι απλώς να μην κρασάρει.
  2. κάθε νότα κάθε καναλιού, streamed μέσα από την τράπεζα, ελέγχεται ενάντια
     στα δεδομένα που παρήγαγε το tools/genboss.py.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import genboss as GB
import z80run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG = 0x8000
SOUND_QUEUE = 0xBCAA

# Οι δύο θέσεις στοίβας που έχουν σημασία, και το γιατί.
STACKS = [("πάνω από το παράθυρο", 0xBFF0),
          ("ΜΕΣΑ στο παράθυρο (MEMORY &7FFF)", 0x7FF0)]
# Τι βρίσκει το πρόγραμμα στην άδεια τράπεζα. Το #00 είναι το μόνο που δίνει ο
# προσομοιωτής από μόνος του, και είναι και το μόνο που δεν συμβαίνει ποτέ.
JUNK = [0xFF, 0xA5, 0x00]

fails = []


def check(cond, msg):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {msg}")
    if not cond:
        fails.append(msg)


class MusicTest(z80run.Z80Test):
    """Το ίδιο harness, αλλά MUSIC.BIN στο #8000 αντί για MAIN.BIN στο #4000."""

    def _build(self):
        out = os.path.join(ROOT, "build", "musicsym.txt")
        os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
        subprocess.run(["rasm", "src/musictest.asm", "-s", "-sa", "-os", out],
                       cwd=ROOT, check=True, capture_output=True)
        with open(out) as f:
            for line in f:
                m = re.match(r"(\S+)\s+#([0-9A-F]+)", line)
                if m:
                    self.syms[m.group(1).upper()] = int(m.group(2), 16)
        return b""

    def load(self, junk=0xFF):
        with open(os.path.join(ROOT, "build", "music.bin"), "rb") as f:
            self.image = f.read()
        for i, b in enumerate(self.image):
            self.m.memory[ORG + i] = b
        for blk in self.banks:
            for i in range(len(blk)):
                blk[i] = junk
        return self

    def at(self, sp):
        """Η επόμενη κλήση γίνεται με ΑΥΤΗ τη στοίβα."""
        self.stack = sp
        return self

    def call(self, name, **kw):
        return super().call(name, **kw) if not hasattr(self, "stack") \
            else self._call_at(name, **kw)

    def _call_at(self, name, **kw):
        self.m.sp = self.stack
        self.m.sp = (self.m.sp - 2) & 0xFFFF
        self.poke16(self.m.sp, z80run.SENTINEL)
        self.m.pc = self.sym(name)
        self.m.halted = False
        for _ in range(2000):
            self.m.ticks_to_stop = 500_000
            self.m.run()
            if self.traps and self.m.pc in self.traps:
                self._trapped()
                continue
            if self.m.halted:
                return self
        raise RuntimeError(f"η {name} δεν επέστρεψε")


def tracks():
    table = GB.collect()
    return table, [(1, GB.stream(GB.BASS, table, GB.VOL_BASS)[0]),
                   (2, GB.stream(GB.LEAD, table, GB.VOL_LEAD)[0]),
                   (4, GB.drums(table)[0])]


print("--- bank_load: τι ΑΛΛΟ ακούμπησε στην κύρια μνήμη")
#
# ΠΡΟΣΟΧΗ, ΕΔΩ ΕΙΝΑΙ ΤΟ ΚΟΛΠΟ: να ελέγχεις μόνο ότι η τράπεζα γέμισε σωστά ΔΕΝ
# πιάνει το σφάλμα. Με μήκος #FFFF το LDIR γράφει και πάλι τα σωστά bytes στις
# σωστές θέσεις της τράπεζας — η διάταξη του προορισμού καθρεφτίζει την πηγή —
# και μετά συνεχίζει για άλλα 60 KB πάνω από το ίδιο το πρόγραμμα. Το τεστ
# πρέπει να κοιτάει ΤΙ ΑΛΛΟ άλλαξε, όχι αν το ζητούμενο έγινε.
table, want = tracks()
for junk in JUNK:
    for label, sp in STACKS:
        t = MusicTest(banking=True).load(junk)
        before = bytes(t.m.memory[a] for a in range(0x10000))
        t.at(sp).call("BANK_LOAD")
        after = bytes(t.m.memory[a] for a in range(0x10000))

        # Οι μόνες θέσεις που επιτρέπεται να αλλάξουν: οι μεταβλητές του ίδιου
        # του bank_load, και η στοίβα κάτω από τον δείκτη της.
        allowed = set(range(t.sym("BL_DST"), t.sym("BL_DST") + 2))
        allowed |= set(range(t.sym("BANK_OK"), t.sym("OUR_STACK")))
        allowed |= set(range(sp - 64, sp))
        stray = [a for a in range(0x10000)
                 if before[a] != after[a] and a not in allowed]
        check(not stray,
              f"τράπεζα #{junk:02X}, στοίβα {label}: "
              + (f"{len(stray)} bytes γράφτηκαν αλλού, από #{stray[0]:04X}"
                 if stray else "τίποτα εκτός των μεταβλητών"))

        src = t.sym("CHAN_SRC")
        good = True
        for i, (_, notes) in enumerate(want):
            addr, ln = t.peek16(src + 4 * i), t.peek16(src + 4 * i + 2)
            data = b"".join(bytes(n) for n in notes)
            if ln != len(data) or t.bank_peek(4, addr, ln) != data:
                good = False
        check(good, f"τράπεζα #{junk:02X}, στοίβα {label}: τα κομμάτια μέσα")

print("--- κάθε νότα, streamed από την τράπεζα")
for label, sp in STACKS:
    t = MusicTest(banking=True).load(0xFF)
    # ΟΠΩΣ ΤΟ ΣΙΔΕΡΟ: το SOUND QUEUE χαλάει και το IX (SOFT968). Χωρίς αυτό η
    # δοκιμή περνάει με έναν player που κρατάει δείκτη εκεί μέσα.
    t.trace(SOUND_QUEUE, corrupt=("a", "bc", "de", "hl", "ix"))
    t.at(sp)
    t.call("BANK_LOAD")
    t.call("CHAN_INIT")
    for _ in range(1 + max(len(n) for _, n in want) // 10):
        t.call("CHAN_STEP")
    # Ο δείκτης καναλιού πρέπει να είναι 1, 2 ή 4. Οτιδήποτε άλλο σημαίνει ότι
    # το snd_block γέμισε μέσα από χαλασμένο IX — δεν είναι λάθος του τεστ.
    got = {1: [], 2: [], 4: []}
    junk = 0
    for blk in t.calls:
        ch = blk[0] & 7
        if ch in got:
            got[ch].append((blk[3] | blk[4] << 8, blk[5], blk[6]))
        else:
            junk += 1
    check(junk == 0, f"κανένα μπλοκ με άκυρο κανάλι, στοίβα {label}"
                     + (f" ({junk} από {len(t.calls)})" if junk else ""))
    periods = [GB.GM.period(n) for n in table]
    wrong = 0
    for ch, notes in want:
        for i, (idx, vol, _) in enumerate(notes[:len(got[ch])]):
            if idx == 0:
                exp = (0, 0)
            elif idx >= GB.GM.MUS_NOISE:
                exp = (0, idx - GB.GM.MUS_NOISE)
            else:
                exp = (periods[idx - 1], 0)
            tone, noise, v = got[ch][i]
            if (tone, noise) != exp or v != vol:
                wrong += 1
    n = sum(len(v) for v in got.values())
    check(wrong == 0 and n > 0, f"{n} νότες στην ουρά, στοίβα {label}")
    check(any(noise for _, noise, _ in got[4]),
          f"το κανάλι 4 έχει θόρυβο (τύμπανα), στοίβα {label}")
    check(not any(noise for ch in (1, 2) for _, noise, _ in got[ch]),
          f"τα κανάλια 1 και 2 δεν έχουν θόρυβο, στοίβα {label}")

print("ΟΛΑ ΣΩΣΤΑ" if not fails else f"ΑΠΕΤΥΧΑΝ {len(fails)}")
sys.exit(1 if fails else 0)
