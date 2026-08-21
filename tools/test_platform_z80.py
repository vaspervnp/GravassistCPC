#!/usr/bin/env python3
"""Η κινούμενη πλατφόρμα, στον ΠΡΑΓΜΑΤΙΚΟ Z80.

Η πλατφόρμα είναι το μόνο αντικείμενο του παιχνιδιού που δεν ζει σε κελί: έχει
θέση σε pixel και κινείται μέσα στο πλέγμα. Ό,τι από αυτήν πηγαίνει σε
καταχωρητή 8 bit κινδυνεύει, και μέσα σε ένα απόγευμα τρία σφάλματα ήταν
ακριβώς αυτό — το ld (pl_dx),de που αντέστρεψε τους άξονες, το ex de,hl που
χάλασε το y, ο μετρητής στο H που τον έγραφε από πάνω η ίδια η ρουτίνα.

Το test_platform_js.py κρατά μοντέλο και browser συγχρονισμένους· εδώ μπαίνει ο
τρίτος. Το βήμα συγκρίνεται pixel προς pixel με το tools/physics.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
import roomfile as RF

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def room_text(cells, footer=""):
    """Άδειο δωμάτιο με τοίχους και ό,τι βάλεις: [(col, row, char), ...]"""
    rows = [list("#" * P.COLS)] \
        + [list("#" + "." * (P.COLS - 2) + "#") for _ in range(P.ROWS - 2)] \
        + [list("#" * P.COLS)]
    for c, r, ch in cells:
        rows[r][c] = ch
    return ";\n" + "\n".join("".join(x) for x in rows) + "\ngravity 0\n" + footer


def model(cells, footer=""):
    rm = P.Room(room_text(cells, footer))
    rm.number, rm.path = 1, ""
    return rm


# Το ρολόι του firmware (KL_TIME_PLEASE, #BD0D) μετράει 1/300 του δευτερολέπτου
# και το μοντέλο μετράει vsync, 1/50: ΕΞΙ παλμοί ανά vsync. Ο ίδιος λόγος ισχύει
# και για τον συσσωρευτή, γι' αυτό το acc συγκρίνεται πολλαπλασιασμένο.
TICKS_PER_VSYNC = 6


def install_clock(t, vsyncs=1):
    """Κάνει το KL_TIME_PLEASE να προχωράει σταθερά, τόσα vsync τη φορά."""
    step = vsyncs * TICKS_PER_VSYNC
    clk = 0x0140
    code = bytes([0x2A, clk & 0xFF, clk >> 8,       # ld hl,(clk)
                  0x11, step & 0xFF, step >> 8,     # ld de,step
                  0x19,                             # add hl,de
                  0x22, clk & 0xFF, clk >> 8,       # ld (clk),hl
                  0xC9])                            # ret
    for i, b in enumerate(code):
        t.m.memory[0xBD0D + i] = b
    t.poke16(clk, 0)
    return t


def screen_band(t, px, py, rows=P.CELL, nbytes=4):
    """Οι διευθύνσεις ενός κελιού στην οθόνη — ΟΛΕΣ οι γραμμές σάρωσής του.

    MODE 1: 80 bytes ανά γραμμή, 4 pixel το byte, και οι γραμμές πλέκονται ανά
    #800. ΜΙΑ γραμμή δεν αρκεί: η πρώτη γραμμή του διακόπτη είναι διάφανη, και
    ένα τεστ που κοίταζε μόνο εκείνη είπε «δεν σχεδιάζεται» ενώ σχεδιαζόταν.
    """
    return [0xC000 + ((py + i) & 7) * 0x800 + ((py + i) >> 3) * 80 + (px >> 2)
            for i in range(rows)]


def band_bytes(t, addrs, nbytes=4):
    return sum(1 for a in addrs for b in t.peek(a, nbytes) if b)


def band_clear(t, addrs, nbytes=4):
    for a in addrs:
        t.poke(a, b"\x00" * nbytes)


def load(t, rm):
    """Φορτώνει την αίθουσα στον Z80 μέσω του ΚΑΝΟΝΙΚΟΥ room_load."""
    t.poke(t.sym("SET_BUF"), RF.build_set([rm]))
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.call("ROOM_LOAD", a=rm.number)


TICK_STEP = 200


def ticks(t, name, cap=4000):
    """Πόσοι κύκλοι Z80 χρειάζονται ώσπου να κάνει RET η ρουτίνα.

    Ο προσομοιωτής δεν λέει πόσους κατανάλωσε, μόνο σταματά όταν εξαντληθεί το
    ticks_to_stop — οπότε τον τρέχουμε με μικρές δόσεις και μετράμε τις δόσεις.
    Η ακρίβεια είναι TICK_STEP· για τη διαφορά «μισό καρέ ή τέσσερα» αρκεί.
    """
    from z80run import SENTINEL
    t.m.sp = 0xBFF0 - 2
    t.poke16(t.m.sp, SENTINEL)
    t.m.pc = t.sym(name)
    t.m.halted = False
    n = 0
    while not t.m.halted and n < cap:
        t.m.ticks_to_stop = TICK_STEP
        t.m.run()
        n += 1
    return n * TICK_STEP


def rec(t, i=0):
    """Η εγγραφή της i-οστής πλατφόρμας ως λεξικό, με τα ονόματα του asm."""
    base = t.sym("PLAT_TAB") + i * t.sym("PL_SIZE")
    g = lambda off, n=1: (t.peek16(base + off) if n == 2
                          else t.peek(base + off, 1)[0])
    return dict(x=g(0, 2), y=g(2), w=g(3), h=g(4),
                ax=g(5, 2), ay=g(7), bx=g(8, 2), by=g(10),
                ch=g(11), spd=g(12), flg=g(13), acc=g(14, 2), wait=g(16, 2),
                rid=g(18), rdx=g(19), rch=g(20))


def main():
    try:
        from z80run import Z80Test
    except RuntimeError as e:
        print(f"  ΠΑΡΑΛΕΙΨΗ τεστ Z80: {e}")
        return 0

    t = Z80Test()
    t.stub("RENDER_ROOM")
    install_clock(t)
    # Ο πίνακας γραμμών χτίζεται στο ξεκίνημα του παιχνιδιού· χωρίς αυτόν το
    # scr_addr επιστρέφει σκουπίδια και ΚΑΘΕ σχεδίαση γράφει στη μηδενική σελίδα.
    t.call("INIT_LINETAB")
    t.fake_set_load()

    print("--- φόρτωση: η εγγραφή λέει ό,τι λέει το μοντέλο")
    # Οριζόντια πλατφόρμα 3 κελιών, διαδρομή ως τη στήλη 20.
    rm = model([(10, 15, "M"), (11, 15, "M"), (12, 15, "M")],
               "plat 10 15 20 15 3 24\n")
    p0 = rm.platforms[0]
    load(t, rm)
    check("μία πλατφόρμα φορτώθηκε", t.peek(t.sym("PLAT_N"), 1)[0] == 1)
    r = rec(t)
    for key in ("x", "y", "w", "h", "ax", "ay", "bx", "by"):
        check(f"  {key}", r[key] == p0[key], f"{r[key]} vs {p0[key]}")
    check("  ταχύτητα", r["spd"] == p0["speed"], f'{r["spd"]} vs {p0["speed"]}')
    check("  κανάλι", r["ch"] == 3, str(r["ch"]))
    check("  ξεκινά κινούμενη", r["flg"] & 1 == 1, f"flg={r['flg']}")
    check("το κελί της άδειασε", t.peek(t.sym("CELL_BUF") + 15 * P.COLS + 10, 1)[0] == 0)

    VS = 4          # ένα πέρασμα με τον παίκτη να περπατάει
    # ΒΓΑΙΝΩ ΚΑΙ ΞΑΝΑΜΠΑΙΝΩ. Στον browser η πλατφόρμα εξαφανιζόταν: το δωμάτιο
    # αποθήκευε το πλέγμα του στην έξοδο, μαζί με το σβήσιμο των «M». Εδώ το
    # room_load ξαναδιαβάζει από το αρχείο και τα κελιά καθαρίζονται ΧΩΡΙΣ να
    # περάσουν από το ημερολόγιο — αυτός ο έλεγχος το κρατά έτσι.
    first = rec(t)
    t.call("ROOM_LOAD", a=rm.number)
    check("δεύτερη είσοδος: η πλατφόρμα είναι πάλι εκεί",
          t.peek(t.sym("PLAT_N"), 1)[0] == 1)
    again = rec(t)
    check("…με την ίδια εγγραφή", again == first,
          f"{[k for k in first if first[k] != again[k]]}")

    print("--- βήμα: pixel προς pixel με το μοντέλο, μέσα από την αναστροφή")
    install_clock(t, VS)
    # ΤΟ ΠΡΩΤΟ ΒΗΜΑ ΔΕΝ ΕΙΝΑΙ ΣΥΓΚΡΙΣΙΜΟ: ορίζει το plat_last, με ό,τι έδειχνε το
    # ρολόι στη φόρτωση, οπότε ο πρώτος συσσωρευτής είναι μισός. Μετά από αυτό
    # η εγγραφή γυρίζει στην αρχική της κατάσταση και οι δύο ξεκινούν ίσοι.
    t.call("PLAT_STEP")
    base = t.sym("PLAT_TAB")
    t.poke16(base + 14, 0)                          # PL_ACC
    t.poke16(base + 16, 0)                          # PL_WAIT
    t.poke16(base + 0, rm.platforms[0]["x"])        # PL_X
    t.poke(base + 13, b"\x01")                      # PL_FLG: κινείται, προς B
    h = P.Hero(rm, 2 * P.CELL, P.GRID_Y0 + 2 * P.CELL)
    diff = 0
    far, reached = 0, False
    for step in range(120):
        h.plat_step(VS)
        t.call("PLAT_STEP")
        r, m = rec(t), rm.platforms[0]
        if (r["x"], r["y"], r["acc"], r["wait"], r["flg"] >> 1) != \
           (m["x"], m["y"], m["acc"] * TICKS_PER_VSYNC,
            m["wait"] * TICKS_PER_VSYNC, 0 if m["dir"] > 0 else 1):
            if diff == 0:
                print(f"      πρώτη διαφορά στο βήμα {step}: "
                      f"Z80 x={r['x']} acc={r['acc']} wait={r['wait']} "
                      f"vs μοντέλο x={m['x']} acc={m['acc']} wait={m['wait']}")
            diff += 1
        far = max(far, r["x"])
        reached = reached or r["x"] == rm.platforms[0]["bx"]
    check("120 βήματα, καμία διαφορά από το μοντέλο", diff == 0, f"{diff} διαφορές")
    check("…και όντως έφτασε στο άκρο μέσα σε αυτά", reached,
          f"max x={far} από {rm.platforms[0]['bx']}")

    print("--- στερεή ΑΠΟ ΠΑΝΤΟΥ, σαν τοίχος")
    rm = model([(10, 15, "M"), (11, 15, "M")], "plat 10 15 20 15 0 24\n")
    load(t, rm)
    py = P.GRID_Y0 + 15 * P.CELL
    for g in (0, 4, 2, 6):
        t.poke(t.sym("HERO_G"), bytes((g,)))
        t.call("PLAT_SOLID", bc=10 * P.CELL + 4, de=py + 2)
        got = bool(t.m.f & 1)
        rm.probe_g = g
        want = bool(rm.plat_at(10 * P.CELL + 4, py + 2))
        check(f"  βαρύτητα {g}: στερεή", got, f"CF={int(got)}")
        check(f"  …και το μοντέλο συμφωνεί", want == got)
    t.call("PLAT_SOLID", bc=30 * P.CELL, de=py + 2)
    check("  μακριά της: κενό", not (t.m.f & 1))

    print("--- …και σε ΚΟΥΒΑΛΑΕΙ με όποια φορά κι αν πατάς")
    # ΤΟ ps_riding ΞΑΝΑΓΡΑΦΤΗΚΕ ΓΙ' ΑΥΤΟ: μετρούσε τα πέλματα με σκέτη πρόσθεση,
    # που ισχύει μόνο με βαρύτητα προς τα κάτω. Τώρα περνά από το h_point, με
    # τους ίδιους πίνακες που χρησιμοποιεί όλη η φυσική. Χωρίς αυτόν τον έλεγχο
    # ο κώδικας για τις άλλες τρεις φορές δεν θα εκτελούνταν ποτέ σε τεστ.
    for g in (0, 4, 2, 6):
        rm = model([(10, 15, "M"), (11, 15, "M")], "plat 10 15 20 15 0 24\n")
        load(t, rm)
        c = rec(t)
        # Ο ήρωας με τα πέλματά του ΜΕΣΑ στην πλατφόρμα, από τη μεριά που τον
        # φέρνει αυτή η βαρύτητα. Το off() είναι του μοντέλου — ίδιος πίνακας.
        fx, fy = P.off(g, 0, P.FEET_B)
        # ΤΑ ΠΕΛΜΑΤΑ ΔΕΙΧΝΟΥΝ ΠΡΟΣ ΤΗ ΒΑΡΥΤΗΤΑ, άρα η πλατφόρμα είναι ΑΠΟ ΕΚΕΙΝΗ
        # τη μεριά του: με βαρύτητα 2 (αριστερά) πατάει τη ΔΕΞΙΑ της όψη. Τα
        # είχα ανάποδα και ο ήρωας έμπαινε ΜΕΣΑ της — το ps_riding έλεγε «ναι»
        # και το ps_carry ακύρωνε την κίνηση, που έμοιαζε με σφάλμα του κώδικα.
        inside = (c["x"] + c["w"] // 2, c["y"] + 1) if g == 0 else \
                 (c["x"] + c["w"] // 2, c["y"] + c["h"] - 2) if g == 4 else \
                 (c["x"] + c["w"] - 2, c["y"] + c["h"] // 2) if g == 2 else \
                 (c["x"] + 1, c["y"] + c["h"] // 2)
        t.poke16(t.sym("HERO_X"), inside[0] - fx)
        t.poke16(t.sym("HERO_Y"), inside[1] - fy)
        t.poke(t.sym("HERO_G"), bytes((g,)))
        t.m.ix = t.sym("PLAT_TAB")
        t.call("PS_RIDING")
        check(f"βαρύτητα {g}: ο Z80 βλέπει ότι την πατάει", bool(t.m.f & 1),
              f"ήρωας ({t.peek16(t.sym('HERO_X'))},{t.peek16(t.sym('HERO_Y'))})")

        install_clock(t, 4)
        hx0, hy0 = t.peek16(t.sym("HERO_X")), t.peek16(t.sym("HERO_Y"))
        px0, py0 = c["x"], c["y"]
        t.call("PLAT_STEP")             # ορίζει το ρολόι
        for _ in range(12):
            t.call("PLAT_STEP")
        c2 = rec(t)
        moved = (c2["x"] - px0, c2["y"] - py0)
        hero = (t.peek16(t.sym("HERO_X")) - hx0, t.peek16(t.sym("HERO_Y")) - hy0)
        check(f"βαρύτητα {g}: ταξιδεύει μαζί της",
              moved != (0, 0) and hero == moved,
              f"πλατφόρμα +{moved}, ήρωας +{hero}")

    print("--- ο διακόπτης του καναλιού τη σταματάει και την ξεκινάει")
    rm = model([(10, 15, "M"), (11, 15, "M")], "plat 10 15 20 15 5 24\n")
    load(t, rm)
    check("ξεκινά κινούμενη", rec(t)["flg"] & 1 == 1)
    t.call("GATE_TOGGLE", a=5)
    check("κανάλι 5 -> σταμάτησε", rec(t)["flg"] & 1 == 0, f"flg={rec(t)['flg']}")
    x0 = rec(t)["x"]
    for _ in range(10):
        t.call("PLAT_STEP")
    check("…και όντως δεν κουνήθηκε", rec(t)["x"] == x0, f"{rec(t)['x']} vs {x0}")
    t.call("GATE_TOGGLE", a=4)
    check("άλλο κανάλι δεν την αγγίζει", rec(t)["flg"] & 1 == 0)
    t.call("GATE_TOGGLE", a=5)
    check("κανάλι 5 ξανά -> ξεκίνησε", rec(t)["flg"] & 1 == 1)
    for _ in range(4):          # το οριζόντιο βήμα είναι 4 pixel: τετραπλάσιο
        t.call("PLAT_STEP")     # κατώφλι, άρα και τετραπλάσια αναμονή
    check("…και κουνήθηκε", rec(t)["x"] != x0, f"{rec(t)['x']} vs {x0}")

    print("--- ο επιβάτης-διακόπτης ταξιδεύει μαζί της")
    # Διακόπτης «κοιτάζει πάνω» στο κελί ΑΚΡΙΒΩΣ από πάνω της.
    rm = model([(10, 15, "M"), (11, 15, "M"), (10, 14, "s"),
                (30, 15, "G")],
               "plat 10 15 18 15 0 24\nsw 10 14 6\ngate 30 15 6\n")
    p0 = rm.platforms[0]
    check("το μοντέλο τον πήρε για επιβάτη", p0["rider"] != 0, str(p0["rider"]))
    load(t, rm)
    r = rec(t)
    check("  ο Z80 επίσης", r["rid"] == p0["rider"], f"{r['rid']} vs {p0['rider']}")
    check("  ίδια μετατόπιση", r["rdx"] == p0["rdx"], f"{r['rdx']} vs {p0['rdx']}")
    check("  ίδιο κανάλι", r["rch"] == 6, str(r["rch"]))
    check("το κελί του άδειασε",
          t.peek(t.sym("CELL_BUF") + 14 * P.COLS + 10, 1)[0] == 0)

    # Το πάτημα: ο ήρωας πάνω στο κουτί του επιβάτη, με βαρύτητα από πάνω.
    before = rec(t)
    t.poke16(t.sym("HERO_X"), before["x"] + before["rdx"] + 2)
    t.poke16(t.sym("HERO_Y"), before["y"] - P.CELL + 2)
    t.poke(t.sym("HERO_G"), b"\x00")
    t.poke(t.sym("PT_PREV"), b"\xFF")
    t.call("PLAT_TOUCH")
    r = rec(t)
    check("πάτημα -> ο επιβάτης γύρισε σε πατημένο",
          r["rid"] != before["rid"], f"{before['rid']} -> {r['rid']}")
    gate = t.peek(t.sym("CELL_BUF") + 15 * P.COLS + 30, 1)[0]
    check("…και άνοιξε την πύλη του καναλιού 6", gate == P.GATE_OPEN,
          f"{gate} vs {P.GATE_OPEN}")
    kind = r["rid"]
    t.call("PLAT_TOUCH")
    check("δεύτερο πέρασμα χωρίς να φύγει: ΔΕΝ ξαναγυρίζει (ακμή)",
          rec(t)["rid"] == kind, f"{kind} -> {rec(t)['rid']}")

    # Και μακριά του: δεν πατιέται από απόσταση, ούτε καν στο διπλανό pixel.
    t.poke16(t.sym("HERO_X"), before["x"] + before["rdx"] + 3 * P.CELL)
    t.call("PLAT_TOUCH")
    check("μακριά του δεν πατιέται", rec(t)["rid"] == kind)

    # Και το κουτί ΤΑΞΙΔΕΥΕΙ: μετά από βήματα, το πάτημα θέλει τη νέα θέση.
    for _ in range(20):
        t.call("PLAT_STEP")
    moved = rec(t)
    check("η πλατφόρμα προχώρησε", moved["x"] != before["x"],
          f"{before['x']} -> {moved['x']}")
    t.poke16(t.sym("HERO_X"), before["x"] + before["rdx"] + 2)   # ΠΑΛΙΑ θέση
    t.poke(t.sym("PT_PREV"), b"\xFF")
    t.call("PLAT_TOUCH")
    check("στην παλιά του θέση δεν πατιέται πια", rec(t)["rid"] == kind)
    t.poke16(t.sym("HERO_X"), moved["x"] + moved["rdx"] + 2)     # ΝΕΑ θέση
    t.call("PLAT_TOUCH")
    check("στη νέα του θέση πατιέται", rec(t)["rid"] != kind,
          f"{kind} -> {rec(t)['rid']}")

    print("--- …ΚΑΙ ΦΑΙΝΕΤΑΙ: ο επιβάτης σχεδιάζεται μαζί της")
    # ΓΙΑΤΙ ΞΕΧΩΡΙΣΤΟΣ ΕΛΕΓΧΟΣ: στον browser ο διακόπτης του επιβάτη δούλεψε
    # από την πρώτη στιγμή και ήταν ΑΟΡΑΤΟΣ — η σχεδίασή του είχε χαθεί σε ένα
    # script που μισο-εφαρμόστηκε. Το ίδιο σπάσιμο στον Z80 δεν κοκκίνιζε
    # τίποτα, ώσπου μπήκε αυτό.
    r = rec(t)
    band = screen_band(t, r["x"] + r["rdx"], r["y"] - P.CELL)
    band_clear(t, band)
    t.call("PLAT_DRAW")
    drawn = band_bytes(t, band)
    check("με επιβάτη, το κελί από πάνω της γράφτηκε", drawn > 0, f"{drawn} bytes")

    t.poke(t.sym("PLAT_TAB") + 18, b"\x00")     # PL_RID = κανένας
    band_clear(t, band)
    t.call("PLAT_DRAW")
    empty = band_bytes(t, band)
    check("χωρίς επιβάτη, το ίδιο κελί μένει άδειο", empty == 0, f"{empty} bytes")

    # ΚΑΙ ΤΑΞΙΔΕΥΕΙ: μετά από βήματα σχεδιάζεται στη ΝΕΑ θέση, όχι στην παλιά.
    t.poke(t.sym("PLAT_TAB") + 18, bytes((r["rid"],)))
    for _ in range(20):
        t.call("PLAT_STEP")
    m = rec(t)
    old_band = band
    new_band = screen_band(t, m["x"] + m["rdx"], m["y"] - P.CELL)
    band_clear(t, old_band)
    band_clear(t, new_band)
    t.call("PLAT_DRAW")
    check("μετά την κίνηση γράφεται στη νέα του θέση",
          band_bytes(t, new_band) > 0, f'x={m["x"]}')

    print("--- το σβήσιμο: χωρίς ίχνη ΚΑΙ χωρίς στιγμή που λείπει")
    # ΜΕ ΕΠΙΒΑΤΗ: το κελί του είναι σχεδόν όλο διάφανο, οπότε είναι εκείνο που
    # μουτζουρώνει χειρότερα — μια δοκιμή χωρίς αυτόν θα έλεγε «καθαρό».
    rm = model([(10, 15, "M"), (11, 15, "M"), (10, 14, "s")],
               "plat 10 15 20 15 0 24\nsw 10 14 6\n")
    load(t, rm)
    t.call("PLAT_SAVE")

    # Η ζώνη που μπορεί να ακουμπήσει: όλη η διαδρομή της, η σειρά της και η
    # σειρά του επιβάτη από πάνω.
    zone = [0xC000 + ((y) & 7) * 0x800 + ((y) >> 3) * 80 + col
            for y in range(P.GRID_Y0 + 14 * P.CELL, P.GRID_Y0 + 16 * P.CELL)
            for col in range(18, 44)]

    def zone_bytes():
        return bytes(t.m.memory[a] for a in zone)

    for a in zone:
        t.m.memory[a] = 0
    t.call("PLAT_DRAW")
    at_start = zone_bytes()
    ink = sum(1 for b in at_start if b)
    check("η πλατφόρμα ζωγραφίστηκε", ink > 0, f"{ink} bytes")

    # ΣΤΙΓΜΗ ΠΟΥ ΛΕΙΠΕΙ: ανάμεσα στο σβήσιμο και τη σχεδίαση μεσολαβεί το
    # draw_hero. Ό,τι λείπει εκεί, τρεμοπαίζει.
    worst = ink
    steps = 0
    while steps < 60:
        t.call("PLAT_SAVE")
        t.call("PLAT_STEP")
        t.call("PLAT_ERASE")
        worst = min(worst, sum(1 for b in zone_bytes() if b))
        t.call("PLAT_DRAW")
        steps += 1
        if rec(t)["x"] == 10 * P.CELL + 2 * P.CELL:
            break
    check("μετά το σβήσιμο το σώμα της είναι ακόμα εκεί",
          worst >= ink * 3 // 4, f"χειρότερο: {worst} από {ink} bytes")

    # ΙΧΝΗ: στη νέα θέση η οθόνη πρέπει να είναι ΑΚΡΙΒΩΣ ό,τι θα ζωγράφιζε μια
    # καθαρή σχεδίαση εκεί. Ένα pixel που ξέμεινε πίσω της φαίνεται εδώ.
    moved = zone_bytes()
    for a in zone:
        t.m.memory[a] = 0
    t.call("PLAT_DRAW")
    clean = zone_bytes()
    bad = sum(1 for x, y in zip(moved, clean) if x != y)
    check(f"καμία διαφορά από καθαρή σχεδίαση μετά από {steps} βήματα",
          bad == 0, f"{bad} bytes διαφορά, x={rec(t)['x']}")

    print("--- …και βάφει το ΦΟΝΤΟ ΤΗΣ ΠΙΣΤΑΣ, όχι μαύρο")
    # Το σβήσιμο γράφει ΤΟ BYTE ΤΟΥ ΠΛΑΚΙΔΙΟΥ που κάθεται από κάτω. Με το
    # draw_tile αυτό ερχόταν τζάμπα· σε επίπεδο byte είναι δική μας δουλειά.
    col, row = 25, 15
    t.poke(t.sym("CELL_BUF") + row * P.COLS + col, bytes((P.SOLID,)))
    y = P.GRID_Y0 + row * P.CELL + 3
    tile = t.sym("TILE_GFX") + P.SOLID * 16 + (y % 8) * 2
    for half in (0, 1):
        t.call("PL_BGBYTE", bc=((col * 2 + half) << 8) | y)
        want = t.peek(tile + half, 1)[0]
        check(f"πάνω σε τοίχο, μισό {half}", t.m.a == want,
              f"#{t.m.a:02X} vs #{want:02X}")
    t.poke(t.sym("CELL_BUF") + row * P.COLS + col, b"\x00")
    t.call("PB_FORGET")     # ο cache κρατά ΕΝΑ κελί· το παιχνίδι τον σβήνει
    t.call("PL_BGBYTE", bc=((col * 2) << 8) | y)
    check("πάνω σε κενό, κενό byte", t.m.a == 0, f"#{t.m.a:02X}")
    t.call("PL_BGBYTE", bc=((col * 2) << 8) | 4)
    check("στη ζώνη του HUD δεν διαβάζει πλακίδιο", t.m.a == 0, f"#{t.m.a:02X}")

    # Η μάσκα: ποια bits του φόντου επιβιώνουν κάτω από ένα byte μελανιού.
    for ink, want in ((0x00, 0xFF),     # όλο διάφανο -> όλο το φόντο
                      (0xFF, 0x00),     # όλο μελάνι  -> τίποτα
                      (0x80, 0x77),     # pen στο pixel 0 (πάνω επίπεδο)
                      (0x08, 0x77)):    # …και στο κάτω: ίδιο pixel, ίδια μάσκα
        t.call("PL_MASK", a=ink)
        check(f"μάσκα του #{ink:02X}", t.m.a == want,
              f"#{t.m.a:02X} vs #{want:02X}")

    print("--- ένα κελί που ΑΛΛΑΞΕ φαίνεται αμέσως")
    # Ο cache του pl_bgbyte κρατά ένα κελί ώστε ο επιβάτης να μη ψάχνει οκτώ
    # φορές το ίδιο. Μια πύλη που ανοίγει από κάτω του αλλάζει τον τύπο — χωρίς
    # ακύρωση ο επιβάτης θα συντίθετο με το ΠΑΛΙΟ πλακίδιο, και κανένα τεστ δεν
    # το έπιανε ώσπου μπήκε αυτό.
    rm = model([(10, 15, "M"), (11, 15, "M"), (10, 14, "s")],
               "plat 10 15 20 15 0 24\nsw 10 14 6\n")
    load(t, rm)
    r = rec(t)
    band = screen_band(t, r["x"] + r["rdx"], r["y"] - P.CELL)
    t.call("PLAT_DRAW")                 # γεμίζει τον cache με το κενό κελί
    before = band_bytes(t, band)
    t.poke(t.sym("CELL_BUF") + 14 * P.COLS + 10, bytes((P.SOLID,)))
    band_clear(t, band)
    t.call("PLAT_DRAW")
    after = band_bytes(t, band)
    check("τοίχος κάτω από τον επιβάτη -> περισσότερο μελάνι",
          after > before, f"{before} -> {after} bytes")
    t.poke(t.sym("CELL_BUF") + 14 * P.COLS + 10, b"\x00")

    print("--- ο ήρωας πάνω στον διακόπτη: κανείς δεν σβήνει τον άλλο")
    # ΤΟ ΣΦΑΛΜΑ: ο επιβάτης ζωγραφιζόταν ΜΕΤΑ τον ήρωα και, εκεί που είναι
    # διάφανος, έβαφε φόντο πάνω στα πόδια του. Η δέσμη τον έπιανε άλλοτε
    # ζωγραφισμένο κι άλλοτε σβησμένο — τρεμόπαιγμα ακριβώς όταν πατάς τον
    # διακόπτη. Τώρα η πλατφόρμα μπαίνει στο ΦΟΝΤΟ του ήρωα (plat_bgline) και
    # η σχεδίαση δεν ξαναγράφει ό,τι εκείνος ζωγράφισε.
    rm = model([(10, 15, "M"), (11, 15, "M"), (10, 14, "s")],
               "plat 10 15 20 15 0 24\nsw 10 14 6\n")
    load(t, rm)
    r = rec(t)
    hero_col = (r["x"] + r["rdx"]) >> 2          # η στήλη του επιβάτη
    hero_top = r["y"] - P.CELL

    def set_hero_rect(col, w, top, bot):
        t.poke(t.sym("DH_C0"), bytes((col,)))
        t.poke(t.sym("DH_W"), bytes((w,)))
        t.poke(t.sym("DH_TOP"), bytes((top,)))
        t.poke(t.sym("DH_Y1"), bytes((bot,)))

    # Ο ήρωας «ζωγράφισε» ένα ορθογώνιο πάνω στο κελί του επιβάτη.
    MARK = 0x5A
    # ΚΑΙ ΟΙ ΔΥΟ ΖΩΝΕΣ, του επιβάτη ΚΑΙ του σώματος: με μόνο του επιβάτη, ένα
    # σπάσιμο που άφηνε το σώμα να γράφει πάνω στον ήρωα έμενε πράσινο.
    inside = (screen_band(t, r["x"] + r["rdx"], hero_top)
              + screen_band(t, r["x"], r["y"]))
    set_hero_rect(hero_col, 2, hero_top, r["y"] + P.CELL - 1)
    for a in inside:
        t.poke(a, bytes([MARK] * 2))
    t.call("PLAT_DRAW")
    kept = sum(1 for a in inside for b in t.peek(a, 2) if b == MARK)
    check("ό,τι ζωγράφισε ο ήρωας μένει ανέγγιχτο", kept == len(inside) * 2,
          f"{kept} από {len(inside) * 2} bytes")

    # …και ΕΞΩ από το ορθογώνιό του η πλατφόρμα είναι ΑΚΡΙΒΩΣ όπως θα ήταν
    # χωρίς αυτόν. ΟΧΙ «υπάρχει κάτι»: το pd_split χαλούσε το BC — τα δύο bytes
    # του πλακιδίου — και οι στήλες δεξιά του ήρωα γράφονταν με σκουπίδια. Ένας
    # έλεγχος «μη μηδενικό» τα δεχόταν, γιατί τα σκουπίδια δεν ήταν μηδενικά.
    set_hero_rect(0, 0, 0, 0)
    body = screen_band(t, r["x"], r["y"])

    def paint(dy):
        """Ένα πλήρες πέρασμα σχεδίασης με τον ήρωα dy pixel από την πλατφόρμα."""
        load(t, rm)
        c = rec(t)
        t.poke16(t.sym("HERO_X"), c["x"] + 4)
        t.poke16(t.sym("HERO_Y"), c["y"] + dy)
        t.poke(t.sym("HERO_G"), b"\x00")
        for a in screen_band(t, c["x"], c["y"] - 2 * P.CELL, rows=40):
            t.poke(a, b"\x00" * 4)
        t.call("PREP_HERO")
        t.call("PLAT_ERASE")
        t.call("DRAW_HERO")
        t.call("PLAT_DRAW")
        return [bytes(t.peek(a, 4)) for a in body]

    far = paint(-40)                    # ο ήρωας αλλού: η αναφορά
    near = paint(4)                     # ο ήρωας μέσα στις γραμμές της
    c0 = t.peek(t.sym("DH_C0"), 1)[0]
    w = t.peek(t.sym("DH_W"), 1)[0]
    col0 = r["x"] >> 2
    bad = wrong = blank = 0
    for row_far, row_near in zip(far, near):
        for i in range(4):
            inside = c0 <= col0 + i < c0 + w
            if inside:
                blank += 1 if row_near[i] == 0 else 0
            elif row_near[i] != row_far[i]:
                wrong += 1
        bad += 1
    check("έξω από τον ήρωα η πλατφόρμα είναι ΙΔΙΑ με το χωρίς αυτόν",
          wrong == 0, f"{wrong} bytes διαφορετικά (παράθυρο {c0}..{c0 + w - 1})")
    check("…και μέσα στο ορθογώνιό του δεν μένει κενή",
          blank == 0, f"{blank} άδεια bytes — ο ήρωας την έσβησε")

    # ΚΑΙ ΜΕΣΑ ΣΤΟ ΦΟΝΤΟ ΤΟΥ: το linebuf πρέπει να έχει την πλατφόρμα, αλλιώς
    # ο ήρωας θα την έσβηνε σε όλο του το ορθογώνιο κάθε πέρασμα.
    lb = t.sym("LINEBUF")
    body_col = r["x"] >> 2
    rid_col = (r["x"] + r["rdx"]) >> 2

    def mask_of(ink):
        """Τα bits του φόντου που επιβιώνουν — ό,τι κάνει το pl_mask."""
        nib = ((ink >> 4) | ink) & 0x0F
        return ~(nib | (nib << 4)) & 0xFF

    def bgline(line, fill=0xFF):
        t.poke(t.sym("DH_YY"), bytes((line,)))
        t.poke(t.sym("DH_C0"), bytes((body_col,)))
        t.poke(t.sym("DH_W"), b"\x08")
        t.poke(lb, bytes([fill]) * 8)
        t.call("PLAT_BGLINE")
        return t.peek(lb, 8)

    # ΤΟ ΣΩΜΑ: αδιαφανές, άρα το byte του πλακιδίου αυτούσιο.
    v = 2
    tile = t.sym("TILE_GFX") + P.PLATFORM * 16 + v * 2
    want = [t.peek(tile + (i & 1), 1)[0] for i in range(4)] + [0xFF] * 4
    got = list(bgline(r["y"] + v))
    check("το σώμα μπαίνει στο φόντο του ήρωα, byte προς byte", got == want,
          f"{[f'{b:02X}' for b in got]} vs {[f'{b:02X}' for b in want]}")

    # Ο ΕΠΙΒΑΤΗΣ: διάφανος, άρα (φόντο ΚΑΙ μάσκα) Ή μελάνι. ΟΧΙ πλήθος bytes:
    # ένα «υπάρχει κάτι» δεχόταν το σφάλμα όπου το pl_mask χαλούσε το μελάνι.
    # ΚΑΙ ΟΧΙ ΜΕ ΦΟΝΤΟ #FF: εκεί το (φόντο & μάσκα) | μελάνι βγαίνει #FF ό,τι κι
    # αν κάνει ο κώδικας — η πρώτη εκδοχή αυτού του ελέγχου δεν έλεγχε τίποτα.
    v = 5
    tile = t.sym("TILE_GFX") + r["rid"] * 16 + v * 2
    off = rid_col - body_col
    for fill in (0x00, 0x0F):
        want = [fill] * 8
        for i in range(2):
            ink = t.peek(tile + i, 1)[0]
            want[off + i] = (fill & mask_of(ink)) | ink
        got = list(bgline(r["y"] - P.CELL + v, fill))
        check(f"ο επιβάτης πάνω σε φόντο #{fill:02X}, byte προς byte", got == want,
              f"{[f'{b:02X}' for b in got]} vs {[f'{b:02X}' for b in want]}")

    t.poke(t.sym("DH_W"), b"\x00")

    print("--- ΤΟ ΚΟΣΤΟΣ: πρέπει να τελειώνει πριν τη δέσμη")
    # ΑΥΤΟΣ ΕΙΝΑΙ Ο ΦΥΛΑΚΑΣ ΤΟΥ ΤΡΕΜΟΠΑΙΓΜΑΤΟΣ, και ο μόνος έλεγχος εδώ που
    # μετράει χρόνο. Η σχεδίαση ανά pixel κόστιζε 150.000 κύκλους και το
    # σβήσιμο 175.000 — μαζί τέσσερα καρέ των 50 Hz, οπότε η δέσμη έβρισκε την
    # πλατφόρμα πάντα μισοσχεδιασμένη. Κανένα άλλο τεστ δεν το έπιανε αυτό:
    # η οθόνη έβγαινε σωστή, απλώς πολύ αργά.
    rm = model([(10, 15, "M"), (11, 15, "M"), (12, 15, "M"), (10, 14, "s")],
               "plat 10 15 20 15 0 24\nsw 10 14 6\n")
    load(t, rm)
    x0 = rec(t)["x"]
    while rec(t)["x"] == x0:            # να έχει όντως κουνηθεί
        t.call("PLAT_SAVE")
        t.call("PLAT_STEP")
    budget = 4_000_000 // 50            # ένα καρέ 50 Hz σε κύκλους Z80
    total = 0
    for r in ("PLAT_ERASE", "PLAT_DRAW"):
        n = ticks(t, r)
        total += n
        print(f"      {r}: ~{n} κύκλοι = {n / 4000:.2f} ms")
    check("σβήσιμο + σχεδίαση χωράνε σε ΜΙΣΟ καρέ", total < budget // 2,
          f"{total} κύκλοι, {100 * total / budget:.0f}% ενός καρέ")

    print(f"\n{'ΟΛΑ ΚΑΛΑ' if not FAILS else 'ΑΠΕΤΥΧΑΝ: ' + ', '.join(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
