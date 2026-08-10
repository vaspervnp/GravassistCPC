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
        check(f"το draw_hud ζωγραφίζει το βέλος κόσμου (φορά {gw})",
              hud_bytes(t.sym("GRAV_WX") if False else 68) == want_w)
        check(f"το draw_hud ζωγραφίζει το βέλος ήρωα (φορά {gh})",
              hud_bytes(72) == want_h)

    # …και ΧΩΡΙΣ hud_dirty, όταν αλλάξει μόνο η βαρύτητα. Ο ήρωας γυρίζει σε
    # κάθε γωνία που περπατάει χωρίς να πειράζει ενέργεια ή inventory: με
    # κριτήριο το hud_dirty τα βελάκια θα έμεναν παγωμένα.
    t.poke(t.sym("HUD_DIRTY"), b"\x00")
    t.poke(t.sym("HERO_G"), b"\x02")
    t.call("DRAW_HUD")
    check("το βέλος ήρωα ενημερώνεται χωρίς hud_dirty",
          hud_bytes(72) == [tuple(GA.pack_mode1(GA.arrow_pixels(2, 2)[y]))
                            for y in range(8)])

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

    # 13. Μουσική: ο player χτίζει σωστά μπλοκ για το SOUND QUEUE και ο
    #     κύκλος ξαναρχίζει από την αρχή. Το firmware εδώ απαντά πάντα
    #     «μπήκε στην ουρά» (SCF; RET), ώστε να προχωράει η ροή σε κάθε βήμα.
    import genmusic as GM
    t.m.memory[0xBCAA] = 0x37           # SCF
    t.m.memory[0xBCAB] = 0xC9           # RET
    t.m.memory[0xBCA7] = 0xC9           # SOUND RESET -> RET
    t.call("MUSIC_START")

    table = GM.collect(GM.BASS, GM.LEAD, GM.PULSE)
    bass, _ = GM.stream(GM.BASS, table, GM.VOL_BASS)

    t.call("MUSIC_STEP")
    # Το snd_block είναι ΚΟΙΝΟ και τα κανάλια γράφουν με τη σειρά, οπότε μετά
    # από ένα βήμα κρατά το ΤΕΛΕΥΤΑΙΟ — τον παλμό.
    pulse, _ = GM.stream(GM.PULSE, table, GM.VOL_PULSE)
    note, vol, dur = pulse[0]
    blk = t.peek(t.sym("SND_BLOCK"), 9)
    want_tone = GM.period(table[note - 1])
    check("το μπλοκ ήχου έχει το σωστό κανάλι", blk[0] == 4, str(blk[0]))
    check("…τη σωστή περίοδο τόνου",
          blk[3] | (blk[4] << 8) == want_tone,
          f"{blk[3] | (blk[4] << 8)} vs {want_tone}")
    check("…τη σωστή ένταση και διάρκεια",
          blk[6] == vol and blk[7] | (blk[8] << 8) == dur,
          f"vol {blk[6]}/{vol}, dur {blk[7] | (blk[8] << 8)}/{dur}")
    check("…και θόρυβο μόνο εκεί που πρέπει",
          blk[5] == GM.NOISE_PULSE, str(blk[5]))

    for name, base in (("bass", "MUS_BASS"), ("lead", "MUS_LEAD"),
                       ("pulse", "MUS_PULSE")):
        ptr = t.peek16(t.sym("MUS_P_" + name.upper()))
        check(f"το κανάλι {name} προχώρησε μία νότα",
              ptr == t.sym(base) + 3, f"#{ptr:04X}")

    # Μία πλήρης περιστροφή: στο τελευταίο βήμα ο δείκτης δείχνει στο #FF και
    # το επόμενο τον γυρίζει στην αρχή.
    for _ in range(len(bass) - 1):
        t.call("MUSIC_STEP")
    check("ο δείκτης φτάνει στο τέλος της ροής",
          t.peek16(t.sym("MUS_P_BASS")) == t.sym("MUS_BASS") + 3 * len(bass),
          f"#{t.peek16(t.sym('MUS_P_BASS')):04X}")
    t.call("MUSIC_STEP")
    check("ο κύκλος ξαναρχίζει από την αρχή",
          t.peek16(t.sym("MUS_P_BASS")) == t.sym("MUS_BASS") + 3,
          f"#{t.peek16(t.sym('MUS_P_BASS')):04X}")

    # Το μήκος του κύκλου: 20 δευτερόλεπτα, και τα τρία κανάλια ίσα.
    for name, track, vol in (("bass", GM.BASS, GM.VOL_BASS),
                             ("lead", GM.LEAD, GM.VOL_LEAD),
                             ("pulse", GM.PULSE, GM.VOL_PULSE)):
        data, total = GM.stream(track, table, vol)
        check(f"το κανάλι {name} κρατά ακριβώς 20 δευτερόλεπτα",
              total == GM.LOOP, f"{total / 100:.1f}s")

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

    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"{len(FAILS)} ΑΠΟΤΥΧΙΕΣ: {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
