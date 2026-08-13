# GRAVASSIST — Amstrad CPC, Z80 assembly, MODE 1

Puzzle game όπου ο παίκτης αλλάζει την **κατεύθυνση της βαρύτητας** για να περπατάει
σε πατώματα, τοίχους, ταβάνια και πλατφόρμες.

- Λεπτομερής σχεδιασμός: [plan.md](plan.md)
- **Visual reference (δεσμευτικό): [docs/concept-art.md](docs/concept-art.md)** —
  διάβασέ το πριν σχεδιάσεις sprites, tiles, HUD ή παλέτα.

## Toolchain (WSL)
Οι διαδρομές ΔΕΝ είναι καρφωμένες: ορίζονται στο [toolchain.json](toolchain.json)
(κατάλογος + ονόματα). `make toolchain` δείχνει τι θα τρέξει τελικά. Παρακάμπτεται
με `GRAVASSIST_RASM` / `GRAVASSIST_IDSK` ή με `make ASM=... DISK=...`.
- Assembler: `rasm` (v3.2.5) — `/usr/local/bin/rasm`
- Disk tool: `iDSK` (v0.20) — `/usr/local/bin/iDSK`
- Emulator: RetroVirtualMachine / WinAPE από τη μεριά των Windows (δεν τρέχει από εδώ)
- Sources των εργαλείων: `~/rasm`, `~/idsk` (additional working dirs)
- Python 3.14 + Pillow 12.3 (για τα `tools/*.py`: PNG <-> asm)
- **.NET SDK 10.0.302** στο `~/.dotnet` — **ΔΕΝ είναι στο PATH**. Χρησιμοποίησε
  `~/.dotnet/dotnet` ή κάνε πρώτα `export PATH="$HOME/.dotnet:$PATH"`.
  Περιλαμβάνει ASP.NET Core runtime και το template `mvc` (level editor).

## Target hardware
- Amstrad CPC 6128, 128 KB RAM, Z80 @ 4 MHz, 50 Hz
- **MODE 1**: 320x200, 4 pens, **4 pixels/byte**, 80 bytes/scanline
- Screen στο #C000, γραμμές interleaved ανά #800 (CRTC standard layout)
- Load / exec address: **#4000**
- Firmware **ενεργό** (jumpblock calls· `MC_WAIT_FLYBACK` για sync)

## Build
```
make              # assemble + φτιάχνει build/gravassist.dsk
make test         # μοντέλο, ΠΡΑΓΜΑΤΙΚΟΣ Z80 σε προσομοιωτή, editor
make trace        # οπτικό ίχνος της διαδρομής του ήρωα
make toolchain    # ποια rasm/iDSK θα τρέξουν τελικά
make editor-data  # δεδομένα για το test run του browser
make clean
```
Το `rasm` βγάζει το `build/main.bin` μέσω `save` directive μέσα στο `src/main.asm`.
Το iDSK φτιάχνει το dsk και βάζει MAIN.BIN (`-t 1 -c 4000 -e 4000`) + τον BASIC
loader, τα `ROOMSnn.BIN` (αίθουσες) και τα `TUNEnn.BIN` (μουσική).
Δοκιμή στον emulator: `RUN"GRAV"`. Και `RUN"MUSIC"` για να ακουστεί μόνο η
μουσική, χωρίς το παιχνίδι — ξεχωριστό πρόγραμμα, δες παρακάτω.

## Δομή project

Ο κώδικας του παιχνιδιού — όλα γίνονται include από το `src/main.asm`:
```
src/main.asm        κύριος βρόχος, σχεδίαση, HUD, μηνύματα (org #4000)
src/hero.asm        φυσική: βάδισμα, γωνίες, ράμπες, πτώση, αντικείμενα
src/level.asm       solid_at με ράμπες, σχεδίαση δωματίου
src/rotate.asm      ξεπακετάρισμα + περιστροφή + packing sprites σε MODE 1
src/roomfile.asm    σετ αιθουσών: RLE, φόρτωση, ημερολόγιο, καλωδίωση
src/bank.asm        οι δεύτερες 64 KB του 6128: μπλοκ 4-6 αίθουσες, 7 μουσική
src/menu.asm        μενού: τίτλος, αρένα επίδειξης, draw_banner, demo_mark
src/endings.asm     GAME OVER / THE END, και το game_reset
src/score.asm       σκορ — 1000 πόντοι, ξοδεύονται στην κίνηση
src/hiscore.asm     οι πέντε μεγαλύτερες βαθμολογίες, στη δισκέτα
src/sfx.asm         ηχητικά εφέ + τα παράσιτα της ζώνης κλειδώματος
src/musicplay.asm   μουσική: streaming από την τράπεζα, διακόπτες M και S
src/loader.bas      BASIC loader -> ASCII με CR+LF + &1A στο build
```

Ξεχωριστό πρόγραμμα, ΔΕΝ γίνεται include από το παιχνίδι — υπάρχει για να
ακούγεται η μουσική πριν πλησιάσει το παιχνίδι:
```
src/musictest.asm   MUSIC.BIN: μόνο η μουσική, org #8000 (δες γιατί μέσα)
src/musicloader.bas ο loader του, MEMORY &7FFF
```

**ΠΑΡΑΓΟΜΕΝΑ — μην τα επεξεργάζεσαι, ξαναγράφονται από το `make`:**
```
src/gamedefs.asm    | tools/genasm.py   (κωδικοί τύπων, μεγέθη, START_ROOM,
src/tables.asm      |                    DEMO_MODE, HURT_FRAMES, SET_ROOMS)
src/rooms.asm       |
src/tune.asm        | tools/genboss.py  (πίνακας νοτών + build/TUNEnn.BIN)
src/music_boss.asm  |                   (το ίδιο κομμάτι για το MUSIC.BIN)
src/gfx_*.asm       | tools/sprites.py  (αυθεντία: τα assets/*.png)
```
Ό,τι σταθερά γράψεις με το χέρι στο `gamedefs.asm` χάνεται στο επόμενο build
— βάλ' την σε χειρόγραφο αρχείο (π.χ. `ROOM_END` στο `endings.asm`).

Δεδομένα και εργαλεία:
```
levels/room_<N>.txt ASCII πίστες (1 χαρακτήρας ανά 8x8 tile)· ο αριθμός
                    ζει ΜΟΝΟ στο όνομα του αρχείου
levels/<email>/     ο προσωπικός φάκελος κάθε λογαριασμού του editor
levels/regress.txt  σταθερό δωμάτιο για τα τεστ — μην το επεξεργάζεσαι
assets/*.png        τα sprites· ΕΔΩ ζωγραφίζεις
tools/physics.py    το μοντέλο φυσικής — ΑΝΑΦΟΡΑ για το src/hero.asm
tools/genasm.py     μοντέλο -> πίνακες Z80·  genjs.py -> ίδιοι για browser
tools/roomfile.py   αίθουσες -> ROOMSnn.BIN (RLE, σετ των SET_ROOMS)
tools/genboss.py    η μεταγραφή του Boss Time -> tune.asm + TUNEnn.BIN
tools/genmusic.py   ΒΙΒΛΙΟΘΗΚΗ πια: ονόματα νοτών, περίοδοι AY, κρουστά
tools/z80run.py     τρέχει το ΠΡΑΓΜΑΤΙΚΟ main.bin σε προσομοιωτή Z80
tools/test_*.py     μοντέλο και Z80 χωριστά· parity.py: Python vs JavaScript
tools/checkdsk.py   ότι η δισκέτα έχει όντως αίθουσες ΚΑΙ μουσική
tools/toolchain.py  πού είναι τα rasm/iDSK (toolchain.json)
editor/             level editor σε ASP.NET Core MVC· δες docs/editor-manual.md
build/              παράγωγα (μην τα commit-άρεις)
```

## Συμβάσεις κώδικα
- Σχόλια κώδικα και μηνύματα commit στα **αγγλικά** (από 2026-08-12).
  Labels/identifiers στα αγγλικά, όπως πάντα. Τα υπάρχοντα ελληνικά σχόλια
  **δεν** μεταφράζονται μαζικά — αλλάζουν όταν αγγίζεται ο κώδικας γύρω τους.
  Η τεκμηρίωση (README, docs/, plan.md) μένει στα ελληνικά όπου είναι ήδη.
- Header block σε κάθε αρχείο με σκοπό + register contract σε κάθε public routine
  (`; IN: HL=..., OUT: A=..., ΑΛΛΟΙΩΝΕΙ: BC,DE`)
- Κάθε firmware call τεκμηριωμένος με τη διεύθυνσή του και ποιους registers χαλάει
- Άμεση πρόσβαση σε hardware (CRTC/gate array) μόνο όπου χρειάζεται, με σχόλιο γιατί
- Τα magic numbers γίνονται `equ` στο πάνω μέρος του αρχείου
- Καμία self-modifying code χωρίς ρητό σχόλιο `; SMC:`

## Παγίδες που έχουν ήδη κοστίσει (μη τις ξαναπατήσεις)
Καθεμιά έβγαλε δισκέτα στον χρήστη που δεν δούλευε, ενώ όλα τα τεστ εδώ ήταν
πράσινα. Ο κώδικας τις τεκμηριώνει στο σημείο τους· εδώ είναι για να τις ξέρεις
ΠΡΙΝ γράψεις.

- **Το παράθυρο των τραπεζών είναι #4000..#7FFF, δηλαδή ΟΛΟΣ ο κώδικας.** Με
  ανοιχτό παράθυρο τρέχει μόνο το `ldir`. Αυτό περιλαμβάνει **τη στοίβα** και
  **τον προορισμό του `bank_copy`**: ένα `push`/`pop` γύρω από την εναλλαγή
  διάβασε την τράπεζα αντί για τη στοίβα και το LDIR έγραψε 64 KB πάνω στο
  πρόγραμμα. Ό,τι γράφεται από την τράπεζα δηλώνεται ΜΕΤΑ το `save` στο
  main.asm, πάνω από το #8000 (δες `mus_chan`).
- **Το SOUND QUEUE (#BCAA) χαλάει το IX** — SOFT968, γιατί ο sound manager
  κρατά εκεί το δικό του channel block. Γενικότερα: κάθε firmware call έχει
  γραπτό συμβόλαιο και το `RET` του προσομοιωτή είναι πιο ευγενικό από το
  σίδερο. Το `tools/z80run.py` παίρνει `corrupt=` γι' αυτό.
- **Ένα πέρασμα του βρόχου ΔΕΝ είναι ένα καρέ** — είναι **3 vsync ακίνητος, 4
  περπατώντας, 7 τρέχοντας** (`CPC_VSYNC_*` στο tools/physics.py, μετρημένα με
  το z80run πάνω στο χτισμένο main.bin· εκεί ζει η αυθεντία). Ό,τι μετριέται σε
  περάσματα και λέγεται «καρέ» είναι ήδη λάθος: 5 δευτερόλεπτα είναι 83
  περάσματα ακίνητος και 36 τρέχοντας. Χρησιμοποίησε το ρολόι
  (`KL_TIME_PLEASE`, 1/300 s) ή συσσώρευσε το κόστος σε vsync.
- **Το `assert` του rasm αποτιμάται σε πρώιμη πέραση** και έχει δώσει και ψεύτικη
  αποτυχία και ψεύτικο πέρασμα σε ελέγχους μεγέθους. Βάλε τον έλεγχο στην Python.
- **Το rasm δεν ξεχωρίζει πεζά από κεφαλαία**: ένα `equ` και μια ετικέτα που
  διαφέρουν μόνο σε αυτό συγκρούονται σιωπηλά. Το `tools/check_names.py` το πιάνει
  και τρέχει πρώτο στο `make test`.
- **Τεστ που δεν αποτυγχάνει στο σπασμένο δεν αποδεικνύει τίποτα.** Δύο φορές σε
  αυτό το repo ένα πράσινο τεστ κάλυπτε πραγματικό σφάλμα. Όταν γράφεις τεστ για
  διόρθωση, χάλασε ξανά τον κώδικα και βεβαιώσου ότι κοκκινίζει.

## Σταθερές του παιχνιδιού (μην τις αλλάζεις χωρίς λόγο)
| Τι | Τιμή |
|---|---|
| Ήρωας | 7 px πλάτος x 12 px ύψος (κάθετος προσανατολισμός) |
| Tile | 8x8 px = 2 bytes x 8 scanlines |
| Playfield grid | 40 στήλες x 24 γραμμές (y = 8..199) |
| HUD | πάνω 8 scanlines (y = 0..7) |
| Ασφαλές ύψος πτώσης | 3 x ύψος ήρωα = **36 px** |
| Κατευθύνσεις βαρύτητας | **8**, ανά **45 μοίρες** (0=DOWN, δεξιόστροφα) |
| Sprite ήρωα | 7x12 στις ορθές φορές, **13x13** στις διαγώνιες |
| Αποθήκευση sprite | **4 pixels ανά byte** (pen = 2 bits)· το `spr_transform` ξεπακετάρει ένα καρέ τη φορά |
| Μουσική | Boss Time, 32 μέτρα / 61 s, στο **μπλοκ 7** της τράπεζας· 3 φωνές |
| Διακόπτες μουσικής | **M** στο μενού, **S** μέσα στο δωμάτιο (το M εκεί είναι βάδισμα) |
| Ελεύθερη κύρια μνήμη | ~4,4 KB — μέτρα την, μη μαντεύεις (δες παρακάτω) |

## Κανόνες δουλειάς
- Πρώτα δούλεψε το plan.md milestone-milestone· μη γράφεις κώδικα για features
  εκτός του τρέχοντος milestone.
- Κάθε οπτική απόφαση (sprite, tile, χρώμα, HUD) ελέγχεται πρώτα ενάντια στο
  [docs/concept-art.md](docs/concept-art.md). Απόκλιση = τεκμηρίωσέ την εκεί.
- Μετά από κάθε αλλαγή: τρέξε `make` και βεβαιώσου ότι assembl-άρει καθαρά.
- Η ΜΝΗΜΗ ΕΙΝΑΙ Ο ΠΕΡΙΟΡΙΣΤΙΚΟΣ ΠΑΡΑΓΟΝΤΑΣ. Μέτρα την πριν και μετά:
  `MEM_CEIL - (set_buf + set_capacity + 2048)` από το `build/symbols.txt`.
  Έχει φτάσει σε 11 bytes. Ό,τι μπαίνει στο #4000..prog_end το πληρώνει η κορυφή.
- Δεν μπορώ να τρέξω τον emulator από εδώ — γράψε τι πρέπει να δει ο χρήστης.
- Πρόσεχε το byte alignment: στο MODE 1 το X σε pixels ΔΕΝ είναι X σε bytes (÷4).
