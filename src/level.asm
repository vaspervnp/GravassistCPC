;=====================================================================
;  GRAVASSIST — δωμάτιο: σχεδίαση και έλεγχος στερεότητας
;
;  Το solid_at είναι το θεμέλιο όλης της φυσικής: κάθε έλεγχος του ήρωα
;  καταλήγει εδώ. Χειρίζεται και τις ράμπες με υπο-κελιακή ακρίβεια, γι'
;  αυτό οι διαγώνιες επιφάνειες δεν χρειάζονται πουθενά ειδική περίπτωση.
;
;  Αναφορά: tools/physics.py (Room.solid_at)
;=====================================================================

; Οι κωδικοί τύπων T_* και τα μεγέθη παιχνιδιού παράγονται στο
; src/level_test.asm από το tools/genasm.py — μία πηγή αλήθειας με το μοντέλο.

;---------------------------------------------------------------------
; cell_at — τύπος κελιού στο pixel (x,y)
;   IN:  BC = x, DE = y (προσημασμένα 16-bit)
;   OUT: A = τύπος· έξω από το δωμάτιο -> T_SOLID
;        (cell_u),(cell_v) = θέση μέσα στο κελί 8x8
;   ΑΛΛΟΙΩΝΕΙ: AF, HL   (BC, DE διατηρούνται)
;---------------------------------------------------------------------
cell_at:        push bc
                push de

                ld   a,d                ; --- y εκτός ορίων; ---
                or   a
                jr   nz,ca_out          ; y < 0 ή y >= 256
                ld   a,e
                sub  LVL_Y0
                jr   c,ca_out           ; πάνω από το grid (ζώνη HUD)
                cp   LVL_ROWS*LVL_CELL
                jr   nc,ca_out
                ld   e,a                ; E = yy (0..191)

                ld   a,b                ; --- x εκτός ορίων; ---
                or   a
                jr   z,ca_xok
                dec  a
                jr   nz,ca_out          ; x < 0 ή x >= 512
                ld   a,c
                cp   LVL_COLS*LVL_CELL-256
                jr   nc,ca_out
ca_xok:
                ld   a,c                ; θέση μέσα στο κελί, για τις ράμπες
                and  7
                ld   (cell_u),a
                ld   a,e
                and  7
                ld   (cell_v),a

                ld   a,c                ; col = x >> 3  (0..39)
                srl  a
                srl  a
                srl  a
                bit  0,b                ; x >= 256 -> +32 στήλες
                jr   z,ca_col
                add  a,32
ca_col:         ld   c,a
                ld   (cell_col),a

                ld   a,e                ; row = yy >> 3  (0..23)
                srl  a
                srl  a
                srl  a
                ld   (cell_row),a
                ld   l,a                ; HL = row*40 + col
                ld   h,0
                add  hl,hl              ; x2
                add  hl,hl              ; x4
                add  hl,hl              ; x8
                ld   d,h
                ld   e,l
                add  hl,hl              ; x16
                add  hl,hl              ; x32
                add  hl,de              ; x32 + x8 = x40
                ld   e,c
                ld   d,0
                add  hl,de
                ld   de,level_data
                add  hl,de
                ld   (cell_ptr),hl      ; για σβήσιμο pickup / αλλαγή κελιού
                ld   a,(hl)
                pop  de
                pop  bc
                ret

ca_out:         pop  de
                pop  bc
                ld   a,T_SOLID
                ret

;---------------------------------------------------------------------
; solid_at — είναι το pixel (x,y) μέσα σε υλικό;
;   IN:  BC = x, DE = y      OUT: CY = στερεό
;   ΑΛΛΟΙΩΝΕΙ: AF, HL       (BC, DE διατηρούνται)
;---------------------------------------------------------------------
solid_at:       call cell_at
                or   a
                ret  z                  ; T_EMPTY -> NC
                cp   T_SOLID
                jr   z,sa_yes
                cp   T_RAMP_UL+1
                jr   c,sa_ramp          ; 2..5 = γεωμετρία με υπο-κελιακό σχήμα

                ld   c,a                ; --- τύποι παιχνιδιού ---
                ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                ld   b,a
                and  F_ONEWAY
                jr   nz,sa_oneway
                ld   a,b
                and  F_SOLID
                jr   z,sa_no
sa_yes:         scf
                ret

                ; Μονόδρομη: στερεή μόνο όταν την πλησιάζεις από τη σωστή
                ; πλευρά, δηλαδή όταν η βαρύτητα δείχνει ΑΝΤΙΘΕΤΑ από την όψη
                ; της. Το ίδιο tile είναι πάτωμα ή αέρας ανάλογα με το πού
                ; κοιτάς — εκεί είναι η αξία του.
sa_oneway:      ld   e,c
                ld   d,0
                ld   hl,tile_facing
                add  hl,de
                ld   a,(hl)
                add  a,4
                and  7
                ld   hl,hero_g
                cp   (hl)
                jr   z,sa_yes
sa_no:          or   a
                ret

sa_ramp:        ld   hl,(cell_u)        ; L = u, H = v (διαδοχικά bytes)
                ld   c,l
                ld   b,h
                cp   T_RAMP_DL
                jr   z,sa_dl
                cp   T_RAMP_UR
                jr   z,sa_ur
                cp   T_RAMP_UL
                jr   z,sa_ul

                ld   a,c                ; RAMP_DR: u+v >= 7
                add  a,b
                cp   7
                ccf
                ret
sa_dl:          ld   a,b                ; RAMP_DL: v >= u
                cp   c
                ccf
                ret
sa_ur:          ld   a,c                ; RAMP_UR: v <= u  <=>  u >= v
                cp   b
                ccf
                ret
sa_ul:          ld   a,c                ; RAMP_UL: u+v <= 7
                add  a,b
                cp   8
                ret

cell_u          db 0
cell_v          db 0                    ; ΠΡΕΠΕΙ να είναι αμέσως μετά το cell_u
cell_ptr        dw 0                    ; δείκτης στο κελί του level_data
cell_col        db 0
cell_row        db 0

;---------------------------------------------------------------------
; render_room — ζωγραφίζει όλα τα 40x24 κελιά. Τρέχει μία φορά.
;---------------------------------------------------------------------
render_room:    ld   hl,level_data
                ld   (rr_ptr),hl
                xor  a
                ld   (rr_row),a
rr_rowlp:       xor  a
                ld   (rr_col),a
rr_collp:
                ld   a,(rr_col)
                ld   c,a
                ld   a,(rr_row)
                ld   b,a
                call draw_tile

                ld   hl,rr_col
                inc  (hl)
                ld   a,(hl)
                cp   LVL_COLS
                jr   nz,rr_collp
                ld   hl,rr_row
                inc  (hl)
                ld   a,(hl)
                cp   LVL_ROWS
                jr   nz,rr_rowlp
                ret


;---------------------------------------------------------------------
; draw_tile — ζωγραφίζει ένα κελί
;   IN: C = στήλη (0..39), B = γραμμή (0..23)
;   Χρησιμοποιείται και για την επαναφορά φόντου κάτω από τον ήρωα.
;---------------------------------------------------------------------
draw_tile:      push bc
                ld   l,b                ; HL = row*40 + col
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl
                ld   d,h
                ld   e,l
                add  hl,hl
                add  hl,hl
                add  hl,de
                ld   e,c
                ld   d,0
                add  hl,de
                ld   de,level_data
                add  hl,de
                ld   a,(hl)             ; τύπος -> γραφικό (16 bytes ανά tile)
                add  a,a
                add  a,a
                add  a,a
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,tile_gfx
                add  hl,de
                ld   (dt_gfx),hl

                ld   a,c                ; στήλη σε bytes
                add  a,a
                ld   c,a
                ld   a,b                ; scanline
                add  a,a
                add  a,a
                add  a,a
                add  a,LVL_Y0
                ld   b,a
                ld   a,LVL_CELL
                ld   (dt_line),a
dt_lp:          push bc
                call scr_addr
                ex   de,hl
                ld   hl,(dt_gfx)
                ldi
                ldi
                ld   (dt_gfx),hl
                pop  bc
                inc  b
                ld   hl,dt_line
                dec  (hl)
                jr   nz,dt_lp
                pop  bc
                ret

dt_gfx          dw 0
dt_line         db 0
rr_ptr          dw 0
rr_gfx          dw 0
rr_row          db 0
rr_col          db 0
rr_line         db 0
