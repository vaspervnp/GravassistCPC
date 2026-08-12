#!/usr/bin/env python3
"""Μορφή αρχείου ΣΕΤ ΑΙΘΟΥΣΩΝ (ROOMSnn.BIN) — η ΜΙΑ πηγή αλήθειας.

Οι αίθουσες έφευγαν από το main.bin γιατί δεν χωρούσαν: 960 bytes ασυμπίεστο
πλέγμα η καθεμία σήμαινε ~10 αίθουσες συνολικά. Με RLE η ίδια αίθουσα πέφτει
στα ~200 bytes, οπότε ένα σετ 40 αιθουσών χωράει ολόκληρο στη μνήμη και τα
περάσματα από πόρτα σε πόρτα μέσα στο σετ δεν αγγίζουν καθόλου τον δίσκο.

ΔΟΜΗ ΑΡΧΕΙΟΥ (όλα little-endian, όπως ο Z80):

    +0    db  'G','R','S'      υπογραφή — ο φορτωτής αρνείται ό,τι άλλο
    +3    db  VERSION
    +4    db  count            πόσες αίθουσες έχει το σετ (1..SET_ROOMS)
    +5    db  numbers[SET_ROOMS]   ο αριθμός κάθε αίθουσας· 0 = κενή θέση
    +9    dw  offs[SET_ROOMS]      offset της εγγραφής από την ΑΡΧΗ του αρχείου
    +17   εγγραφές αιθουσών

(Οι θέσεις εξαρτώνται από το SET_ROOMS. Το HEADER τις υπολογίζει, και το
tools/genasm.py τα βγάζει ως SET_NUMBERS/SET_OFFS — μην τα γράψεις στο χέρι.)

ΕΓΓΡΑΦΗ ΑΙΘΟΥΣΑΣ:

    dw  start_x, start_y
    db  start_g
    (col,row,room,two)*   #FF      έξοδοι
    (origin,col,row,g)*   #FF      σημεία άφιξης
    (col,row,dcol,drow)*  #FF      τηλεμεταφορές
    (col,row,τιμή)*       #FF      ιδιότητες κελιών (κανάλι / ταυτότητα)
    RLE κελιά, μέχρι να βγουν COLS*ROWS:
        0ttttttt                   ΕΝΑ κελί τύπου t
        1ttttttt count             count κελιά τύπου t

Οι τρεις πίνακες τερματίζονται με #FF ακριβώς όπως πριν, ώστε οι βρόχοι
σάρωσης του src/hero.asm να δουλεύουν πάνω στο αρχείο χωρίς αντιγραφή.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P

MAGIC = b"GRS"
# 2 = RLE με σημαία στο bit 7 του τύπου (πριν: σκέτα ζεύγη πλήθος/τύπος).
# Ο φορτωτής του src/roomfile.asm ΤΗΝ ΕΛΕΓΧΕΙ: μια παλιά δισκέτα με σετ της
# έκδοσης 1 περνούσε την υπογραφή 'GRS' και ξεδιπλωνόταν σε σκουπίδια.
VERSION = 2
# ΑΙΘΟΥΣΕΣ ΑΝΑ ΑΡΧΕΙΟ — και το μέγεθος των πινάκων της κεφαλίδας.
#
# Ήταν 40, μετά 4, τώρα 2 — και ο λόγος είναι πάντα ο ίδιος: ο buffer του CPC
# ΜΙΚΡΑΙΝΕΙ σε κάθε γραμμή κώδικα που προστίθεται. Το σκορ πήρε ~430 bytes και
# ένα σετ των τεσσάρων (860 bytes) δεν χωρούσε πια σε buffer 747.
#
# Λιγότερες αίθουσες ανά σετ = μικρότερο σετ = μικρότερος buffer που αρκεί.
# Με ΜΙΑ, το σετ είναι μία αίθουσα συν 8 bytes κεφαλή και το μεγαλύτερο πέφτει
# κάτω από 360 bytes — αρκετό περιθώριο για τον πίνακα βαθμολογιών.
#
# ΕΙΝΑΙ ΤΟ ΤΕΛΕΥΤΑΙΟ ΞΥΡΙΣΜΑ ΠΟΥ ΥΠΑΡΧΕΙ. Το επόμενο feature που θέλει RAM
# πρέπει να λύσει το πραγματικό πρόβλημα: ο set_buf κρατά ΟΛΟΚΛΗΡΟ το σετ όσο
# παίζεις, ενώ το παιχνίδι διαβάζει μόνο τους τέσσερις μικρούς πίνακες της
# τρέχουσας αίθουσας. Αντιγράφοντας μόνο αυτούς ελευθερώνονται ~350 bytes.
#
# Το τίμημα είναι μία φόρτωση από δισκέτα ανά αίθουσα — αλλά ΜΟΝΟ σε
# μηχάνημα 64K: με τις τράπεζες όλα τα σετ είναι ήδη στη μνήμη και η πόρτα
# δεν αγγίζει τον δίσκο καθόλου (src/bank.asm).
SET_ROOMS = 1
HEADER = 3 + 1 + 1 + SET_ROOMS + 2 * SET_ROOMS          # = 8 με SET_ROOMS 1
CELLS = P.COLS * P.ROWS         # 960

# --- ΟΙ ΑΙΘΟΥΣΕΣ ΣΤΗ ΔΕΥΤΕΡΗ ΜΝΗΜΗ ΤΟΥ 6128 --------------------------
#
# Ο 6128 έχει δεύτερα 64 KB σε τέσσερα μπλοκ των 16 KB, που μπαίνουν ένα-ένα
# στο #4000..#7FFF (δες src/bank.asm). Εκεί χωράει ΟΛΟ το παιχνίδι: τα σετ
# αντιγράφονται μια φορά στην εκκίνηση και μετά η αλλαγή αίθουσας είναι ένα
# LDIR των 6 ms αντί για μισό δευτερόλεπτο διαβάσματος από δισκέτα.
#
# ΣΤΑΘΕΡΕΣ ΘΕΣΕΙΣ, όχι πίνακας offsets: ο Z80 βρίσκει το σετ με μια ολίσθηση
# αντί για αναζήτηση, και δεν χρειάζεται δεύτερος πίνακας που θα μπορούσε να
# ξεσυγχρονιστεί με τη δισκέτα. Το τίμημα είναι το κενό στο τέλος κάθε θέσης
# και ΕΝΑ ΣΚΛΗΡΟ ΟΡΙΟ: κανένα σετ δεν επιτρέπεται να ξεπεράσει το SLOT_SIZE.
BANK_SIZE = 0x4000
FIRST_BANK = 4                  # μπλοκ 4..7 = οργανώσεις #C4..#C7
BANK_COUNT = 4
SLOT_SIZE = 512
SLOTS_PER_BANK = BANK_SIZE // SLOT_SIZE         # 32
# ΤΟ ΟΝΟΜΑ ΑΡΧΕΙΟΥ ΕΙΝΑΙ ΤΟ ΣΤΕΝΟ ΣΗΜΕΙΟ, όχι οι τράπεζες: το AMSDOS δέχεται
# 8.3, οπότε το "ROOMSnn.BIN" χωράει δύο ψηφία και τελειώνει στο 99. Οι θέσεις
# στις τράπεζες είναι περισσότερες, αλλά ένα σετ που δεν μπορεί να γραφτεί στη
# δισκέτα δεν μπορεί ούτε να φορτωθεί στην τράπεζα — το γέμισμα περνά από εκεί.
MAX_SETS = min(SLOTS_PER_BANK * BANK_COUNT, 99)
BANK_WIN = 0x4000               # πού φαίνεται το μπλοκ στη μνήμη

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


RLE_RUN = 0x80          # bit 7 του τύπου: «ακολουθεί byte πλήθους»


def _runs(cells):
    """(τιμή, μήκος) για κάθε σειρά ίδιων κελιών. Χωρίς όριο στο μήκος."""
    prev, run = None, 0
    for v in cells:
        if v == prev:
            run += 1
            continue
        if prev is not None:
            yield prev, run
        prev, run = v, 1
    if prev is not None:
        yield prev, run


def rle_encode(cells):
    """ΕΝΑ byte για μεμονωμένο κελί, δύο για σειρά. Το bit 7 του τύπου λέει
    «ακολουθεί πλήθος».

    Τα σκέτα ζεύγη (πλήθος, τύπος) πλήρωναν 2 bytes ακόμα και για ΕΝΑ κελί,
    και οι πίστες είναι γεμάτες μεμονωμένα κελιά: στις έξι αίθουσες τα 320
    από τα 635 run είχαν μήκος 1, δηλαδή 640 bytes για 320 κελιά — το RLE
    δούλευε ανάποδα και τα φούσκωνε. Με τη σημαία το πλέγμα έπεσε από 1276
    σε 956 bytes χωρίς καμία απώλεια.

    Το bit είναι ελεύθερο επειδή οι τύποι φτάνουν ως 33 (P.NTYPES). Το assert
    το κρατά αληθινό: ο 128ός τύπος θα έσπαγε σιωπηλά κάθε πίστα.
    """
    assert P.NTYPES <= RLE_RUN, (
        f"{P.NTYPES} τύποι: το bit 7 δεν είναι πια ελεύθερο για τη σημαία RLE")
    out = bytearray()
    for value, run in _runs(cells):
        while run:
            # Το πλήθος είναι ένα byte, οπότε οι μεγάλες σειρές σπάνε στα 255.
            take = min(run, 255)
            if take == 1:
                out.append(value)
            else:
                out += bytes((value | RLE_RUN, take))
            run -= take
    return bytes(out)


def rle_decode(data, n=CELLS):
    """Αντίστροφο του rle_encode — η αναφορά για το rle_unpack του Z80."""
    out = bytearray()
    i = 0
    while len(out) < n:
        if i >= len(data):
            raise ValueError("τα δεδομένα RLE τελείωσαν πριν γεμίσει το πλέγμα")
        head = data[i]
        i += 1
        if head & RLE_RUN:
            if i >= len(data):
                raise ValueError("σειρά RLE χωρίς το byte του πλήθους της")
            value, count = head & (RLE_RUN - 1), data[i]
            i += 1
        else:
            value, count = head, 1
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
    """AMSDOS 8.3. Δύο ψηφία, άρα ως 99 σετ."""
    if not 1 <= index <= 99:
        raise ValueError(
            f"σετ {index}: το ROOMSnn.BIN χωράει δύο ψηφία (1..99)")
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


def slot_of(index):
    """(μπλοκ, διεύθυνση μέσα στο παράθυρο) για το σετ με δείκτη index (1..).

    Ο ΙΔΙΟΣ υπολογισμός ζει στον Z80 ως δύο ολισθήσεις — δες το set_load του
    src/roomfile.asm. Εδώ είναι η πηγή αλήθειας και το τεστ τον συγκρίνει.
    """
    i = index - 1
    if not 0 <= i < MAX_SETS:
        raise ValueError(
            f"σετ {index}: χωράνε {MAX_SETS} σετ στις τράπεζες "
            f"({MAX_SETS * SET_ROOMS} αίθουσες)")
    return (FIRST_BANK + i // SLOTS_PER_BANK,
            BANK_WIN + (i % SLOTS_PER_BANK) * SLOT_SIZE)


def check_buffer():
    """Ο buffer του CPC δεν επιτρέπεται να ΞΕΠΕΡΝΑ τη θέση τράπεζας.

    Το slot_copy φέρνει set_capacity bytes από την αρχή της θέσης. Μικρότερος
    buffer είναι μια χαρά — απλώς αγνοεί το γέμισμα. ΜΕΓΑΛΥΤΕΡΟΣ όμως θα
    διάβαζε μέσα στην επόμενη θέση, και στην τελευταία, έξω από την τράπεζα.

    Ο έλεγχος είναι ΕΔΩ και όχι σε assert του assembler: το rasm αποτιμά τα
    assert σε πρώιμο πέρασμα, όπου το set_buf δεν έχει την τελική του θέση.
    """
    if SET_MAX > SLOT_SIZE:
        raise ValueError(
            f"ο buffer του CPC είναι {SET_MAX} bytes και η θέση τράπεζας "
            f"{SLOT_SIZE}. Το slot_copy θα διάβαζε μέσα στην επόμενη θέση — "
            f"μεγάλωσε το SLOT_SIZE.")


def check_slots():
    """Κάθε σετ πρέπει να χωράει στη θέση του μέσα στην τράπεζα.

    ΑΥΣΤΗΡΟΤΕΡΟ από τον buffer του CPC: ο buffer έχει σήμερα 1297 bytes, η
    θέση 1024. Ο έλεγχος γίνεται εδώ ώστε να σπάσει το build και όχι η
    δισκέτα — ένα σετ που ξεχειλίζει θα πατούσε πάνω στο επόμενο.
    """
    for index, _, data in all_sets():
        if len(data) > SLOT_SIZE:
            raise ValueError(
                f"το σετ {index} θέλει {len(data)} bytes και η θέση στην "
                f"τράπεζα είναι {SLOT_SIZE}. Λιγότερες ή πιο αραιές αίθουσες "
                f"ανά σετ (SET_ROOMS = {SET_ROOMS}).")
        slot_of(index)          # και μέσα στα 64 σετ που υπάρχουν


def set_count():
    """Ο ΜΕΓΑΛΥΤΕΡΟΣ δείκτης σετ που υπάρχει — όσο ψάχνει ο Z80 στην εκκίνηση.

    Όχι το πλήθος: αν οι αίθουσες έχουν κενά (1..4 και 9..12), τα σετ είναι
    το 1 και το 3, και ο βρόχος πρέπει να φτάσει ως το 3.

    ΧΩΡΙΣ να χτιστεί κανένα σετ: το genasm.py καλεί αυτή τη συνάρτηση για να
    γράψει το gamedefs.asm, και το gamedefs.asm καθορίζει πόση μνήμη μένει για
    τον buffer. Αν εδώ τρέχαμε το build_set, ένα σετ που δεν χωράει θα εμπόδιζε
    να παραχθεί το ίδιο το αρχείο που θα του έδινε τον χώρο.
    """
    return max((set_of(r.number) for r in P.all_rooms()), default=0)


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
        # ΠΡΟΕΙΔΟΠΟΙΗΣΗ ΠΡΙΝ ΤΟ ΟΡΙΟ, όχι μετά: όταν ξεπεραστεί, το build
        # σταματά και δεν έχεις δισκέτα καθόλου. Καλύτερα να το δεις όσο
        # έχεις ακόμα περιθώριο να αραιώσεις ή να χωρίσεις τις αίθουσες.
        if pct >= 85:
            print(f"  ΠΡΟΣΟΧΗ: μένουν μόνο {SET_MAX - len(data)} bytes στο "
                  f"{name}. Άλλη μία αίθουσα ίσως δεν χωρέσει.")

    # Οι τράπεζες δεν παίρνουν δικά τους αρχεία: ο Z80 γεμίζει τις θέσεις
    # στην εκκίνηση από ΑΥΤΑ τα ίδια ROOMSnn.BIN. Εδώ ελέγχεται μόνο ότι
    # χωράνε — και το build σπάει αν δεν χωράνε.
    check_buffer()
    check_slots()
    for index, name, data in all_sets():
        bank, addr = slot_of(index)
        print(f"  {name} -> τράπεζα: μπλοκ {bank} @ #{addr:04X}, "
              f"{SLOT_SIZE - len(data)} bytes ελεύθερα στη θέση")
