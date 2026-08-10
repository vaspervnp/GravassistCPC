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
    for index, name, data in RF.all_sets():
        t.poke(set_buf, data)
        t.poke(t.sym("SET_CUR"), bytes((index,)))    # «είναι ήδη φορτωμένο»
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
                      set_buf <= ptr < set_buf + len(data))
                got, p = [], ptr
                while t.peek(p)[0] != 0xFF and len(got) < 64:
                    got.append(tuple(t.peek(p, 4)))
                    p += 4
                check(f"room_load {room.number}: {label}",
                      got == expect, f"{got} vs {expect}")

    # 3β. Το όνομα αρχείου φτιάχνεται με δύο ψηφία επιτόπου. Λάθος εδώ και το
    #     παιχνίδι ζητά αρχείο που δεν υπάρχει — χωρίς κανένα μήνυμα.
    for index, want in ((1, b"ROOMS01.BIN"), (9, b"ROOMS09.BIN"),
                        (10, b"ROOMS10.BIN"), (42, b"ROOMS42.BIN")):
        t.call("SET_LOAD", a=index)     # το firmware εδώ είναι RET, άρα αποτυγχάνει
        got = t.peek(t.sym("SET_FNAME"), 11)
        check(f"set_load: όνομα για σετ {index}", got == want, f"{got} vs {want}")
        check(f"set_load: αποτυχία δίσκου δεν κλειδώνει το σετ {index}",
              t.peek(t.sym("SET_CUR"))[0] == 0)

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
    for g in range(8):
        for a in range(0xC000, 0x10000):
            t.m.memory[a] = 0
        t.call("DRAW_GARROW", a=g, hl=t.sym("GRAV_GFX_WORLD"), bc=68)
        got, want = [], []
        for y in range(8):
            base = 0xC000 + (y % 8) * 0x800 + (y // 8) * 80 + 68
            got.append((t.m.memory[base], t.m.memory[base + 1]))
            want.append(tuple(GA.pack_mode1(GA.arrow_pixels(g, 3)[y])))
        check(f"βέλος βαρύτητας φοράς {g} στο HUD", got == want)

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

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
