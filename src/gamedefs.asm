;=====================================================================
;  GRAVASSIST — κωδικοί τύπων κελιού και μεγέθη παιχνιδιού
;  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py — ΜΗΝ το επεξεργάζεσαι.
;  Μία πηγή αλήθειας με το tools/physics.py.
;=====================================================================

T_EMPTY          equ 0
T_SOLID          equ 1
T_RAMP_DR        equ 2
T_RAMP_DL        equ 3
T_RAMP_UR        equ 4
T_RAMP_UL        equ 5
T_SPIKE_U        equ 6
T_SPIKE_L        equ 7
T_SPIKE_D        equ 8
T_SPIKE_R        equ 9
T_ONEWAY_U       equ 10
T_ONEWAY_L       equ 11
T_ONEWAY_D       equ 12
T_ONEWAY_R       equ 13
T_GRAVLOCK       equ 14
T_CRUMBLE        equ 15
T_EXIT           equ 16
T_ENERGY         equ 17
T_PARACHUTE      equ 18
T_KEY            equ 19
T_LOCK           equ 20
T_GATE           equ 21
T_SWITCH_U       equ 22
T_PLATE          equ 23
T_TELEPORT       equ 24
T_CRATE          equ 25
T_START          equ 26
T_LOCK_OPEN      equ 27
T_GATE_OPEN      equ 28
T_PLATE_DOWN     equ 29
T_SPIKE_U_OFF    equ 30
T_SPIKE_L_OFF    equ 31
T_SPIKE_D_OFF    equ 32
T_SPIKE_R_OFF    equ 33
T_SWITCH_L       equ 34
T_SWITCH_D       equ 35
T_SWITCH_R       equ 36
T_SWITCH_U_ON    equ 37
T_SWITCH_L_ON    equ 38
T_SWITCH_D_ON    equ 39
T_SWITCH_R_ON    equ 40
T_TURRET_V       equ 41
T_TURRET_H       equ 42
T_TURRET_V_OFF   equ 43
T_TURRET_H_OFF   equ 44
T_PLATFORM       equ 45
T_PLATFORM_OFF   equ 46
T_GRAVLOCK_U     equ 47
T_GRAVLOCK_L     equ 48
T_GRAVLOCK_R     equ 49

; Αίθουσα εκκίνησης. Ο editor τη γράφει με --start ώστε να δοκιμάζεις
; οποιαδήποτε αίθουσα χωρίς να πειράζεις τα αρχεία των πιστών.
START_ROOM      equ 1

; Γεωμετρία πινάκων — εδώ ώστε να είναι ορατή σε assert του main.asm
TAB_ROW         equ 64
RTAB_OFF        equ 16
GTAB_OFF        equ 15

; --- σετ αιθουσών σε αρχείο (tools/roomfile.py) --------------
SET_ROOMS       equ 4
SET_VERSION     equ 4          ; ο φορτωτής απορρίπτει ό,τι άλλο
; Οι θέσεις των σετ μέσα στις τράπεζες του 6128 (src/bank.asm).
; Ο Z80 βρίσκει τη θέση με ολισθήσεις, οπότε τα δύο μεγέθη ΠΡΕΠΕΙ
; να είναι δυνάμεις του 2 — το assert από κάτω το επιβάλλει.
SLOT_SHIFT      equ 11         ; 1 << 11 = 2048 bytes ανά θέση
SLOTS_SHIFT     equ 3         ; 1 << 3 = 8 θέσεις ανά μπλοκ
MAX_SETS        equ 32         ; = 128 αίθουσες στη μνήμη
SET_COUNT       equ 4          ; πόσα σετ ψάχνει η εκκίνηση
; Πόσα bytes προχωράει η μπάρα φόρτωσης ανά σετ. Υπολογισμένο εδώ
; ώστε η μπάρα να γεμίζει ακριβώς όσο και οι αίθουσες, όποιες κι
; αν είναι — στον Z80 μια διαίρεση θα κόστιζε περισσότερο από όσο
; αξίζει μια μπάρα.
BAR_STEP        equ 16

; --- σκορ (tools/physics.py) ---------------------------------
SCORE_START     equ 1000
SCORE_EXIT      equ 100
SCORE_PLATE     equ 50
SCORE_GATE      equ 30
SCORE_SWITCH    equ 20
SCORE_LOCK      equ 40
SCORE_PARA_LAND equ 10
SCORE_PARA_KEEP equ 80
SCORE_PICKUP    equ 5
; Τα αρνητικά μπαίνουν ως ΣΥΜΠΛΗΡΩΜΑ 2 σε ένα byte: το score_add
; επεκτείνει το πρόσημο μόνο του.
SCORE_STEP      equ 255         ; -1
SCORE_GRAV      equ 254         ; -2
HISCORE_MAX     equ 5
HISCORE_NAME    equ 3
; Χάρτης επισκεμμένων αιθουσών: ένα bit ανά αίθουσα, όσες χωράνε
; στις τράπεζες.
VISIT_BYTES     equ 16
SET_NUMBERS     equ 5          ; offset του numbers[] στην κεφαλή
SET_OFFS        equ 9         ; offset του offs[]
LVL_CELLS       equ 960
; Πόσες αλλαγές κελιών θυμάται το παιχνίδι συνολικά. Κάθε εγγραφή
; είναι 4 bytes· γεμάτο ημερολόγιο σημαίνει ότι οι παλιότερες
; αλλαγές δεν επιβιώνουν όταν ξαναμπείς στην αίθουσα.
JOURNAL_MAX     equ 64
TRAIL_MAX       equ 4    ; πόσα δωμάτια πίσω γυρνάς

; Ταβάνι μνήμης με ενεργό AMSDOS — δες την assert στο main.asm.
MEM_CEIL        equ #A67B

NTYPES          equ 50
ATTR_MAX        equ 8   ; κανάλια διακοπτών / ταυτότητες κλειδιών
T_LOCK_AUTO     equ 8    ; bit: η κλειδαριά ανοίγει μόλις την ακουμπήσεις
SPIKE_TICKS     equ 10
HURT_FRAMES     equ 40
LAND_TICKS      equ 4
DEMO_MODE       equ 0   ; 1 = δισκέτα επίδειξης
ENERGY_MAX      equ 8
ENERGY_PICK     equ 2
SPIKE_DMG       equ 2

; --- ΠΥΡΓΙΣΚΟΙ ---
TURRET_RANGE    equ 80
ARROW_STEP      equ 6
TURRET_MAX      equ 2
; Η φόρτιση σε παλμούς του ρολογιού του firmware (1/300 s), ΟΧΙ σε
; περάσματα βρόχου: ένα πέρασμα είναι 3 ως 7 vsync ανάλογα με το τι
; κάνει ο παίκτης, οπότε ένας μετρητής περασμάτων θα έδινε πέντε
; δευτερόλεπτα ακίνητος και έντεκα τρέχοντας.
TURRET_RELOAD   equ 1500
; Η προεπιλογή σε ΔΕΥΤΕΡΟΛΕΠΤΑ, για πυργίσκο που δεν δηλώνει τίποτα.
TURRET_COOL_DEF equ 5
ARROW_DMG_NEAR  equ 3
ARROW_DMG_MID   equ 2
ARROW_DMG_FAR   equ 1
; Πόσους πυργίσκους κρατά ο πίνακας μιας αίθουσας. Ό,τι περισσεύει
; αγνοείται σιωπηλά — το tools/roomfile.py σπάει το build αντ' αυτού.
TURRET_SLOTS    equ 8
; Κινούμενες πλατφόρμες: πόσες χωράνε, και οι δύο χρόνοι τους.
PLAT_MAX        equ 2
PLAT_SPEED_DEF  equ 24
; Το οριζόντιο βήμα: 4 pixel = ένα byte του MODE 1. Δες PLAT_XSTEP
; στο tools/physics.py για το γιατί — είναι μετρημένο, όχι γούστο.
PLAT_XSTEP      equ 4
; Πόσοι παλμοί του 1/300 για ένα βήμα, ανά άξονα.
PLAT_TICK       equ 300
PLAT_TICK_X     equ 1200
; Η παύση στα άκρα, σε παλμούς του ρολογιού 1/300.
PLAT_PAUSE      equ 600
; Στερεή μόνο από πάνω: η βαρύτητα που την κάνει πάτωμα.
PLAT_GRAV       equ 0
CRATE_TICKS     equ 4
FALL_SAFE       equ 36
FALL_V0         equ 256
FALL_ACCEL      equ 26
FALL_VMAX       equ 1024
PARA_V          equ 256
WALK_V          equ 1024

; Ιδιότητες ανά τύπο — ένα AND αντί για σκόρπιες συγκρίσεις
F_SOLID         equ #01
F_DEADLY        equ #02
F_PICKUP        equ #04
F_NOFLIP        equ #08
F_FRAGILE       equ #10
F_ONEWAY        equ #20
F_TRIGGER       equ #40
; A switch, any facing, either state — the eight numbers are not
; contiguous, so a range check would break the first time a type
; is inserted.
F_SWITCH        equ #80
