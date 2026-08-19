#!/usr/bin/env python3
"""Τρέχει ΤΟΝ ΙΔΙΟ κώδικα Z80 που μπαίνει στη δισκέτα, σε προσομοιωτή.

Το parity harness (Python <-> JavaScript) δεν μπορεί να πιάσει σφάλματα που
υπάρχουν μόνο στον Z80: καμία από τις δύο γλώσσες δεν έχει καταχωρητές 8 bit
ούτε flags. Δύο τέτοια σφάλματα έφτασαν στον χρήστη — το type*16 που έδειχνε
τα κιβώτια σαν αγκάθια και το col*8 που έστελνε τον teleporter αλλού. Και τα
δύο ήταν υπερχείλιση σε 8 bit· και τα δύο πιάνονται εδώ.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import physics as P
import roomfile as RF

# Τι χαλάει στ' αλήθεια το SOUND QUEUE (#BCAA) — SOFT968: «A, BC, DE, IX and
# the other flags are corrupt». Το harness από μόνο του κάνει RET, που τα
# διατηρεί όλα· η διαφορά κόστισε ένα MUSIC.BIN που κρατούσε δείκτη στο IX.
# Ο ήχος του παιχνιδιού δεν αγγίζει index registers, οπότε εδώ ο έλεγχος απλώς
# κλειδώνει ότι θα συνεχίσει να μην τους αγγίζει.
FW_QUEUE_KILLS = ("a", "bc", "de", "hl", "ix")

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def main():
    try:
        from z80run import Z80Test
    except RuntimeError as e:
        print(f"  ΠΑΡΑΛΕΙΨΗ τεστ Z80: {e}")
        return 0

    t = Z80Test()
    t.stub("RENDER_ROOM")           # χωρίς οθόνη δεν έχει τι να επαληθεύσει
    cell_buf = t.sym("CELL_BUF")
    set_buf = t.sym("SET_BUF")

    # 1. hero_to_cell: col*8 πρέπει να γίνεται σε 16 bits. Με 'add a,a' σε 8
    #    bits, κάθε στήλη από 32 και πάνω τύλιγε και ο ήρωας προσγειωνόταν
    #    στην αριστερή άκρη της οθόνης.
    scratch = 0x0100
    for col, row in ((0, 0), (26, 22), (32, 0), (37, 22), (39, 23)):
        t.poke(scratch, bytes((col, row)))
        t.call("HERO_TO_CELL", hl=scratch)
        got = (t.peek16(t.sym("HERO_X")), t.peek16(t.sym("HERO_Y")))
        want = (col * P.CELL + P.CELL // 2, P.GRID_Y0 + row * P.CELL + P.CELL // 2)
        check(f"hero_to_cell ({col},{row})", got == want, f"{got} vs {want}")

    # 2. rle_unpack: ό,τι κωδικοποιεί η Python πρέπει να το ξεδιπλώνει ο Z80
    #    byte προς byte. Εδώ συγκρίνονται ΟΛΑ τα 960 κελιά κάθε αίθουσας.
    for room in P.all_rooms():
        flat = bytes(v for r in room.cells for v in r)
        packed = RF.rle_encode(flat)
        t.poke(scratch, packed)
        t.poke(cell_buf, b"\xAA" * RF.CELLS)        # γέμισε με σκουπίδια πρώτα
        t.m.ix = scratch
        t.call("RLE_UNPACK", de=cell_buf)
        got = t.peek(cell_buf, RF.CELLS)
        check(f"rle_unpack room_{room.number}", got == flat,
              f"{len(packed)} bytes -> {RF.CELLS} κελιά")

    # 3. room_find + room_load πάνω στο ΠΡΑΓΜΑΤΙΚΟ αρχείο σετ.
    set_load_orig = t.fake_set_load()
    for index, name, data in RF.all_sets():
        t.poke(set_buf, data)
        t.poke(t.sym("JR_COUNT"), b"\x00")

        for room in P.all_rooms():
            if RF.set_of(room.number) != index:
                continue
            t.call("ROOM_LOAD", a=room.number)

            flat = bytes(v for r in room.cells for v in r)
            got = t.peek(cell_buf, RF.CELLS)
            check(f"room_load {room.number}: πλέγμα", got == flat)
            check(f"room_load {room.number}: level_ptr",
                  t.peek16(t.sym("LEVEL_PTR")) == cell_buf)
            check(f"room_load {room.number}: βαρύτητα",
                  t.peek(t.sym("HERO_G"))[0] == room.start_g,
                  f"{t.peek(t.sym('HERO_G'))[0]} vs {room.start_g}")

            # Οι τρεις πίνακες δείχνουν ΜΕΣΑ στο σετ και ο καθένας τελειώνει
            # στο #FF του. Λάθος βάδισμα εδώ θα έδινε εξόδους-σκουπίδια.
            expect_exits = [(c, r, dest, 1 if two else 0)
                            for _, dest, two, cells in room.exit_groups()
                            for c, r in cells]
            expect_arr = [(o.number,) + tuple(room.arrival_for(o.number))
                          for o in P.all_rooms()
                          if room.arrival_for(o.number)]
            expect_tps = [(c, r, d[0], d[1])
                          for _, d, cells in room.teleport_groups() if d
                          for c, r in cells]

            for label, expect in (("ROOM_EXITS", expect_exits),
                                  ("ROOM_ARR", expect_arr),
                                  ("ROOM_TPS", expect_tps)):
                ptr = t.peek16(t.sym(label))
                check(f"room_load {room.number}: {label} μέσα στο σετ",
                      set_buf <= ptr < set_buf + len(data),
                      f"#{ptr:04X} εκτός #{set_buf:04X}..#{set_buf+len(data):04X}")
                got, p = [], ptr
                while t.peek(p)[0] != 0xFF and len(got) < 64:
                    got.append(tuple(t.peek(p, 4)))
                    p += 4
                check(f"room_load {room.number}: {label}",
                      got == expect, f"{got} vs {expect}")

    # Ο δρόμος του δίσκου ξαναγίνεται αληθινός: τα επόμενα τεστ ελέγχουν
    # ακριβώς αυτόν.
    t.poke(t.sym("SET_LOAD"), set_load_orig)

    # 3β. Το όνομα αρχείου φτιάχνεται με δύο ψηφία επιτόπου. Λάθος εδώ και το
    #     παιχνίδι ζητά αρχείο που δεν υπάρχει — χωρίς κανένα μήνυμα.
    for index, want in ((1, b"ROOMS01.BIN"), (9, b"ROOMS09.BIN"),
                        (10, b"ROOMS10.BIN"), (42, b"ROOMS42.BIN")):
        t.call("SET_LOAD", a=index)     # το firmware εδώ είναι RET, άρα αποτυγχάνει
        got = t.peek(t.sym("SET_FNAME"), 11)
        check(f"set_load: όνομα για σετ {index}", got == want, f"{got} vs {want}")
        check(f"set_load: αποτυχία δίσκου δεν κλειδώνει το σετ {index}",
              t.peek(t.sym("SET_CUR"))[0] == 0)

    # 3γ. ΠΟΙΑ ΑΙΘΟΥΣΑ ΣΕ ΠΟΙΟ ΣΕΤ. Ο Z80 το βγάζει με επαναλαμβανόμενη
    #     αφαίρεση του SET_ROOMS, η Python με διαίρεση. Δύο υλοποιήσεις της
    #     ίδιας πράξης — και το SET_ROOMS μόλις άλλαξε από 40 σε 4, οπότε αν
    #     κάπου έμεινε καρφωμένο το παλιό, το παιχνίδι θα ζητούσε λάθος
    #     αρχείο και θα έσκαγε με «not found».
    for room_no in (1, 2, 4, 5, 8, 9, 12, 13, 40, 41, 99):
        t.poke(t.sym("SET_CUR"), b"\x00")
        t.call("ROOM_LOAD", a=room_no)      # ο δίσκος αποτυγχάνει· μας νοιάζει
        got = t.peek(t.sym("SET_FNAME"), 11)   # ΠΟΙΟ αρχείο ζήτησε
        want = f"ROOMS{RF.set_of(room_no):02d}.BIN".encode()
        check(f"αίθουσα {room_no} -> {want.decode()}", got == want,
              f"{got.decode(errors='replace')} vs {want.decode()}")

    t.fake_set_load()       # ξανά: κανένα από τα υπόλοιπα δεν δοκιμάζει δίσκο

    # 4. Το ημερολόγιο: ό,τι αλλάζει ο παίκτης πρέπει να επιβιώνει όταν
    #    ξαναμπαίνει στην αίθουσα. Χωρίς αυτό η ενέργεια θα ήταν άπειρη —
    #    μπες, βγες, ξαναμάζεψέ τη.
    rooms = [r for r in P.all_rooms()]
    if rooms:
        room = rooms[0]
        index = RF.set_of(room.number)
        data = dict((i, d) for i, _, d in RF.all_sets())[index]
        t.poke(set_buf, data)
        t.poke(t.sym("SET_CUR"), bytes((index,)))
        t.poke(t.sym("JR_COUNT"), b"\x00")
        t.call("ROOM_LOAD", a=room.number)

        off = 3 * P.COLS + 5                        # ένα οποιοδήποτε κελί
        t.call("CELL_SET", hl=cell_buf + off, a=P.CRATE)
        check("cell_set: γράφει το κελί",
              t.peek(cell_buf + off)[0] == P.CRATE)
        check("cell_set: κρατά μία εγγραφή", t.peek(t.sym("JR_COUNT"))[0] == 1)

        t.call("CELL_SET", hl=cell_buf + off, a=P.EMPTY)
        check("cell_set: το ίδιο κελί ΔΕΝ προσθέτει δεύτερη εγγραφή",
              t.peek(t.sym("JR_COUNT"))[0] == 1,
              f"{t.peek(t.sym('JR_COUNT'))[0]}")

        t.call("ROOM_LOAD", a=room.number)          # ξαναμπές
        check("η αλλαγή επιβιώνει της επιστροφής",
              t.peek(cell_buf + off)[0] == P.EMPTY,
              P.TYPE_NAMES[t.peek(cell_buf + off)[0]])

        # Άλλη αίθουσα δεν πρέπει να δει την αλλαγή.
        other = next((r for r in rooms[1:] if RF.set_of(r.number) == index), None)
        if other is not None:
            t.call("ROOM_LOAD", a=other.number)
            flat = bytes(v for r in other.cells for v in r)
            check("το ημερολόγιο δεν διαρρέει σε άλλη αίθουσα",
                  t.peek(cell_buf, RF.CELLS) == flat)

    # 5. Διακόπτης -> ΠΟΛΛΕΣ πόρτες, και ιδιότητες κελιών. Χτίζουμε δωμάτιο
    #    επί τούτου: το κανάλι είναι ο σύνδεσμος, όχι η γειτνίαση.
    t.stub("DRAW_TILE")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[5][1] = "S"
    for c in (10, 20, 30):
        rows[8][c] = "G"
    rows[12][5] = "G"                                   # άλλο κανάλι
    rows[22][7] = "K"                                   # κλειδαριά ταυτότητας 3
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "sw 1 5 1", "gate 10 8 1", "gate 20 8 1", "gate 30 8 1",
         "gate 5 12 2", "lock 7 22 3"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.call("ROOM_LOAD", a=1)

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    for c, r, want in ((1, 5, 1), (10, 8, 1), (5, 12, 2), (7, 22, 3), (0, 0, 0)):
        t.call("CELL_ATTR", bc=(c << 8) | r)
        check(f"cell_attr ({c},{r})", t.m.a == want, f"{t.m.a} vs {want}")

    check("οι πόρτες ξεκινούν κλειστές",
          all(cell(c, 8) == P.GATE for c in (10, 20, 30)))
    t.call("GATE_TOGGLE", a=1)
    check("ένας διακόπτης άνοιξε ΚΑΙ ΤΙΣ ΤΡΕΙΣ πόρτες του καναλιού",
          all(cell(c, 8) == P.GATE_OPEN for c in (10, 20, 30)),
          str([P.TYPE_NAMES[cell(c, 8)] for c in (10, 20, 30)]))
    check("η πόρτα άλλου καναλιού ΔΕΝ πειράχτηκε", cell(5, 12) == P.GATE,
          P.TYPE_NAMES[cell(5, 12)])
    t.call("GATE_TOGGLE", a=1)
    check("ο διακόπτης ξανακλείνει (δεν είναι μιας χρήσης)",
          all(cell(c, 8) == P.GATE for c in (10, 20, 30)))

    check("το άνοιγμα πόρτας μπήκε στο ημερολόγιο",
          t.peek(t.sym("JR_COUNT"))[0] == 3,
          f"{t.peek(t.sym('JR_COUNT'))[0]} εγγραφές")

    # 6. Τα βελάκια βαρύτητας του HUD φτάνουν στη σωστή θέση της οθόνης, με
    #    τα σωστά pixel. Η διάταξη της οθόνης του CPC είναι interleaved και
    #    ένα λάθος εδώ ζωγραφίζει μέσα στην πίστα αντί για το HUD.
    import genasm as GA
    t.call("INIT_LINETAB")

    def hud_bytes(col):
        return [(t.m.memory[0xC000 + (y % 8) * 0x800 + col],
                 t.m.memory[0xC000 + (y % 8) * 0x800 + col + 1]) for y in range(8)]

    # Μέσα από το ΙΔΙΟ το draw_hud, όχι καλώντας το draw_garrow απευθείας.
    #
    # ΓΙΑΤΙ ΕΧΕΙ ΣΗΜΑΣΙΑ: τα βελάκια ήταν γραμμένα σε σημείο του draw_hud όπου
    # δεν φτάνει ποτέ η ροή, οπότε ΔΕΝ ζωγραφίζονταν καθόλου στον πραγματικό
    # Amstrad. Το προηγούμενο τεστ καλούσε το draw_garrow μόνο του και έλεγε
    # «σωστό»: επαλήθευε τη ρουτίνα, όχι ότι κάποιος τη φωνάζει.
    for gw, gh in ((0, 6), (3, 5), (7, 1)):
        for a in range(0xC000, 0x10000):
            t.m.memory[a] = 0
        t.poke(t.sym("WORLD_G"), bytes((gw,)))
        t.poke(t.sym("HERO_G"), bytes((gh,)))
        t.poke(t.sym("HUD_DIRTY"), b"\x01")
        t.call("DRAW_HUD")
        want_w = [tuple(GA.pack_mode1(GA.arrow_pixels(gw, 3)[y])) for y in range(8)]
        want_h = [tuple(GA.pack_mode1(GA.arrow_pixels(gh, 2)[y])) for y in range(8)]
        # ΑΠΟ ΤΑ ΣΥΜΒΟΛΑ, όχι καρφωτά: οι στήλες μετακινήθηκαν όταν τα δύο
        # βελάκια κόλλησαν μεταξύ τους στη δεξιά άκρη, και ένα τεστ που ξέρει
        # τη θέση από μόνο του λέει «χάλασε» σε κάθε αλλαγή διάταξης.
        check(f"το draw_hud ζωγραφίζει το βέλος κόσμου (φορά {gw})",
              hud_bytes(t.sym("GRAV_WX")) == want_w)
        check(f"το draw_hud ζωγραφίζει το βέλος ήρωα (φορά {gh})",
              hud_bytes(t.sym("GRAV_HX")) == want_h)

    # …και ΧΩΡΙΣ hud_dirty, όταν αλλάξει μόνο η βαρύτητα. Ο ήρωας γυρίζει σε
    # κάθε γωνία που περπατάει χωρίς να πειράζει ενέργεια ή inventory: με
    # κριτήριο το hud_dirty τα βελάκια θα έμεναν παγωμένα.
    t.poke(t.sym("HUD_DIRTY"), b"\x00")
    t.poke(t.sym("HERO_G"), b"\x02")
    t.call("DRAW_HUD")
    check("το βέλος ήρωα ενημερώνεται χωρίς hud_dirty",
          hud_bytes(t.sym("GRAV_HX")) == [
              tuple(GA.pack_mode1(GA.arrow_pixels(2, 2)[y])) for y in range(8)])

    # ΤΑ ΔΥΟ ΒΕΛΑΚΙΑ ΕΙΝΑΙ ΚΟΛΛΗΤΑ: μία ανάγνωση, όχι δύο ξεχωριστά εικονίδια.
    check("τα δύο βελάκια είναι διπλανά",
          t.sym("GRAV_HX") - t.sym("GRAV_WX") == 2,
          f"απόσταση {t.sym('GRAV_HX') - t.sym('GRAV_WX')} bytes")

    # …και τα δύο σταθερά σύμβολα μπροστά από ενέργεια και σκορ.
    for name, col, art, pen in (("κεραυνός", t.sym("HUD_BOLT_X"), GA.HUD_BOLT, 3),
                                ("αστέρι", t.sym("HUD_STAR_X"), GA.HUD_STAR, 2)):
        want = [tuple(GA.pack_mode1([pen if ch == "X" else 0 for ch in row]))
                for row in art]
        check(f"το draw_hud ζωγραφίζει το σύμβολο: {name}",
              hud_bytes(col) == want)

    # 7. Η πόρτα ανοίγει ΜΟΝΟ με ενεργοποίηση. Το h_touch δεν την κοιτάει
    #    πια· το h_use την κρίνει από το κελί του ΣΩΜΑΤΟΣ.
    rooms_all = P.all_rooms()
    door = next((r for r in rooms_all if r.exit_groups()), None)
    if door is not None:
        index = RF.set_of(door.number)
        t.poke(set_buf, dict((i, d) for i, _, d in RF.all_sets())[index])
        t.poke(t.sym("SET_CUR"), bytes((index,)))
        t.poke(t.sym("JR_COUNT"), b"\x00")
        t.call("ROOM_LOAD", a=door.number)

        (col, row), dest, _two, _cells = door.exit_groups()[0]
        t.poke16(t.sym("HERO_X"), col * P.CELL + P.CELL // 2)
        t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + row * P.CELL + P.CELL // 2)
        t.poke(t.sym("PENDING_ROOM"), b"\x00")

        t.stub("CRATE_STEP")
        t.call("H_TOUCH")
        check("η επαφή με την πόρτα ΔΕΝ αλλάζει αίθουσα",
              t.peek(t.sym("PENDING_ROOM"))[0] == 0,
              f"{t.peek(t.sym('PENDING_ROOM'))[0]}")

        t.call("H_USE")
        check("η ενεργοποίηση πάνω στην πόρτα αλλάζει αίθουσα",
              t.peek(t.sym("PENDING_ROOM"))[0] == dest,
              f"{t.peek(t.sym('PENDING_ROOM'))[0]} vs {dest}")

    # 8. Ο παίκτης κρατάει ό,τι κουβαλάει περνώντας πόρτα. Το room_load
    #    μηδένιζε το hero_carry και το κιβώτιο εξαφανιζόταν στην πόρτα.
    if rooms_all:
        r0 = rooms_all[0]
        index = RF.set_of(r0.number)
        t.poke(set_buf, dict((i, d) for i, _, d in RF.all_sets())[index])
        t.poke(t.sym("SET_CUR"), bytes((index,)))
        t.poke(t.sym("JR_COUNT"), b"\x00")

        t.poke(t.sym("HERO_ENERGY"), b"\x03")
        t.poke(t.sym("HERO_CARRY"), b"\x01")
        t.poke(t.sym("HERO_PARA"), b"\x02")
        t.poke(t.sym("HERO_KEYS"), bytes([0, 1, 0, 2, 0, 0, 0, 0]))
        t.call("ROOM_LOAD", a=r0.number)

        for name, want in (("HERO_ENERGY", 3), ("HERO_CARRY", 1),
                           ("HERO_PARA", 2)):
            got = t.peek(t.sym(name))[0]
            check(f"το {name.lower()} επιβιώνει της πόρτας", got == want,
                  f"{got} vs {want}")
        keys = list(t.peek(t.sym("HERO_KEYS"), P.ATTR_MAX))
        check("τα κλειδιά επιβιώνουν της πόρτας",
              keys == [0, 1, 0, 2, 0, 0, 0, 0], str(keys))
        # …ενώ ό,τι ανήκει στην ΑΙΘΟΥΣΑ μηδενίζει.
        check("το αλεξίπτωτο κλείνει στη νέα αίθουσα",
              t.peek(t.sym("HERO_PARAOPEN"))[0] == 0)
        check("τα κιβώτια ξεκινούν ακίνητα στη νέα αίθουσα",
              t.peek(t.sym("CRATES_ON"))[0] == 0)

    # 9. Στοίβα διαδρομής: γυρνάς πίσω ως TRAIL_MAX δωμάτια και οι πόρτες
    #    προς ό,τι ξεχείλισε γίνονται μπλοκ. Συγκρίνεται ΒΗΜΑ-ΒΗΜΑ με το
    #    μοντέλο — η λογική έχει τρεις κλάδους (μπροστά, πίσω, ξεχείλισμα) και
    #    κανένας δεν είναι προφανής στον Z80.
    TR, TRN, SEAL = t.sym("TRAIL"), t.sym("TRAIL_N"), t.sym("SEALED")
    t.poke(TRN, b"\x00")
    t.poke(SEAL, bytes(32))
    ref = P.Trail()
    for a, b in [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 5), (5, 6),
                 (6, 7), (7, 8), (8, 3)]:
        t.poke(t.sym("FROM_ROOM"), bytes((a,)))
        t.call("TRAIL_ENTER", a=b)
        ref.enter(a, b)
        n = t.peek(TRN)[0]
        rooms = list(t.peek(TR, P.TRAIL_MAX))[:n]
        sealed = [r for r in range(256)
                  if t.peek(SEAL + (r >> 3))[0] & (1 << (r & 7))]
        check(f"διαδρομή {a}->{b}",
              rooms == ref.rooms and sealed == sorted(ref.sealed),
              f"Z80 {rooms}/{sealed} vs {ref.rooms}/{sorted(ref.sealed)}")

    # 10. (Το παλιό τεστ του door_msg αντικαταστάθηκε από το 16: το μήνυμα
    #     δεν αφορά πια μόνο την πόρτα.)

    # 11. Οθόνη μενού: ο τίτλος σε δύο χρώματα και ο ήρωας που κάνει τον γύρο
    #     της αρένας. Ο γύρος ΔΕΝ είναι animation — τρέχει η πραγματική φυσική,
    #     οπότε αν σπάσουν οι γωνίες, το μενού το δείχνει αμέσως.
    t.call("INIT_LINETAB")
    for a in range(0xC000, 0x10000):
        t.m.memory[a] = 0
    t.call("DRAW_FRAME")
    t.call("DRAW_TITLE")

    def pen(v, s):
        return (1 if v & (1 << (7 - s)) else 0) | (2 if v & (1 << (3 - s)) else 0)

    lit, pens = 0, set()
    for y in range(16, 32):
        base = 0xC000 + (y % 8) * 0x800 + (y // 8) * 80
        for b in range(20, 60):
            for s in range(4):
                p = pen(t.m.memory[base + b], s)
                if p:
                    lit += 1
                    pens.add((p, b))
    check("ο τίτλος ζωγραφίστηκε", lit > 400, f"{lit} pixel")
    left = {p for p, b in pens if b < 36}       # GRAV
    right = {p for p, b in pens if b >= 36}     # ASSIST
    check("GRAV και ASSIST σε ΔΙΑΦΟΡΕΤΙΚΑ χρώματα, όπως στο concept art",
          left == {3} and right == {2}, f"{left} vs {right}")

    # Το πλαίσιο: τέσσερις πλευρές γύρω από τα γράμματα, όπως τα panels του
    # concept art. Ελέγχεται ότι υπάρχει και πάνω και κάτω και στα δύο πλάγια.
    def lit_at(x, y):
        base = 0xC000 + (y % 8) * 0x800 + (y // 8) * 80
        return pen(t.m.memory[base + (x >> 2)], x & 3) != 0

    check("το πλαίσιο έχει πάνω και κάτω πλευρά",
          lit_at(160, 8) and lit_at(160, 43))
    check("το πλαίσιο έχει αριστερή και δεξιά πλευρά",
          lit_at(72, 25) and lit_at(244, 25))
    check("το εσωτερικό του πλαισίου δεν είναι γεμάτο", not lit_at(160, 11))

    # Η αρένα και ο γύρος του ήρωα.
    t.stub("DRAW_TILE")
    t.call("MENU_ARENA")
    cb = t.sym("CELL_BUF")

    def cell(c, r):
        return t.peek(cb + r * P.COLS + c)[0]

    check("η αρένα είναι κλειστή", all(
        cell(c, 9) == P.SOLID and cell(c, 13) == P.SOLID for c in range(15, 25))
        and all(cell(15, r) == P.SOLID and cell(24, r) == P.SOLID
                for r in range(9, 14)))
    check("το εσωτερικό της είναι κενό",
          all(cell(c, r) == P.EMPTY
              for c in range(16, 24) for r in range(10, 13)))

    t.poke16(t.sym("HERO_X"), 18 * P.CELL + P.CELL // 2)
    t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + 11 * P.CELL + P.CELL // 2)
    t.poke(t.sym("HERO_G"), b"\x00")
    t.poke(t.sym("WORLD_G"), b"\x00")
    t.poke(t.sym("HERO_STATE"), b"\x02")
    t.stub("CRATE_STEP")
    seen = set()
    for _ in range(500):
        t.call("HERO_UPDATE", a=1)
        seen.add(t.peek(t.sym("HERO_G"))[0])
    check("ο ήρωας κάνει τον γύρο: και οι τέσσερις ορθές φορές",
          {0, 2, 4, 6} <= seen, str(sorted(seen)))

    # 12. Ένα κλειδί ανοίγει ΟΛΕΣ τις κλειδαριές της ταυτότητάς του — αλλά
    #     μόνο όσες είναι ΚΑΛΩΔΙΩΜΕΝΕΣ. Η ταυτότητα 0 σημαίνει ακαλωδίωτη και
    #     ανοίγει μόνη της, αλλιώς μια πίστα με πολλές απλές κλειδαριές θα
    #     ξεκλείδωνε ολόκληρη με ένα κλειδί.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for c in (5, 12, 20):
        rows[22][c] = "K"               # ταυτότητα 2
    rows[22][30] = "K"                  # άλλη ταυτότητα
    rows[22][35] = "K"                  # ακαλωδίωτη
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "lock 5 22 2", "lock 12 22 2", "lock 20 22 2",
         "lock 30 22 3"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.call("ROOM_LOAD", a=1)

    t.poke(t.sym("HERO_KEYS"), bytes([0, 0, 1, 0, 0, 0, 0, 0]))
    t.poke16(t.sym("HERO_X"), 5 * P.CELL + P.CELL // 2)
    t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + P.CELL // 2)
    t.poke(t.sym("HERO_G"), b"\x00")
    t.stub("CRATE_STEP")
    for _ in range(60):
        t.call("HERO_UPDATE", a=0)
    t.call("H_USE")

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    check("η κλειδαριά που πάτησες ανοίγει",
          cell(5, 22) == P.LOCK_OPEN, P.TYPE_NAMES[cell(5, 22)])
    check("ανοίγουν ΟΛΕΣ όσες μοιράζονται την ταυτότητα",
          cell(12, 22) == P.LOCK_OPEN and cell(20, 22) == P.LOCK_OPEN,
          f"{P.TYPE_NAMES[cell(12, 22)]}, {P.TYPE_NAMES[cell(20, 22)]}")
    check("άλλη ταυτότητα ΔΕΝ ανοίγει",
          cell(30, 22) == P.LOCK, P.TYPE_NAMES[cell(30, 22)])
    check("ακαλωδίωτη κλειδαριά ΔΕΝ ανοίγει",
          cell(35, 22) == P.LOCK, P.TYPE_NAMES[cell(35, 22)])
    check("καταναλώθηκε ΕΝΑ κλειδί",
          t.peek(t.sym("HERO_KEYS"), 8)[2] == 0,
          str(list(t.peek(t.sym("HERO_KEYS"), 8))))

    # 13. Μουσική: ΔΕΝ ΔΟΚΙΜΑΖΕΤΑΙ ΕΔΩ ΠΙΑ.
    #
    #     Ο player του μενού διάβαζε νότες από τη βασική μνήμη· ο σημερινός τις
    #     ρουφάει από την τράπεζα με bank_copy, οπότε χρειάζεται μοντέλο
    #     τραπεζών — και το harness αυτού του αρχείου τρέχει χωρίς. Όλα όσα
    #     έλεγχε αυτό το τμήμα ζουν στο tools/test_music.py, μαζί με όσα δεν
    #     μπορούσε να ελέγξει: τη ραφή του κύκλου, τη γεμάτη ουρά, την επιλογή
    #     M, και το ότι το SOUND QUEUE χαλάει το IX.

    # 14. Πλάκα πίεσης -> πύλες. ΣΤΙΓΜΙΑΙΑ: ανοίγει όσο πατιέται και κλείνει
    #     μόλις φύγεις. Το κιβώτιο πάνω της την κρατά πατημένη χωρίς εσένα —
    #     αυτός είναι όλος ο λόγος που υπάρχει το PLATE_DOWN.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "p"                  # πλάκα, κανάλι 1
    rows[8][20] = "G"                   # πύλη ίδιου καναλιού
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "plate 10 22 1", "gate 20 8 1"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.call("ROOM_LOAD", a=1)
    t.stub("CRATE_STEP")

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    def stand(c, r):
        t.poke16(t.sym("HERO_X"), c * P.CELL + P.CELL // 2)
        t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + r * P.CELL + P.CELL // 2)
        t.call("PLATE_STEP")

    check("η πύλη ξεκινά κλειστή", cell(20, 8) == P.GATE,
          P.TYPE_NAMES[cell(20, 8)])
    stand(10, 22)
    check("πατώντας την πλάκα, η πύλη ανοίγει",
          cell(20, 8) == P.GATE_OPEN, P.TYPE_NAMES[cell(20, 8)])
    stand(4, 22)
    check("φεύγοντας, η πύλη ξανακλείνει",
          cell(20, 8) == P.GATE, P.TYPE_NAMES[cell(20, 8)])

    # Κιβώτιο πάνω στην πλάκα: μένει πατημένη χωρίς τον ήρωα.
    t.poke(cell_buf + 22 * P.COLS + 10, bytes((P.PLATE_DOWN,)))
    t.call("PLATE_STEP")
    check("κιβώτιο στην πλάκα: η πύλη ανοίγει",
          cell(20, 8) == P.GATE_OPEN, P.TYPE_NAMES[cell(20, 8)])
    stand(4, 22)
    check("…και ΜΕΝΕΙ ανοιχτή χωρίς τον ήρωα",
          cell(20, 8) == P.GATE_OPEN, P.TYPE_NAMES[cell(20, 8)])
    t.poke(cell_buf + 22 * P.COLS + 10, bytes((P.PLATE,)))
    t.call("PLATE_STEP")
    check("σηκώνοντας το κιβώτιο, η πύλη κλείνει",
          cell(20, 8) == P.GATE, P.TYPE_NAMES[cell(20, 8)])

    # 15. Το κιβώτιο ΔΕΝ είναι στερεό: περνάς από μέσα, το σηκώνεις από το
    #     κελί που στέκεσαι, και το αφήνεις εκεί που στέκεσαι.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "B"
    rows[22][20] = "p"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0\nplate 20 22 1"
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.call("ROOM_LOAD", a=1)

    check("το κιβώτιο δεν είναι στερεό",
          not (t.peek(t.sym("TILE_PROPS") + P.CRATE)[0] & P.F_SOLID))

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    def at(c, r):
        t.poke16(t.sym("HERO_X"), c * P.CELL + P.CELL // 2)
        t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + r * P.CELL + P.CELL // 2)

    t.poke(t.sym("HERO_CARRY"), b"\x00")
    at(10, 22)
    t.call("H_USE")
    check("σηκώνεις το κιβώτιο από το κελί που στέκεσαι",
          t.peek(t.sym("HERO_CARRY"))[0] == 1 and cell(10, 22) == P.EMPTY,
          P.TYPE_NAMES[cell(10, 22)])

    at(14, 22)
    t.call("H_USE")
    check("το αφήνεις ΕΚΕΙ ΠΟΥ ΣΤΕΚΕΣΑΙ",
          t.peek(t.sym("HERO_CARRY"))[0] == 0 and cell(14, 22) == P.CRATE,
          P.TYPE_NAMES[cell(14, 22)])

    at(14, 22)
    t.call("H_USE")                     # ξανασήκωσέ το
    at(20, 22)
    t.call("H_USE")                     # …και άσ' το πάνω στην πλάκα
    check("πάνω σε πλάκα η πλάκα δεν χάνεται",
          cell(20, 22) == P.PLATE_DOWN, P.TYPE_NAMES[cell(20, 22)])

    # 16. Μήνυμα ανά αντικείμενο. Η σειρά προτεραιότητας πρέπει να είναι Η
    #     ΙΔΙΑ με του h_use, αλλιώς το μήνυμα υπόσχεται κάτι που το πλήκτρο
    #     δεν κάνει — π.χ. «άσε το κιβώτιο» ενώ πατάς τηλεμεταφορά.
    t.call("INIT_LINETAB")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][5] = "K"                   # κλειδαριά (στερεή: την πατάς)
    rows[21][10] = "T"
    rows[21][14] = "B"
    rows[21][18] = "p"
    rows[21][22] = "g"
    rows[21][26] = "X"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "lock 5 22 1", "tp 10 21 30 21", "exit 26 21 2"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.call("ROOM_LOAD", a=1)

    def hint(c, r, carry=0, keys=(0,) * 8):
        t.poke(t.sym("HERO_CARRY"), bytes((carry,)))
        t.poke(t.sym("HERO_KEYS"), bytes(keys))
        t.poke16(t.sym("HERO_X"), c * P.CELL + P.CELL // 2)
        t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + r * P.CELL + P.CELL // 2)
        t.poke(t.sym("MSG_CUR"), b"\xFF")
        t.call("HINT_MSG")
        i = t.peek(t.sym("MSG_CUR"))[0]
        if i == 0xFF:
            return ""
        ptr = t.peek16(t.sym("HINT_PTR") + i * 2)
        return t.peek(ptr + 1, t.peek(ptr)[0]).decode()

    for where, args, want in (
            ("πόρτα", (26, 21, 0, (0,) * 8), "Up or down to exit room"),
            ("τηλεμεταφορά", (10, 21, 0, (0,) * 8), "Up or down to teleport"),
            ("κιβώτιο", (14, 21, 0, (0,) * 8), "Up or down to pick up crate"),
            ("γεμάτα χέρια πάνω σε πλάκα", (18, 21, 1, (0,) * 8),
             "Up or down to drop crate"),
            ("γεμάτα χέρια αλλού: σιωπή", (14, 21, 1, (0,) * 8), ""),
            ("πλάκα", (18, 21, 0, (0,) * 8), "A crate here keeps gates opened"),
            ("ανοιχτή πύλη", (22, 21, 0, (0,) * 8), "This gate is open"),
            ("κλειδαριά χωρίς κλειδί", (5, 21, 0, (0,) * 8),
             "You need the matching key"),
            ("κλειδαριά με κλειδί", (5, 21, 0, (0, 1, 0, 0, 0, 0, 0, 0)),
             "Up or down to unlock"),
            ("κενό", (35, 21, 0, (0,) * 8), "")):
        got = hint(*args)
        check(f"μήνυμα σε {where}", got == want, f"«{got}» vs «{want}»")

    # Κλειστή πύλη ΜΠΡΟΣΤΑ: το μήνυμα λέει ΤΙ την ανοίγει — το μόνο που δεν
    # φαίνεται κοιτάζοντάς την.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][6] = rows[22][12] = rows[22][18] = rows[22][24] = "G"
    rows[21][30] = rows[21][34] = "S"
    rows[21][32] = rows[21][36] = "p"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "gate 6 22 1", "gate 12 22 2", "gate 18 22 3",
         "gate 24 22 4", "sw 30 21 1", "plate 32 21 2", "sw 34 21 3",
         "plate 36 21 3"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.call("ROOM_LOAD", a=1)
    t.poke(t.sym("HERO_FACE"), b"\x01")

    for col, what, want in (
            (5, "διακόπτη", "Find its switch to open this"),
            (11, "πλάκα", "Weigh down its plate to open"),
            (17, "διακόπτη ΚΑΙ πλάκα", "A switch or a plate opens this"),
            (23, "τίποτα", "This gate has nothing to open it")):
        got = hint(col, 22)
        check(f"δίπλα σε κλειστή πύλη με {what}", got == want, f"«{got}»")

    # Η πύλη είναι στερεή, άρα και ΠΑΤΩΜΑ: στέκεσαι από πάνω της και το
    # μήνυμα πρέπει να λέει το ίδιο πράγμα.
    for col, what, want in (
            (6, "διακόπτη", "Find its switch to open this"),
            (12, "πλάκα", "Weigh down its plate to open")):
        got = hint(col, 21)
        check(f"ΠΑΝΩ σε κλειστή πύλη με {what}", got == want, f"«{got}»")

    # Τα μηνύματα είναι ΟΔΗΓΟΣ: σβήνουν μετά τις πρώτες αίθουσες, αλλιώς
    # γίνονται μόνιμος θόρυβος για παίκτη που ξέρει ήδη τα πλήκτρα.
    # (Στο δωμάτιο των πυλών που μόλις φορτώθηκε· η πόρτα του προηγούμενου
    # δεν υπάρχει πια εδώ.)
    t.poke(t.sym("CUR_ROOM"), bytes((10,)))
    check("στην 10η αίθουσα το μήνυμα ακόμα φαίνεται",
          hint(5, 22) == "Find its switch to open this")
    t.poke(t.sym("CUR_ROOM"), bytes((11,)))
    check("από την 11η και μετά, σιωπή", hint(5, 22) == "")
    t.poke(t.sym("CUR_ROOM"), bytes((1,)))

    # 17. Ζώνη κλειδώματος: η βαρύτητα ΚΑΤΩ, καμία στροφή σε γωνίες — και
    #     βήμα-βήμα ίδια με το μοντέλο, γιατί εδώ άλλαξε ΡΟΗ ΕΛΕΓΧΟΥ και όχι
    #     πίνακας: ακριβώς το είδος αλλαγής που αποκλίνει σιωπηλά.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    for r in range(14, 23):
        rows[r][20] = "#"
    for r in range(10, 23):
        for c in range(12, 20):
            rows[r][c] = ":"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0"
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.call("ROOM_LOAD", a=1)

    ref = P.Hero(P.Room(text), 14 * P.CELL + 4, P.GRID_Y0 + 21 * P.CELL + 4, 0)
    t.poke16(t.sym("HERO_X"), 14 * P.CELL + 4)
    t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)
    t.poke(t.sym("HERO_G"), b"\x00")
    t.poke(t.sym("HERO_STATE"), b"\x02")
    seen, diverged = set(), None
    for i in range(200):
        t.call("HERO_UPDATE", a=1)
        ref.update(1)
        z = (t.peek16(t.sym("HERO_X")), t.peek16(t.sym("HERO_Y")),
             t.peek(t.sym("HERO_G"))[0])
        if z != (ref.x, ref.y, ref.g) and diverged is None:
            diverged = (i, z, (ref.x, ref.y, ref.g))
        seen.add(z[2])
    check("ζώνη κλειδώματος: η βαρύτητα μένει ΚΑΤΩ", seen == {0},
          str(sorted(seen)))
    check("ζώνη κλειδώματος: Z80 και μοντέλο ταυτίζονται 200 frames",
          diverged is None, str(diverged))

    # Η σημαία που διαβάζει ο ήχος: χωρίς αυτήν τα παράσιτα δεν ξέρουν πότε
    # να ξεκινήσουν. Ο ήρωας είναι ΜΕΣΑ στη ζώνη μετά τα 200 frames.
    check("η ζώνη αφήνει σημάδι για τον ήχο",
          t.peek(t.sym("HERO_ZONE"))[0] == 1,
          str(t.peek(t.sym("HERO_ZONE"))[0]))
    t.poke16(t.sym("HERO_X"), 30 * P.CELL + 4)   # έξω από τη ζώνη
    t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)
    t.call("HERO_UPDATE", a=0)
    check("…και σβήνει μόλις βγει", t.peek(t.sym("HERO_ZONE"))[0] == 0,
          str(t.peek(t.sym("HERO_ZONE"))[0]))

    # 18. Αυτόματη κλειδαριά: ανοίγει με ΤΗΝ ΕΠΑΦΗ, χωρίς πλήκτρο. Η σημαία
    #     ζει στο bit 3 της ίδιας τιμής, οπότε κάθε σύγκριση ταυτότητας
    #     πρέπει να κάνει AND 7 — αλλιώς η αυτόματη κλειδαριά «2» δεν
    #     ταιριάζει με το κλειδί «2».
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][5] = "K"                   # αυτόματη, ταυτότητα 2
    rows[22][12] = "K"                  # χειροκίνητη, ταυτότητα 3
    rows[21][20] = "k"
    rows[21][26] = "k"
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "lock 5 22 10", "lock 12 22 3", "key 20 21 2",
         "key 26 21 3"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.poke(t.sym("MSG_LEFT"), b"\x00")
    t.poke(t.sym("HERO_KEYS"), bytes(8))
    t.call("ROOM_LOAD", a=1)

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    def stand(c, r):
        t.poke16(t.sym("HERO_X"), c * P.CELL + P.CELL // 2)
        t.poke16(t.sym("HERO_Y"), P.GRID_Y0 + r * P.CELL + P.CELL // 2)
        t.call("H_TOUCH")

    stand(20, 21)
    check("μαζεύοντας το κλειδί αυτόματης κλειδαριάς βγαίνει μήνυμα",
          t.peek(t.sym("MSG_LEFT"))[0] > 0
          and t.peek(t.sym("MSG_FORCE"))[0] == 12,
          f"hold={t.peek(t.sym('MSG_LEFT'))[0]}")
    stand(5, 21)
    check("η αυτόματη κλειδαριά ανοίγει με ΤΗΝ ΕΠΑΦΗ",
          cell(5, 22) == P.LOCK_OPEN, P.TYPE_NAMES[cell(5, 22)])
    check("…και καταναλώνει το κλειδί",
          t.peek(t.sym("HERO_KEYS"), 8)[2] == 0)

    t.poke(t.sym("MSG_LEFT"), b"\x00")
    stand(26, 21)
    check("κλειδί ΧΕΙΡΟΚΙΝΗΤΗΣ κλειδαριάς δεν βγάζει μήνυμα",
          t.peek(t.sym("MSG_LEFT"))[0] == 0)
    for _ in range(5):
        stand(12, 21)
    check("η χειροκίνητη ΔΕΝ ανοίγει με την επαφή",
          cell(12, 22) == P.LOCK, P.TYPE_NAMES[cell(12, 22)])

    # 19. ΗΧΟΣ. Δεν ελέγχουμε πώς ακούγεται — ελέγχουμε ότι ο σωστός ήχος
    #     μπαίνει στην ουρά τη σωστή στιγμή, ΜΙΑ φορά. Αυτό δεν φαίνεται από
    #     τη μνήμη: το μπλοκ είναι κοινό και κρατά μόνο το τελευταίο, οπότε
    #     παγιδεύουμε τις ίδιες τις κλήσεις στο SOUND QUEUE.
    t.trace("SOUND_QUEUE", corrupt=FW_QUEUE_KILLS)

    def sfx():
        """Τα κανάλια των ήχων που μπήκαν στην ουρά από την τελευταία κλήση."""
        out = [b[0] for b in t.calls]
        t.calls.clear()
        return out

    def blocks():
        out = list(t.calls)
        t.calls.clear()
        return out

    t.calls.clear()
    t.call("SFX_PLAY", a=1)             # SFXID_SWITCH
    b = blocks()
    check("ο διακόπτης βάζει δύο μπλοκ στο κανάλι ενεργειών",
          len(b) == 2 and all(x[0] == 1 for x in b), str([x[0] for x in b]))
    check("…με τους τόνους του πίνακα, όχι σκουπίδια",
          (b[0][3] | b[0][4] << 8, b[1][3] | b[1][4] << 8) == (595, 298),
          str((b[0][3] | b[0][4] << 8, b[1][3] | b[1][4] << 8)))

    t.call("SFX_PLAY", a=0)             # SFXID_STEP
    b = blocks()
    check("το βήμα πάει σε ΑΛΛΟ κανάλι από τις ενέργειες",
          len(b) == 1 and b[0][0] == 2, str([x[0] for x in b]))

    t.call("SFX_PLAY", a=99)
    check("άγνωστος αριθμός εφέ δεν παίζει τίποτα", not sfx())

    # Γεμάτη ουρά: το εφέ κόβεται, δεν επαναλαμβάνεται στο άπειρο.
    t.trace("SOUND_QUEUE", carry=False, corrupt=FW_QUEUE_KILLS)
    t.calls.clear()
    t.call("SFX_PLAY", a=5)             # SFXID_TELE, τέσσερα βήματα
    check("με γεμάτη ουρά δοκιμάζει ΜΙΑ φορά και τα παρατά",
          len(t.calls) == 1, f"{len(t.calls)} κλήσεις")
    t.trace("SOUND_QUEUE", carry=True, corrupt=FW_QUEUE_KILLS)

    # --- Τα παράσιτα της ζώνης
    t.call("SFX_RESET")
    t.calls.clear()
    t.call("SFX_AMB", a=1)              # μόλις μπήκε
    b = blocks()
    check("μπαίνοντας στη ζώνη ακούγονται παράσιτα αμέσως",
          len(b) == 1 and b[0][0] == 4, str([x[0] for x in b]))
    check("…είναι θόρυβος χωρίς τόνο, και σιγανός",
          b[0][3] == 0 and b[0][4] == 0 and b[0][5] > 0 and b[0][6] <= 4,
          f"τόνος={b[0][3] | b[0][4] << 8} θόρ={b[0][5]} έντ={b[0][6]}")

    for _ in range(7):
        t.call("SFX_AMB", a=1)
    check("δεν ξαναστέλνει σε κάθε καρέ", not t.calls, f"{len(t.calls)}")
    t.call("SFX_AMB", a=1)
    check("…αλλά ανανεώνει πριν σωπάσει", len(sfx()) == 1)

    t.call("SFX_AMB", a=0)
    b = blocks()
    check("βγαίνοντας από τη ζώνη αδειάζει το κανάλι ΑΜΕΣΩΣ",
          len(b) == 1 and b[0][0] == 4 + 0x80 and b[0][6] == 0,
          f"chan={b[0][0]:#04x} vol={b[0][6]}")
    t.call("SFX_AMB", a=0)
    check("…και μετά σιωπή, όχι ριπή από flush", not sfx())

    # --- Ο ήχος της πύλης παίζει ΜΙΑ φορά, όχι μία ανά πύλη
    t.poke(t.sym("SFX_GATECHG"), b"\x00")
    t.call("SFX_GATE")
    check("χωρίς αλλαγή πύλης δεν ακούγεται τίποτα", not sfx())
    t.poke(t.sym("SFX_GATECHG"), b"\x01")
    t.call("SFX_GATE")
    # Ο ήχος της πύλης είναι ανοδική σκάλα τριών βημάτων — τρία μπλοκ, ΕΝΑΣ
    # ήχος. Το ζητούμενο είναι να μην ακουστεί ΞΑΝΑ, όχι να είναι ένα μπλοκ.
    check("με αλλαγή ακούγεται", len(sfx()) == 3)
    t.call("SFX_GATE")
    check("…και η σημαία καθαρίζει, δεν ξαναχτυπά", not sfx())

    # 20. ΕΝΑΣ κόσμος αριθμών, στον ΠΡΑΓΜΑΤΙΚΟ Z80. Οι πίνακες παράγονται
    #     αυτόματα, αλλά η ροή του gate_toggle/gate_set γράφτηκε στο χέρι —
    #     ακριβώς το είδος αλλαγής που αποκλίνει σιωπηλά από το μοντέλο.
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "S"          # διακόπτης 3
    rows[22][20] = "K"          # κλειδαριά 3  -> ο διακόπτης την ανοίγει
    rows[22][14] = "^"          # αγκάθια 4
    rows[22][16] = "G"          # πύλη 5       -> το κλειδί την ανοίγει
    rows[21][30] = "k"          # κλειδί 5
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "sw 10 22 3", "lock 20 22 3", "spikes 14 22 4",
         "gate 16 22 5", "key 30 21 5"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t.poke(set_buf, RF.build_set([room]))
    t.poke(t.sym("SET_CUR"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x00")
    t.poke(t.sym("SEALED"), bytes(32))
    t.poke(t.sym("TRAIL_N"), b"\x00")
    t.poke(t.sym("PLATE_PREV"), b"\x00")
    t.poke(t.sym("HERO_KEYS"), bytes(8))
    t.call("ROOM_LOAD", a=1)

    def cell(c, r):
        return t.peek(cell_buf + r * P.COLS + c)[0]

    t.call("GATE_TOGGLE", a=3)
    check("Z80: ο διακόπτης ανοίγει ΚΛΕΙΔΑΡΙΑ",
          cell(20, 22) == P.LOCK_OPEN, P.TYPE_NAMES[cell(20, 22)])
    t.call("GATE_TOGGLE", a=3)
    check("Z80: …και την ξανακλειδώνει", cell(20, 22) == P.LOCK,
          P.TYPE_NAMES[cell(20, 22)])

    t.call("GATE_SET", a=4, bc=1)       # C=1 -> ανοιχτό
    check("Z80: η πλάκα τραβάει τα ΑΓΚΑΘΙΑ μέσα",
          cell(14, 22) == P.SPIKE_U_OFF, P.TYPE_NAMES[cell(14, 22)])
    t.call("GATE_SET", a=4, bc=0)
    check("Z80: …και ξαναβγαίνουν με τη ΣΩΣΤΗ φορά",
          cell(14, 22) == P.SPIKE_U, P.TYPE_NAMES[cell(14, 22)])

    t.call("LOCK_OPEN_ALL", a=5)
    check("Z80: το κλειδί ανοίγει ΠΥΛΗ", cell(16, 22) == P.GATE_OPEN,
          P.TYPE_NAMES[cell(16, 22)])

    before = cell(10, 22)
    t.call("GATE_TOGGLE", a=0)
    check("Z80: το κανάλι 0 δεν αγγίζει τίποτα", cell(10, 22) == before)

    # 21. Οι οθόνες τέλους. Δεν ελέγχουμε pixel — ελέγχουμε ότι τρέχουν ως το
    #     τέλος τους (φτάνουν στον βρόχο αναμονής) και ότι ο ήχος είναι ο
    #     σωστός. Το KM_TEST_KEY γίνεται «κανένα πλήκτρο», οπότε ο βρόχος
    #     αναμονής δεν τερματίζει ποτέ: αυτό ΕΙΝΑΙ η επιβεβαίωση ότι έφτασε.
    t.m.memory[t.sym("KM_TEST_KEY")] = 0xAF         # XOR A -> Z
    t.m.memory[t.sym("KM_TEST_KEY") + 1] = 0xC9

    def run_screen(name, timeout=6.0):
        t.calls.clear()
        try:
            t.call(name, timeout=timeout)
            return "ret", list(t.calls)
        except RuntimeError as e:
            return t.where(t.m.pc), list(t.calls)

    where, blocks = run_screen("GAME_OVER")
    # Ο βρόχος αναμονής καλεί δύο stub του firmware, οπότε το «πού κόλλησε»
    # πέφτει άλλοτε στον βρόχο και άλλοτε μέσα τους. Σημασία έχει ότι ΔΕΝ
    # γύρισε: η οθόνη ζωγραφίστηκε και περιμένει πλήκτρο.
    check("το GAME OVER περιμένει αντί να γυρίσει αμέσως", where != "ret", where)
    check("…με τέσσερις τόνους στο κανάλι ενεργειών",
          len(blocks) == 4 and all(b[0] == 1 for b in blocks),
          f"{len(blocks)} μπλοκ")
    tones = [b[3] | b[4] << 8 for b in blocks]
    # Μεγαλύτερη περίοδος = χαμηλότερος τόνος. Ένα τέλος που ΑΝΕΒΑΙΝΕΙ
    # ακούγεται σαν επιτυχία — ακριβώς το αντίθετο μήνυμα.
    check("…που ΚΑΤΕΒΑΙΝΟΥΝ", tones == sorted(tones), str(tones))

    where, blocks = run_screen("THE_END")
    # Πού ακριβώς σταματά μέσα στον player δεν έχει σημασία και αλλάζει με
    # κάθε νότα· σημασία έχει ότι ΔΕΝ γύρισε — περιμένει, με τη μουσική να παίζει.
    check("το THE END περιμένει αντί να γυρίσει αμέσως", where != "ret", where)
    # ΤΟ ΟΤΙ ΠΑΙΖΕΙ Η ΜΟΥΣΙΚΗ ΔΕΝ ΕΛΕΓΧΕΤΑΙ ΕΔΩ. Οι νότες έρχονται από την
    # τράπεζα και αυτό το harness τρέχει χωρίς μοντέλο τραπεζών (banking=False,
    # για ταχύτητα). Το tools/test_music.py το ελέγχει νότα προς νότα.
    #
    # Αυτό όμως που ΜΠΟΡΕΙ να ελεγχθεί εδώ αξίζει: χωρίς φορτωμένο κομμάτι ο
    # player πρέπει να σωπαίνει, όχι να στέλνει σκουπίδια στην ουρά. Είναι ο
    # δρόμος του μηχανήματος 64K και της δισκέτας χωρίς TUNEnn.BIN.
    check("…και χωρίς κομμάτι στην τράπεζα δεν βγάζει ήχο",
          not blocks, str(sorted({b[0] for b in blocks})))

    # 22. ΜΕΤΑ ΤΟ GAME OVER ΤΟ ΠΑΙΧΝΙΔΙ ΠΡΕΠΕΙ ΝΑ ΞΑΝΑΡΧΙΖΕΙ.
    #     Η ενέργεια αρχικοποιείται μόνο κατά τη συναρμολόγηση, οπότε έμενε 0
    #     και κάθε νέα παρτίδα πέθαινε στο πρώτο frame: ατέρμονη σειρά από
    #     οθόνες GAME OVER, που στον πραγματικό Amstrad μοιάζει με κρέμασμα.
    t.poke(t.sym("HERO_ENERGY"), b"\x00")
    t.poke(t.sym("HERO_CARRY"), b"\x01")
    t.poke(t.sym("GAME_DONE"), b"\x01")
    t.poke(t.sym("JR_COUNT"), b"\x07")
    t.poke(t.sym("TRAIL_N"), b"\x03")
    t.poke(t.sym("HERO_KEYS"), b"\x02" * 8)
    t.poke(t.sym("SEALED"), b"\xFF" * 32)
    t.call("GAME_RESET")

    check("μετά το reset η ενέργεια είναι ΓΕΜΑΤΗ",
          t.peek(t.sym("HERO_ENERGY"))[0] == 8,
          str(t.peek(t.sym("HERO_ENERGY"))[0]))
    check("…και το ημερολόγιο αλλαγών άδειο",
          t.peek(t.sym("JR_COUNT"))[0] == 0)
    check("…και οι τσέπες άδειες",
          t.peek(t.sym("HERO_KEYS"), 8) == bytes(8)
          and t.peek(t.sym("HERO_CARRY"))[0] == 0)
    check("…και καμία σφραγισμένη πόρτα",
          t.peek(t.sym("SEALED"), 32) == bytes(32))
    check("…και η σημαία τέλους καθαρή",
          t.peek(t.sym("GAME_DONE"))[0] == 0
          and t.peek(t.sym("TRAIL_N"))[0] == 0)

    # 23. Κιβώτιο που ΠΕΦΤΕΙ πάνω σε πλάκα την πατάει, στον πραγματικό Z80.
    #
    #     ΔΙΚΗ ΤΟΥ ΜΗΧΑΝΗ: οι 22 προηγούμενες ενότητες μοιράζονται την ίδια
    #     και αφήνουν πίσω τους κατάσταση που σταματά τα κιβώτια. Ο έλεγχος
    #     της πτώσης θέλει καθαρή αφετηρία, αλλιώς δείχνει «δεν έπεσε» για
    #     λόγο άσχετο με αυτό που μετράμε.
    t23 = Z80Test()
    t23.fake_set_load()
    t23.stub("RENDER_ROOM")
    t23.stub("DRAW_TILE")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "p"          # πλάκα στο πάτωμα
    rows[14][10] = "B"          # κιβώτιο οκτώ κελιά ψηλότερα
    rows[22][30] = "G"          # η πύλη του ίδιου καναλιού
    text = ";\n" + "\n".join("".join(r) for r in rows) + "\n" + "\n".join(
        ["gravity 0", "plate 10 22 1", "gate 30 22 1"])
    room = P.Room(text)
    room.number, room.path = 1, ""
    t23.poke(t23.sym("SET_BUF"), RF.build_set([room]))
    for sym, val in (("SET_CUR", 1), ("JR_COUNT", 0), ("TRAIL_N", 0),
                     ("PLATE_PREV", 0)):
        t23.poke(t23.sym(sym), bytes((val,)))
    t23.poke(t23.sym("SEALED"), bytes(32))
    t23.call("ROOM_LOAD", a=1)
    t23.poke16(t23.sym("HERO_X"), 5 * P.CELL + 4)
    t23.poke16(t23.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)
    t23.poke(t23.sym("CRATES_ON"), b"\x01")
    for _ in range(200):
        t23.call("HERO_UPDATE", a=0)

    cb23 = t23.sym("CELL_BUF")

    def cell23(c, r):
        return t23.peek(cb23 + r * P.COLS + c)[0]

    check("Z80: το κιβώτιο που πέφτει ΠΑΤΑΕΙ την πλάκα",
          cell23(10, 22) == P.PLATE_DOWN, P.TYPE_NAMES[cell23(10, 22)])
    check("Z80: …και η πύλη του καναλιού ανοίγει",
          cell23(30, 22) == P.GATE_OPEN, P.TYPE_NAMES[cell23(30, 22)])

    # 24. Ατρωσία μετά από χτύπημα, στον πραγματικό Z80. Δική της μηχανή:
    #     το χτύπημα εξαρτάται από μετρητές που οι προηγούμενες ενότητες
    #     έχουν ήδη κουνήσει.
    t24 = Z80Test()
    t24.fake_set_load()
    t24.stub("RENDER_ROOM")
    t24.stub("DRAW_TILE")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "^"          # αγκάθια στο πάτωμα
    room = P.Room(";\n" + "\n".join("".join(r) for r in rows) + "\ngravity 0")
    room.number, room.path = 1, ""
    t24.poke(t24.sym("SET_BUF"), RF.build_set([room]))
    for sym, val in (("SET_CUR", 1), ("JR_COUNT", 0), ("TRAIL_N", 0),
                     ("PLATE_PREV", 0)):
        t24.poke(t24.sym(sym), bytes((val,)))
    t24.poke(t24.sym("SEALED"), bytes(32))
    t24.call("ROOM_LOAD", a=1)
    t24.poke16(t24.sym("HERO_X"), 10 * P.CELL + 4)
    t24.poke16(t24.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)

    def energy24():
        return t24.peek(t24.sym("HERO_ENERGY"))[0]

    full = energy24()
    t24.call("HERO_UPDATE", a=0)
    check("Z80: το πρώτο άγγιγμα αγκαθιού πονάει", energy24() < full,
          f"{full} -> {energy24()}")
    check("Z80: …και ανάβει ο μετρητής ατρωσίας",
          t24.peek(t24.sym("HERO_HURT"))[0] == P.HURT_FRAMES,
          str(t24.peek(t24.sym("HERO_HURT"))[0]))
    after = energy24()
    for _ in range(P.HURT_FRAMES - 1):
        t24.call("HERO_UPDATE", a=0)
    check("Z80: …και σε ΟΛΑ τα καρέ ατρωσίας δεν ξαναπονάει",
          energy24() == after, f"{after} -> {energy24()}")
    for _ in range(P.SPIKE_TICKS + 2):
        t24.call("HERO_UPDATE", a=0)
    check("Z80: …και μετά ξαναπονάει", energy24() < after,
          f"{after} -> {energy24()}")

    # 25. Το κλειδί ανοίγει και ΠΥΛΗ που πατάς, όχι μόνο λουκέτο. Ο Z80
    #     γράφει την ανοιχτή μορφή ΤΟΥ ΤΥΠΟΥ: καρφωμένο T_LOCK_OPEN θα
    #     μεταμόρφωνε την πύλη σε λουκέτο, που είναι άλλο αντικείμενο.
    t25 = Z80Test()
    t25.fake_set_load()
    t25.stub("RENDER_ROOM")
    t25.stub("DRAW_TILE")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "G"          # πύλη που την ΠΑΤΑΣ
    rows[22][30] = "K"          # λουκέτο ίδιου καναλιού, αλλού
    room = P.Room(";\n" + "\n".join("".join(r) for r in rows) + "\n"
                  + "\n".join(["gravity 0", "gate 10 22 3", "lock 30 22 3"]))
    room.number, room.path = 1, ""
    t25.poke(t25.sym("SET_BUF"), RF.build_set([room]))
    for sym, val in (("SET_CUR", 1), ("JR_COUNT", 0), ("TRAIL_N", 0),
                     ("PLATE_PREV", 0), ("HERO_CARRY", 0)):
        t25.poke(t25.sym(sym), bytes((val,)))
    t25.poke(t25.sym("SEALED"), bytes(32))
    t25.poke(t25.sym("HERO_KEYS"), bytes(8))
    t25.call("ROOM_LOAD", a=1)
    cb25 = t25.sym("CELL_BUF")

    def c25(c, r):
        return t25.peek(cb25 + r * P.COLS + c)[0]

    # Πάνω στην πύλη, ΧΩΡΙΣ κλειδί
    t25.poke16(t25.sym("HERO_X"), 10 * P.CELL + 4)
    t25.poke16(t25.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)
    t25.call("H_USE")
    check("Z80: χωρίς κλειδί η πύλη μένει κλειστή", c25(10, 22) == P.GATE,
          P.TYPE_NAMES[c25(10, 22)])

    keys = bytearray(8)
    keys[3] = 1
    t25.poke(t25.sym("HERO_KEYS"), bytes(keys))
    t25.call("H_USE")
    check("Z80: με το κλειδί της, η πύλη που πατάς ανοίγει",
          c25(10, 22) == P.GATE_OPEN, P.TYPE_NAMES[c25(10, 22)])
    check("Z80: …και μένει ΠΥΛΗ, δεν γίνεται λουκέτο",
          c25(10, 22) != P.LOCK_OPEN, P.TYPE_NAMES[c25(10, 22)])
    check("Z80: …και ανοίγει και το λουκέτο του ίδιου καναλιού",
          c25(30, 22) == P.LOCK_OPEN, P.TYPE_NAMES[c25(30, 22)])
    check("Z80: …και ξοδεύτηκε ΕΝΑ κλειδί",
          t25.peek(t25.sym("HERO_KEYS"), 8)[3] == 0)

    # 26. Το μήνυμα στην κλειστή πύλη. Αν ΚΡΑΤΑΣ το κλειδί της, το «ψάξε τον
    #     διακόπτη» είναι λάθος συμβουλή: η πύλη ανοίγει τώρα, με ένα πάτημα.
    t26 = Z80Test()
    t26.fake_set_load()
    t26.stub("RENDER_ROOM")
    t26.stub("DRAW_TILE")
    rows = [list("#" * 40)] + [list("#" + "." * 38 + "#") for _ in range(22)] \
        + [list("#" * 40)]
    rows[22][10] = "G"
    rows[22][20] = "S"
    room = P.Room(";\n" + "\n".join("".join(r) for r in rows) + "\n"
                  + "\n".join(["gravity 0", "gate 10 22 3", "sw 20 22 3"]))
    room.number, room.path = 1, ""
    t26.poke(t26.sym("SET_BUF"), RF.build_set([room]))
    for sym, val in (("SET_CUR", 1), ("JR_COUNT", 0), ("TRAIL_N", 0),
                     ("PLATE_PREV", 0), ("HERO_CARRY", 0)):
        t26.poke(t26.sym(sym), bytes((val,)))
    t26.poke(t26.sym("SEALED"), bytes(32))
    t26.poke(t26.sym("HERO_KEYS"), bytes(8))
    t26.call("ROOM_LOAD", a=1)
    t26.poke16(t26.sym("HERO_X"), 10 * P.CELL + 4)
    t26.poke16(t26.sym("HERO_Y"), P.GRID_Y0 + 21 * P.CELL + 4)

    t26.call("HINT_PICK")
    check("κλειστή πύλη χωρίς κλειδί: λέει να βρεις τον διακόπτη",
          t26.m.a == 8, f"μήνυμα {t26.m.a}")      # MSG_GSW

    keys = bytearray(8)
    keys[3] = 1
    t26.poke(t26.sym("HERO_KEYS"), bytes(keys))
    t26.call("HINT_PICK")
    check("…αλλά με το κλειδί της λέει πώς ανοίγει ΤΩΡΑ",
          t26.m.a == 13, f"μήνυμα {t26.m.a}")     # MSG_GKEY

    keys[3] = 0
    keys[5] = 1                                   # κλειδί ΑΛΛΟΥ καναλιού
    t26.poke(t26.sym("HERO_KEYS"), bytes(keys))
    t26.call("HINT_PICK")
    check("…και κλειδί άλλου καναλιού δεν μετράει",
          t26.m.a == 8, f"μήνυμα {t26.m.a}")

    check_switch_facing()
    check_hud_energy()
    check_hiscore()
    check_banking()

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


def check_switch_facing():
    """A switch answers only from the side it is mounted on.

    This is the whole point of making switches rotatable, and it is invisible
    to every other test: a wrong facing looks like a switch that simply does
    not work, in one room, for one gravity. The eight variants are found
    through the F_SWITCH flag, so a ninth added later is covered too.
    """
    from z80run import Z80Test
    t = Z80Test()
    t.fake_set_load()
    t.stub("RENDER_ROOM")
    t.stub("DRAW_TILE")
    cb = t.sym("CELL_BUF")

    # WHICH CELL THE BODY IS IN is sprite geometry, not something to hardcode:
    # hero_y is not the centre of a cell. Ask the code once, then put the
    # switch exactly there — otherwise the test passes for the wrong reason.
    # cell_at reads through level_ptr, not cell_buf directly. Without this the
    # room looks empty and every check passes for the wrong reason — the two
    # negative cases would still be green.
    t.poke16(t.sym("LEVEL_PTR"), cb)
    HX, HY = 20 * P.CELL + 4, P.GRID_Y0 + 12 * P.CELL + 4
    # h_touch reads the body cell with cell_at(hero_x, hero_y). Asking cell_at
    # directly, and not cell_col after the call, because h_touch overwrites
    # cell_col/cell_row with the SUPPORT cell before it returns.
    t.call("CELL_AT", bc=HX, de=HY)
    at = cb + t.peek(t.sym("CELL_ROW"))[0] * P.COLS + t.peek(t.sym("CELL_COL"))[0]

    def run(cell_type, gravity):
        """Stand on the switch with the given gravity and touch it once."""
        t.poke(cb, bytes(P.COLS * P.ROWS))          # empty room
        t.poke(at, bytes((cell_type,)))
        t.poke(t.sym("SW_PREV"), b"\xFF\xFF")      # not the same cell as last frame
        t.poke(t.sym("HERO_G"), bytes((gravity,)))
        t.poke16(t.sym("HERO_X"), HX)
        t.poke16(t.sym("HERO_Y"), HY)
        t.call("H_TOUCH")
        return t.peek(at)[0]

    # Floor switch: pressed with gravity DOWN, ignored hanging from a ceiling.
    got = run(P.SWITCH_U, 0)
    check("floor switch pressed with gravity down",
          got == P.SWITCH_U_ON, P.TYPE_NAMES[got])
    got = run(P.SWITCH_U, 4)
    check("…and ignored with gravity up", got == P.SWITCH_U, P.TYPE_NAMES[got])

    # Ceiling switch: the mirror image.
    got = run(P.SWITCH_D, 4)
    check("ceiling switch pressed with gravity up",
          got == P.SWITCH_D_ON, P.TYPE_NAMES[got])
    got = run(P.SWITCH_D, 0)
    check("…and ignored with gravity down", got == P.SWITCH_D, P.TYPE_NAMES[got])

    # WALL SWITCHES: the pair nobody checked. The letter is the FACING, not the
    # wall — 'Q' is SWITCH_L, it faces left, so it is bolted to the RIGHT wall
    # and answers with gravity pulling right. The editor's palette drew these
    # two mirrored for a long time and no test disagreed with it.
    got = run(P.SWITCH_L, 6)
    check("right-wall switch pressed with gravity right",
          got == P.SWITCH_L_ON, P.TYPE_NAMES[got])
    got = run(P.SWITCH_L, 2)
    check("…and ignored with gravity left", got == P.SWITCH_L, P.TYPE_NAMES[got])

    got = run(P.SWITCH_R, 2)
    check("left-wall switch pressed with gravity left",
          got == P.SWITCH_R_ON, P.TYPE_NAMES[got])
    got = run(P.SWITCH_R, 6)
    check("…and ignored with gravity right", got == P.SWITCH_R, P.TYPE_NAMES[got])

    # Pressing again turns it back: a toggle, not a one-shot.
    got = run(P.SWITCH_U_ON, 0)
    check("a pressed switch turns back off", got == P.SWITCH_U,
          P.TYPE_NAMES[got])

    # END TO END, ON A REAL ROOM. The synthetic grid above proved the facing
    # rule but not the wiring: the attribute is attached during parsing, by
    # cell type, and the ceiling switch was dropped there — the lever turned
    # and the gate never opened. Nothing that pokes its own grid can catch it.
    for room in P.all_rooms():
        sw = [(c, r) for r in range(P.ROWS) for c in range(P.COLS)
              if room.cells[r][c] in P.SWITCHES]
        if not sw:
            continue
        t2 = Z80Test()
        t2.fake_set_load()
        t2.stub("RENDER_ROOM")
        data = dict((i, d) for i, _, d in RF.all_sets())[RF.set_of(room.number)]
        t2.poke(t2.sym("SET_BUF"), data)
        t2.poke(t2.sym("JR_COUNT"), b"\x00")
        t2.call("ROOM_LOAD", a=room.number)
        for c, r in sw:
            want = room.attrs.get((c, r), 0)
            t2.call("CELL_ATTR", bc=(c << 8) | r)
            check(f"room {room.number}: switch ({c},{r}) keeps its channel",
                  t2.m.a == want, f"{t2.m.a} vs {want}")

    # A SWITCH PULLING SPIKES IN, ALL FOUR FACINGS, THROUGH HERO_UPDATE.
    #
    # Every wiring test above drives the targets by calling set_targets or
    # toggle_targets directly — which is exactly the step that skips the wiring.
    # The browser had a fault of that shape and 120 identical frames said
    # nothing, because the comparison also poked the cell by hand. Here the hero
    # stands on the switch and the game does the rest: touch, channel lookup,
    # target scan, cell rewrite.
    #
    # The four cases also pin down which surface each facing needs — the thing
    # the editor's palette got backwards for the two wall switches.
    CLK, ATTR = 0xB7FE, 0xB600
    for ch, gravity, (sc, sr), (hc, hr), spike, where in (
            ("S", 0, (10, 22), (10, 21), "^", "floor"),
            ("A", 4, (10,  1), (10,  2), "v", "ceiling"),
            ("Q", 6, (38, 12), (37, 12), "<", "right wall"),
            ("E", 2, ( 1, 12), ( 2, 12), ">", "left wall")):
        t3 = Z80Test()
        # Το ρολόι του firmware σε 11 bytes· χωρίς αυτό το KL_TIME_PLEASE
        # γυρίζει ό,τι έτυχε και ο πυργίσκος μέσα στο hero_update παραληρεί.
        code = bytes([0x2A, CLK & 0xFF, CLK >> 8, 0x11, 30, 0, 0x19,
                      0x22, CLK & 0xFF, CLK >> 8, 0xC9])
        for i, b in enumerate(code):
            t3.m.memory[0xBD0D + i] = b
        t3.poke16(CLK, 0)

        grid = [[P.EMPTY] * P.COLS for _ in range(P.ROWS)]
        for c in range(P.COLS):
            grid[0][c] = grid[P.ROWS - 1][c] = P.SOLID
        for r in range(P.ROWS):
            grid[r][0] = grid[r][P.COLS - 1] = P.SOLID
        grid[sr][sc] = P.CHARS[ch]
        grid[12][20] = P.CHARS[spike]
        t3.poke(t3.sym("CELL_BUF"), bytes(v for row in grid for v in row))
        t3.poke16(t3.sym("LEVEL_PTR"), t3.sym("CELL_BUF"))
        t3.poke(t3.sym("HERO_ENERGY"), bytes([P.ENERGY_MAX]))
        t3.poke(t3.sym("HERO_HURT"), b"\x00")
        t3.poke(t3.sym("HERO_G"), bytes([gravity]))
        t3.poke(ATTR, bytes((sc, sr, 1)) + bytes((20, 12, 1)) + b"\xFF")
        t3.poke16(t3.sym("ROOM_ATTRS"), ATTR)
        t3.call("TURRET_LOAD")          # άδειος πίνακας βελών
        t3.poke16(t3.sym("HERO_X"), hc * P.CELL + P.CELL // 2)
        t3.poke(t3.sym("HERO_Y"),
                bytes([P.GRID_Y0 + hr * P.CELL + P.CELL // 2]))

        at = t3.sym("CELL_BUF") + 12 * P.COLS + 20
        before = t3.peek(at)[0]
        for _ in range(60):
            t3.m.a = 0
            t3.call("HERO_UPDATE")
            if t3.peek(at)[0] != before:
                break
        check(f"{where} switch pulls its spikes in",
              t3.peek(at)[0] == P.SPIKE_OFF[before],
              f"{P.TYPE_NAMES[before]} -> {P.TYPE_NAMES[t3.peek(at)[0]]}")

    # Every variant carries the flag, so nothing is reachable only by number.
    missing = [P.TYPE_NAMES[x] for x in sorted(P.SWITCHES)
               if not (P.PROPS[x] & P.F_SWITCH)]
    check("every switch variant carries F_SWITCH", not missing, str(missing))


def check_hud_energy():
    """ΚΑΘΕ δρόμος απώλειας ενέργειας πρέπει να λερώνει το HUD.

    Το draw_hud ξαναζωγραφίζει μόνο όταν hud_dirty != 0. Τα αγκάθια και τα
    pickups το σήκωναν, η ΖΗΜΙΑ ΑΠΟ ΠΤΩΣΗ όχι — η μπάρα έμενε παγωμένη ως το
    επόμενο άσχετο συμβάν και ο παίκτης δεν έβλεπε γιατί πέθανε. Το τεστ
    κρατά και τους τρεις δρόμους μαζί: όποιος προστεθεί τέταρτος και ξεχάσει
    το hud_dirty θα το μάθει εδώ.
    """
    from z80run import Z80Test
    t = Z80Test()
    t.fake_set_load()
    dirty, energy = t.sym("HUD_DIRTY"), t.sym("HERO_ENERGY")

    # --- πτώση πάνω από το ασφαλές όριο ------------------------------
    t.poke(dirty, b"\x00")
    t.poke(energy, bytes((P.ENERGY_MAX,)))
    t.poke(t.sym("HERO_HURT"), b"\x00")
    t.poke(t.sym("HERO_PARAOPEN"), b"\x00")
    t.poke16(t.sym("HERO_FALL"), P.FALL_SAFE + 24)      # ζημιά 1 + 24/12 = 3
    t.call("H_LAND")
    lost = P.ENERGY_MAX - t.peek(energy)[0]
    check("κακή προσγείωση: χάνεται ενέργεια", lost > 0, f"-{lost}")
    check("…και το HUD ενημερώνεται ΤΟ ΙΔΙΟ ΚΑΡΕ",
          t.peek(dirty) == b"\x01", f"hud_dirty = {t.peek(dirty)[0]}")

    # --- ασφαλής πτώση: ούτε ζημιά ούτε άσκοπο ξαναζωγράφισμα --------
    t.poke(dirty, b"\x00")
    t.poke(energy, bytes((P.ENERGY_MAX,)))
    t.poke(t.sym("HERO_HURT"), b"\x00")
    t.poke16(t.sym("HERO_FALL"), P.FALL_SAFE - 1)
    t.call("H_LAND")
    check("ασφαλής πτώση: καμία ζημιά",
          t.peek(energy)[0] == P.ENERGY_MAX)
    check("…και κανένα άσκοπο ξαναζωγράφισμα", t.peek(dirty) == b"\x00")

    # --- νέα παρτίδα: γεμάτη μπάρα από το πρώτο καρέ -----------------
    t.poke(dirty, b"\x00")
    t.poke(energy, b"\x01")
    t.call("GAME_RESET")
    check("game_reset: γεμάτη ενέργεια", t.peek(energy)[0] == P.ENERGY_MAX)
    check("…και το HUD το δείχνει χωρίς να περιμένει συμβάν",
          t.peek(dirty) == b"\x01")


def check_hiscore():
    """Ο πίνακας βαθμολογιών: κατάταξη, εισαγωγή, μορφοποίηση ψηφίων.

    Ο ΔΙΣΚΟΣ ΔΕΝ ΔΟΚΙΜΑΖΕΤΑΙ ΕΔΩ και δεν μπορεί: όλο το jumpblock του firmware
    είναι RET, οπότε τα CAS_OUT_* δεν κάνουν τίποτα. Ό,τι ελέγχεται είναι η
    λογική που ζει στη μνήμη — γι' αυτό γράφτηκε χωριστά από τον δίσκο.
    """
    from z80run import Z80Test
    t = Z80Test()
    tab = t.sym("HS_TABLE")
    entry = 3 + P.HISCORE_NAME

    def put(scores):
        for i, (sc, nm) in enumerate(scores):
            t.poke(tab + i * entry, sc.to_bytes(3, "little", signed=True))
            t.poke(tab + i * entry + 3, nm.encode())

    def table():
        out = []
        for i in range(P.HISCORE_MAX):
            b = t.peek(tab + i * entry, entry)
            out.append((int.from_bytes(b[:3], "little", signed=True),
                        b[3:].decode(errors="replace")))
        return out

    # --- hs_reset ----------------------------------------------------
    put([(9, "ZZZ")] * P.HISCORE_MAX)
    t.call("HS_RESET")
    check("hs_reset: πέντε μηδενικά με όνομα NUL",
          table() == [(0, "NUL")] * P.HISCORE_MAX, str(table()[:2]))

    # --- hs_place ----------------------------------------------------
    base = [(500, "AAA"), (400, "BBB"), (300, "CCC"), (200, "DDD"), (100, "EEE")]
    for score, want in ((600, 0), (450, 1), (350, 2), (150, 4), (50, None),
                        (100, None), (500, 1)):
        put(base)
        t.poke(t.sym("HS_SCORE"), score.to_bytes(3, "little", signed=True))
        t.call("HS_PLACE")
        placed = bool(t.m.f & 1)
        if want is None:
            check(f"hs_place {score}: δεν μπαίνει", not placed,
                  f"μπήκε στη θέση {t.m.a}" if placed else "")
        else:
            check(f"hs_place {score}: θέση {want}",
                  placed and t.m.a == want,
                  f"{'θέση ' + str(t.m.a) if placed else 'δεν μπήκε'}")

    # ΙΣΟΠΑΛΙΑ ΚΑΤΩ: το 100 δεν εκτοπίζει το 100 που είναι ήδη εκεί, αλλιώς
    # κάθε επανάληψη του ίδιου σκορ θα έσπρωχνε τον προηγούμενο παίκτη έξω.

    # --- hs_insert ---------------------------------------------------
    put(base)
    t.poke(t.sym("HS_SCORE"), (450).to_bytes(3, "little"))
    t.poke(t.sym("HS_NAME"), b"NEW")
    t.call("HS_INSERT", a=1)
    check("hs_insert: μπαίνει στη θέση και σπρώχνει τα από κάτω",
          table() == [(500, "AAA"), (450, "NEW"), (400, "BBB"),
                      (300, "CCC"), (200, "DDD")], str(table()))

    put(base)
    t.poke(t.sym("HS_SCORE"), (1).to_bytes(3, "little"))
    t.poke(t.sym("HS_NAME"), b"LST")
    t.call("HS_INSERT", a=P.HISCORE_MAX - 1)
    check("hs_insert: τελευταία θέση δεν σπρώχνει τίποτα",
          table() == base[:-1] + [(1, "LST")], str(table()[-2:]))

    put(base)
    t.poke(t.sym("HS_SCORE"), (999).to_bytes(3, "little"))
    t.poke(t.sym("HS_NAME"), b"TOP")
    t.call("HS_INSERT", a=0)
    check("hs_insert: πρώτη θέση σπρώχνει όλες",
          table() == [(999, "TOP")] + base[:-1], str(table()[:2]))

    # --- score_digits ------------------------------------------------
    for value, want in ((1000, " 001000"), (0, " 000000"), (42, " 000042"),
                        (999999, " 999999"), (32768, " 032768"),
                        (100000, " 100000"), (-5, "-000005"),
                        (-1234, "-001234")):
        t.poke(t.sym("SCORE"), (value & 0xFFFFFF).to_bytes(3, "little"))
        t.call("SCORE_DIGITS")
        got = t.peek(t.sym("SCORE_TXT"), 7).decode(errors="replace")
        check(f"score_digits {value} -> '{want}'", got == want, f"'{got}'")


def check_banking():
    """Το μοντέλο τραπεζών του z80run — ΠΡΙΝ γραφτεί κώδικας banking.

    Χωρίς αυτό, ένα τεστ για τη μελλοντική bank.asm θα περνούσε ακόμα κι αν ο
    προσομοιωτής αγνοούσε εντελώς το OUT: θα διάβαζε τη βασική μνήμη και θα
    έβρισκε ό,τι μόλις έγραψε. Πράσινο εδώ, σκουπίδια-αίθουσες στο σίδερο.
    """
    from z80run import Z80Test, BANK_LO

    # Δοκιμαστικό πρόγραμμα ΠΑΝΩ από το #8000, γιατί ακριβώς αυτός είναι ο
    # κανόνας που θα τηρεί και η bank.asm: ο κώδικας δεν επιτρέπεται να ζει
    # μέσα στο παράθυρο που εναλλάσσει.
    PROG = 0x8000
    CELL = BANK_LO + 0x0123         # κάπου μέσα στο παράθυρο

    def program(org_in, org_out):
        # ld bc,#7F00+org_in / out (c),c    -> σελίδα μέσα
        # ld a,(CELL) / ld (PROG+0x40),a    -> διάβασε ΜΕΣΑ από την τράπεζα
        # ld bc,#7F00+org_out / out (c),c   -> σελίδα έξω
        # halt
        return bytes((0x01, org_in, 0x7F, 0xED, 0x49,
                      0x3A, CELL & 0xFF, CELL >> 8,
                      0x32, (PROG + 0x40) & 0xFF, (PROG + 0x40) >> 8,
                      0x01, org_out, 0x7F, 0xED, 0x49,
                      0x76))

    t = Z80Test(banking=True)
    t.poke(CELL, b"\xAA")                       # βασική μνήμη (μπλοκ 1)
    t.bank_poke(4, CELL, b"\x55")               # ίδια διεύθυνση, μπλοκ 4
    t.poke(PROG, program(0xC4, 0xC0))
    t.m.pc = PROG
    t.m.halted = False
    t.m.ticks_to_stop = 100000
    t.m.run()
    check("η οργάνωση 4 φέρνει το μπλοκ 4 στο #4000",
          t.peek(PROG + 0x40) == b"\x55", f"διάβασε #{t.peek(PROG + 0x40)[0]:02X}")
    check("…και η βασική μνήμη δεν πειράχτηκε",
          t.peek(CELL) == b"\xAA")
    check("…και η οργάνωση επέστρεψε στο 0", t.ram_org == 0)

    # Το ΙΔΙΟ πρόγραμμα σε μηχάνημα 64K: το OUT αγνοείται, οπότε διαβάζει τη
    # βασική μνήμη. Αυτό είναι που θα πρέπει να πιάνει το bank_probe.
    t64 = Z80Test()                             # banking=False = 64K
    t64.poke(CELL, b"\xAA")
    t64.poke(PROG, program(0xC4, 0xC0))
    t64.m.pc = PROG
    t64.m.halted = False
    t64.m.ticks_to_stop = 100000
    t64.m.run()
    check("σε μηχάνημα 64K η ίδια αλληλουχία διαβάζει τη ΒΑΣΙΚΗ μνήμη",
          t64.peek(PROG + 0x40) == b"\xAA",
          f"διάβασε #{t64.peek(PROG + 0x40)[0]:02X}")

    # Τέσσερις τράπεζες, τέσσερις διαφορετικές τιμές στην ΙΔΙΑ διεύθυνση.
    t4 = Z80Test(banking=True)
    for i, org in enumerate((0xC4, 0xC5, 0xC6, 0xC7)):
        t4.bank_poke(4 + i, CELL, bytes((0x10 + i,)))
    got = []
    for i, org in enumerate((0xC4, 0xC5, 0xC6, 0xC7)):
        t4.poke(PROG, program(org, 0xC0))
        t4.m.pc = PROG
        t4.m.halted = False
        t4.m.ticks_to_stop = 100000
        t4.m.run()
        got.append(t4.peek(PROG + 0x40)[0])
    check("και τα τέσσερα μπλοκ διακρίνονται μεταξύ τους",
          got == [0x10, 0x11, 0x12, 0x13],
          " ".join(f"#{v:02X}" for v in got))

    check_bank_asm()


def check_bank_asm():
    """Το src/bank.asm πάνω στο μοντέλο τραπεζών."""
    from z80run import Z80Test, BANK_LO

    # --- bank_probe σε μηχάνημα 128K ---------------------------------
    t = Z80Test(banking=True)
    orig = t.peek(BANK_LO)                  # η πρώτη εντολή του προγράμματος
    t.call("BANK_PROBE")
    check("bank_probe βρίσκει τις τράπεζες σε 128K",
          t.peek(t.sym("BANK_OK")) == b"\x01")
    check("…και αφήνει τον κώδικα στο #4000 όπως τον βρήκε",
          t.peek(BANK_LO) == orig,
          f"#{orig[0]:02X} -> #{t.peek(BANK_LO)[0]:02X}")
    check("…και την οργάνωση πίσω στη βασική", t.ram_org == 0)

    # --- bank_probe σε μηχάνημα 64K ----------------------------------
    t64 = Z80Test()                         # banking=False: το OUT αγνοείται
    orig64 = t64.peek(BANK_LO)
    t64.call("BANK_PROBE")
    check("bank_probe ΔΕΝ βρίσκει τράπεζες σε 64K",
          t64.peek(t64.sym("BANK_OK")) == b"\x00")
    check("…και εκεί επίσης αφήνει τον κώδικα ανέπαφο",
          t64.peek(BANK_LO) == orig64)

    # --- η στοίβα μέσα στο παράθυρο απαγορεύει το banking ------------
    # Χειροκίνητα, γιατί το Z80Test.call ορίζει το ίδιο το SP.
    ts = Z80Test(banking=True)
    ts.poke(ts.sym("BANK_OK"), b"\xEE")     # ώστε το 0 να είναι δική του δουλειά
    ts.m.sp = 0x6000                        # ΜΕΣΑ στο #4000..#7FFF
    ts.m.sp = (ts.m.sp - 2) & 0xFFFF
    ts.poke16(ts.m.sp, 0x0038)
    ts.m.pc = ts.sym("BANK_PROBE")
    ts.m.halted = False
    ts.m.ticks_to_stop = 100000
    ts.m.run()
    check("στοίβα μέσα στο παράθυρο -> κανένα banking",
          ts.peek(ts.sym("BANK_OK")) == b"\x00",
          f"bank_ok = #{ts.peek(ts.sym('BANK_OK'))[0]:02X}")

    # --- bank_copy: τράπεζα -> βασική μνήμη --------------------------
    PATTERN = bytes(range(0x40, 0x50))
    SCRATCH = 0x0200                        # μπλοκ 0, έξω από το παράθυρο
    for i, org in enumerate((0xC4, 0xC5, 0xC6, 0xC7)):
        tc = Z80Test(banking=True)
        src = BANK_LO + 0x0800
        tc.bank_poke(4 + i, src, bytes(b ^ (i * 0x11) for b in PATTERN))
        tc.poke(src, b"\xFF" * len(PATTERN))    # βασική μνήμη: σκουπίδια
        tc.call("BANK_COPY", a=org, hl=src, de=SCRATCH, bc=len(PATTERN))
        want = bytes(b ^ (i * 0x11) for b in PATTERN)
        check(f"bank_copy φέρνει το μπλοκ {4 + i} έξω",
              tc.peek(SCRATCH, len(PATTERN)) == want)
        if i == 0:
            check("…και δεν άφησε το παράθυρο ανοιχτό", tc.ram_org == 0)
            check("…και η βασική μνήμη στην ίδια διεύθυνση δεν πειράχτηκε",
                  tc.peek(src, len(PATTERN)) == b"\xFF" * len(PATTERN))

    # --- bank_fill: βασική μνήμη -> τράπεζα --------------------------
    tf = Z80Test(banking=True)
    dst = BANK_LO + 0x1000
    # ΟΧΙ «είναι μηδενικά»: το #5000 είναι ΚΩΔΙΚΑΣ του παιχνιδιού και το
    # περιεχόμενό του μετακινείται σε κάθε αλλαγή. Κρατάμε τι ήταν και
    # ελέγχουμε ότι έμεινε ίδιο — αυτό ρωτάει το τεστ ούτως ή άλλως.
    before = tf.peek(dst, len(PATTERN))
    tf.poke(SCRATCH, PATTERN)
    tf.call("BANK_FILL", a=0xC6, hl=SCRATCH, de=dst, bc=len(PATTERN))
    check("bank_fill γράφει ΜΕΣΑ στην τράπεζα",
          tf.bank_peek(6, dst, len(PATTERN)) == PATTERN)
    check("…χωρίς να αγγίξει τη βασική μνήμη στην ίδια διεύθυνση",
          tf.peek(dst, len(PATTERN)) == before,
          " ".join(f"{b:02X}" for b in tf.peek(dst, len(PATTERN))[:4]))
    check("…και οι άλλες τράπεζες δεν πειράχτηκαν",
          tf.bank_peek(4, dst, len(PATTERN)) == b"\x00" * len(PATTERN))

    # --- slot_addr: ο Z80 πρέπει να συμφωνεί με το roomfile.slot_of ---
    # Δύο υλοποιήσεις της ίδιας αριθμητικής, σε δύο γλώσσες. Αν αποκλίνουν, ο
    # Z80 διαβάζει σετ από λάθος θέση και η αίθουσα βγαίνει σκουπίδι.
    ta = Z80Test(banking=True)
    bad = []
    # Οι δείκτες βγαίνουν από το ΙΔΙΟ το εργαλείο: το μέγεθος θέσης έχει
    # αλλάξει τρεις φορές και μια καρφωμένη λίστα ξεπερνούσε το όριο.
    #
    # SETS_USABLE και ΟΧΙ MAX_SETS: το τελευταίο μπλοκ ανήκει στη μουσική και
    # το roomfile.slot_of αρνείται να δώσει θέση εκεί. Το MAX_SETS παραμένει
    # το μέγεθος του bank_map — δύο διαφορετικά πράγματα με παρόμοιο όνομα.
    per = RF.SLOTS_PER_BANK
    top = RF.SETS_USABLE
    idxs = sorted({1, 2, per, per + 1, 2 * per, 2 * per + 1, top - 1, top}
                  & set(range(1, top + 1)))
    for idx in idxs:
        want_bank, want_addr = RF.slot_of(idx)
        ta.call("SLOT_ADDR", a=idx)
        got_addr, got_org = ta.m.hl, ta.m.bc & 0xFF
        if (got_addr, got_org) != (want_addr, 0xC0 + want_bank):
            bad.append(f"σετ {idx}: #{got_addr:04X}/#{got_org:02X} αντί για "
                       f"#{want_addr:04X}/#{0xC0 + want_bank:02X}")
    check(f"slot_addr συμφωνεί με το roomfile.slot_of ({len(idxs)} σημεία, "
          f"{top} σετ· το μπλοκ 7 είναι της μουσικής)",
          not bad, "; ".join(bad))

    # --- slot_full: ο χάρτης γεμάτων θέσεων ---------------------------
    tm = Z80Test(banking=True)
    tm.poke(tm.sym("BANK_MAP"), bytes(RF.MAX_SETS // 8))    # όλα άδεια
    tm.call("SLOT_FULL", a=1)
    check("άδεια θέση -> CF=0", not (tm.m.f & 1))
    tm.poke(tm.sym("BANK_MAP"), b"\x01")                    # σετ 1 = bit 0
    tm.call("SLOT_FULL", a=1)
    check("γεμάτη θέση -> CF=1", bool(tm.m.f & 1))
    tm.call("SLOT_FULL", a=2)
    check("…και μόνο αυτή", not (tm.m.f & 1))
    tm.call("SLOT_FULL", a=RF.MAX_SETS + 1)
    check("δείκτης έξω από τον χάρτη -> CF=0", not (tm.m.f & 1))


if __name__ == "__main__":
    sys.exit(main())
