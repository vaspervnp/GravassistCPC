;=====================================================================
;  GRAVASSIST - sprites αντικειμένων (PLACEHOLDERS)
;  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/sprites.py — ΜΗΝ το επεξεργάζεσαι.
;  30 frames, 8x8, 4 pixels ανά byte
;  (2 bytes ανά γραμμή), κανονική φορά βαρύτητας DOWN.
;  Ξεπακετάρισμα + περιστροφή: src/rotate.asm
;=====================================================================

obj_gfx_w       equ 8
obj_gfx_h       equ 8
obj_gfx_frames  equ 30
obj_gfx_stride  equ 2
obj_gfx_size    equ 16

obj_gfx:
                ; --- frame 0 ---
                db 63,252
                db 48,12
                db 51,12
                db 63,204
                db 51,12
                db 51,12
                db 48,12
                db 63,252
                ; --- frame 1 ---
                db 63,252
                db 58,172
                db 59,172
                db 63,236
                db 59,172
                db 59,172
                db 58,172
                db 63,252
                ; --- frame 2 ---
                db 255,252
                db 34,32
                db 34,32
                db 34,32
                db 34,32
                db 34,32
                db 34,32
                db 255,252
                ; --- frame 3 ---
                db 255,252
                db 34,32
                db 34,32
                db 255,252
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                ; --- frame 4 ---
                db 0,0
                db 0,0
                db 0,0
                db 48,0
                db 12,0
                db 12,0
                db 3,0
                db 42,168
                ; --- frame 5 ---
                db 0,0
                db 0,0
                db 0,0
                db 0,12
                db 0,48
                db 0,192
                db 3,0
                db 42,168
                ; --- frame 6 ---
                db 0,0
                db 15,240
                db 12,48
                db 12,48
                db 14,176
                db 14,176
                db 15,240
                db 0,0
                ; --- frame 7 ---
                db 0,0
                db 15,240
                db 14,176
                db 14,176
                db 14,176
                db 14,176
                db 15,240
                db 0,0
                ; --- frame 8 ---
                db 255,255
                db 224,11
                db 200,35
                db 194,131
                db 194,131
                db 200,35
                db 224,11
                db 255,255
                ; --- frame 9 ---
                db 255,255
                db 224,11
                db 202,163
                db 202,163
                db 202,163
                db 202,163
                db 224,11
                db 255,255
                ; --- frame 10 ---
                db 0,0
                db 0,0
                db 0,0
                db 255,255
                db 255,255
                db 32,8
                db 32,8
                db 32,8
                ; --- frame 11 ---
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 255,255
                db 255,255
                db 32,8
                ; --- frame 12 ---
                db 2,128
                db 8,32
                db 8,32
                db 63,252
                db 48,12
                db 50,12
                db 48,12
                db 63,252
                ; --- frame 13 ---
                db 2,128
                db 8,32
                db 8,32
                db 63,252
                db 48,12
                db 48,12
                db 48,12
                db 63,252
                ; --- frame 14 ---
                db 255,255
                db 255,255
                db 0,0
                db 8,32
                db 42,168
                db 8,32
                db 8,32
                db 0,0
                ; --- frame 15 ---
                db 255,255
                db 255,255
                db 0,0
                db 8,32
                db 42,168
                db 8,32
                db 8,32
                db 0,0
                ; --- frame 16 ---
                db 136,136
                db 0,0
                db 139,136
                db 15,240
                db 139,136
                db 3,0
                db 136,136
                db 0,0
                ; --- frame 17 ---
                db 204,204
                db 0,0
                db 207,204
                db 15,240
                db 207,204
                db 3,0
                db 204,204
                db 0,0
                ; --- frame 18 ---
                db 170,170
                db 130,2
                db 130,2
                db 170,170
                db 128,130
                db 128,130
                db 128,130
                db 170,170
                ; --- frame 19 ---
                db 170,170
                db 178,2
                db 142,2
                db 171,170
                db 128,194
                db 128,178
                db 128,142
                db 170,170
                ; --- frame 20 ---
                db 0,0
                db 0,0
                db 12,48
                db 12,48
                db 12,48
                db 51,204
                db 51,204
                db 170,170
                ; --- frame 21 ---
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 12,48
                db 12,48
                db 51,204
                db 170,170
                ; --- frame 22 ---
                db 0,0
                db 63,252
                db 58,172
                db 56,44
                db 56,44
                db 58,172
                db 63,252
                db 0,0
                ; --- frame 23 ---
                db 0,0
                db 63,252
                db 63,252
                db 60,60
                db 60,60
                db 63,252
                db 63,252
                db 0,0
                ; --- frame 24 ---
                db 0,0
                db 63,0
                db 51,0
                db 63,192
                db 0,48
                db 0,44
                db 0,8
                db 0,0
                ; --- frame 25 ---
                db 0,0
                db 63,0
                db 51,0
                db 63,192
                db 0,48
                db 0,60
                db 0,12
                db 0,0
                ; --- frame 26 ---
                db 0,0
                db 0,0
                db 15,240
                db 47,248
                db 8,32
                db 8,32
                db 2,128
                db 0,0
                ; --- frame 27 ---
                db 0,0
                db 0,0
                db 15,240
                db 47,248
                db 8,32
                db 8,32
                db 3,192
                db 0,0
                ; --- frame 28 ---
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                ; --- frame 29 ---
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85
                db 85,85

; --- δείκτες frame του obj_gfx ---
obj_gfx_EXIT_0     equ 0
obj_gfx_EXIT_1     equ 1
obj_gfx_GATE_0     equ 2
obj_gfx_GATE_1     equ 3
obj_gfx_SWITCH_0   equ 4
obj_gfx_SWITCH_1   equ 5
obj_gfx_ENERGY_0   equ 6
obj_gfx_ENERGY_1   equ 7
obj_gfx_CRATE_0    equ 8
obj_gfx_CRATE_1    equ 9
obj_gfx_PLATE_0    equ 10
obj_gfx_PLATE_1    equ 11
obj_gfx_LOCK_0     equ 12
obj_gfx_LOCK_1     equ 13
obj_gfx_ONEWAY_0   equ 14
obj_gfx_ONEWAY_1   equ 15
obj_gfx_GRAVLOCK_0 equ 16
obj_gfx_GRAVLOCK_1 equ 17
obj_gfx_CRUMBLE_0  equ 18
obj_gfx_CRUMBLE_1  equ 19
obj_gfx_SPIKES_0   equ 20
obj_gfx_SPIKES_1   equ 21
obj_gfx_TELEPORT_0 equ 22
obj_gfx_TELEPORT_1 equ 23
obj_gfx_KEY_0      equ 24
obj_gfx_KEY_1      equ 25
obj_gfx_PARACHUTE_0 equ 26
obj_gfx_PARACHUTE_1 equ 27
obj_gfx_TURRET_0   equ 28
obj_gfx_TURRET_1   equ 29
