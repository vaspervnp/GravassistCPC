#!/usr/bin/env python3
"""Η εισαγωγική μουσική του μενού -> src/music.asm.

ΓΙΑΤΙ ΓΕΝΝΙΕΤΑΙ: οι περίοδοι τόνου του AY δεν είναι νότες αλλά διαιρέτες
(period = 125000 / συχνότητα). Γραμμένες στο χέρι θα ήταν 150 magic numbers
που κανείς δεν μπορεί να διορθώσει. Εδώ γράφονται ΝΟΤΕΣ και ο υπολογισμός
γίνεται μία φορά.

ΜΟΡΦΗ ΡΟΗΣ: 3 bytes ανά νότα — δείκτης νότας, ένταση, διάρκεια. Ο παίκτης
χτίζει από αυτά το μπλοκ 9 bytes που θέλει το SOUND QUEUE του firmware.
Ολόκληρα μπλοκ στη μνήμη θα κόστιζαν τριπλάσια, και ο χώρος αφαιρείται από
τις αίθουσες.

Ο θρίλερ χαρακτήρας βγαίνει από τρία πράγματα: χαμηλό ostinato που δεν
σταματά, ημιτόνιο (D -> Eb) που δεν λύνεται, και τρίτονο (D -> Ab) στο τέλος
του κύκλου. Καμία νότα δεν είναι «γλυκιά» — το κλειδί είναι ρε ελάσσων χωρίς
τρίτη, ώστε να μη δηλώνεται καν το τονικό χρώμα.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ο AY του CPC: period = 125000 / f. Το firmware θέλει ακέραιο 16-bit.
CLOCK = 125000

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# --- Η μελωδία, σε νότες -----------------------------------------------
# Ρυθμός: 120 BPM, δηλαδή 50 μονάδες (μισό δευτερόλεπτο) ανά παλμό. Ο κύκλος
# είναι 10 μέτρα των 4/4 = 2000 μονάδες = ΑΚΡΙΒΩΣ 20 δευτερόλεπτα, ώστε τα
# τρία κανάλια να ξαναρχίζουν μαζί.
BEAT = 50
BAR = 4 * BEAT
LOOP = 10 * BAR

R = None            # παύση

BASS = (
    [("D2", 2 * BEAT), ("D2", BEAT), ("D#2", BEAT)] * 4 +
    [("D2", 2 * BEAT), ("D2", BEAT), ("D#2", BEAT)] * 4 +
    [("G#2", 2 * BEAT), ("G#2", BEAT), ("A2", BEAT)] +
    [("G#2", 2 * BEAT), ("D2", 2 * BEAT)]
)

LEAD = (
    [(R, 2 * BAR)] +
    [("A4", 3 * BEAT), (R, BEAT)] +
    [("F4", 2 * BEAT), ("E4", 2 * BEAT)] +
    [("D4", 3 * BEAT), (R, BEAT)] +
    [("A#3", 2 * BEAT), ("A3", 2 * BEAT)] +
    [(R, BAR)] +
    [("G#4", 2 * BEAT), ("A4", 2 * BEAT)] +
    [("F4", BAR)] +
    [("E4", 2 * BEAT), ("D#4", 2 * BEAT)]
)

# Χτύπος καρδιάς: δύο κοντά χτυπήματα ανά μέτρο, με λίγο θόρυβο.
PULSE = [("D1", BEAT // 2), (R, BEAT // 2), ("D1", BEAT // 2),
         (R, 5 * BEAT // 2)] * 10

VOL_BASS, VOL_LEAD, VOL_PULSE = 11, 9, 13
NOISE_PULSE = 12

# --- ΤΑ ΤΥΜΠΑΝΑ ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ ----------------------------------------
#
# Μεταγραμμένα από το musicsamples/8-bit-marching-drums_160bpm.wav: τέσσερα
# μέτρα, με το 1ο και το 3ο ίδια. Η ανάλυση (ενέργεια + zero-crossing ανά
# δέκατο έκτο) έδειξε μπάσο τύμπανο στα χαμηλά ZCR και ταμπούρο στα υψηλά.
#
# 150 BPM ΚΑΙ ΟΧΙ 160: οι διάρκειες του firmware είναι εκατοστά του
# δευτερολέπτου, οπότε στα 160 ένα δέκατο έκτο βγαίνει 9,375 — μη ακέραιο, και
# ο κύκλος θα «γλιστρούσε». Στα 150 είναι ακριβώς 10 και το μέτρο 160. Η
# διαφορά 6% δεν ακούγεται σε βάδισμα· ένας κύκλος που ξεσυγχρονίζεται, ναι.
DRUM_STEP = 10                      # ένα δέκατο έκτο
DRUM_BAR = 16 * DRUM_STEP

# Δείκτες >= MUS_NOISE είναι κρουστά χωρίς τόνο· η διαφορά είναι η περίοδος
# θορύβου του AY. Μικρή περίοδος = φωτεινό «τσακ», μεγάλη = υπόκωφο.
MUS_NOISE = 200
SNARE = MUS_NOISE + 6               # ταμπούρο: κοφτό και φωτεινό
SNARE_S = MUS_NOISE + 14            # πιο σβηστό, για τα αδύναμα χτυπήματα
KICK = "C1"                         # μπάσο τύμπανο: πολύ χαμηλός τόνος

# Κάθε μέτρο ως 16 θέσεις. K = μπάσο, k = αδύναμο μπάσο (flam), S = ταμπούρο,
# s = αδύναμο ταμπούρο, τελεία = σιωπή.
DRUM_BARS = [
    "Kk..S...K...S.Kk",
    "k.S.K...s.KkK.S.",
    "Kk..S...K...S.Kk",
    "k.S.K...s.S.K.Kk",
]


def midi(name):
    """«A#3» -> αριθμός MIDI. Το 4 είναι η οκτάβα του A4 = 440 Hz."""
    i = 2 if len(name) > 2 else 1
    step = NAMES.index(name[:i])
    octave = int(name[i:])
    return 12 * (octave + 1) + step


def period(name):
    freq = 440.0 * 2 ** ((midi(name) - 69) / 12.0)
    return int(round(CLOCK / freq))


def collect(*tracks):
    """Οι μοναδικές νότες όλων των κομματιών, ταξινομημένες."""
    names = {n for tr in tracks for n, _ in tr if n}
    return sorted(names, key=midi)


def stream(track, table, volume):
    """Μία ροή σε τριάδες (δείκτης νότας, ένταση, διάρκεια).

    Κάθε νότα κόβεται λίγο πριν το τέλος της και ακολουθεί σιωπή: χωρίς αυτό
    οι ίδιες νότες στη σειρά ακούγονται σαν ΕΝΑ συνεχές μπουρδόνι και ο
    ρυθμός εξαφανίζεται.
    """
    out, total = [], 0

    def emit(note, vol, dur):
        # Η διάρκεια είναι ΕΝΑ byte. Ό,τι ξεπερνά τα 255 σπάει σε κομμάτια,
        # αλλιώς ο assembler την περικόπτει σιωπηλά και η νότα βγαίνει
        # τέταρτο της κανονικής — το είδα να συμβαίνει σε παύση ολόκληρου
        # μέτρου, όπου δεν ακούγεται καν ότι κάτι πήγε στραβά.
        while dur > 0:
            step = min(dur, 200)
            out.append((note, vol, step))
            dur -= step

    for name, dur in track:
        total += dur
        if name is None:
            emit(0, 0, dur)
            continue
        gap = max(2, dur // 8)
        emit(table.index(name) + 1, volume, dur - gap)
        emit(0, 0, gap)
    return out, total


# Ένταση ανά σύμβολο. Το flam (μικρό k) είναι σαφώς πιο σιγανό από το κύριο
# χτύπημα — αυτό είναι που κάνει το «μπαμ-πα» να ακούγεται ως ένα χτύπημα με
# στολίδι και όχι ως δύο ξεχωριστά.
DRUM_VOICE = {"K": (KICK, 13), "k": (KICK, 8),
              "S": (SNARE, 12), "s": (SNARE_S, 8)}
DRUM_HIT = 3            # πόσο κρατά ο κρότος· το υπόλοιπο του βήματος σιωπή


def drum_stream(table):
    """Τα τέσσερα μέτρα σε τριάδες, με σιωπή ανάμεσα στα χτυπήματα.

    Η σιωπή ΔΕΝ είναι διακοσμητική: χωρίς αυτήν το AY κρατά τον τόνο ως το
    επόμενο χτύπημα και το μπάσο τύμπανο γίνεται συνεχές μπουρδόνι.
    """
    out, total = [], 0
    for bar in DRUM_BARS:
        assert len(bar) == 16, f"μέτρο με {len(bar)} θέσεις αντί για 16"
        for cell in bar:
            total += DRUM_STEP
            if cell == ".":
                out.append((0, 0, DRUM_STEP))
                continue
            voice, vol = DRUM_VOICE[cell]
            idx = voice if isinstance(voice, int) else table.index(voice) + 1
            out.append((idx, vol, DRUM_HIT))
            out.append((0, 0, DRUM_STEP - DRUM_HIT))
    return out, total


def note_table():
    """Ο ΕΝΑΣ πίνακας νοτών. Και το tools/test_z80.py τον παίρνει από εδώ:

    όταν μπήκε το μπάσο τύμπανο (C1, χαμηλότερο απ' όλα), όλοι οι δείκτες
    μετατοπίστηκαν κατά ένα και το τεστ σύγκρινε με δικό του αντίγραφο.
    """
    return collect(BASS, LEAD, PULSE, [(KICK, 0)])


def main():
    table = note_table()
    tracks = [("bass", BASS, VOL_BASS, 1, 0),
              ("lead", LEAD, VOL_LEAD, 2, 0),
              ("pulse", PULSE, VOL_PULSE, 4, NOISE_PULSE)]

    out = [";" + "=" * 69,
           ";  GRAVASSIST — μουσική μενού",
           ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genmusic.py — ΜΗΝ το επεξεργάζεσαι.",
           ";" + "=" * 69,
           "",
           f"; Κύκλος {LOOP} εκατοστά του δευτερολέπτου = {LOOP // 100} "
           "δευτερόλεπτα.",
           "; Και τα τρία κανάλια έχουν ΑΚΡΙΒΩΣ αυτό το μήκος, ώστε να",
           "; ξαναρχίζουν μαζί και ο κύκλος να μη «γλιστράει».",
           "",
           "; Περίοδοι τόνου του AY: period = 125000 / συχνότητα.",
           "note_tab:"]
    for name in table:
        out.append(f"                dw {period(name):5d}      ; {name}")

    for label, track, vol, chan, noise in tracks:
        data, total = stream(track, table, vol)
        assert total == LOOP, f"{label}: {total} αντί για {LOOP}"
        out += ["",
                f"; --- {label}: κανάλι {chan}"
                + (f", θόρυβος {noise}" if noise else ""),
                f"MUS_{label.upper()}_CH  equ {chan}",
                f"MUS_{label.upper()}_NZ  equ {noise}",
                f"mus_{label}:"]
        for note, v, dur in data:
            out.append(f"                db {note},{v},{dur}")
        out.append("                db #FF          ; τέλος: πίσω στην αρχή")

    # --- τα τύμπανα του παιχνιδιού -----------------------------------
    data, total = drum_stream(table)
    assert total == len(DRUM_BARS) * DRUM_BAR, total
    out += ["",
            f"; --- τύμπανα: κανάλι 4, {len(DRUM_BARS)} μέτρα, κύκλος "
            f"{total} εκατοστά",
            "; Μεταγραφή του musicsamples/8-bit-marching-drums_160bpm.wav.",
            f"MUS_NOISE     equ {MUS_NOISE}   ; δείκτης >= αυτό = κρουστό",
            "MUS_DRUMS_CH  equ 4",
            "MUS_DRUMS_NZ  equ 0",
            "mus_drums:"]
    for note, v, dur in data:
        out.append(f"                db {note},{v},{dur}")
    out.append("                db #FF          ; τέλος: πίσω στην αρχή")

    text = "\n".join(out) + "\n"
    path = os.path.join(ROOT, "src", "music.asm")
    with open(path, "w") as f:
        f.write(text)
    total = sum(len(stream(tr, table, v)[0]) * 3 + 1
                for _, tr, v, _, _ in tracks) + len(table) * 2
    print(f"  src/music.asm: {len(table)} νότες, κύκλος μενού {LOOP // 100}s, "
          f"τύμπανα {len(DRUM_BARS)} μέτρα")


if __name__ == "__main__":
    sys.exit(main())
