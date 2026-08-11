#!/usr/bin/env python3
"""Ελέγχει ότι η δισκέτα έχει ΟΝΤΩΣ ό,τι χρειάζεται το παιχνίδι.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: μια δισκέτα χωρίς αίθουσες χτίζεται μια χαρά και αποτυγχάνει
αργότερα, στον emulator, με «ROOMS01.BIN not found» — μακριά από την αιτία.
Ο έλεγχος γίνεται στο ΤΕΛΟΣ του build, όπου η αιτία είναι ακόμα μπροστά σου.

Διαβάζει τον κατάλογο του .dsk κατευθείαν (μορφή Extended/Standard CPC), χωρίς
να εξαρτάται από την έξοδο του iDSK.
"""

import sys

NEEDED = ["MAIN    BIN", "GRAV    BAS"]     # 8+3, με κενά
NEED_PREFIX = "ROOMS"                       # τουλάχιστον ένα ROOMSnn.BIN


def entries(path):
    """Τα ονόματα αρχείων του καταλόγου, ως '8χαρακτήρες3'."""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"MV -") and not data.startswith(b"EXTENDED"):
        raise SystemExit(f"checkdsk: το {path} δεν μοιάζει με .dsk")

    # Κεφαλίδα δισκέτας 256 bytes, μετά ανά track: κεφαλίδα 256 + τομείς.
    # Ο κατάλογος AMSDOS είναι οι 4 πρώτοι τομείς των δεδομένων του track 0.
    # Αντί να αποκωδικοποιήσουμε πλήρως τη γεωμετρία —που διαφέρει ανά μορφή—
    # σαρώνουμε για εγγραφές καταλόγου: 32 bytes, user 0..15, όνομα ASCII.
    names = set()
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
            names.add(txt)
    return names


def main(argv):
    if len(argv) != 2:
        print("χρήση: checkdsk.py <αρχείο.dsk>", file=sys.stderr)
        return 2
    names = entries(argv[1])
    missing = [n for n in NEEDED if n not in names]
    rooms = sorted(n for n in names if n.startswith(NEED_PREFIX))

    if missing or not rooms:
        print(f"ΣΦΑΛΜΑ: η {argv[1]} δεν είναι πλήρης.", file=sys.stderr)
        for n in missing:
            print(f"        λείπει: {n.strip()}", file=sys.stderr)
        if not rooms:
            print("        λείπουν ΟΛΕΣ οι αίθουσες (ROOMSnn.BIN) — το "
                  "παιχνίδι θα σκάσει με «not found»", file=sys.stderr)
        print(f"        βρέθηκαν: {', '.join(sorted(names)) or '(τίποτα)'}",
              file=sys.stderr)
        return 1

    print(f"  Η δισκέτα έχει: MAIN.BIN, GRAV.BAS, "
          f"{len(rooms)} σετ αιθουσών ({', '.join(r.strip() for r in rooms)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
