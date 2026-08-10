#!/usr/bin/env python3
"""Μορφή αρχείου ΣΕΤ ΑΙΘΟΥΣΩΝ (ROOMSnn.BIN) — η ΜΙΑ πηγή αλήθειας.

Οι αίθουσες έφευγαν από το main.bin γιατί δεν χωρούσαν: 960 bytes ασυμπίεστο
πλέγμα η καθεμία σήμαινε ~10 αίθουσες συνολικά. Με RLE η ίδια αίθουσα πέφτει
στα ~200 bytes, οπότε ένα σετ 40 αιθουσών χωράει ολόκληρο στη μνήμη και τα
περάσματα από πόρτα σε πόρτα μέσα στο σετ δεν αγγίζουν καθόλου τον δίσκο.

ΔΟΜΗ ΑΡΧΕΙΟΥ (όλα little-endian, όπως ο Z80):

    +0    db  'G','R','S'      υπογραφή — ο φορτωτής αρνείται ό,τι άλλο
    +3    db  VERSION
    +4    db  count            πόσες αίθουσες έχει το σετ (1..40)
    +5    db  numbers[40]      ο αριθμός κάθε αίθουσας· 0 = κενή θέση
    +45   dw  offs[40]         offset της εγγραφής από την ΑΡΧΗ του αρχείου
    +125  εγγραφές αιθουσών

ΕΓΓΡΑΦΗ ΑΙΘΟΥΣΑΣ:

    dw  start_x, start_y
    db  start_g
    (col,row,room,two)*   #FF      έξοδοι
    (origin,col,row,g)*   #FF      σημεία άφιξης
    (col,row,dcol,drow)*  #FF      τηλεμεταφορές
    (col,row,τιμή)*       #FF      ιδιότητες κελιών (κανάλι / ταυτότητα)
    (count,type)*                  RLE κελιά, μέχρι να βγουν COLS*ROWS

Οι τρεις πίνακες τερματίζονται με #FF ακριβώς όπως πριν, ώστε οι βρόχοι
σάρωσης του src/hero.asm να δουλεύουν πάνω στο αρχείο χωρίς αντιγραφή.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

MAGIC = b"GRS"
VERSION = 1
SET_ROOMS = 40                  # αίθουσες ανά αρχείο — και το μέγεθος των πινάκων
HEADER = 3 + 1 + 1 + SET_ROOMS + 2 * SET_ROOMS          # = 125
CELLS = P.COLS * P.ROWS         # 960

# Πόσα bytes χωράει ένα σετ στη μνήμη του CPC. Ο έλεγχος γίνεται ΕΔΩ και όχι
# στον Z80: καλύτερα να σπάσει το build παρά η δισκέτα.
#
# Το νούμερο δεν είναι αυθαίρετο — είναι ό,τι περισσεύει κάτω από το #A67B
# (ταβάνι με ενεργό AMSDOS) αφού πάρουν το μερίδιό τους ο κώδικας, το
# ξεδιπλωμένο πλέγμα και το ημερολόγιο αλλαγών. Το src/main.asm το επιβάλλει
# με assert, οπότε τα δύο δεν μπορούν να ξεσυγχρονιστούν σιωπηλά.
# Χωράνε 40 αραιές αίθουσες ή περίπου 27 πυκνές σαν τη room_1 ΑΝΑ ΣΕΤ· τα
# σετ όμως είναι όσα θες, οπότε το σύνολο των αιθουσών δεν έχει όριο.
def set_capacity():
    """Πόσα bytes περισσεύουν στην πράξη για ένα σετ.

    ΔΕΝ είναι σταθερά: το σύμβολο βγαίνει από τον assembler (MEM_CEIL μείον
    την αρχή του set_buf), οπότε κάθε γραμμή κώδικα που προσθέτουμε μικραίνει
    αυτόματα τη χωρητικότητα σε αίθουσες. Ένα χειρόγραφο νούμερο εδώ σήμαινε
    ότι το build έσπαγε σε κάθε αλλαγή και ζητούσε ξανασυντονισμό.

    Αν δεν υπάρχει ακόμα πίνακας συμβόλων (πρώτο build), πέφτουμε σε μια
    συντηρητική τιμή — ο assembler θα πει την αλήθεια στο επόμενο πέρασμα.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "build", "symbols.txt")
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r"SET_CAPACITY\s+#([0-9A-F]+)", line, re.I)
                if m:
                    return int(m.group(1), 16)
    except OSError:
        pass
    return 4096


SET_MAX = set_capacity()


def rle_encode(cells):
    """Ζεύγη (πλήθος, τύπος). Το πλήθος χωράει σε ένα byte, άρα σπάει στα 255."""
    out = bytearray()
    run, prev = 0, None
    for v in cells:
        if v == prev and run < 255:
            run += 1
            continue
        if prev is not None:
            out += bytes((run, prev))
        prev, run = v, 1
    if prev is not None:
        out += bytes((run, prev))
    return bytes(out)


def rle_decode(data, n=CELLS):
    """Αντίστροφο του rle_encode — η αναφορά για το rle_unpack του Z80."""
    out = bytearray()
    i = 0
    while len(out) < n:
        if i + 1 >= len(data) + 1:
            raise ValueError("τα δεδομένα RLE τελείωσαν πριν γεμίσει το πλέγμα")
        count, value = data[i], data[i + 1]
        i += 2
        out += bytes([value]) * count
    if len(out) != n:
        raise ValueError(f"RLE έβγαλε {len(out)} κελιά αντί για {n}")
    return bytes(out)


def room_record(room):
    """Τα bytes μιας αίθουσας, ακριβώς όπως τα διαβάζει το src/roomfile.asm."""
    out = bytearray()
    out += room.start_x.to_bytes(2, "little")
    out += room.start_y.to_bytes(2, "little")
    out.append(room.start_g)

    for (c, r), dest, two, cells in room.exit_groups():
        for cc, cr in cells:
            out += bytes((cc, cr, dest, 1 if two else 0))
    out.append(0xFF)

    for other in P.all_rooms():
        a = room.arrival_for(other.number)
        if a:
            out += bytes((other.number, a[0], a[1], a[2]))
    out.append(0xFF)

    for (c, r), dest, cells in room.teleport_groups():
        if dest is None:
            continue                    # αδήλωτη: δεν κάνει τίποτα στο παιχνίδι
        for cc, cr in cells:
            out += bytes((cc, cr, dest[0], dest[1]))
    out.append(0xFF)

    # Ιδιότητες κελιών: κανάλι για διακόπτες/πόρτες, ταυτότητα για
    # κλειδιά/κλειδαριές. Μόνο οι μη μηδενικές — το 0 είναι η προεπιλογή και
    # δεν χρειάζεται να ταξιδεύει.
    for (cc, cr), v in sorted(room.attrs.items()):
        if v:
            out += bytes((cc, cr, v))
    out.append(0xFF)

    flat = [v for row in room.cells for v in row]
    packed = rle_encode(flat)
    assert rle_decode(packed) == bytes(flat), "το RLE δεν κάνει round-trip"
    out += packed
    return bytes(out)


def set_of(room_number):
    """Σε ποιο αρχείο ζει η αίθουσα. Υπολογίσιμο ΧΩΡΙΣ να διαβαστεί αρχείο —
    ο Z80 πρέπει να ξέρει ποιο σετ να ζητήσει πριν έχει οτιδήποτε στη μνήμη."""
    return (room_number - 1) // SET_ROOMS + 1


def set_name(index):
    """AMSDOS 8.3. Δύο ψηφία -> ως 99 σετ -> 3960 αίθουσες."""
    return f"ROOMS{index:02d}.BIN"


def build_set(rooms):
    """Το πλήρες αρχείο ενός σετ."""
    if len(rooms) > SET_ROOMS:
        raise ValueError(f"{len(rooms)} αίθουσες σε σετ των {SET_ROOMS}")

    records = [room_record(r) for r in rooms]
    numbers = bytearray(SET_ROOMS)
    offs = [0] * SET_ROOMS
    pos = HEADER
    for i, (r, rec) in enumerate(zip(rooms, records)):
        numbers[i] = r.number
        offs[i] = pos
        pos += len(rec)

    out = bytearray()
    out += MAGIC
    out.append(VERSION)
    out.append(len(rooms))
    out += numbers
    for o in offs:
        out += o.to_bytes(2, "little")
    assert len(out) == HEADER, f"κεφαλή {len(out)} αντί για {HEADER}"
    for rec in records:
        out += rec

    if len(out) > SET_MAX:
        raise ValueError(
            f"το σετ θέλει {len(out)} bytes και ο buffer του CPC είναι "
            f"{SET_MAX}. Λιγότερες ή πιο αραιές αίθουσες.")
    return bytes(out)


def all_sets():
    """[(index, όνομα, bytes)] για κάθε σετ που προκύπτει από το levels/."""
    rooms = P.all_rooms()
    groups = {}
    for r in rooms:
        groups.setdefault(set_of(r.number), []).append(r)
    return [(i, set_name(i), build_set(sorted(g, key=lambda r: r.number)))
            for i, g in sorted(groups.items())]


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build = os.path.join(root, "build")
    os.makedirs(build, exist_ok=True)
    for index, name, data in all_sets():
        with open(os.path.join(build, name), "wb") as f:
            f.write(data)
        pct = 100 * len(data) // SET_MAX
        print(f"  build/{name}: {len(data)} bytes ({pct}% του buffer {SET_MAX})")
