#!/usr/bin/env python3
"""Ελέγχει ότι η δισκέτα έχει ΟΝΤΩΣ ό,τι χρειάζεται το παιχνίδι.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: μια δισκέτα χωρίς αίθουσες χτίζεται μια χαρά και αποτυγχάνει
αργότερα, στον emulator, με «ROOMS01.BIN not found» — μακριά από την αιτία.
Ο έλεγχος γίνεται στο ΤΕΛΟΣ του build, όπου η αιτία είναι ακόμα μπροστά σου.

Διαβάζει τον κατάλογο του .dsk κατευθείαν (μορφή Extended/Standard CPC), χωρίς
να εξαρτάται από την έξοδο του iDSK.
"""

import os
import sys

NEEDED = ["MAIN    BIN", "GRAV    BAS"]     # 8+3, με κενά
NEED_PREFIX = "ROOMS"                       # τουλάχιστον ένα ROOMSnn.BIN
# Η ΜΟΥΣΙΚΗ ΕΙΝΑΙ ΚΙ ΑΥΤΗ ΑΡΧΕΙΑ ΣΤΗ ΔΙΣΚΕΤΑ. Λείπουν σιωπηλά: το tune_boot
# απλώς δεν βρίσκει τα TUNEnn.BIN, αφήνει tune_ok=0 και το παιχνίδι παίζει
# ΧΩΡΙΣ ΗΧΟ — χωρίς μήνυμα, χωρίς κρασάρισμα, χωρίς τρόπο να καταλάβεις γιατί.
# Πόσα πρέπει να είναι το ξέρει η γεννήτρια, οπότε τη ρωτάμε.
TUNE_PREFIX = "TUNE"


def tune_count():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import genboss
        _, tracks, _ = genboss.build()
        data, _ = genboss.blob(tracks)
        return -(-len(data) // genboss.CHUNK)
    except Exception:
        return None


def check_sets(dsk, names):
    """Ότι τα σετ αιθουσών είναι ΔΙΑΒΑΣΙΜΑ, όχι απλώς παρόντα.

    ΓΙΑΤΙ ΔΕΝ ΦΤΑΝΕΙ ΤΟ ΟΝΟΜΑ ΣΤΟΝ ΚΑΤΑΛΟΓΟ: το ROOMSnn.BIN έχει πέντε πίνακες
    πριν από τα συμπιεσμένα κελιά, και ο τελευταίος (οι χρόνοι των πυργίσκων)
    μπήκε τελευταίος. Ένα σετ γραμμένο με άλλη μορφή από αυτήν που περιμένει ο
    src/roomfile.asm περνάει κάθε έλεγχο ονόματος και ξεδιπλώνεται σε σκουπίδια
    στην οθόνη του Amstrad.

    Ελέγχονται τα build/ROOMSnn.BIN — τα ΙΔΙΑ bytes που έβαλε το iDSK μέσα — και
    ξεχωριστά ότι το μέγεθός τους ταιριάζει με ό,τι λέει ο κατάλογος της
    δισκέτας. Έτσι το ξεδίπλωμα αφορά όντως το αρχείο που ταξιδεύει.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import roomfile

    problems = []
    folder = os.path.dirname(os.path.abspath(dsk))
    for name, records in sorted(names.items()):
        if not name.startswith(NEED_PREFIX):
            continue
        plain = name[:8].rstrip() + "." + name[8:].rstrip()
        path = os.path.join(folder, plain)
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            problems.append(f"{plain}: είναι στη δισκέτα αλλά δεν βρέθηκε στο "
                            f"{folder} για έλεγχο")
            continue

        # Στη δισκέτα προηγείται κεφαλίδα AMSDOS 128 bytes (iDSK -t 1), και το
        # μέγεθος στρογγυλεύεται σε εγγραφές των 128.
        want = 1 + -(-len(data) // 128)
        if records != want:
            problems.append(
                f"{plain}: η δισκέτα κρατά {records} εγγραφές των 128 και το "
                f"αρχείο θέλει {want} — δεν είναι το ίδιο αρχείο")
            continue

        try:
            rooms = roomfile.parse_set(data, plain)
        except ValueError as ex:
            problems.append(str(ex))
            continue

        for r in rooms:
            if len(r["cells"]) != roomfile.CELLS:
                problems.append(
                    f"{plain}: η αίθουσα {r['number']} ξεδίπλωσε "
                    f"{len(r['cells'])} κελιά αντί για {roomfile.CELLS}")
    return problems


def entries(path):
    """Τα ονόματα αρχείων του καταλόγου, με τις εγγραφές των 128 bytes καθενός."""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"MV -") and not data.startswith(b"EXTENDED"):
        raise SystemExit(f"checkdsk: το {path} δεν μοιάζει με .dsk")

    # Κεφαλίδα δισκέτας 256 bytes, μετά ανά track: κεφαλίδα 256 + τομείς.
    # Ο κατάλογος AMSDOS είναι οι 4 πρώτοι τομείς των δεδομένων του track 0.
    # Αντί να αποκωδικοποιήσουμε πλήρως τη γεωμετρία —που διαφέρει ανά μορφή—
    # σαρώνουμε για εγγραφές καταλόγου: 32 bytes, user 0..15, όνομα ASCII.
    # Το πλήθος εγγραφών αθροίζεται σε όλα τα extent του ίδιου ονόματος: ένα
    # αρχείο πάνω από 16 KB πιάνει περισσότερα από ένα.
    names = {}
    for off in range(0, len(data) - 32, 32):
        rec = data[off:off + 32]
        if rec[0] > 15:
            continue
        # Τα υπόλοιπα πεδία μιας πραγματικής εγγραφής: extent 0..31, το
        # byte 13 πάντα 0, record count 0..128. Χωρίς αυτά, οποιαδήποτε
        # 32άδα από ASCII μέσα στα ΔΕΔΟΜΕΝΑ περνούσε για όνομα αρχείου και
        # το μήνυμα λάθους γέμιζε σκουπίδια.
        if rec[12] > 31 or rec[13] != 0 or rec[15] > 128:
            continue
        name = rec[1:12]
        if not all(32 <= (b & 0x7F) < 127 for b in name):
            continue
        txt = bytes(b & 0x7F for b in name).decode("ascii")
        base, ext = txt[:8].rstrip(), txt[8:].rstrip()
        ok = set(base + ext) <= set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-!#&%@")
        if base and ext and ok:
            names[txt] = names.get(txt, 0) + rec[15]
    return names


def main(argv):
    if len(argv) != 2:
        print("χρήση: checkdsk.py <αρχείο.dsk>", file=sys.stderr)
        return 2
    names = entries(argv[1])
    missing = [n for n in NEEDED if n not in names]
    rooms = sorted(n for n in names if n.startswith(NEED_PREFIX))
    tunes = sorted(n for n in names if n.startswith(TUNE_PREFIX))
    want_tunes = tune_count()
    tune_bad = want_tunes is not None and len(tunes) != want_tunes
    broken = check_sets(argv[1], names) if rooms else []

    if missing or not rooms or tune_bad or broken:
        print(f"ΣΦΑΛΜΑ: η {argv[1]} δεν είναι πλήρης.", file=sys.stderr)
        for n in missing:
            print(f"        λείπει: {n.strip()}", file=sys.stderr)
        if not rooms:
            print("        λείπουν ΟΛΕΣ οι αίθουσες (ROOMSnn.BIN) — το "
                  "παιχνίδι θα σκάσει με «not found»", file=sys.stderr)
        if tune_bad:
            print(f"        η μουσική: {len(tunes)} από {want_tunes} "
                  f"TUNEnn.BIN — το παιχνίδι θα έπαιζε βουβό", file=sys.stderr)
        for p in broken:
            print(f"        {p}", file=sys.stderr)
        print(f"        βρέθηκαν: {', '.join(sorted(names)) or '(τίποτα)'}",
              file=sys.stderr)
        return 1

    print(f"  Η δισκέτα έχει: MAIN.BIN, GRAV.BAS, "
          f"{len(rooms)} σετ αιθουσών ({', '.join(r.strip() for r in rooms)}) "
          f"που ξεδιπλώνονται καθαρά, μουσική σε {len(tunes)} αρχεία")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
