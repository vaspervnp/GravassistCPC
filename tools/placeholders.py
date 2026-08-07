#!/usr/bin/env python3
"""Placeholder sprites των αντικειμένων πίστας: 13 τύποι x 2 frames, 8x8.

Προσωρινά. Ο στόχος είναι μόνο να ΞΕΧΩΡΙΖΟΥΝ μεταξύ τους μέσα στην πίστα
μέχρι να γίνει η τελική εικονογράφηση — ζωγράφισέ τα από πάνω στο
assets/objects.png. Το frame 1 είναι πάντα η "ενεργή" εκδοχή (πόρτα ανοιχτή,
διακόπτης πατημένος, κ.λπ.).

Δες docs/sprites.md §6 και docs/level-elements.md.
"""

from cpcgfx import blank, line, put, rect

S = 8   # τα αντικείμενα είναι πάντα ένα κελί 8x8

# id -> (όνομα, χαρακτηρισμός για σχόλιο στο asm)
TYPES = [
    ("EXIT",     "στόχος της πίστας"),
    ("GATE",     "πόρτα· ανοίγει από switch"),
    ("SWITCH",   "διακόπτης toggle"),
    ("ENERGY",   "+2 ενέργεια"),
    ("CRATE",    "κιβώτιο· πέφτει κι αυτό με τη βαρύτητα"),
    ("PLATE",    "πλάκα πίεσης· ενεργή όσο έχει βάρος"),
    ("LOCK",     "κλειδαριά· ανοίγει με το KEY"),
    ("ONEWAY",   "μονόδρομη πλατφόρμα· στερεή από μία πλευρά"),
    ("GRAVLOCK", "ζώνη όπου απαγορεύεται η αλλαγή βαρύτητας"),
    ("CRUMBLE",  "εύθραυστο πλακίδιο· καταρρέει μετά το πάτημα"),
    ("SPIKES",   "κατευθυντικά αγκάθια· πονάνε από τη μύτη"),
    ("TELEPORT", "ζεύγος τηλεμεταφοράς"),
    ("KEY",      "κλειδί· ανοίγει το LOCK του"),
]


def _frame(kind, active):
    """Ζωγραφίζει ένα 8x8 placeholder. pen2 = σώμα, pen3 = τονισμός."""
    f = blank(S, S)
    body, hi = 2, 3

    if kind == "EXIT":                       # πόρτα με βέλος προς τα μέσα
        rect(f, 1, 0, 6, 7, hi)
        if active:
            rect(f, 2, 1, 5, 6, body, fill=True)
        line(f, 3, 5, 3, 2, hi); line(f, 2, 3, 3, 2, hi); line(f, 4, 3, 3, 2, hi)

    elif kind == "GATE":                     # κάγκελα· ανοιχτή = μισό ύψος
        h = 3 if active else 7
        for x in (1, 3, 5):
            line(f, x, 0, x, h, body)
        line(f, 0, 0, 6, 0, hi)
        line(f, 0, h, 6, h, hi)

    elif kind == "SWITCH":                   # μοχλός σε βάση
        line(f, 1, 7, 6, 7, body)
        line(f, 3, 6, 6 if active else 1, 3, hi)

    elif kind == "ENERGY":                   # καρδιά / μπαταρία
        rect(f, 2, 1, 5, 6, hi)
        rect(f, 3, 2 if active else 4, 4, 5, body, fill=True)

    elif kind == "CRATE":                    # κιβώτιο με χιαστί
        rect(f, 0, 0, 7, 7, hi)
        line(f, 1, 1, 6, 6, body); line(f, 6, 1, 1, 6, body)
        if active:
            rect(f, 2, 2, 5, 5, body, fill=True)

    elif kind == "PLATE":                    # πλάκα· πατημένη = χαμηλότερη
        y = 5 if active else 3
        rect(f, 0, y, 7, y + 1, hi, fill=True)
        line(f, 1, y + 2, 1, 7, body); line(f, 6, y + 2, 6, 7, body)

    elif kind == "LOCK":                     # κλειδαριά
        rect(f, 1, 3, 6, 7, hi)
        line(f, 2, 2, 2, 1, body); line(f, 5, 2, 5, 1, body)
        line(f, 3, 0, 4, 0, body)
        put(f, 3, 5, body if not active else 0)

    elif kind == "ONEWAY":                   # πλατφόρμα με βελάκια περάσματος
        rect(f, 0, 0, 7, 1, hi, fill=True)
        for x in (1, 4):
            line(f, x, 4, x + 2, 4, body)
            line(f, x + 1, 3, x + 1, 6, body)

    elif kind == "GRAVLOCK":                 # πλέγμα ζώνης + λουκέτο-σταυρός
        for x in range(0, S, 2):
            for y in range(0, S, 2):
                put(f, x, y, body if not active else hi)
        line(f, 2, 3, 5, 3, hi); line(f, 3, 2, 3, 5, hi)

    elif kind == "CRUMBLE":                  # τούβλα· ραγισμένα όταν ενεργό
        rect(f, 0, 0, 7, 7, body)
        line(f, 0, 3, 7, 3, body); line(f, 3, 0, 3, 3, body); line(f, 4, 4, 4, 7, body)
        if active:
            line(f, 1, 1, 6, 6, hi)

    elif kind == "SPIKES":                   # μύτες προς τα πάνω (orient=0)
        line(f, 0, 7, 7, 7, body)
        for x in (1, 4):
            line(f, x, 6, x + 1, 2 if not active else 4, hi)
            line(f, x + 2, 6, x + 1, 2 if not active else 4, hi)

    elif kind == "TELEPORT":                 # δακτύλιος
        rect(f, 1, 1, 6, 6, hi)
        rect(f, 2, 2, 5, 5, body if not active else hi)
        put(f, 3, 3, 0); put(f, 4, 4, 0)

    elif kind == "KEY":                      # κλειδί
        rect(f, 1, 1, 3, 3, hi)
        line(f, 4, 3, 6, 5, hi)
        line(f, 5, 5, 6, 6, body if not active else hi)

    return f


def build_frames():
    """Επιστρέφει 26 frames: type0/f0, type0/f1, type1/f0, ..."""
    out = []
    for name, _ in TYPES:
        out.append(_frame(name, False))
        out.append(_frame(name, True))
    return out


FRAME_NAMES = [f"{n}_{i}" for n, _ in TYPES for i in (0, 1)]


if __name__ == "__main__":
    from cpcgfx import to_ascii
    for name, fr in zip(FRAME_NAMES, build_frames()):
        print(f"--- {name} ---")
        print(to_ascii(fr))
