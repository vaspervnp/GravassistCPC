#!/usr/bin/env python3
"""Πιάνει συγκρούσεις ονομάτων που ο rasm ΔΕΝ θεωρεί σφάλμα.

ΤΟ ΠΡΟΒΛΗΜΑ: ο rasm είναι case-insensitive. Μια μεταβλητή `msg_hold` και μια
σταθερά `MSG_HOLD equ 150` είναι ΤΟ ΙΔΙΟ όνομα. Συνήθως βγαίνει «duplicate
label» και το βλέπεις αμέσως — αλλά όχι πάντα:

    MSG_HOLD  equ 150
    msg_hold  db  0
    ...
    ld (msg_hold),a      ; γράφει στη ΔΙΕΥΘΥΝΣΗ 150

Η γραμμή είναι απολύτως έγκυρη — το 150 είναι νόμιμη διεύθυνση. Ο assembler
δεν λέει τίποτα, ο κώδικας χαλάει σιωπηλά κάτι άλλο, και το βρίσκεις όταν
κάποιο άσχετο κομμάτι αρχίσει να συμπεριφέρεται παράξενα.

Έχει συμβεί τέσσερις φορές σε αυτό το project (LINEBUF/linebuf, cell_ptr,
exit_cool/EXIT_COOL, menu_page/MENU_PAGE, msg_hold/MSG_HOLD). Ένα grep το
πιάνει, οπότε δεν υπάρχει λόγος να ξανασυμβεί.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

EQU = re.compile(r"^\s*(\w+)\s+equ\s", re.I)
DATA = re.compile(r"^(\w+):?\s+(db|dw|ds)\s", re.I)
LABEL = re.compile(r"^(\w+):")


def main():
    equs, others = {}, {}
    for name in sorted(os.listdir(SRC)):
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(SRC, name)) as f:
            for n, line in enumerate(f, 1):
                line = re.sub(r";.*", "", line)
                m = EQU.match(line)
                if m:
                    equs.setdefault(m.group(1).upper(), []).append(f"{name}:{n}")
                    continue
                m = DATA.match(line) or LABEL.match(line)
                if m:
                    others.setdefault(m.group(1).upper(), []).append(f"{name}:{n}")

    clashes = sorted(set(equs) & set(others))
    for key in clashes:
        print(f"  ΛΑΘΟΣ σύγκρουση ονόματος «{key}»: "
              f"equ σε {', '.join(equs[key])} και ετικέτα σε "
              f"{', '.join(others[key])}")
    if clashes:
        print(f"{len(clashes)} ΣΥΓΚΡΟΥΣΕΙΣ: ο rasm είναι case-insensitive και "
              "θα διαβάσει τη ΣΤΑΘΕΡΑ ως διεύθυνση, σιωπηλά.")
        return 1
    print(f"  ΟΚ   κανένα όνομα δεν είναι ταυτόχρονα equ και ετικέτα "
          f"({len(equs)} σταθερές, {len(others)} ετικέτες)")
    return check_palette()


def check_palette():
    """Η παλέτα του editor απέναντι στο tools/physics.py.

    ΓΙΑΤΙ ΥΠΑΡΧΕΙ: το editor/Models/TileType.cs είναι ΧΕΙΡΟΓΡΑΦΟΣ κατάλογος,
    ένας τύπος ανά χαρακτήρα, και τίποτα δεν τον συνέδεε με το μοντέλο. Ένας
    τύπος που μπαίνει στο physics.py και ξεχνιέται εκεί απλώς δεν υπάρχει για
    τον σχεδιαστή: δεν μπορεί να τον ζωγραφίσει, χωρίς κανένα μήνυμα. Ο
    αντίστροφος δρόμος είναι χειρότερος — ένας χαρακτήρας που ζωγραφίζεται και
    δεν τον ξέρει το παιχνίδι σπάει τη φόρτωση της αίθουσας.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "tools"))
    import physics as P
    path = os.path.join(root, "editor", "Models", "TileType.cs")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print("  ΠΑΡΑΛΕΙΨΗ παλέτας: δεν βρέθηκε το TileType.cs")
        return 0
    # Χαρακτήρας της C#: 'x', ή '\\' για το ίδιο το backslash.
    # Δύο μορφές μόνο: δύο backslash για το ίδιο το backslash, ή ένας χαρακτήρας.
    cs = set()
    for lit in re.findall(r"new TileType\('(\\\\|[^'])'", text):
        cs.add("\\" if lit == "\\\\" else lit)
    py = set(P.CHARS)
    missing = sorted(py - cs)
    extra = sorted(cs - py)
    for c in missing:
        print(f"  ΛΑΘΟΣ ο τύπος «{c}» ({P.TYPE_NAMES[P.CHARS[c]]}) λείπει από "
              f"την παλέτα του editor")
    for c in extra:
        print(f"  ΛΑΘΟΣ η παλέτα έχει «{c}», που δεν το ξέρει το physics.py")
    if missing or extra:
        return 1
    print(f"  ΟΚ   η παλέτα του editor ξέρει και τους {len(py)} τύπους")
    return 0


if __name__ == "__main__":
    sys.exit(main())
