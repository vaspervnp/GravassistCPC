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
T_SWITCH         equ 22
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

; Αίθουσα εκκίνησης. Ο editor τη γράφει με --start ώστε να δοκιμάζεις
; οποιαδήποτε αίθουσα χωρίς να πειράζεις τα αρχεία των πιστών.
START_ROOM      equ 1

; Γεωμετρία πινάκων — εδώ ώστε να είναι ορατή σε assert του main.asm
TAB_ROW         equ 64
RTAB_OFF        equ 16
GTAB_OFF        equ 15

; --- σετ αιθουσών σε αρχείο (tools/roomfile.py) --------------
SET_ROOMS       equ 2
SET_VERSION     equ 2          ; ο φορτωτής απορρίπτει ό,τι άλλο
; Οι θέσεις των σετ μέσα στις τράπεζες του 6128 (src/bank.asm).
; Ο Z80 βρίσκει τη θέση με ολισθήσεις, οπότε τα δύο μεγέθη ΠΡΕΠΕΙ
; να είναι δυνάμεις του 2 — το assert από κάτω το επιβάλλει.
SLOT_SHIFT      equ 10         ; 1 << 10 = 1024 bytes ανά θέση
SLOTS_SHIFT     equ 4         ; 1 << 4 = 16 θέσεις ανά μπλοκ
MAX_SETS        equ 64         ; = 128 αίθουσες στη μνήμη
SET_COUNT       equ 4          ; πόσα σετ ψάχνει η εκκίνηση

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
SET_OFFS        equ 7         ; offset του offs[]
LVL_CELLS       equ 960
; Πόσες αλλαγές κελιών θυμάται το παιχνίδι συνολικά. Κάθε εγγραφή
; είναι 4 bytes· γεμάτο ημερολόγιο σημαίνει ότι οι παλιότερες
; αλλαγές δεν επιβιώνουν όταν ξαναμπείς στην αίθουσα.
; 40 και όχι 64: το σκορ πήρε ~290 bytes RAM και ο set_buf έπεσε
; κάτω από το μεγαλύτερο σετ. Το ημερολόγιο είναι ο μόνος
; καταναλωτής που μικραίνει χωρίς να σπάσει κάτι — απλώς θυμάται
; λιγότερες αλλαγές κελιών σε όλη την παρτίδα.
JOURNAL_MAX     equ 40
TRAIL_MAX       equ 4    ; πόσα δωμάτια πίσω γυρνάς

; Ταβάνι μνήμης με ενεργό AMSDOS — δες την assert στο main.asm.
MEM_CEIL        equ #A67B

NTYPES          equ 34
ATTR_MAX        equ 8   ; κανάλια διακοπτών / ταυτότητες κλειδιών
T_LOCK_AUTO     equ 8    ; bit: η κλειδαριά ανοίγει μόλις την ακουμπήσεις
SPIKE_TICKS     equ 10
HURT_FRAMES     equ 40
DEMO_MODE       equ 0   ; 1 = δισκέτα επίδειξης
ENERGY_MAX      equ 8
ENERGY_PICK     equ 2
SPIKE_DMG       equ 2
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
