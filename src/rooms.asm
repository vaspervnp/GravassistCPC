;=====================================================================
;  GRAVASSIST — αίθουσες, γραφικά tiles και ιδιότητες
;  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/genasm.py (πηγή: levels/room_*.txt)
;=====================================================================

LVL_COLS        equ 40
LVL_ROWS        equ 24
LVL_CELL        equ 8
LVL_Y0          equ 8

; Γραφικά: 45 τύποι x 8 γραμμές x 2 bytes (MODE 1)
tile_gfx:
                ; 0 EMPTY
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                ; 1 SOLID
                db #FF,#FF
                db #8F,#1F
                db #8F,#1F
                db #8F,#1F
                db #8F,#1F
                db #8F,#1F
                db #8F,#1F
                db #FF,#FF
                ; 2 RAMP_DR
                db #00,#11
                db #00,#23
                db #00,#47
                db #00,#8F
                db #11,#0F
                db #23,#0F
                db #47,#0F
                db #8F,#0F
                ; 3 RAMP_DL
                db #88,#00
                db #4C,#00
                db #2E,#00
                db #1F,#00
                db #0F,#88
                db #0F,#4C
                db #0F,#2E
                db #0F,#1F
                ; 4 RAMP_UR
                db #8F,#0F
                db #47,#0F
                db #23,#0F
                db #11,#0F
                db #00,#8F
                db #00,#47
                db #00,#23
                db #00,#11
                ; 5 RAMP_UL
                db #0F,#1F
                db #0F,#2E
                db #0F,#4C
                db #0F,#88
                db #1F,#00
                db #2E,#00
                db #4C,#00
                db #88,#00
                ; 6 SPIKE_U
                db #00,#00
                db #00,#00
                db #22,#44
                db #22,#44
                db #22,#44
                db #55,#AA
                db #55,#AA
                db #0F,#0F
                ; 7 SPIKE_L
                db #00,#01
                db #00,#67
                db #33,#89
                db #00,#67
                db #00,#67
                db #33,#89
                db #00,#67
                db #00,#01
                ; 8 SPIKE_D
                db #0F,#0F
                db #55,#AA
                db #55,#AA
                db #22,#44
                db #22,#44
                db #22,#44
                db #00,#00
                db #00,#00
                ; 9 SPIKE_R
                db #08,#00
                db #6E,#00
                db #19,#CC
                db #6E,#00
                db #6E,#00
                db #19,#CC
                db #6E,#00
                db #08,#00
                ; 10 ONEWAY_U
                db #FF,#FF
                db #FF,#FF
                db #00,#00
                db #02,#04
                db #07,#0E
                db #02,#04
                db #02,#04
                db #00,#00
                ; 11 ONEWAY_L
                db #CC,#00
                db #CC,#08
                db #CD,#0E
                db #CC,#08
                db #CC,#08
                db #CD,#0E
                db #CC,#08
                db #CC,#00
                ; 12 ONEWAY_D
                db #00,#00
                db #02,#04
                db #02,#04
                db #07,#0E
                db #02,#04
                db #00,#00
                db #FF,#FF
                db #FF,#FF
                ; 13 ONEWAY_R
                db #00,#33
                db #01,#33
                db #07,#3B
                db #01,#33
                db #01,#33
                db #07,#3B
                db #01,#33
                db #00,#33
                ; 14 GRAVLOCK
                db #0A,#0A
                db #00,#00
                db #1B,#0A
                db #33,#CC
                db #1B,#0A
                db #11,#00
                db #0A,#0A
                db #00,#00
                ; 15 CRUMBLE
                db #0F,#0F
                db #09,#01
                db #09,#01
                db #0F,#0F
                db #08,#09
                db #08,#09
                db #08,#09
                db #0F,#0F
                ; 16 EXIT
                db #77,#EE
                db #44,#22
                db #55,#22
                db #77,#AA
                db #55,#22
                db #55,#22
                db #44,#22
                db #77,#EE
                ; 17 ENERGY
                db #00,#00
                db #33,#CC
                db #22,#44
                db #22,#44
                db #23,#4C
                db #23,#4C
                db #33,#CC
                db #00,#00
                ; 18 PARACHUTE
                db #00,#00
                db #00,#00
                db #33,#CC
                db #37,#CE
                db #02,#04
                db #02,#04
                db #01,#08
                db #00,#00
                ; 19 KEY
                db #00,#00
                db #77,#00
                db #55,#00
                db #77,#88
                db #00,#44
                db #00,#26
                db #00,#02
                db #00,#00
                ; 20 LOCK
                db #01,#08
                db #02,#04
                db #02,#04
                db #77,#EE
                db #44,#22
                db #45,#22
                db #44,#22
                db #77,#EE
                ; 21 GATE
                db #FF,#EE
                db #05,#04
                db #05,#04
                db #05,#04
                db #05,#04
                db #05,#04
                db #05,#04
                db #FF,#EE
                ; 22 SWITCH_U
                db #00,#00
                db #00,#00
                db #00,#00
                db #44,#00
                db #22,#00
                db #22,#00
                db #11,#00
                db #07,#0E
                ; 23 PLATE
                db #00,#00
                db #00,#00
                db #00,#00
                db #FF,#FF
                db #FF,#FF
                db #04,#02
                db #04,#02
                db #04,#02
                ; 24 TELEPORT
                db #00,#00
                db #77,#EE
                db #47,#2E
                db #46,#26
                db #46,#26
                db #47,#2E
                db #77,#EE
                db #00,#00
                ; 25 CRATE
                db #FF,#FF
                db #8C,#13
                db #8A,#15
                db #89,#19
                db #89,#19
                db #8A,#15
                db #8C,#13
                db #FF,#FF
                ; 26 START
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                ; 27 LOCK_OPEN
                db #01,#08
                db #02,#04
                db #02,#04
                db #77,#EE
                db #44,#22
                db #44,#22
                db #44,#22
                db #77,#EE
                ; 28 GATE_OPEN
                db #FF,#EE
                db #05,#04
                db #05,#04
                db #FF,#EE
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#00
                ; 29 PLATE_DOWN
                db #FF,#FF
                db #8C,#13
                db #89,#19
                db #89,#19
                db #8C,#13
                db #FF,#FF
                db #FF,#FF
                db #04,#02
                ; 30 SPIKE_U_OFF
                db #DD,#BB
                db #FF,#FF
                db #88,#11
                db #88,#11
                db #88,#11
                db #88,#11
                db #88,#11
                db #FF,#FF
                ; 31 SPIKE_L_OFF
                db #FF,#FF
                db #CC,#11
                db #44,#11
                db #CC,#11
                db #CC,#11
                db #44,#11
                db #CC,#11
                db #FF,#FF
                ; 32 SPIKE_D_OFF
                db #FF,#FF
                db #88,#11
                db #88,#11
                db #88,#11
                db #88,#11
                db #88,#11
                db #FF,#FF
                db #DD,#BB
                ; 33 SPIKE_R_OFF
                db #FF,#FF
                db #88,#33
                db #88,#22
                db #88,#33
                db #88,#33
                db #88,#22
                db #88,#33
                db #FF,#FF
                ; 34 SWITCH_L
                db #00,#00
                db #00,#01
                db #00,#01
                db #00,#01
                db #00,#23
                db #00,#CD
                db #11,#01
                db #00,#00
                ; 35 SWITCH_D
                db #07,#0E
                db #00,#88
                db #00,#44
                db #00,#44
                db #00,#22
                db #00,#00
                db #00,#00
                db #00,#00
                ; 36 SWITCH_R
                db #00,#00
                db #08,#88
                db #3B,#00
                db #4C,#00
                db #08,#00
                db #08,#00
                db #08,#00
                db #00,#00
                ; 37 SWITCH_U_ON
                db #00,#00
                db #00,#00
                db #00,#00
                db #00,#22
                db #00,#44
                db #00,#88
                db #11,#00
                db #07,#0E
                ; 38 SWITCH_L_ON
                db #00,#00
                db #11,#01
                db #00,#89
                db #00,#45
                db #00,#23
                db #00,#01
                db #00,#01
                db #00,#00
                ; 39 SWITCH_D_ON
                db #07,#0E
                db #00,#88
                db #11,#00
                db #22,#00
                db #44,#00
                db #00,#00
                db #00,#00
                db #00,#00
                ; 40 SWITCH_R_ON
                db #00,#00
                db #08,#00
                db #08,#00
                db #4C,#00
                db #2A,#00
                db #19,#00
                db #08,#88
                db #00,#00
                ; 41 TURRET_V
                db #11,#88
                db #07,#0E
                db #37,#CE
                db #04,#02
                db #04,#02
                db #37,#CE
                db #07,#0E
                db #11,#88
                ; 42 TURRET_H
                db #00,#00
                db #07,#0E
                db #26,#46
                db #AE,#57
                db #AE,#57
                db #26,#46
                db #07,#0E
                db #00,#00
                ; 43 TURRET_V_OFF
                db #03,#0C
                db #07,#0E
                db #37,#CE
                db #04,#02
                db #04,#02
                db #37,#CE
                db #07,#0E
                db #03,#0C
                ; 44 TURRET_H_OFF
                db #00,#00
                db #07,#0E
                db #2E,#47
                db #2E,#47
                db #2E,#47
                db #2E,#47
                db #07,#0E
                db #00,#00

grav_gfx_world:      ; 8 φορές x 8 γραμμές x 2 bytes
                ; φορά 0
                db #33,#00
                db #33,#00
                db #33,#00
                db #FF,#CC
                db #77,#88
                db #33,#00
                db #00,#00
                db #00,#00
                ; φορά 1
                db #00,#00
                db #00,#00
                db #00,#CC
                db #11,#88
                db #FF,#00
                db #EE,#00
                db #FF,#00
                db #FF,#00
                ; φορά 2
                db #00,#88
                db #11,#88
                db #33,#FF
                db #33,#FF
                db #11,#88
                db #00,#88
                db #00,#00
                db #00,#00
                ; φορά 3
                db #FF,#00
                db #FF,#00
                db #EE,#00
                db #FF,#00
                db #11,#88
                db #00,#CC
                db #00,#00
                db #00,#00
                ; φορά 4
                db #00,#00
                db #00,#00
                db #00,#CC
                db #11,#EE
                db #33,#FF
                db #00,#CC
                db #00,#CC
                db #00,#CC
                ; φορά 5
                db #00,#FF
                db #00,#FF
                db #00,#77
                db #00,#FF
                db #11,#88
                db #33,#00
                db #00,#00
                db #00,#00
                ; φορά 6
                db #00,#00
                db #00,#00
                db #11,#00
                db #11,#88
                db #FF,#CC
                db #FF,#CC
                db #11,#88
                db #11,#00
                ; φορά 7
                db #00,#00
                db #00,#00
                db #33,#00
                db #11,#88
                db #00,#FF
                db #00,#77
                db #00,#FF
                db #00,#FF

grav_gfx_hero:      ; 8 φορές x 8 γραμμές x 2 bytes
                ; φορά 0
                db #03,#00
                db #03,#00
                db #03,#00
                db #0F,#0C
                db #07,#08
                db #03,#00
                db #00,#00
                db #00,#00
                ; φορά 1
                db #00,#00
                db #00,#00
                db #00,#0C
                db #01,#08
                db #0F,#00
                db #0E,#00
                db #0F,#00
                db #0F,#00
                ; φορά 2
                db #00,#08
                db #01,#08
                db #03,#0F
                db #03,#0F
                db #01,#08
                db #00,#08
                db #00,#00
                db #00,#00
                ; φορά 3
                db #0F,#00
                db #0F,#00
                db #0E,#00
                db #0F,#00
                db #01,#08
                db #00,#0C
                db #00,#00
                db #00,#00
                ; φορά 4
                db #00,#00
                db #00,#00
                db #00,#0C
                db #01,#0E
                db #03,#0F
                db #00,#0C
                db #00,#0C
                db #00,#0C
                ; φορά 5
                db #00,#0F
                db #00,#0F
                db #00,#07
                db #00,#0F
                db #01,#08
                db #03,#00
                db #00,#00
                db #00,#00
                ; φορά 6
                db #00,#00
                db #00,#00
                db #01,#00
                db #01,#08
                db #0F,#0C
                db #0F,#0C
                db #01,#08
                db #01,#00
                ; φορά 7
                db #00,#00
                db #00,#00
                db #03,#00
                db #01,#08
                db #00,#0F
                db #00,#07
                db #00,#0F
                db #00,#0F

hud_bolt:        ; 8 γραμμές x 2 bytes
                db #11,#CC
                db #33,#88
                db #77,#00
                db #FF,#CC
                db #11,#CC
                db #33,#88
                db #77,#00
                db #CC,#00

hud_star:        ; 8 γραμμές x 2 bytes
                db #01,#08
                db #01,#08
                db #0F,#0F
                db #07,#0E
                db #03,#0C
                db #07,#0E
                db #06,#06
                db #0C,#03

; Γράμματα του τίτλου: 8x8 μάσκα, ένα bit ανά pixel. Ζωγραφίζονται
; σε διπλό μέγεθος με τον πίνακα font_x2 από κάτω.
TITLE_LEN       equ 10
TITLE_H         equ 12
font_glyphs:
                db #3C,#7E,#C3,#C0,#C0,#CF,#CF,#C3,#C3,#7E,#3C,#00   ; G
                db #FC,#FE,#C3,#C3,#FE,#FC,#CC,#C6,#C3,#C3,#C3,#00   ; R
                db #3C,#7E,#C3,#C3,#C3,#FF,#FF,#C3,#C3,#C3,#C3,#00   ; A
                db #C3,#C3,#C3,#C3,#C3,#66,#66,#66,#3C,#3C,#18,#00   ; V
                db #3C,#7E,#C3,#C0,#7C,#3E,#03,#C3,#7E,#3C,#00,#00   ; S
                db #7E,#7E,#18,#18,#18,#18,#18,#18,#18,#7E,#7E,#00   ; I
                db #FF,#FF,#18,#18,#18,#18,#18,#18,#18,#18,#18,#00   ; T
                db #C3,#E7,#FF,#FF,#DB,#C3,#C3,#C3,#C3,#C3,#C3,#00   ; M
                db #FF,#FF,#C0,#C0,#FC,#FC,#C0,#C0,#C0,#FF,#FF,#00   ; E
                db #3C,#7E,#C3,#C3,#C3,#C3,#C3,#C3,#C3,#7E,#3C,#00   ; O
                db #C3,#C3,#C3,#C3,#FF,#FF,#C3,#C3,#C3,#C3,#C3,#00   ; H
                db #C3,#E3,#F3,#FB,#DF,#CF,#C7,#C3,#C3,#C3,#C3,#00   ; N
                db #FC,#FE,#C3,#C3,#C3,#C3,#C3,#C3,#C3,#FE,#FC,#00   ; D
                db #00,#00,#00,#00,#00,#00,#00,#00,#00,#00,#00,#00   ;  

; Η σειρά των γραμμάτων του τίτλου, ως δείκτες μέσα στο font_glyphs.
title_idx:      db 0,1,2,3,2,4,4,5,4,6

GO_IDX_LEN     equ 9
go_idx:         db 0,2,7,8,13,9,3,8,1   ; GAME OVER
END_IDX_LEN     equ 7
end_idx:        db 6,10,8,13,8,11,12   ; THE END

; 4 bits μάσκας -> 2 bytes MODE 1 σε διπλό πλάτος, ανά χρώμα.
font_x2_a:      db #00,#00,#00,#33,#00,#CC,#00,#FF,#33,#00,#33,#33,#33,#CC,#33,#FF,#CC,#00,#CC,#33,#CC,#CC,#CC,#FF,#FF,#00,#FF,#33,#FF,#CC,#FF,#FF
font_x2_b:      db #00,#00,#00,#03,#00,#0C,#00,#0F,#03,#00,#03,#03,#03,#0C,#03,#0F,#0C,#00,#0C,#03,#0C,#0C,#0C,#0F,#0F,#00,#0F,#03,#0F,#0C,#0F,#0F

; Ιδιότητες ανά τύπο κελιού — ένα AND αντί για σκόρπιες συγκρίσεις
tile_props:     db #00,#01,#01,#01,#01,#01,#03,#03,#03,#03,#21,#21,#21,#21,#08,#11,#40,#04,#04,#04,#01,#01,#C0,#40,#40,#00,#00,#00,#00,#40,#01,#01,#01,#01,#C0,#C0,#C0,#C0,#C0,#C0,#C0,#00,#00,#00,#00

; Η φορά που 'κοιτάει' κάθε κατευθυντικός τύπος· #FF = άσχετο.
tile_facing:    db 255,255,255,255,255,255,4,2,0,6,4,2,0,6,255,255,255,255,255,255,255,255,4,255,255,255,255,255,255,255,255,255,255,255,2,0,6,4,2,0,6,255,255,255,255

; Οι ΑΙΘΟΥΣΕΣ δεν είναι πια εδώ. Ασυμπίεστες κόστιζαν 960 bytes
; η καθεμία και χωρούσαν ~10 συνολικά· τώρα ζουν RLE μέσα στα
; build/ROOMSnn.BIN, σετ των 40. Δες tools/roomfile.py.
