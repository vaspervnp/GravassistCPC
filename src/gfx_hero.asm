;=====================================================================
;  GRAVASSIST - sprites ήρωα
;  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/sprites.py — ΜΗΝ το επεξεργάζεσαι.
;  22 frames, 7x12, 4 pixels ανά byte
;  (2 bytes ανά γραμμή), κανονική φορά βαρύτητας DOWN.
;  Ξεπακετάρισμα + περιστροφή: src/rotate.asm
;=====================================================================

hero_gfx_w       equ 7
hero_gfx_h       equ 12
hero_gfx_frames  equ 22
hero_gfx_stride  equ 2
hero_gfx_size    equ 24

hero_gfx:
                ; --- frame 0 ---
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 65,4
                db 65,4
                db 4,64
                db 4,64
                db 16,16
                db 16,16
                ; --- frame 1 ---
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 65,4
                db 1,0
                db 4,64
                db 4,64
                db 16,16
                db 16,16
                ; --- frame 2 ---
                db 1,80
                db 1,16
                db 1,80
                db 0,64
                db 1,64
                db 21,80
                db 65,4
                db 65,4
                db 4,64
                db 4,64
                db 4,64
                db 4,64
                ; --- frame 3 ---
                db 1,80
                db 1,16
                db 1,80
                db 0,64
                db 1,64
                db 21,80
                db 17,4
                db 65,0
                db 68,64
                db 4,64
                db 16,16
                db 16,0
                ; --- frame 4 ---
                db 0,0
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 17,4
                db 65,0
                db 68,64
                db 16,16
                db 16,0
                ; --- frame 5 ---
                db 21,0
                db 17,0
                db 21,0
                db 4,0
                db 5,0
                db 21,80
                db 17,4
                db 65,0
                db 68,64
                db 4,64
                db 16,16
                db 16,0
                ; --- frame 6 ---
                db 21,0
                db 17,0
                db 21,0
                db 4,0
                db 5,0
                db 21,80
                db 65,4
                db 65,4
                db 4,64
                db 4,64
                db 4,64
                db 4,64
                ; --- frame 7 ---
                db 21,0
                db 17,0
                db 21,0
                db 4,0
                db 5,0
                db 21,80
                db 65,16
                db 1,4
                db 4,68
                db 4,64
                db 16,16
                db 0,16
                ; --- frame 8 ---
                db 0,0
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 65,16
                db 1,4
                db 4,68
                db 16,16
                db 0,16
                ; --- frame 9 ---
                db 1,80
                db 1,16
                db 1,80
                db 0,64
                db 1,64
                db 21,80
                db 65,16
                db 1,4
                db 4,68
                db 4,64
                db 16,16
                db 0,16
                ; --- frame 10 ---
                db 5,64
                db 4,64
                db 5,64
                db 65,0
                db 21,84
                db 1,0
                db 1,0
                db 1,0
                db 4,64
                db 4,64
                db 16,16
                db 0,0
                ; --- frame 11 ---
                db 5,64
                db 4,64
                db 5,64
                db 1,4
                db 85,80
                db 1,0
                db 1,0
                db 1,0
                db 4,64
                db 4,64
                db 16,16
                db 16,0
                ; --- frame 12 ---
                db 5,64
                db 4,64
                db 5,64
                db 65,0
                db 21,84
                db 1,0
                db 1,0
                db 1,0
                db 4,64
                db 4,64
                db 16,16
                db 0,16
                ; --- frame 13 ---
                db 5,64
                db 4,64
                db 5,64
                db 1,4
                db 85,80
                db 1,0
                db 1,0
                db 1,0
                db 4,64
                db 4,64
                db 4,64
                db 0,0
                ; --- frame 14 ---
                db 0,0
                db 0,0
                db 0,0
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 21,80
                db 65,4
                db 65,4
                db 20,80
                db 64,4
                ; --- frame 15 ---
                db 0,0
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 65,4
                db 65,4
                db 4,64
                db 4,64
                db 80,20
                ; --- frame 16 ---
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 1,0
                db 21,80
                db 65,4
                db 65,4
                db 4,64
                db 4,64
                db 16,16
                db 16,16
                ; --- frame 17 ---
                db 0,0
                db 5,64
                db 4,64
                db 5,64
                db 1,0
                db 85,84
                db 1,0
                db 1,0
                db 4,64
                db 4,64
                db 16,16
                db 16,16
                ; --- frame 18 ---
                db 0,0
                db 1,80
                db 1,16
                db 1,80
                db 0,64
                db 1,64
                db 5,20
                db 20,4
                db 68,4
                db 5,0
                db 4,64
                db 81,0
                ; --- frame 19 ---
                db 0,0
                db 0,0
                db 0,0
                db 1,80
                db 1,16
                db 1,80
                db 0,64
                db 5,20
                db 17,4
                db 20,4
                db 17,0
                db 85,0
                ; --- frame 20 ---
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 1,80
                db 1,16
                db 1,80
                db 5,64
                db 1,64
                db 84,64
                db 84,0
                ; --- frame 21 ---
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 0,0
                db 4,0
                db 65,84
                db 65,68
                db 21,84
                db 69,0

; --- δείκτες frame του hero_gfx ---
hero_gfx_IDLE0      equ 0
hero_gfx_IDLE1      equ 1
hero_gfx_WALK0      equ 2
hero_gfx_WALK1      equ 3
hero_gfx_WALK2      equ 4
hero_gfx_WALK3      equ 5
hero_gfx_WALK4      equ 6
hero_gfx_WALK5      equ 7
hero_gfx_WALK6      equ 8
hero_gfx_WALK7      equ 9
hero_gfx_FALL0      equ 10
hero_gfx_FALL1      equ 11
hero_gfx_FALL2      equ 12
hero_gfx_FALL3      equ 13
hero_gfx_LAND0      equ 14
hero_gfx_LAND1      equ 15
hero_gfx_LAND2      equ 16
hero_gfx_DEATH0     equ 17
hero_gfx_DEATH1     equ 18
hero_gfx_DEATH2     equ 19
hero_gfx_DEATH3     equ 20
hero_gfx_DEATH4     equ 21
