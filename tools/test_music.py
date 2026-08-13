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
    """Τα τρία κανάλια όπως τα βγάζει η γεννήτρια — ΟΛΟ το κομμάτι.

    Από την ίδια συνάρτηση με τον κώδικα που μπαίνει στη δισκέτα: αν το τεστ
    ξανάγραφε τη συναρμολόγηση των τμημάτων, θα δοκίμαζε τη δική του εκδοχή.
    """
    table, tr, _ = GB.build()
    return table, [(1, tr["bass"]), (2, tr["lead"]), (4, tr["drums"])]


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


# =====================================================================
#  Ο PLAYER ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ — το ίδιο κομμάτι, άλλος κώδικας
#
#  Ο standalone player παραπάνω και ο player του παιχνιδιού είναι δύο
#  ΔΙΑΦΟΡΕΤΙΚΕΣ υλοποιήσεις της ίδιας ιδέας: ο ένας ζει στο #8000 και έχει
#  δικές του ρουτίνες τραπεζών, ο άλλος ζει μέσα στο παράθυρο και δανείζεται
#  το bank_copy. Το ότι δουλεύει ο ένας δεν λέει τίποτα για τον άλλο.
# =====================================================================
print("--- ο player του παιχνιδιού, από το μπλοκ 7")

# Ό,τι χαλάει το SOUND QUEUE στ' αλήθεια. Χωρίς το IX εδώ, το τεστ θα περνούσε
# με έναν player που κρατά δείκτη σε index register — δες tools/z80run.py.
FW_KILLS = ("a", "bc", "de", "hl", "ix")


def game():
    """Το main.bin με το κομμάτι ήδη στη θέση του, σαν να έτρεξε το tune_boot."""
    t = z80run.Z80Test(banking=True)
    _, tr, _ = GB.build()
    data, _ = GB.blob(tr)
    t.bank_poke(7, 0x4000, data)
    t.poke(t.sym("TUNE_OK"), b"\x01")
    t.poke(t.sym("MUSIC_ON"), b"\x01")
    return t


def queued(t, steps=60):
    t.trace("SOUND_QUEUE", corrupt=FW_KILLS)
    for _ in range(steps):
        t.call("MUSIC_STEP")
    got = {}
    for blk in t.calls:
        got.setdefault(blk[0] & 7, []).append(
            (blk[3] | blk[4] << 8, blk[5], blk[6]))
    return got


table, want = tracks()
periods = [GB.GM.period(n) for n in table]


def expect(idx):
    if idx == 0:
        return (0, 0)
    if idx >= GB.GM.MUS_NOISE:
        return (0, idx - GB.GM.MUS_NOISE)
    return (periods[idx - 1], 0)


# --- το μενού: και οι τρεις φωνές, σωστές νότα προς νότα ---------------
t = game()
t.call("MUSIC_FULL")
t.call("MUSIC_START")
got = queued(t)
check(sorted(got) == [1, 2, 4],
      f"μενού: παίζουν και τα τρία κανάλια {sorted(got)}")
wrong = 0
for ch, notes in want:
    for i, (idx, vol, _) in enumerate(notes[:len(got.get(ch, []))]):
        tone, noise, v = got[ch][i]
        if (tone, noise) != expect(idx) or v != vol:
            wrong += 1
n = sum(len(v) for v in got.values())
check(wrong == 0, f"μενού: {n} νότες, όλες όπως τις έγραψε η γεννήτρια"
                  + (f" — {wrong} λάθος" if wrong else ""))
check(any(nz for _, nz, _ in got.get(4, [])), "μενού: τα τύμπανα έχουν θόρυβο")
check(not any(nz for ch in (1, 2) for _, nz, _ in got.get(ch, [])),
      "μενού: μπάσο και lead δεν έχουν θόρυβο")

# --- το παιχνίδι: το κανάλι B μένει ελεύθερο για τα εφέ ----------------
t = game()
t.call("MUSIC_GAME")
t.call("MUSIC_START")
got = queued(t)
check(sorted(got) == [1, 4],
      f"παιχνίδι: παίζουν μόνο μπάσο και τύμπανα {sorted(got)}")

# --- η επιλογή M -------------------------------------------------------
t = game()
t.call("MUSIC_TOGGLE")
check(t.peek(t.sym("MUSIC_ON"))[0] == 0, "M: το πρώτο πάτημα σβήνει")
got = queued(t, steps=5)
check(not got, "M: σβηστή σημαίνει καμία νότα στην ουρά")
t.call("MUSIC_TOGGLE")
check(t.peek(t.sym("MUSIC_ON"))[0] == 1, "M: το δεύτερο πάτημα ανάβει")

# --- χωρίς το κομμάτι στην τράπεζα: σιωπή, όχι σκουπίδια ---------------
t = game()
t.poke(t.sym("TUNE_OK"), b"\x00")
t.call("MUSIC_FULL")
t.call("MUSIC_START")
check(not queued(t, steps=5), "χωρίς TUNEnn.BIN: καμία νότα, κανένα σκουπίδι")

# --- γεμάτη ουρά: μία προσπάθεια ανά κανάλι, και τίποτα δεν προχωράει --
t = game()
t.call("MUSIC_FULL")
t.call("MUSIC_START")
t.trace("SOUND_QUEUE", carry=False, corrupt=FW_KILLS)
t.call("MUSIC_STEP")
first = len(t.calls)
t.call("MUSIC_STEP")
check(first == 3 and len(t.calls) == 6,
      f"γεμάτη ουρά: μία προσπάθεια ανά κανάλι ({first}, {len(t.calls)})")
# ΟΧΙ το CH_POS: αυτό δείχνει ΠΟΥ ΔΙΑΒΑΣΑΜΕ, και ο buffer όντως γέμισε — σωστά.
# Το ερώτημα είναι αν ΚΑΤΑΝΑΛΩΘΗΚΕ νότα, δηλαδή το CH_TAKE και το CH_LEFT.
ch = t.sym("MUS_CHAN")
take, left = t.peek(ch + 3)[0], t.peek(ch + 2)[0]
check(take == 0 and left == 4,
      f"γεμάτη ουρά: καμία νότα δεν καταναλώθηκε (take={take}, left={left})")

# --- το τύλιγμα: ο κύκλος του λεπτού ------------------------------------
#
# ΕΔΩ ΘΑ ΑΚΟΥΓΟΤΑΝ Η ΓΡΑΤΖΟΥΝΙΑ: μία φορά ανά λεπτό, στη ραφή. Τρέχουμε
# αρκετά για να περάσει και το ΜΑΚΡΥΤΕΡΟ κανάλι το τέλος του, και ελέγχουμε
# ότι οι νότες μετά τη ραφή είναι οι ΠΡΩΤΕΣ του κομματιού, όχι σκουπίδια.
longest = max(len(n) for _, n in want)
t = game()
t.call("MUSIC_FULL")
t.call("MUSIC_START")
got = queued(t, steps=longest // 4 + 8)
wrapped = 0
for chan, notes in want:
    seq = got.get(chan, [])
    if len(seq) <= len(notes):
        continue
    wrapped += 1
    extra = seq[len(notes):]
    idx, vol, _ = notes[0]
    check(extra[0] == (expect(idx)[0], expect(idx)[1], vol),
          f"τύλιγμα καναλιού {chan}: ξαναρχίζει από την πρώτη νότα")
check(wrapped == 3, f"και τα τρία κανάλια τύλιξαν ({wrapped})")

# --- tune_boot: τα τρία αρχεία γίνονται ΕΝΑ blob στην τράπεζα ----------
#
# Οι θέσεις μέσα σε ένα μπλοκ είναι συνεχόμενες — πάνω σε αυτό στηρίζεται όλο
# το σχέδιο, γι' αυτό δοκιμάζεται. Το CAS του firmware είναι σκέτο RET εδώ,
# οπότε οι παγίδες λένε «πέτυχε» και ο set_buf κρατά ό,τι βάλουμε εμείς.
t = z80run.Z80Test(banking=True)
mark = bytes((i * 7 + 1) & 0xFF for i in range(1536))
t.poke(t.sym("SET_BUF"), mark)
for name in ("CAS_IN_OPEN", "CAS_IN_DIRECT", "CAS_IN_CLOSE"):
    t.trace(name, nbytes=1, carry=True)
t.call("TUNE_BOOT")
check(t.peek(t.sym("TUNE_OK"))[0] == 1, "tune_boot: δηλώνει επιτυχία")
ok = all(t.bank_peek(7, 0x4000 + i * 1536, 1536) == mark for i in range(3))
check(ok, "tune_boot: τα τρία κομμάτια, το ένα μετά το άλλο, στο μπλοκ 7")
after = t.bank_peek(7, 0x4000 + 3 * 1536, 16)
check(after == bytes(16), "tune_boot: και τίποτα πέρα από αυτά")

# --- τα εφέ: στο B μόνο όσο παίζει μουσική μέσα σε δωμάτιο -------------
print("--- τα ηχητικά εφέ απέναντι στη μουσική")
SFXCH_ACT, SFXCH_MOVE, SFXCH_AMB = 1, 2, 4
for on, quiet, want_ch, label in (
        (0, 1, SFXCH_ACT, "μουσική σβηστή -> το εφέ κρατά το κανάλι του"),
        (1, 0, SFXCH_ACT, "μενού -> το εφέ κρατά το κανάλι του"),
        (1, 1, SFXCH_MOVE, "παιχνίδι -> το εφέ πάει στο B")):
    t = game()
    t.poke(t.sym("MUSIC_ON"), bytes([on]))
    t.poke(t.sym("MUS_QUIET"), bytes([quiet]))
    t.call("SFX_CHAN", a=SFXCH_ACT)
    check(t.m.a == want_ch, f"{label}  [{t.m.a}]")
t = game()
t.poke(t.sym("MUS_QUIET"), b"\x01")
t.call("SFX_CHAN", a=SFXCH_AMB + 0x80)
check(t.m.a == SFXCH_MOVE + 0x80, f"η σημαία αδειάσματος επιβιώνει [{t.m.a:#04x}]")

print("ΟΛΑ ΣΩΣΤΑ" if not fails else f"ΑΠΕΤΥΧΑΝ {len(fails)}")
sys.exit(1 if fails else 0)
