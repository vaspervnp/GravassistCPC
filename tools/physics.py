#!/usr/bin/env python3
"""Μοντέλο φυσικής του GRAVASSIST — ΑΝΑΦΟΡΑ για την υλοποίηση σε Z80.

Εδώ δοκιμάζεται η μηχανική πριν γραφτεί σε assembly, γιατί ο Z80 κώδικας δεν
μπορεί να τρέξει από το περιβάλλον ανάπτυξης. Ό,τι αλλάζει εδώ πρέπει να
αλλάξει και στο src/hero.asm — και το αντίστροφο.

Οι δύο κανόνες που βγάζουν όλη τη συμπεριφορά:

  1. Ο ήρωας ΣΤΕΚΕΤΑΙ αν και τα ΔΥΟ πέλματα πατάνε σε στερεό.
     Ένα πέλμα -> ασταθής -> γλιστράει. Κανένα -> πέφτει.
     Από αυτόν τον κανόνα προκύπτει ΔΩΡΕΑΝ ότι η διαγώνια βαρύτητα σε
     επίπεδο πάτωμα γλιστράει, ενώ σε ράμπα 45 μοιρών στέκεται.

  2. Περπατώντας, αν κλείσει ο δρόμος -> στροφή ΑΝΤΙΘΕΤΑ (κοίλη γωνία).
     Αν χαθεί το έδαφος -> στροφή ΠΡΟΣ τη φορά (κυρτή γωνία).
     Οι ράμπες προκύπτουν από το ίδιο, με βήμα 45 αντί για 90.
"""

import math
import os
import sys


def r(v):
    """Στρογγυλοποίηση όπως θα την κάνει ο Z80 (floor(v+0.5)).
    Η ενσωματωμένη r() είναι banker's rounding και δίνει άλλα αποτελέσματα."""
    return math.floor(v + 0.5)

CELL = 8
COLS, ROWS = 40, 24
GRID_Y0 = 8                     # η πρώτη scanline του grid (πάνω από αυτήν = HUD)

# --- Τύποι κελιών -----------------------------------------------------
EMPTY, SOLID = 0, 1
RAMP_DR, RAMP_DL, RAMP_UR, RAMP_UL = 2, 3, 4, 5     # στερεό κάτω-δεξιά κ.λπ.

CHARS = {".": EMPTY, "#": SOLID,
         "/": RAMP_DR, "\\": RAMP_DL, "7": RAMP_UR, "F": RAMP_UL}

# Για κάθε ράμπα: είναι στερεό το pixel (u,v) μέσα στο κελί 8x8;
RAMP_TEST = {
    RAMP_DR: lambda u, v: v >= 7 - u,     # υποτείνουσα κάτω-αριστερά -> πάνω-δεξιά
    RAMP_DL: lambda u, v: v >= u,         # υποτείνουσα πάνω-αριστερά -> κάτω-δεξιά
    RAMP_UR: lambda u, v: v <= u,
    RAMP_UL: lambda u, v: v <= 7 - u,
}

# Η φορά βαρύτητας ΠΑΝΩ σε κάθε ράμπα: το κάθετο στην επιφάνεια, προς το υλικό.
# Επειδή ο κόσμος είναι από tiles γνωστού σχήματος, η κλίση δεν χρειάζεται να
# εκτιμηθεί — διαβάζεται. Αυτό εξαφανίζει την ασάφεια στις συμβολές.
RAMP_GRAVITY = {RAMP_DR: 7, RAMP_DL: 1, RAMP_UR: 5, RAMP_UL: 3}

# --- Γεωμετρία βαρύτητας ---------------------------------------------
# G = μοναδιαίο διάνυσμα προς τη βαρύτητα, R = "μπροστά" (G γυρισμένο 90 CCW).
def gvec(g):
    a = math.radians(g * 45)
    return (-math.sin(a), math.cos(a))

def rvec(g):
    gx, gy = gvec(g)
    return (gy, -gx)

class Room:
    def __init__(self, text):
        # Γραμμή πίστας = ακριβώς COLS έγκυροι χαρακτήρες. Τα σχόλια είναι ";"
        # (ΟΧΙ "#": το "#" είναι στερεό κελί).
        rows = [ln for ln in text.splitlines()
                if len(ln) == COLS and all(c in CHARS for c in ln)]
        assert len(rows) == ROWS, f"περίμενα {ROWS} γραμμές, βρήκα {len(rows)}"
        self.cells = [[CHARS[c] for c in ln] for ln in rows]

    def cell(self, col, row):
        if col < 0 or row < 0 or col >= COLS or row >= ROWS:
            return SOLID                    # έξω από το δωμάτιο = τοίχος
        return self.cells[row][col]

    def solid_at(self, px, py):
        """Είναι το pixel (px,py) μέσα σε υλικό; Χειρίζεται και τις ράμπες."""
        py -= GRID_Y0
        if py < 0:
            return True
        col, row = px // CELL, py // CELL
        t = self.cell(col, row)
        if t == EMPTY:
            return False
        if t == SOLID:
            return True
        return RAMP_TEST[t](px % CELL, py % CELL)


# Το σώμα 7x12 μοντελοποιείται ΣΤΕΝΟ: μια κατακόρυφη ράβδος με δύο "πέλματα".
# Με πλατύ bounding box κάθε ράμπα μοιάζει με τοίχο.
FEET_B   = 6        # απόσταση πέλματος από το κέντρο, κατά τη βαρύτητα
FOOT_A   = 2        # μισό άνοιγμα ποδιών, κάθετα στη βαρύτητα
WALL_A   = 3        # μισό πλάτος κορμού
SCAN_MAX = 14       # πόσο βαθιά ψάχνουμε έδαφος
TILT_45  = 3        # διαφορά ύψους (σε 2*FOOT_A pixels) που μετράει για 45 μοίρες


def gvec(g):
    a = math.radians(g * 45)
    return (-math.sin(a), math.cos(a))


def rvec(g):
    gx, gy = gvec(g)
    return (gy, -gx)


class Hero:
    """Θέση = ΚΕΝΤΡΟ του σώματος σε pixels.

    Η βαρύτητα δεν συμπεραίνεται από το τι εμποδίζει· η κλίση της επιφάνειας
    ΜΕΤΡΙΕΤΑΙ ψάχνοντας το έδαφος κάτω από το μπροστινό και το πίσω πέλμα. Έτσι
    μια ράμπα δεν μπερδεύεται ποτέ με τοίχο, όσο πλατύ κι αν είναι το σώμα.
    """

    def __init__(self, room, x, y, g=0):
        self.room, self.x, self.y, self.g = room, x, y, g
        self.fall_dist = 0
        self.state = "FALL"
        self.prev_support = EMPTY

    # --- πρωτογενείς έλεγχοι --------------------------------------
    def at(self, a, b):
        """Στερεό στο σημείο (a = πλάγια, b = προς τα πόδια) του ήρωα;"""
        rx, ry = rvec(self.g)
        gx, gy = gvec(self.g)
        return self.room.solid_at(r(self.x + a * rx + b * gx),
                                  r(self.y + a * ry + b * gy))

    def ground_depth(self, a):
        """Σε πόσα pixels κατά τη βαρύτητα βρίσκεται έδαφος στη στήλη `a`;
        None αν δεν βρεθεί μέσα στο SCAN_MAX."""
        for k in range(0, SCAN_MAX):
            if self.at(a, k):
                return k
        return None

    def wall_ahead(self, d):
        """Εμπόδιο στο ύψος του ΚΟΡΜΟΥ (όχι των ποδιών) — αυτό είναι τοίχος."""
        return self.at(WALL_A * d, 0) or self.at(WALL_A * d, -4)

    def tilt(self, d):
        """Διαφορά ύψους εδάφους μπροστά-πίσω. Αρνητικό = ανηφόρα μπροστά.
        None αν λείπει έδαφος σε κάποια από τις δύο πλευρές."""
        f = self.ground_depth(FOOT_A * d)
        b = self.ground_depth(-FOOT_A * d)
        if f is None or b is None:
            return None
        return f - b

    def stable(self):
        """Στέκεται αν υπάρχει έδαφος ΚΑΙ η επιφάνεια είναι κάθετη στη βαρύτητα.
        Από εδώ βγαίνει δωρεάν το γλίστρημα: με διαγώνια βαρύτητα σε επίπεδο
        πάτωμα η κλίση βγαίνει μεγάλη -> ασταθής -> γλιστράει."""
        t = self.tilt(1)
        if t is None or abs(t) > 1:
            return False
        k = self.ground_depth(0)
        return k is not None and k <= FEET_B + 2

    def slipping(self):
        """Γλιστράει; Ναι αν η βαρύτητα δεν είναι κάθετη στην επιφάνεια.

        Ακριβές, γιατί το κελί λέει μονοσήμαντα ποια φορά "στέκεται" πάνω του:
        σε ράμπα μόνο η διαγώνια της, σε στερεό μόνο οι τέσσερις ορθές. Από εδώ
        βγαίνει ο κανόνας "διαγώνια βαρύτητα σε επίπεδο πάτωμα -> γλιστράς".
        """
        st = self.support_type()
        if st == EMPTY:
            return False                      # δεν ακουμπάει: πτώση, όχι γλίστρημα
        if st in RAMP_GRAVITY:
            return self.g != RAMP_GRAVITY[st]
        return self.g % 2 == 1

    # --- κίνηση ---------------------------------------------------
    def rotate(self, steps):
        self.g = (self.g + steps) % 8

    def snap(self):
        """Κάθισε τα πέλματα ακριβώς πάνω στην επιφάνεια."""
        gx, gy = gvec(self.g)
        for _ in range(SCAN_MAX):
            k = self.ground_depth(0)
            if k is None:
                return False
            if abs(k - FEET_B) <= 1:
                return True
            step = 1 if k > FEET_B else -1
            self.x += r(gx) * step
            self.y += r(gy) * step
        return False

    def update(self, walk=0):
        """Η ΣΕΙΡΑ εδώ είναι ο πυρήνας του παιχνιδιού:

        Η βαρύτητα ευθυγραμμίζεται με την επιφάνεια ΜΟΝΟ μέσα από το περπάτημα
        (do_walk). Αν ο παίκτης βάλει βαρύτητα που δεν ταιριάζει με το πάτωμα,
        δεν "ισιώνει" μόνη της — ο ήρωας γλιστράει. Αν το κάναμε ανάποδα, το
        γλίστρημα δεν θα συνέβαινε ποτέ.
        """
        k = self.ground_depth(0)
        if k is None or k > FEET_B + 2:
            self.do_fall()
            return
        if self.state == "FALL":
            self.land()
        # Το ΠΕΡΠΑΤΗΜΑ ευθυγραμμίζει τη βαρύτητα με την επιφάνεια (§2.3). Ο
        # έλεγχος γλιστρήματος πρέπει να γίνει ΜΕΤΑ, αλλιώς ο ήρωας γλιστράει
        # στο πρώτο pixel κάθε ράμπας πριν προλάβει να κουμπώσει πάνω της.
        if walk:
            self.do_walk(walk)
        elif self.slipping():
            self.do_fall()
        else:
            self.state = "IDLE"
        self.prev_support = self.support_type()

    def do_fall(self):
        self.state = "FALL"
        gx, gy = gvec(self.g)
        if not self.at(0, FEET_B):                 # ελεύθερος -> πέφτε
            self.x += r(gx)
            self.y += r(gy)
            self.fall_dist += 1
            return
        # ακουμπάει αλλά η επιφάνεια δεν είναι κάθετη -> γλίστρα κατά μήκος της
        t = self.tilt(1)
        slide = 0 if t is None else (1 if t > 0 else -1)
        if slide == 0:
            slide = 1 if not self.at(FOOT_A, FEET_B) else -1
        rx, ry = rvec(self.g)
        nx, ny = self.x + r(rx) * slide, self.y + r(ry) * slide
        if not self.room.solid_at(nx, ny):
            self.x, self.y = nx, ny
        self.snap()

    def land(self):
        self.state = "IDLE"
        dmg = max(0, self.fall_dist - 36)
        self.fall_dist = 0
        return dmg

    def do_walk(self, d):
        """Ένα pixel. Τέσσερις περιπτώσεις, όλες στροφή γύρω από το ίδιο σημείο:
             τοίχος μπροστά   -> -2 βήματα (κοίλη γωνία, 90 μοίρες)
             ανηφόρα 45       -> -1 βήμα
             κατηφόρα 45      -> +1 βήμα
             χάθηκε το έδαφος -> +2 βήματα (κυρτή γωνία, 90 μοίρες)
        """
        self.state = "WALK"
        ox, oy, og = self.x, self.y, self.g

        if self.wall_ahead(d):
            self.corner(-2 * d, d, ox, oy, og)   # ΚΟΙΛΗ: ανεβαίνει στον τοίχο
            return

        rx, ry = rvec(self.g)
        self.x += r(rx) * d
        self.y += r(ry) * d

        if self.ground_depth(0) is None:            # ΚΥΡΤΗ: τέλος πλατώματος
            self.x, self.y = ox, oy
            self.corner(2 * d, d, ox, oy, og)
            return

        self.snap()
        self.align(d)
        if self.slipping() and self.prev_support == self.support_type():
            self.do_fall()          # δεν κούμπωσε και δεν είναι μετάβαση

    def pivot_to(self, newg):
        """Αλλάζει φορά βαρύτητας περιστρέφοντας το σώμα ΓΥΡΩ ΑΠΟ ΤΟ ΣΗΜΕΙΟ
        ΕΠΑΦΗΣ των πελμάτων, όχι γύρω από το κέντρο του.

        Αυτό ήταν το βασικό σφάλμα του μοντέλου: με στροφή γύρω από το κέντρο,
        μετά από κάθε 45 μοίρες τα πέλματα βρίσκονταν 4-5 pixels στο πλάι από
        εκεί που πατούσαν, οπότε ο ήρωας "ξεκολλούσε" από τη ράμπα στη συμβολή
        της με το επίπεδο και γλιστρούσε.
        """
        k = self.ground_depth(0)
        if k is None:
            return False
        gx, gy = gvec(self.g)
        cx, cy = self.x + k * gx, self.y + k * gy       # σημείο επαφής
        ngx, ngy = gvec(newg)
        self.g = newg
        self.x = r(cx - FEET_B * ngx)               # ίδιο σημείο, νέα φορά
        self.y = r(cy - FEET_B * ngy)
        return self.snap()

    def support_type(self):
        """Ο τύπος του κελιού που στηρίζει τα πέλματα."""
        k = self.ground_depth(0)
        if k is None:
            return EMPTY
        gx, gy = gvec(self.g)                 # ΤΟ ΜΕΤΡΗΜΕΝΟ βάθος επαφής, όχι
        px = r(self.x + k * gx)           # σταθερό: ένα pixel πιο βαθιά και
        py = r(self.y + k * gy)           # διαβάζεις το κελί από κάτω
        return self.room.cell(px // CELL, (py - GRID_Y0) // CELL)

    def align(self, d):
        """Ευθυγραμμίζει τη βαρύτητα με την επιφάνεια, ΔΙΑΒΑΖΟΝΤΑΣ το κελί.

        Προηγουμένως εκτιμούσαμε την κλίση από τη διαφορά βάθους των δύο
        πελμάτων. Στη συμβολή ράμπας με επίπεδο τα πέλματα πατάνε σε διαφορετικές
        γεωμετρίες, η μέτρηση έβγαινε ενδιάμεση, και ΚΑΜΙΑ φορά δεν ήταν ευσταθής
        — ο ήρωας κολλούσε στη βάση της ράμπας. Ο τύπος του κελιού είναι
        μονοσήμαντος και δεν έχει αυτό το πρόβλημα.
        """
        st = self.support_type()
        if st in RAMP_GRAVITY:
            if self.g == RAMP_GRAVITY[st]:
                return True
            save = (self.x, self.y, self.g)
            if self.pivot_to(RAMP_GRAVITY[st]) and not self.slipping():
                return True
            # Στο πρώτο pixel μιας ράμπας υπάρχει μόλις 1 pixel υλικού: η
            # περιστροφή γύρω από αυτό θα πετούσε το σώμα πίσω στο επίπεδο.
            # Μένουμε στην τρέχουσα φορά και ξαναδοκιμάζουμε το επόμενο pixel.
            self.x, self.y, self.g = save
            return False
        if st == SOLID and self.g % 2 and self.prev_support in RAMP_GRAVITY:
            # βγαίνουμε από ράμπα σε επίπεδη έδρα: ποια από τις δύο γειτονικές
            # ορθές φορές είναι αυτή; Η επιφάνεια είναι επίπεδη, άρα αποφασίζει.
            for cand in ((self.g - 1) % 8, (self.g + 1) % 8):
                save = (self.x, self.y, self.g)
                # Κριτήριο: δεν γλιστράει ΚΑΙ το σώμα δεν είναι μέσα στο υλικό.
                # (Ο έλεγχος κλίσης που ήταν εδώ απέρριπτε τη σωστή λύση: στη
                #  βάση της ράμπας το μπροστινό πέλμα πατάει ακόμα στην κεκλιμένη
                #  επιφάνεια, οπότε η κλίση δεν έχει μηδενίσει.)
                if (self.pivot_to(cand) and not self.slipping()
                        and not self.at(0, 0) and not self.at(0, -FEET_B)):
                    return True
                self.x, self.y, self.g = save
        return False

    def corner(self, steps, d, ox, oy, og):
        """Στροφή 90 μοιρών σε γωνία, ΤΥΛΙΓΟΝΤΑΣ γύρω από την ακμή.

        Το σημείο περιστροφής είναι η ΑΚΜΗ (μπροστινή-κάτω γωνία του σώματος),
        όχι τα πέλματα: στην κοίλη γωνία είναι εκεί που ο τοίχος συναντά το
        πάτωμα, στην κυρτή εκεί που τελειώνει η πλατφόρμα. Και στις δύο, μετά τη
        στροφή η ίδια ακμή βρίσκεται πάλι στην μπροστινή-κάτω γωνία του σώματος —
        γι' αυτό ο τύπος είναι ένας:

            C          = κέντρο + WALL_A*d*R_παλιό + FEET_B*G_παλιό
            νέο κέντρο = C + WALL_A*d*R_νέο - FEET_B*G_νέο
        """
        rxo, ryo = rvec(self.g)
        gxo, gyo = gvec(self.g)
        cx = self.x + WALL_A * d * rxo + FEET_B * gxo
        cy = self.y + WALL_A * d * ryo + FEET_B * gyo

        newg = (self.g + steps) % 8
        rxn, ryn = rvec(newg)
        gxn, gyn = gvec(newg)
        self.g = newg
        self.x = r(cx + WALL_A * d * rxn - FEET_B * gxn)
        self.y = r(cy + WALL_A * d * ryn - FEET_B * gyn)

        if self.snap() and not self.slipping():
            return True
        self.x, self.y, self.g = ox, oy, og      # αδύνατη στροφή: μείνε ως έχεις
        return False


# --- Απεικόνιση για έλεγχο -------------------------------------------
GLYPH = {0: "↓", 1: "↙", 2: "←", 3: "↖",
         4: "↑", 5: "↗", 6: "→", 7: "↘"}
BACK = {EMPTY: " ", SOLID: "█", RAMP_DR: "◢", RAMP_DL: "◣",
        RAMP_UR: "◥", RAMP_UL: "◤"}


def render(room, hero, w=40, h=24):
    out = [[BACK[room.cell(c, r)] for c in range(w)] for r in range(h)]
    c, r = hero.x // CELL, (hero.y - GRID_Y0) // CELL
    if 0 <= c < w and 0 <= r < h:
        out[r][c] = GLYPH[hero.g]
    return "\n".join("".join(row) for row in out)


def load_room(path=None):
    path = path or os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "levels", "test.txt")
    with open(path) as f:
        return Room(f.read())


if __name__ == "__main__":
    room = load_room()
    hero = Hero(room, 60, 40)
    walk = 1 if len(sys.argv) < 2 else int(sys.argv[1])
    for i in range(400):
        hero.update(walk)
    print(render(room, hero))
    print(f"θέση ({hero.x},{hero.y}) βαρύτητα {hero.g} κατάσταση {hero.state}")
