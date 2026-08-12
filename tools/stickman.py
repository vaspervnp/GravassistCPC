#!/usr/bin/env python3
"""Γεννήτρια των 32 frames του ήρωα (7x12, κανονική φορά βαρύτητας DOWN).

Δεν ζωγραφίζουμε pixel-pixel: κρατάμε έναν ΣΚΕΛΕΤΟ (αρθρώσεις σε συντεταγμένες)
και τραβάμε γραμμές. Έτσι το walk cycle ρυθμίζεται με αριθμούς αντί για
επαναζωγράφισμα. Το PNG παραμένει η τελική αυθεντία — ό,τι ζωγραφίσεις από
πάνω υπερισχύει στο επόμενο `sprites.py build`.

Δες docs/sprites.md §4.
"""

import math
import sys

from cpcgfx import blank, line, put

W, H = 7, 12
W45 = H45 = 13              # στις 45 μοίρες χρειάζεται η διαγώνιος: sqrt(7^2+12^2)=13.9
PEN = 1                     # ο ήρωας είναι λευκός (pen 1), όπως στο concept art

# --- Ο σκελετός σε κανονική όρθια στάση -------------------------------
# Αναλογίες: κεφάλι γραμμές 0-2, κορμός 4-7, πόδια 7-11.
BASE = {
    "head":     (3, 1),     # κέντρο του δακτυλίου 3x3
    "neck":     (3, 3),
    "shoulder": (3, 4),
    "hip":      (3, 7),
    "elbow_l":  (1, 5), "hand_l": (0, 7),
    "elbow_r":  (5, 5), "hand_r": (6, 7),
    "knee_l":   (2, 9), "foot_l": (1, 11),
    "knee_r":   (4, 9), "foot_r": (5, 11),
}

# Βαθύ κάθισμα προσγείωσης — ο σκελετός συμπιεσμένος προς τα κάτω.
CROUCH = {
    "head":     (3, 4),
    "neck":     (3, 6),
    "shoulder": (3, 6),
    "hip":      (3, 9),
    "elbow_l":  (1, 7), "hand_l": (0, 9),
    "elbow_r":  (5, 7), "hand_r": (6, 9),
    "knee_l":   (1, 10), "foot_l": (0, 11),
    "knee_r":   (5, 10), "foot_r": (6, 11),
}

# Γονατιστός — ενδιάμεσος σταθμός της κατάρρευσης.
KNEEL = {
    "head":     (4, 4),
    "neck":     (4, 6),
    "shoulder": (4, 6),
    "hip":      (2, 9),
    "elbow_l":  (2, 7), "hand_l": (1, 9),
    "elbow_r":  (6, 7), "hand_r": (6, 9),
    "knee_l":   (1, 10), "foot_l": (0, 11),
    "knee_r":   (3, 11), "foot_r": (1, 11),
}

# Ξαπλωμένος, κεφάλι δεξιά — η πόζα `0 HP: GAME OVER` του concept art.
LYING = {
    "head":     (5, 9),
    "neck":     (3, 10),
    "shoulder": (3, 10),
    "hip":      (1, 10),
    "elbow_l":  (3, 8), "hand_l": (2, 7),
    "elbow_r":  (3, 11), "hand_r": (2, 11),
    "knee_l":   (0, 9), "foot_l": (0, 8),
    "knee_r":   (0, 11), "foot_r": (0, 11),
}


# --- Χειρισμός πόζας --------------------------------------------------

def pose(base=None, **moves):
    """Αντιγράφει μια πόζα και μετατοπίζει αρθρώσεις: pose(head=(0,-1))."""
    p = dict(base if base is not None else BASE)
    for joint, (dx, dy) in moves.items():
        x, y = p[joint]
        p[joint] = (x + dx, y + dy)
    return p


def lerp(a, b, t):
    """Γραμμική παρεμβολή ανάμεσα σε δύο πόζες."""
    return {k: (a[k][0] + (b[k][0] - a[k][0]) * t,
                a[k][1] + (b[k][1] - a[k][1]) * t) for k in a}


def shear(p, amount):
    """Κλίση όλου του σώματος: τα ψηλά σημεία μετακινούνται περισσότερο,
    τα πέλματα (y=11) μένουν καρφωμένα. Χρησιμοποιείται στις στροφές γωνίας."""
    return {k: (x + amount * (11 - y) / 10.0, y) for k, (x, y) in p.items()}


def rot45(p):
    """Περιστροφή του ΣΚΕΛΕΤΟΥ κατά 45 μοίρες δεξιόστροφα, με επανατοποθέτηση
    στο κέντρο καμβά 13x13.

    Περιστρέφουμε τις αρθρώσεις και ξαναζωγραφίζουμε γραμμές — ΔΕΝ κάνουμε
    resampling της εικόνας. Γι' αυτό το αποτέλεσμα βγαίνει καθαρό σε τόσο
    μικρό sprite, ενώ μια περιστροφή bitmap θα έδινε σκουπίδια.

    Σε συντεταγμένες οθόνης (y προς τα κάτω) η δεξιόστροφη περιστροφή κατά a
    είναι (x,y) -> (x*cos a - y*sin a, x*sin a + y*cos a). Για a=45 και τα δύο
    ημίτονα είναι sqrt(1/2).
    """
    k = math.sqrt(0.5)
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0        # κέντρο της κανονικής μορφής
    ncx = ncy = (W45 - 1) / 2.0                  # κέντρο του καμβά 13x13
    out = {}
    for name, (x, y) in p.items():
        dx, dy = x - cx, y - cy
        out[name] = (ncx + (dx - dy) * k, ncy + (dx + dy) * k)
    return out


# --- Ζωγραφική --------------------------------------------------------

def draw(p, w=W, h=H):
    fr = blank(w, h)
    # Το κεφάλι είναι δακτύλιος 3x3: το κέντρο πρέπει να απέχει >=1 px από κάθε
    # άκρη, αλλιώς κόβεται η μισή κορυφή του και η φιγούρα διαλύεται.
    hx = min(max(round(p["head"][0]), 1), w - 2)
    hy = min(max(round(p["head"][1]), 1), h - 2)

    # κεφάλι: ανοιχτός δακτύλιος 3x3
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                put(fr, hx + dx, hy + dy, PEN)

    line(fr, *p["neck"], *p["hip"], PEN)                       # κορμός
    for side in ("l", "r"):
        line(fr, *p["shoulder"], *p[f"elbow_{side}"], PEN)     # βραχίονας
        line(fr, *p[f"elbow_{side}"], *p[f"hand_{side}"], PEN) # πήχης
        line(fr, *p["hip"], *p[f"knee_{side}"], PEN)           # μηρός
        line(fr, *p[f"knee_{side}"], *p[f"foot_{side}"], PEN)  # κνήμη
    return fr


# --- Τα 32 frames -----------------------------------------------------

def walk_pose(i):
    """Μετωπικός κύκλος βάδισης 8 frames (δύο βήματα).

    Τρεις ανεξάρτητες φάσεις ώστε και τα 8 frames να διαφέρουν πραγματικά:
    άνοιγμα ποδιών (2 κύκλοι), αιώρηση χεριών και λίκνισμα κεφαλιού (1 κύκλος).
    """
    t = i / 8.0
    s = math.sin(2 * math.pi * t)
    off = 1.0 + abs(s) * 1.2            # άνοιγμα ποδιών, ΠΟΤΕ 0 (αλλιώς γίνονται ένα)
    swing = round(s)                    # -1..1, αιώρηση χεριών
    sway = round(math.cos(2 * math.pi * t))   # -1..1, λίκνισμα κεφαλιού

    # Ποιο πόδι αιωρείται: σηκώνεται 1 px από το έδαφος. Αυτό είναι που κάνει
    # τη βάδιση αναγνωρίσιμη σε τόσο μικρό sprite.
    lift_l = 1 if s < -0.3 else 0
    lift_r = 1 if s > 0.3 else 0
    # Πόδια ανοιχτά -> ο γοφός χαμηλώνει 1 px. (Χαμηλώνει, δεν ανεβαίνει: το
    # κεφάλι είναι ήδη στη γραμμή 1 και δεν έχει χώρο προς τα πάνω.)
    drop = 1 if off > 1.9 else 0

    p = dict(BASE)
    p["foot_l"] = (3 - off, 11 - lift_l)
    p["foot_r"] = (3 + off, 11 - lift_r)
    p["knee_l"] = (3 - off / 2.0, 9)
    p["knee_r"] = (3 + off / 2.0, 9)
    p["hip"] = (3, 7 + drop)
    p["shoulder"] = (3, 4 + drop)
    p["neck"] = (3 + sway * 0.5, 3 + drop)
    p["head"] = (3 + sway, 1 + drop)
    # Η αιώρηση εφαρμόζεται ΜΟΝΟ στα χέρια: αν κουνηθεί και ο αγκώνας, ανεβαίνει
    # πάνω από τον ώμο και η φιγούρα δείχνει να σηκώνει το χέρι αντί να βαδίζει.
    p["hand_l"] = (0, 7 + drop + swing)
    p["hand_r"] = (6, 7 + drop - swing)
    p["elbow_l"] = (1, 5 + drop)
    p["elbow_r"] = (5, 5 + drop)
    return p


def fall_pose(i):
    """Πτώση: χέρια ψηλά, πόδια μαζεμένα, ελαφρύ σπαρτάρισμα ανά frame."""
    hl = (0, 3 + (i % 2))
    hr = (6, 3 + ((i + 1) % 2))
    fl = (1 + (1 if i == 3 else 0), 10 + (1 if i == 1 else 0))
    fr_ = (5 - (1 if i == 3 else 0), 10 + (1 if i == 2 else 0))
    p = dict(BASE)
    p.update({
        "elbow_l": (1, 4), "hand_l": hl,
        "elbow_r": (5, 4), "hand_r": hr,
        "knee_l": (2, 9), "foot_l": fl,
        "knee_r": (4, 9), "foot_r": fr_,
    })
    return p


# ΜΟΝΟ ΟΣΑ ΖΩΓΡΑΦΙΖΟΝΤΑΙ. Ο ΜΟΝΟΣ παραγωγός δείκτη καρέ είναι το anim_frame
# του src/main.asm — ό,τι δεν το ζητά εκεί είναι νεκρό βάρος, και στα
# διαγώνια κάθε καρέ κοστίζει 169 bytes.
#
# Τα TURNOUT και TURNIN μένουν έξω: κανένας κανόνας δεν τα ζητά. Τα LAND και
# DEATH μπήκαν όταν ελευθερώθηκε χώρος από το αχρησιμοποίητο gfx_objects.asm.
FRAME_NAMES = (
    ["IDLE0", "IDLE1"]
    + [f"WALK{i}" for i in range(8)]
    + [f"FALL{i}" for i in range(4)]
    + [f"LAND{i}" for i in range(3)]
    + [f"DEATH{i}" for i in range(5)]
)


def build_poses():
    poses = []

    # 0-1  IDLE — ανάσα: τα χέρια ανεβαίνουν 1 px
    poses.append(BASE)
    poses.append(pose(hand_l=(0, -1), hand_r=(0, -1)))

    # 2-9  WALK
    poses += [walk_pose(i) for i in range(8)]

    # 10-13 FALL
    poses += [fall_pose(i) for i in range(4)]

    # 14-16 LAND — από βαθύ κάθισμα προς όρθιος
    poses += [lerp(CROUCH, BASE, t) for t in (0.0, 0.5, 0.85)]

    # 17-21 DEATH — όρθιος -> γονατιστός -> ξαπλωμένος
    poses.append(pose(hand_l=(0, -2), hand_r=(0, -2), head=(0, 1)))
    poses.append(lerp(BASE, KNEEL, 0.5))
    poses.append(KNEEL)
    poses.append(lerp(KNEEL, LYING, 0.5))
    poses.append(LYING)             # η πόζα «0 HP» του concept art
    return poses

    # ΔΕΝ ΠΑΡΑΓΟΝΤΑΙ: κανένας κανόνας του anim_frame δεν τα ζητά.
    # TURNOUT — τύλιγμα σε κυρτή γωνία, κλίση προς τα έξω
    poses += [shear(BASE, a) for a in (0.8, 1.6, 2.4, 3.0)]
    # TURNIN — ανέβασμα σε κοίλη γωνία, κλίση προς τα μέσα
    poses += [shear(BASE, -a) for a in (0.8, 1.6, 2.4, 3.0)]

    # 22-24 LAND — από βαθύ κάθισμα προς όρθιος
    poses += [lerp(CROUCH, BASE, t) for t in (0.0, 0.5, 0.85)]

    # 25-26 HURT — τίναγμα: χέρια πεταμένα, πόδια ανοιχτά
    hurt = pose(hand_l=(0, -3), hand_r=(0, -3), elbow_l=(0, -1), elbow_r=(0, -1),
                foot_l=(-1, 0), foot_r=(1, 0), knee_l=(-1, 0), knee_r=(1, 0))
    poses.append(hurt)
    poses.append(pose(hurt, head=(0, -1), neck=(0, -1), shoulder=(0, -1)))

    # 27-31 DEATH — όρθιος -> γονατιστός -> ξαπλωμένος
    poses.append(pose(hand_l=(0, -2), hand_r=(0, -2), head=(0, 1)))
    poses.append(lerp(BASE, KNEEL, 0.5))
    poses.append(KNEEL)
    poses.append(lerp(KNEEL, LYING, 0.5))
    poses.append(LYING)

    assert len(poses) == 32, f"περίμενα 32 πόζες, βρήκα {len(poses)}"
    return poses


def build_frames():
    """Τα 32 frames στην κανονική μορφή (7x12). Δίνουν τις φορές 0/90/180/270."""
    return [draw(p) for p in build_poses()]


def build_frames45():
    """Τα ίδια 32 frames γυρισμένα 45 μοίρες (13x13).

    Από αυτά ο κώδικας των 90 μοιρών βγάζει τις φορές 135/225/315 — γι' αυτό
    αποθηκεύεται ΜΟΝΟ η μία διαγώνια δέσμη. Δες docs/sprites.md §2.
    """
    return [draw(rot45(p), W45, H45) for p in build_poses()]


if __name__ == "__main__":
    from cpcgfx import to_ascii
    which = sys.argv[1] if len(sys.argv) > 1 else "0"
    frames = build_frames45() if which == "45" else build_frames()
    for name, fr in zip(FRAME_NAMES, frames):
        print(f"--- {name} ---")
        print(to_ascii(fr))
