# GRAVASSIST — Amstrad CPC, Z80 assembly, MODE 1

Puzzle game όπου ο παίκτης αλλάζει την **κατεύθυνση της βαρύτητας** για να περπατάει
σε πατώματα, τοίχους, ταβάνια και πλατφόρμες.

- Λεπτομερής σχεδιασμός: [plan.md](plan.md)
- **Visual reference (δεσμευτικό): [docs/concept-art.md](docs/concept-art.md)** —
  διάβασέ το πριν σχεδιάσεις sprites, tiles, HUD ή παλέτα.

## Toolchain (WSL, στο PATH)
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
make            # assemble + φτιάχνει build/gravassist.dsk
make clean
```
Το `rasm` βγάζει το `build/main.bin` μέσω `save` directive μέσα στο `src/main.asm`.
Το iDSK φτιάχνει το dsk και βάζει MAIN.BIN (`-t 1 -c 4000 -e 4000`) + τον BASIC loader.
Δοκιμή στον emulator: `RUN"GRAV"`.

## Δομή project
```
src/main.asm        κύριος κώδικας (org #4000)
src/*.asm           modules (include από το main.asm)
src/loader.bas      BASIC loader -> ASCII με CR+LF + &1A στο build
levels/*.txt        ASCII πίστες (1 χαρακτήρας ανά 8x8 tile)
tools/gensprites.py γεννά sprites: 4 orientations x pre-shifts x frames
tools/genlevels.py  ASCII πίστες -> RLE .asm include
build/              παράγωγα (μην τα commit-άρεις)
```

## Συμβάσεις κώδικα
- Σχόλια στα **ελληνικά**, labels/identifiers στα **αγγλικά** (όπως στο ~/cpc6128)
- Header block σε κάθε αρχείο με σκοπό + register contract σε κάθε public routine
  (`; IN: HL=..., OUT: A=..., ΑΛΛΟΙΩΝΕΙ: BC,DE`)
- Κάθε firmware call τεκμηριωμένος με τη διεύθυνσή του και ποιους registers χαλάει
- Άμεση πρόσβαση σε hardware (CRTC/gate array) μόνο όπου χρειάζεται, με σχόλιο γιατί
- Τα magic numbers γίνονται `equ` στο πάνω μέρος του αρχείου
- Καμία self-modifying code χωρίς ρητό σχόλιο `; SMC:`

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

## Κανόνες δουλειάς
- Πρώτα δούλεψε το plan.md milestone-milestone· μη γράφεις κώδικα για features
  εκτός του τρέχοντος milestone.
- Κάθε οπτική απόφαση (sprite, tile, χρώμα, HUD) ελέγχεται πρώτα ενάντια στο
  [docs/concept-art.md](docs/concept-art.md). Απόκλιση = τεκμηρίωσέ την εκεί.
- Μετά από κάθε αλλαγή: τρέξε `make` και βεβαιώσου ότι assembl-άρει καθαρά.
- Δεν μπορώ να τρέξω τον emulator από εδώ — γράψε τι πρέπει να δει ο χρήστης.
- Πρόσεχε το byte alignment: στο MODE 1 το X σε pixels ΔΕΝ είναι X σε bytes (÷4).
