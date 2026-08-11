#!/usr/bin/env python3
"""Πού βρίσκονται τα εργαλεία του build (rasm, iDSK, python).

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: το Makefile είχε τα ονόματα καρφωμένα (`ASM = rasm`), οπότε το
build δούλευε μόνο αν τα εργαλεία ήταν στο PATH με ακριβώς αυτά τα ονόματα.
Σε άλλο μηχάνημα — ή με δεύτερη έκδοση του rasm δίπλα — δεν υπήρχε τρόπος να
το πεις χωρίς να πειράξεις το Makefile.

Η ΣΕΙΡΑ ΠΡΟΤΕΡΑΙΟΤΗΤΑΣ, από την ισχυρότερη:

  1. `make ASM=/κάπου/rasm`      — ρητή παράκαμψη στη γραμμή εντολών
  2. μεταβλητή περιβάλλοντος     — GRAVASSIST_RASM, GRAVASSIST_IDSK, ...
  3. toolchain.json              — το «dir» και τα ονόματα
  4. σκέτο όνομα                 — το βρίσκει το PATH

Το αρχείο ρυθμίσεων δείχνεται με GRAVASSIST_TOOLCHAIN, αλλιώς είναι το
`toolchain.json` της ρίζας του repo.

Χρήση από το Makefile:

    ASM  ?= $(shell $(PY) tools/toolchain.py rasm)

και για έλεγχο με το μάτι:

    python3 tools/toolchain.py --all
"""

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.environ.get("GRAVASSIST_TOOLCHAIN") or os.path.join(ROOT, "toolchain.json")

# όνομα -> (κλειδί json, προεπιλογή, μεταβλητή περιβάλλοντος, ψάξε στο "dir")
# Ο python είναι ο διερμηνέας του συστήματος, όχι εργαλείο του CPC: δεν τον
# ψάχνουμε στον κατάλογο των rasm/iDSK ούτε γκρινιάζουμε που λείπει από κει.
TOOLS = {
    "rasm":   ("rasm",   "rasm",    "GRAVASSIST_RASM",   True),
    "idsk":   ("idsk",   "iDSK",    "GRAVASSIST_IDSK",   True),
    "python": ("python", "python3", "GRAVASSIST_PYTHON", False),
}


def load():
    """Οι ρυθμίσεις, ή άδειες αν λείπει/χάλασε το αρχείο.

    Ένα χαλασμένο json ΔΕΝ σταματά το build: πέφτουμε στα σκέτα ονόματα και
    το λέμε στο stderr. Το να μην μπορείς να χτίσεις επειδή έχει ένα κόμμα
    παραπάνω ένα αρχείο ρυθμίσεων είναι χειρότερο από το να χτίσεις με τα
    εργαλεία του PATH.
    """
    try:
        with open(CONFIG, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"toolchain.py: αγνοώ το {CONFIG}: {e}", file=sys.stderr)
        return {}


def resolve(tool, cfg=None):
    """Η εντολή που πρέπει να τρέξει το Makefile για το `tool`."""
    if tool not in TOOLS:
        raise KeyError(tool)
    key, default, envvar, in_dir = TOOLS[tool]
    cfg = load() if cfg is None else cfg

    override = os.environ.get(envvar)
    if override:
        return override

    name = cfg.get(key) or default
    # Απόλυτη (ή ρητά σχετική) διαδρομή: την εμπιστευόμαστε όπως δόθηκε.
    if os.path.isabs(name) or os.sep in name:
        return name

    directory = cfg.get("dir") if in_dir else None
    if directory:
        directory = os.path.expanduser(directory)
        if not os.path.isabs(directory):
            directory = os.path.join(ROOT, directory)
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        # Δεν είναι εκεί. Αν το βρίσκει το PATH συνεχίζουμε, αλλά το λέμε:
        # σιωπηλή υποχώρηση θα έκρυβε ένα τυπογραφικό στο "dir".
        if shutil.which(name):
            print(f"toolchain.py: το {name} δεν είναι στο {directory}, "
                  f"χρησιμοποιώ αυτό του PATH", file=sys.stderr)

    return name


def main(argv):
    if len(argv) == 2 and argv[1] == "--all":
        cfg = load()
        print(f"ρυθμίσεις: {CONFIG}"
              f"{'' if os.path.exists(CONFIG) else '  (ΔΕΝ ΥΠΑΡΧΕΙ)'}")
        for tool in TOOLS:
            path = resolve(tool, cfg)
            found = shutil.which(path) or (path if os.path.isfile(path) else None)
            print(f"  {tool:8} -> {path}"
                  f"{'' if found else '   ΔΕΝ ΒΡΕΘΗΚΕ'}")
        return 0

    if len(argv) != 2 or argv[1] not in TOOLS:
        print(f"χρήση: {os.path.basename(argv[0])} "
              f"{{{'|'.join(TOOLS)}}} | --all", file=sys.stderr)
        return 2

    print(resolve(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
