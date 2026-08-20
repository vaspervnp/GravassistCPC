#!/usr/bin/env python3
"""Η παλέτα του editor και τα πλακίδια του παιχνιδιού, στην ίδια φορά.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: το ίδιο κελί ζωγραφίζεται ΔΥΟ φορές, από δύο ανεξάρτητα χέρια.
Ο Amstrad και το test run του browser παίρνουν pixel από το tools/placeholders.py
στραμμένα κατά PLACEHOLDER/SPIKE_OFF_TURNS· το πλέγμα του editor παίρνει SVG από
το editor/Models/TileType.cs, στραμμένο με `rotate(...)`. Κανείς δεν τα
συνέκρινε.

Ο διακόπτης τοίχου πλήρωσε ακριβώς αυτό: το 'Q' είναι SWITCH_L, κοιτάζει
αριστερά, άρα η βάση του πατάει στον ΔΕΞΙΟ τοίχο — και η παλέτα το ζωγράφιζε
καθρεφτισμένο, με ετικέτα «left wall». Ο σχεδιαστής έβαζε διακόπτη βλέποντας το
ένα και το παιχνίδι έδειχνε το άλλο.

ΤΙ ΕΛΕΓΧΕΤΑΙ: όπου το SVG εκφράζει ένα πλακίδιο ως ΣΤΡΟΦΗ ενός κοινού σχήματος,
η γωνία πρέπει να είναι η ίδια με του παιχνιδιού — `rotate(N)` απέναντι σε
`τέταρτα x 90`. Τα πλακίδια που η παλέτα τα ζωγραφίζει χωριστά δεν αφορούν αυτόν
τον έλεγχο: δεν υπάρχει γωνία να συγκριθεί.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import genasm
import physics as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILES = os.path.join(ROOT, "editor", "Models", "TileType.cs")


def palette_chars():
    """(χαρακτήρας -> όνομα) για ΚΑΘΕ πλακίδιο της παλέτας."""
    with open(TILES, encoding="utf-8") as f:
        src = f.read()
    out = {}
    for ch, name in re.findall(r"new TileType\('(\\?.)',\s*\"([a-z0-9_]+)\"", src):
        out[{"\\\\": "\\", "\\'": "'"}.get(ch, ch)] = name
    return out


def check_chars():
    """Η παλέτα και ο parser δέχονται ΤΟΥΣ ΙΔΙΟΥΣ χαρακτήρες.

    ΤΟ ΣΧΟΛΙΟ ΤΟΥ TileCatalog ΤΟ ΕΛΕΓΕ ΚΑΙ ΚΑΝΕΙΣ ΔΕΝ ΤΟ ΕΛΕΓΧΕ. Ένας τύπος που
    μπαίνει στο μοντέλο και ξεχνιέται εδώ δεν ζωγραφίζεται πουθενά: ο
    σχεδιαστής δεν τον βλέπει και δεν μπορεί να τον βάλει. Ανάποδα, ένας
    χαρακτήρας που ζωγραφίζεται εδώ και δεν υπάρχει στο CHARS γίνεται πίστα
    που ο parser απορρίπτει.
    """
    pal, model = palette_chars(), P.CHARS
    bad = []
    for ch in sorted(set(model) - set(pal)):
        bad.append(f"το «{ch}» ({P.TYPE_NAMES[model[ch]]}) λείπει από την παλέτα")
    for ch in sorted(set(pal) - set(model)):
        bad.append(f"το «{ch}» ({pal[ch]}) της παλέτας δεν υπάρχει στο CHARS")
    return bad


def game_turns(tile):
    """Πόσα τέταρτα δεξιόστροφα στρίβει το παιχνίδι αυτόν τον τύπο."""
    if tile in genasm.SPIKE_OFF_TURNS:
        return genasm.SPIKE_OFF_TURNS[tile]
    art = genasm.PLACEHOLDER.get(tile)
    return art[1] if art else 0


def palette_rotations():
    """(χαρακτήρας, όνομα, γωνία) για κάθε πλακίδιο που δηλώνει `rotate`."""
    with open(TILES, encoding="utf-8") as f:
        src = f.read()
    out = []
    for ch, name, body in re.findall(
            r"new TileType\('(.)',\s*\"([^\"]+)\"(.*?)\"\"\"\)", src, re.S):
        m = re.search(r"rotate\((\d+)\s+4\s+4\)", body)
        if m:
            out.append((ch, name, int(m.group(1))))
    return out


def main():
    rots = palette_rotations()
    if not rots:
        print("ΣΦΑΛΜΑ: δεν βρέθηκε ούτε ένα rotate() στο TileType.cs — "
              "άλλαξε η μορφή του αρχείου και ο έλεγχος δεν ελέγχει τίποτα.",
              file=sys.stderr)
        return 1

    bad = check_chars()
    for ch, name, angle in rots:
        tile = P.CHARS.get(ch)
        if tile is None:
            bad.append(f"'{ch}' ({name}): δεν είναι χαρακτήρας του physics.py")
            continue
        want = game_turns(tile) * 90
        if angle != want:
            bad.append(f"'{ch}' ({name}, {P.TYPE_NAMES[tile]}): η παλέτα το "
                       f"στρίβει {angle} μοίρες, το παιχνίδι {want}")

    if bad:
        print("ΣΦΑΛΜΑ: η παλέτα του editor δείχνει άλλα από το παιχνίδι.",
              file=sys.stderr)
        for b in bad:
            print(f"        {b}", file=sys.stderr)
        return 1

    print(f"  Παλέτα και πλακίδια συμφωνούν σε {len(rots)} στραμμένα κελιά "
          f"και {len(palette_chars())} χαρακτήρες")
    return 0


if __name__ == "__main__":
    sys.exit(main())
