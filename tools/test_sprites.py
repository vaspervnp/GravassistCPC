#!/usr/bin/env python3
"""Το spr_unpack του Z80, απέναντι στα ίδια τα PNG.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ: τα sprites αποθηκεύονται πλέον τέσσερα pixels ανά byte — ένα pen
του MODE 1 είναι δύο bits και τα δεδομένα κρατούσαν ολόκληρο byte για καθένα,
πράγμα που κόστιζε 4890 bytes σε μηχάνημα που είχε μείνει με έντεκα ελεύθερα.
Ο περιστροφέας όμως δεν άλλαξε: ξεπακετάρει ένα καρέ σε πρόχειρο buffer και
δουλεύει όπως πάντα.

Άρα ΟΛΟ το ρίσκο της συμπίεσης είναι σε μία καινούργια ρουτίνα, το spr_unpack,
και σε αυτήν κανένα από τα υπάρχοντα τεστ δεν ακουμπά: το verify_rotate.py
δουλεύει πάνω στο μοντέλο της Python, και το round-trip του sprites.py ελέγχει
τη γεννήτρια απέναντι στον εαυτό της. Εδώ τρέχει ο ΠΡΑΓΜΑΤΙΚΟΣ Z80 πάνω στα
ΠΡΑΓΜΑΤΙΚΑ bytes του MAIN.BIN, καρέ προς καρέ, pixel προς pixel.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cpcgfx
import sprites
import stickman
import verify_rotate as VR

FAILS = []


def check(name, cond, detail=""):
    print(f"  {'ΟΚ  ' if cond else 'ΛΑΘΟΣ'} {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def main():
    try:
        from z80run import Z80Test
    except RuntimeError as e:
        print(f"  ΠΑΡΑΛΕΙΨΗ τεστ sprites: {e}")
        return 0

    t = Z80Test()
    src = t.sym("SPR_SRC")
    total = 0
    for sh in sprites.SHEETS:
        if sh.label.upper() not in t.syms:
            continue                    # sheet που δεν το κάνει include κανείς
        if not os.path.exists(sh.path_png()):
            continue
        frames = cpcgfx.read_sheet(sh.path_png(), sh.w, sh.h, sh.cols, sh.count)
        stride = (sh.w + 3) // 4
        base = t.sym(sh.label)
        bad = []
        for i, fr in enumerate(frames):
            t.call("SPR_UNPACK", hl=base + i * stride * sh.h,
                   bc=(sh.w << 8) | sh.h)
            got = list(t.peek(src, sh.w * sh.h))
            want = [v for row in fr for v in row]
            if got != want:
                first = next(k for k in range(len(want)) if got[k] != want[k])
                bad.append(f"καρέ {i} pixel {first}: {got[first]} αντί για "
                           f"{want[first]}")
            total += 1
        check(f"{sh.key}: {len(frames)} καρέ {sh.w}x{sh.h} ξεπακετάρονται "
              f"ακριβώς", not bad, "; ".join(bad[:2]))

        # Και ΤΙ ΑΛΛΟ άγγιξε: ο buffer είναι SPR_SRCSZ και το καρέ μικρότερο,
        # οπότε ό,τι είναι πέρα από W*H δεν επιτρέπεται να αλλάξει. Χωρίς αυτό
        # ένα λάθος στο μέτρημα γραμμών θα έγραφε πάνω στον spr_buf σιωπηλά.
        t.poke(src + sh.w * sh.h, b"\xC7" * 8)
        t.call("SPR_UNPACK", hl=base, bc=(sh.w << 8) | sh.h)
        check(f"{sh.key}: δεν γράφει πέρα από το καρέ",
              t.peek(src + sh.w * sh.h, 8) == b"\xC7" * 8)

        # Και ότι γυρίζει τα W/H στον καλούντα: το spr_transform τα θέλει.
        check(f"{sh.key}: επιστρέφει B=W, C=H και HL=spr_src",
              t.m.bc == ((sh.w << 8) | sh.h) and t.m.hl == src,
              f"BC=#{t.m.bc:04X} HL=#{t.m.hl:04X}")

    # --- ΚΑΙ Ο ΙΔΙΟΣ Ο ΜΕΤΑΣΧΗΜΑΤΙΣΜΟΣ, END TO END ----------------------
    #
    # Το spr_transform δεν δοκιμαζόταν ΠΟΤΕ σε Z80 — μόνο ο αλγόριθμός του, σε
    # Python, από το verify_rotate.py. Αυτό ήταν ανεκτό όσο η ρουτίνα δεν
    # άλλαζε· τώρα η είσοδός της κάνει πρώτα spr_unpack, οπότε ένα λάθος στη
    # συνεννόηση των δύο (καταχωρητής που χάθηκε, push χωρίς pop) δεν θα
    # φαινόταν πουθενά αλλού παρά στην οθόνη του Amstrad.
    #
    # Σύγκριση με το ΙΔΙΟ μοντέλο που ήδη εμπιστευόμαστε, για κάθε φορά
    # βαρύτητας και κάθε μετατόπιση pixel.
    frames = stickman.build_frames()
    frames45 = stickman.build_frames45()
    buf, bw, bh = t.sym("SPR_BUF"), t.sym("SPR_BW"), t.sym("SPR_BH")
    bad, n = [], 0
    for grav in range(8):
        src = frames45 if grav & 1 else frames
        for fi in (0, 5, 13, 21):
            for shift in range(4):
                t.poke(t.sym("SPR_SHIFT"), bytes([shift]))
                t.call("HERO_TRANSFORM", a=grav, bc=fi << 8)
                w = t.peek(bw)[0]
                h = t.peek(bh)[0]
                got = list(t.peek(buf, w * h * 2))
                ew, eh, want = VR.table_driven(src[fi], grav >> 1, shift)
                flat = [v for pair in want for v in pair]
                if (w, h) != (ew, eh) or got != flat:
                    bad.append(f"grav {grav} καρέ {fi} shift {shift}")
                n += 1
    check(f"hero_transform: {n} συνδυασμοί ίδιοι με το μοντέλο",
          not bad, "; ".join(bad[:3]))

    check("δοκιμάστηκαν καρέ", total > 0, str(total))
    print("ΟΛΑ ΣΩΣΤΑ" if not FAILS else f"ΑΠΕΤΥΧΑΝ {len(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
