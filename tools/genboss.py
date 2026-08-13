#!/usr/bin/env python3
"""The Boss Time theme -> the game's music and the standalone MUSIC.BIN.

WHERE IT CAME FROM: transcribed from musicsamples/1min_Boss_Time.mp3 (and its
15 second edit, which is the same recording) with an FFT analysis — chromagram
for the key, spectral flux plus autocorrelation for the tempo, harmonic product
spectrum for pitch, per-band onsets and a bar-to-bar chroma self-similarity for
the structure. The numbers below are the OUTPUT of that analysis, pasted here on
purpose: the mp3 is in musicsamples/ but re-running the transcription would make
numpy and ffmpeg build dependencies, and would let a library upgrade silently
rewrite the music.

WHAT THE ANALYSIS ESTABLISHED, and how much of it to believe:

  TEMPO  128.4 BPM. The first pass reported 64.2 and that was half time; the
         onset grid only makes sense at double. We play at 125 so a sixteenth
         is exactly 12 hundredths of a second and the three channels stay in
         step — a 3% drift is inaudible, three channels sliding apart is not.

  KEY    C# minor, with a chromatic C natural. The bass chroma reads C
         strongest, which looks wrong until you notice the riff is a descending
         C#-C-B: the C is a passing tone and it is all over the piece.

  FORM   32 bars, three sections, from bar-to-bar chroma similarity (1.00
         inside a section, 0.94-0.97 across a boundary):
           A  bars 0-7    the material of the 15 second edit, twice
           B  bars 8-23   lead climbs C#4-D#4-E4-C#5; two-bar alternation
           C  bars 24-31  lead sits on G#4 against B4, and winds down
         That is the skeleton below. 32 bars x 16 x 12 = 61.4 seconds.

  BASS   transcribed for section A — a coherent C# minor riff that the pitch
         tracker resolved cleanly. For B and C the tracker gave pitch classes
         per bar but not a line, so those two are WRITTEN to the harmony it
         reported (B alternates a D-ish and a C-ish bar; C returns to A's) in
         the same idiom as A. Honest label: arranged, not transcribed.

  LEAD   the motifs are real — C#4/B4 in A, C#4-D#4-E4-C#5 in B, G#4/B4 in C
         all came out of the harmonic product spectrum and survive in the
         per-bar chroma. The passing notes between them are arranged.

  DRUMS  NOT transcribed. Per-band onset detection found the hits but no
         repeating bar — a real recording with fills, and the per-position
         energy is nearly flat, which means "busy" and nothing more. These are
         hand-written backbeats, one per section, getting busier through B and
         thinning out at the end of C.

TWO OUTPUTS, ONE ARRANGEMENT:
  src/music_boss.asm  the whole thing as assembly, for the standalone MUSIC.BIN
  src/tune.asm + build/TUNEnn.BIN
                      for the game: the note table stays in main memory (it is
                      forty bytes and needed on every note) and the streams go
                      to the disc, to be loaded into an upper RAM bank at boot.
                      The game has 105 bytes of main memory free; five kilobytes
                      of music could never have lived there.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import genmusic as GM

STEP = 12                       # one sixteenth, in hundredths of a second
BAR = 16 * STEP
R = None

# --- section A: bars 0-7 --------------------------------------------------
# Four bars, played twice. This is the 15 second edit, unchanged: it is the
# part that was listened to and approved, so it is the part not to touch.
BASS_A = [
    ("C#2", 2), ("C2", 1), ("B1", 2), ("C#2", 1), ("C2", 1), ("B1", 1),
    ("E3", 1), ("E2", 1), ("C#2", 2), ("G#2", 2), ("C#2", 4), ("C2", 1),
    ("B1", 1), ("C#2", 1), ("C2", 1), ("A#1", 1), ("B1", 1), ("F#2", 1),
    ("A1", 1), ("E2", 1), ("B1", 2), ("C#2", 4), ("C2", 1), ("B1", 2),
    ("C#2", 1), ("C2", 1), ("B1", 1), ("E3", 1), ("E2", 1), ("C#2", 2),
    ("G#2", 1), ("C#3", 1), ("C#2", 5), ("B1", 1), ("C#2", 1), ("C2", 1),
    ("B1", 2), ("F#2", 1), ("E2", 2), ("B1", 2), ("C#2", 4),
]

LEAD_A = [
    ("C#4", 4), ("B4", 1), ("C#4", 2), ("B4", 1), ("E4", 2), ("C#4", 2),
    ("G#4", 1), ("C#4", 6), ("B4", 1), ("C#4", 3), ("B4", 1), ("F#4", 1),
    ("E4", 2), ("B4", 2), ("C#4", 6), ("B4", 1), ("C#4", 2), ("B4", 1),
    ("E4", 2), ("C#4", 2), ("G#4", 1), ("C#4", 6), ("B4", 1), ("C#4", 2),
    ("B4", 1), ("F#4", 2), ("E4", 2), ("B4", 2), ("C#4", 4),
]

DRUMS_A = [
    "K..kS...K..kS...",
    "K..kS...K..kS.k.",
    "K..kS...K..kS...",
    "K..kS..kK.kkS.SS",
]

# --- section B: bars 8-23 -------------------------------------------------
# Four bars, played four times. The lead is the climbing figure the tracker
# resolved; the bass alternates the two harmonies the per-bar chroma reported.
BASS_B = [
    ("C#2", 1), ("C#2", 1), ("C2", 1), ("B1", 1), ("C#2", 2), ("E2", 1),
    ("C#2", 1), ("B1", 2), ("C#2", 2), ("G#2", 2), ("C#2", 2),

    ("C2", 1), ("C2", 1), ("B1", 1), ("A#1", 1), ("B1", 2), ("D#2", 1),
    ("B1", 1), ("A1", 2), ("B1", 2), ("F#2", 2), ("B1", 2),

    ("C#2", 1), ("C#2", 1), ("C2", 1), ("B1", 1), ("C#2", 2), ("E2", 1),
    ("C#2", 1), ("B1", 2), ("C#2", 2), ("G#2", 2), ("C#2", 2),

    ("C#2", 1), ("C2", 1), ("B1", 1), ("A#1", 1), ("A1", 2), ("G#1", 2),
    ("E2", 2), ("G#2", 2), ("C#3", 2), ("C#2", 2),
]

LEAD_B = [
    ("C#4", 1), ("D#4", 2), ("E4", 1), ("C#5", 3), (R, 2), ("C#4", 1), (R, 6),
    ("C#4", 1), ("D#4", 2), ("E4", 1), ("C#5", 2), (R, 2), ("C#4", 1),
    ("G#4", 1), (R, 6),
    ("C#4", 1), ("D#4", 2), ("E4", 1), ("C#5", 3), (R, 1), ("B4", 1),
    ("C#5", 1), (R, 6),
    ("C#4", 1), ("D#4", 1), ("E4", 2), ("G#4", 2), ("C#5", 4), ("B4", 2),
    ("C#5", 4),
]

DRUMS_B = [
    "K..kS.k.K..kS.k.",
    "K..kS.k.K.kkS.k.",
    "K..kS.k.K..kS.k.",
    "K.kkS.k.K.kkS.SS",
]

# --- section C: bars 24-31 ------------------------------------------------
# Four bars, played twice. G#4 against B4, then the descent that ends it.
BASS_C = [
    ("C#2", 2), ("C2", 1), ("B1", 1), ("C#2", 2), ("G#2", 2), ("C#2", 4),
    ("G#1", 4),
    ("C#2", 2), ("C2", 1), ("B1", 1), ("C#2", 2), ("E2", 2), ("C#2", 4),
    ("B1", 4),
    ("C#2", 2), ("C2", 1), ("B1", 1), ("A1", 2), ("G#1", 2), ("C#2", 4),
    ("E2", 4),
    ("C#2", 4), ("G#1", 4), ("C#2", 8),
]

LEAD_C = [
    ("G#4", 4), (R, 2), ("G#4", 2), ("B4", 2), ("G#4", 6),
    ("G#4", 2), (R, 1), ("G#4", 1), ("D#4", 2), ("B4", 2), ("G#4", 8),
    ("G#4", 3), (R, 1), ("G#4", 2), ("B4", 2), ("G#4", 4), ("D#4", 4),
    ("D#4", 2), ("E4", 2), ("C#4", 4), ("B4", 2), ("C#4", 6),
]

DRUMS_C = [
    "K...S...K...S...",
    "K...S...K...S.k.",
    "K...S...K...S...",
    "K...S..kK.kkSSSS",
]

# How the sections are laid out end to end: (name, bass, lead, drums, repeats).
FORM = [
    ("A", BASS_A, LEAD_A, DRUMS_A, 2),
    ("B", BASS_B, LEAD_B, DRUMS_B, 4),
    ("C", BASS_C, LEAD_C, DRUMS_C, 2),
]
BARS_PER_SECTION = 4

VOL_BASS, VOL_LEAD = 13, 10
DRUM_HIT = 3                    # how long a drum crack lasts
DRUM_VOICE = {"K": (GM.KICK, 13), "k": (GM.KICK, 8),
              "S": (GM.SNARE, 12), "s": (GM.SNARE_S, 8)}

# The bank is 16 KB and the streams are about five, so nothing here is squeezed
# for space. Chunks exist only because the loader stages them through set_buf.
CHUNK = 1536


def collect():
    """Every distinct pitch, low to high — the note table for this piece."""
    names = set()
    for _, bass, lead, _, _ in FORM:
        names |= {n for n, _ in bass + lead if n is not None}
    names.add(GM.KICK)
    return sorted(names, key=GM.midi)


def stream(track, table, volume):
    """Note triples, with a short silence at the end of each note.

    Without the gap two equal notes in a row merge into one long drone and the
    riff loses its shape — the same reason genmusic.stream does it. It costs
    an entry per note and it is what the approved arrangement sounds like, so
    it stays even though the piece is now eight times longer.
    """
    out, total = [], 0
    for name, steps in track:
        dur = steps * STEP
        total += dur
        if name is None:
            out.append((0, 0, dur))
            continue
        gap = max(2, dur // 8)
        out.append((table.index(name) + 1, volume, dur - gap))
        out.append((0, 0, gap))
    return out, total


def drums(bars, table):
    out, total = [], 0

    def rest(n):
        if out and out[-1][0] == 0 and out[-1][2] + n <= 200:
            v, vol, d = out[-1]
            out[-1] = (v, vol, d + n)
        else:
            out.append((0, 0, n))

    for bar in bars:
        assert len(bar) == 16, bar
        for cell in bar:
            total += STEP
            if cell == ".":
                rest(STEP)
                continue
            voice, vol = DRUM_VOICE[cell]
            idx = voice if isinstance(voice, int) else table.index(voice) + 1
            out.append((idx, vol, DRUM_HIT))
            rest(STEP - DRUM_HIT)
    return out, total


def build():
    """The three channels of the whole piece, end to end."""
    table = collect()
    tracks = {"bass": [], "lead": [], "drums": []}
    bars = 0
    for name, bass, lead, drum, times in FORM:
        parts = (("bass", stream(bass, table, VOL_BASS)),
                 ("lead", stream(lead, table, VOL_LEAD)),
                 ("drums", drums(drum, table)))
        for label, (notes, total) in parts:
            want = BARS_PER_SECTION * BAR
            if total != want:
                raise SystemExit(
                    f"section {name}, {label}: {total} hundredths instead of "
                    f"{want} — the three channels would drift apart")
            tracks[label] += notes * times
        bars += BARS_PER_SECTION * times
    return table, tracks, bars


def check_indices(table, tracks):
    """No note index may fall outside the table unless it is a noise voice.

    THE BUG THIS EXISTS FOR: the drum voices are borrowed from genmusic, where
    an index at or above MUS_NOISE means percussion. A player that does not
    implement that convention treats 206 as a table position, overflows eight
    bits doubling it, and reads garbage as a tone period — continuous noise,
    with nothing in the data to suggest anything is wrong.
    """
    # The player doubles the index to reach a word in the table. Past 127 that
    # doubling overflows eight bits — the same failure, one table away.
    if len(table) > 127:
        raise SystemExit(f"note table has {len(table)} entries; the player's "
                         "`add a,a` overflows above 127")
    for label, notes in tracks.items():
        for idx, _, _ in notes:
            if idx == 0 or idx <= len(table):
                continue
            if idx >= GM.MUS_NOISE:
                continue
            raise SystemExit(
                f"{label}: note index {idx} is outside the {len(table)} entry "
                f"table and below MUS_NOISE ({GM.MUS_NOISE})")


def blob(tracks):
    """The three streams end to end, plus where each one starts."""
    order = ("bass", "lead", "drums")
    data, where = bytearray(), {}
    for label in order:
        where[label] = (len(data), len(tracks[label]) * 3)
        for note, vol, dur in tracks[label]:
            data += bytes((note, vol, dur))
    return bytes(data), where


def write_asm(root, table, tracks, bars):
    """src/music_boss.asm — the whole arrangement, for the standalone player."""
    out = [";" + "=" * 69,
           ";  GRAVASSIST - Boss Time, the full minute",
           ";  GENERATED by tools/genboss.py - do not edit.",
           ";",
           f";  {bars} bars at 125 BPM = {bars * BAR / 100:.1f} seconds, three",
           ";  channels in step. Sections A(8) B(16) C(8), see the tool's",
           ";  header for what is transcribed and what is arranged.",
           ";" + "=" * 69,
           "",
           "; AY tone periods: period = 125000 / frequency.",
           "boss_notes:"]
    for name in table:
        out.append(f"                dw {GM.period(name):5d}      ; {name}")
    out += ["",
            f"BOSS_TRACKS     equ 3",
            "; At or above this, a note index is percussion and the remainder",
            "; is the AY noise period. The player MUST branch on it.",
            f"BOSS_NOISE      equ {GM.MUS_NOISE}"]
    for label in ("bass", "lead", "drums"):
        notes = tracks[label]
        out += ["", f"; --- {label}: {len(notes)} entries", f"boss_{label}:"]
        for note, vol, dur in notes:
            out.append(f"                db {note},{vol},{dur}")
        out.append(f"boss_{label}_end:")
    out += ["",
            "; Where each track sits and how long it is. The player streams",
            "; them out of the bank, so it needs both.",
            "boss_tab:"]
    for label in ("bass", "lead", "drums"):
        out.append(f"                dw boss_{label}, "
                   f"boss_{label}_end-boss_{label}")
    out.append("")
    path = os.path.join(root, "src", "music_boss.asm")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return path


def set_capacity(root):
    """Πόσο είναι ο set_buf, από τον ΙΔΙΟ τον κώδικα και όχι από μνήμης."""
    path = os.path.join(root, "src", "main.asm")
    try:
        with open(path) as f:
            m = re.search(r"^set_capacity\s+equ\s+(\d+)", f.read(), re.M)
    except OSError:
        return None
    return int(m.group(1)) if m else None


def write_game(root, table, where, data, bars):
    """src/tune.asm + build/TUNEnn.BIN — the game's copy.

    The split is the whole point: the note table is small and hot, so it stays
    in main memory; the streams are five kilobytes and cold, so they go to the
    disc and from there into an upper bank the game never has to make room for.
    """
    # Το tune_boot περνά κάθε κομμάτι μέσα από τον set_buf. Αν το CHUNK το
    # ξεπεράσει, το CAS_IN_DIRECT γράφει πέρα από τον buffer — πάνω στον
    # cas_buffer και μετά έξω από τη μνήμη του παιχνιδιού.
    cap = set_capacity(root)
    if cap is not None and CHUNK > cap:
        raise SystemExit(f"CHUNK={CHUNK} > set_capacity={cap}: το tune_boot θα "
                         f"γράψει έξω από τον set_buf")
    chunks = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
    out = [";" + "=" * 69,
           ";  GRAVASSIST - the tune's note table and its shape in the bank",
           ";  GENERATED by tools/genboss.py - do not edit.",
           ";",
           ";  The notes themselves are NOT here: they are in build/TUNEnn.BIN",
           ";  on the disc, loaded into RAM bank block " + str(7) + " at boot.",
           ";  Only what the player needs on every single note lives in main",
           ";  memory, because main memory is what there is none of.",
           ";" + "=" * 69,
           "",
           f"TUNE_BARS       equ {bars}",
           # ΟΧΙ "TUNE_NOTES": το rasm δεν ξεχωρίζει πεζά από κεφαλαία και
           # το όνομα θα χτυπούσε με το label tune_notes δύο γραμμές πιο κάτω.
           f"TUNE_NCOUNT     equ {len(table)}",
           "TUNE_NOISE      equ %d      ; index >= this is percussion"
           % GM.MUS_NOISE,
           f"TUNE_BYTES      equ {len(data)}",
           "; Το μήκος του κομματιού σε παλμούς του ρολογιού του firmware",
           "; (1/300 s). Ο player κρατά τη θέση του lead σε αυτές τις μονάδες",
           "; και τυλίγει και τις δύο εδώ, ώστε η αφαίρεση να μένει στα 16 bit.",
           f"TUNE_TICKS      equ {bars * BAR * 3}",
           f"TUNE_CHUNK      equ {CHUNK}",
           f"TUNE_CHUNKS     equ {len(chunks)}",
           "",
           "; Offset and length of each track inside the blob, which the boot",
           "; code lays down at the start of the block.",
           ]
    for label in ("bass", "lead", "drums"):
        off, ln = where[label]
        out.append(f"TUNE_{label.upper()}_OFF equ {off}")
        out.append(f"TUNE_{label.upper()}_LEN equ {ln}")
    out += ["",
            "; AY tone periods: period = 125000 / frequency.",
            "tune_notes:"]
    for name in table:
        out.append(f"                dw {GM.period(name):5d}      ; {name}")
    out.append("")
    path = os.path.join(root, "src", "tune.asm")
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")

    build = os.path.join(root, "build")
    os.makedirs(build, exist_ok=True)
    # ΤΟ ΜΗΚΟΣ ΗΤΑΝ 12 ΚΑΙ ΤΟ ΟΝΟΜΑ ΕΙΝΑΙ 10: "TUNE01.BIN". Ο έλεγχος δεν
    # ταίριαζε ΠΟΤΕ, οπότε ένα TUNE04.BIN από παλιότερο, μεγαλύτερο κομμάτι θα
    # έμενε στο build/ και θα έφευγε στη δισκέτα — και το tune_boot θα το
    # φόρτωνε σαν να ανήκε στο σημερινό. Regex αντί για μέτρημα χαρακτήρων.
    for old in sorted(os.listdir(build)):
        if re.fullmatch(r"TUNE\d\d\.BIN", old):
            os.remove(os.path.join(build, old))
    names = []
    for i, chunk in enumerate(chunks, 1):
        name = f"TUNE{i:02d}.BIN"
        with open(os.path.join(build, name), "wb") as f:
            f.write(chunk)
        names.append(name)
    return path, names, chunks


def main():
    table, tracks, bars = build()
    check_indices(table, tracks)
    data, where = blob(tracks)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    write_asm(root, table, tracks, bars)
    _, names, chunks = write_game(root, table, where, data, bars)

    entries = sum(len(v) for v in tracks.values())
    print(f"  Boss Time: {bars} bars, {bars * BAR / 100:.1f} s, "
          f"{len(table)} notes, {entries} entries")
    print(f"  src/music_boss.asm: {len(data) + len(table) * 2} bytes "
          f"(standalone MUSIC.BIN)")
    print(f"  src/tune.asm: {len(table) * 2} bytes in main memory")
    print(f"  {len(names)} x TUNE.BIN: {len(data)} bytes to the bank "
          f"({', '.join(str(len(c)) for c in chunks)})")


if __name__ == "__main__":
    sys.exit(main())
