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

NTYPES          equ 26
ENERGY_MAX      equ 8
ENERGY_PICK     equ 2
SPIKE_DMG       equ 2
FALL_SAFE       equ 36
FALL_V0         equ 256
FALL_ACCEL      equ 26
FALL_VMAX       equ 1024
PARA_V          equ 128

; Ιδιότητες ανά τύπο — ένα AND αντί για σκόρπιες συγκρίσεις
F_SOLID         equ #01
F_DEADLY        equ #02
F_PICKUP        equ #04
F_NOFLIP        equ #08
F_FRAGILE       equ #10
F_ONEWAY        equ #20
F_TRIGGER       equ #40
