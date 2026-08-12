;=====================================================================
;  GRAVASSIST — οθόνη μενού
;
;  Ο τίτλος όπως στο docs/concept-art.png: GRAV σε ένα χρώμα, ASSIST σε άλλο,
;  σε διπλό μέγεθος pixel. Το concept έχει κίτρινο και κυανό· η παλέτα του
;  MODE 1 έχει τέσσερα χρώματα και δεν περιλαμβάνει κανένα από τα δύο, οπότε
;  μπαίνουν πορτοκαλί και πράσινο — η ΑΝΤΙΘΕΣΗ των δύο μισών διατηρείται, που
;  είναι το νόημα του σχεδίου.
;
;  Κάτω από τον τίτλο ο ήρωας κάνει κύκλους μέσα σε αρένα 10x5. ΔΕΝ είναι
;  animation: τρέχει η ΠΡΑΓΜΑΤΙΚΗ φυσική με walk=1 μονίμως, και οι στροφές στις
;  γωνίες βγαίνουν από τον ίδιο κανόνα που τις βγάζει μέσα στο παιχνίδι. Το
;  μενού είναι έτσι και επίδειξη του μηχανισμού.
;=====================================================================

TITLE_X         equ 20          ; στήλη byte· (80 - 10 γράμματα x 4) / 2
TITLE_Y         equ 14          ; scanline

; Το πλαίσιο, με περιθώριο γύρω από τα γράμματα.
FRAME_X0        equ TITLE_X-2
FRAME_X1        equ TITLE_X+TITLE_LEN*4+1
FRAME_Y0        equ TITLE_Y-6
FRAME_Y1        equ TITLE_Y+TITLE_H*2+5
FRAME_MID       equ TITLE_X+4*4         ; εκεί που τελειώνει το GRAV

ARENA_C         equ 15          ; πάνω-αριστερό κελί της αρένας
ARENA_R         equ 9
ARENA_W         equ 10
ARENA_H         equ 5

; Οι γραμμές 16..21 πήγαν στον πίνακα βαθμολογιών, οπότε το «Press Space»
; κατέβηκε από τη 20 στη 22.
MENU_TXT_ROW    equ 22          ; γραμμές κειμένου του firmware (από 1)
MENU_SIG_ROW    equ 23
MENU_PAGE       equ 500         ; frames ανά σελίδα πλήκτρων = 10 δευτερόλεπτα

;---------------------------------------------------------------------
; menu_show — δείχνει το μενού και γυρίζει όταν πατηθεί SPACE
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
menu_show:      ld   a,1
                call SCR_SET_MODE       ; καθαρίζει την οθόνη
                call set_palette
                call draw_frame
                call draw_title
if DEMO_MODE
                ld   a,INK_HERO_PEN     ; κάτω από τον τίτλο, κεντραρισμένο
                call TXT_SET_PEN
                ld   h,19
                ld   l,(TITLE_Y+26)/8+1
                ld   de,demo_txt
                ld   b,4
                call menu_puts
endif
                call menu_arena
                call menu_text
                call menu_keys
                call hs_menu            ; οι πέντε μεγαλύτερες, από τη δισκέτα
                call music_start        ; ο βρόχος τη συντηρεί, νότα τη νότα

                ; Ο ήρωας ξεκινά μέσα στην αρένα και περπατάει για πάντα.
                ld   hl,(ARENA_C+3)*LVL_CELL+LVL_CELL/2
                ld   (hero_x),hl
                ld   hl,LVL_Y0+(ARENA_R+2)*LVL_CELL+LVL_CELL/2
                ld   (hero_y),hl
                xor  a
                ld   (hero_g),a
                ld   (world_g),a
                ld   (hero_carry),a
                ld   (hero_paraopen),a
                ld   (crates_on),a
                ld   a,HST_FALL
                ld   (hero_state),a
                ld   a,#FF
                ld   (last_valid),a
                xor  a
                ld   (last_valid),a

menu_loop:      ld   hl,(menu_tick)     ; κάθε MENU_PAGE frames, άλλαξε σελίδα
                inc  hl
                ld   (menu_tick),hl
                ld   a,h
                cp   MENU_PAGE/256
                jr   nz,mk_no
                ld   a,l
                cp   MENU_PAGE&255
                jr   nz,mk_no
                ld   hl,0
                ld   (menu_tick),hl
                ld   a,(key_page)
                xor  1
                ld   (key_page),a
                call menu_keys
mk_no:
if DEMO_MODE
                call demo_mark
endif
                call music_step
                ld   a,1                ; ΠΑΝΤΑ μπροστά: ο γύρος βγαίνει μόνος
                call hero_update
                call anim_frame
                call prep_hero
                call MC_WAIT_FLYBACK
                call draw_hero
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   z,menu_loop
                jp   music_stop         ; σιωπή πριν ξεκινήσει το παιχνίδι

;---------------------------------------------------------------------
; menu_arena — χτίζει και ζωγραφίζει την αρένα 10x5 μέσα στο cell_buf
;
;   Το υπόλοιπο πλέγμα μένει κενό, ώστε το σβήσιμο του ήρωα (που ζωγραφίζει
;   ξανά τα πλακίδια από κάτω του) να μη σβήνει τίτλο ή κείμενο — αυτά είναι
;   ζωγραφισμένα κατευθείαν στην οθόνη και δεν υπάρχουν στο πλέγμα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
menu_arena:     ld   hl,cell_buf        ; όλα κενά
                ld   (hl),T_EMPTY
                ld   de,cell_buf+1
                ld   bc,LVL_CELLS-1
                ldir
                ld   hl,cell_buf
                ld   (level_ptr),hl

                ; Οι πίνακες αντικειμένων δείχνουν σε σκέτο τερματικό: το
                ; hero_update τους σαρώνει και χωρίς αυτό θα διάβαζε ό,τι
                ; έτυχε να υπάρχει στη μνήμη.
                ld   hl,menu_term
                ld   (room_exits),hl
                ld   (room_tps),hl
                ld   (room_arr),hl
                ld   (room_attrs),hl

                ld   b,ARENA_R          ; --- το περίγραμμα ---
                ld   c,ARENA_C
                ld   a,ARENA_H
                ld   (ma_rows),a
ma_row:         ld   a,ARENA_W
                ld   (ma_cols),a
                ld   c,ARENA_C
ma_cell:        push bc
                ld   a,b                ; πάνω ή κάτω γραμμή -> στερεό
                cp   ARENA_R
                jr   z,ma_solid
                cp   ARENA_R+ARENA_H-1
                jr   z,ma_solid
                ld   a,c                ; αριστερή ή δεξιά στήλη -> στερεό
                cp   ARENA_C
                jr   z,ma_solid
                cp   ARENA_C+ARENA_W-1
                jr   z,ma_solid
                ld   a,T_EMPTY
                jr   ma_put
ma_solid:       ld   a,T_SOLID
ma_put:         push af
                call cell_addr
                pop  af
                ld   (hl),a
                pop  bc
                push bc
                call draw_tile
                pop  bc
                inc  c
                ld   hl,ma_cols
                dec  (hl)
                jr   nz,ma_cell
                inc  b
                ld   hl,ma_rows
                dec  (hl)
                jr   nz,ma_row
                ret

ma_rows         db 0
ma_cols         db 0
menu_term       db #FF

;---------------------------------------------------------------------
; menu_text — οι δύο γραμμές κάτω από την αρένα
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
menu_text:      ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   hl,menu_lines
mt_lp:          ld   a,(hl)             ; στήλη· 0 = τέλος του πίνακα
                or   a
                ret  z
                ld   d,a
                inc  hl
                ld   e,(hl)             ; γραμμή
                inc  hl
                ld   b,(hl)             ; μήκος
                inc  hl
                ex   de,hl              ; HL = θέση (H=στήλη, L=γραμμή),
                call menu_puts          ; DE = κείμενο· γυρίζει DE μετά το τέλος
                ex   de,hl              ; …που είναι η επόμενη εγγραφή
                jr   mt_lp

; menu_keys — γράφει τη σελίδα πλήκτρων που ισχύει τώρα
menu_keys:      ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   hl,menu_keys_a
                ld   a,(key_page)
                or   a
                jr   z,mk_go
                ld   hl,menu_keys_b
mk_go:          jr   mt_lp

; ΟΧΙ 'menu_page': το rasm είναι case-insensitive και θα
; συγκρουόταν με τη σταθερά MENU_PAGE.
key_page        db 0
menu_tick       dw 0

; menu_puts — τυπώνει B χαρακτήρες από το DE στη θέση (H,L)
;   OUT: DE = ένα byte μετά το κείμενο
menu_puts:      push de
                call TXT_SET_CURSOR
                pop  de
mp_lp:          ld   a,(de)
                push de
                push bc
                call TXT_OUTPUT
                pop  bc
                pop  de
                inc  de
                djnz mp_lp
                ret

; Πίνακας: στήλη, γραμμή, μήκος, κείμενο. Στήλη 0 = τέλος.
;
; Τα χειριστήρια πλαισιώνουν την αρένα — αριστερά η βαρύτητα σε πλέγμα 3x3
; όπου η ΘΕΣΗ του πλήκτρου είναι η κατεύθυνση, δεξιά τα υπόλοιπα. Η αρένα
; πιάνει τις στήλες χαρακτήρων 16..25, οπότε τα δύο μπλοκ δεν την αγγίζουν.
; Ό,τι ΔΕΝ αλλάζει: γράφεται μία φορά.
menu_lines:     db 2,11,7
                db "GRAVITY"
                db 28,12,9
                db "SHIFT run"
                db 28,14,9
                db "UP/DOWN ="
                db 28,15,9
                db "use  door"
                db 8,MENU_TXT_ROW,25
                db "Press Space to start game"
                db 8,MENU_SIG_ROW,26
                db "REVIVE8BIT - 2026 - VASPER"
                db 0

; Οι δύο σελίδες πλήκτρων. Τα ΙΔΙΑ πλάτη και στις δύο (8 και 9 χαρακτήρες),
; ώστε η μία να γράφει ακριβώς πάνω στην άλλη και να μη χρειάζεται σβήσιμο —
; το σβήσιμο με κενά θα άφηνε τρεμόπαιγμα κάθε δέκα δευτερόλεπτα.
menu_keys_a:    db 3,12,8
                db "Q W E   "
                db 3,13,8
                db "A   D   "
                db 3,14,8
                db "Z X C   "
                db 28,11,9
                db "M N  walk"
                db 0

menu_keys_b:    db 3,12,8
                db "F7 F8 F9"
                db 3,13,8
                db "F4    F6"
                db 3,14,8
                db "F1 F2 F3"
                db 28,11,9
                db "< >  walk"
                db 0

;---------------------------------------------------------------------
; draw_frame — το πλαίσιο γύρω από τον τίτλο
;
;   Τα panels του concept art έχουν κυανό περίγραμμα. Το MODE 1 δεν έχει
;   κυανό· μπαίνει πράσινο, το ίδιο που παίρνει και το ASSIST — στο concept
;   το περίγραμμα και το ASSIST μοιράζονται κι εκεί το ίδιο χρώμα.
;
;   Οριζόντια το πάχος είναι ΕΝΑ byte (4 pixel) και κάθετα ΔΥΟ scanlines. Στην
;   οθόνη του CPC το pixel του MODE 1 είναι περίπου διπλάσιο σε ύψος παρά σε
;   πλάτος, οπότε οι δύο πλευρές βγαίνουν οπτικά ίδιες.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
draw_frame:     ld   b,FRAME_Y0         ; πάνω και κάτω πλευρά
                call df_bar
                ld   b,FRAME_Y0+1
                call df_bar
                ld   b,FRAME_Y1-1
                call df_bar
                ld   b,FRAME_Y1
                call df_bar

                ld   b,FRAME_Y0+2       ; οι δύο κάθετες πλευρές
df_side:        push bc
                ld   c,FRAME_X0
                call scr_addr
                ld   (hl),BYTE_PEN3     ; αριστερά: το χρώμα του GRAV
                pop  bc
                push bc
                ld   c,FRAME_X1
                call scr_addr
                ld   (hl),BYTE_PEN2     ; δεξιά: το χρώμα του ASSIST
                pop  bc
                inc  b
                ld   a,b
                cp   FRAME_Y1-1
                jr   c,df_side
                ret

; df_bar — οριζόντια πλευρά στη scanline B.
;
;   Ξεκινά ΕΝΑ byte μέσα από τη γωνία και σταματά ένα byte πριν την άλλη: μαζί
;   με τις κάθετες πλευρές που αρχίζουν δύο scanlines χαμηλότερα, οι γωνίες
;   βγαίνουν ΚΟΜΜΕΝΕΣ — όπως το πλαίσιο του concept art, που δεν έχει ορθές
;   γωνίες αλλά λοξοτομή.
df_bar:         push bc
                ld   c,FRAME_X0+1
                call scr_addr
                ld   b,FRAME_X1-FRAME_X0-1
                ld   c,FRAME_X0+1
df_blp:         ld   a,c                ; το χρώμα αλλάζει στη μέση, μαζί με
                cp   FRAME_MID          ; τα γράμματα: GRAV | ASSIST
                ld   a,BYTE_PEN3
                jr   c,df_bp
                ld   a,BYTE_PEN2
df_bp:          ld   (hl),a
                inc  hl
                inc  c
                djnz df_blp
                pop  bc
                ret

;---------------------------------------------------------------------
; draw_title — «GRAVASSIST» σε διπλό μέγεθος pixel
;
;   Τα πρώτα τέσσερα γράμματα σε ένα χρώμα και τα υπόλοιπα σε άλλο, όπως το
;   GRAV/ASSIST του concept art.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
draw_title:     ld   a,TITLE_X
                ld   (dt_col),a
                ld   hl,title_idx
                ld   (dt_ptr),hl
                ld   b,TITLE_LEN
tt_lp:          push bc
                ld   a,TITLE_LEN        ; πόσο μακριά είμαστε από την αρχή
                sub  b
                cp   4                  ; GRAV | ASSIST
                ld   hl,font_x2_a
                jr   c,tt_pen
                ld   hl,font_x2_b
tt_pen:         ld   (dt_tab),hl
                ld   a,TITLE_Y
                ld   (dt_row),a
                ld   hl,(dt_ptr)
                ld   a,(hl)
                inc  hl
                ld   (dt_ptr),hl
                call draw_glyph
                ld   hl,dt_col
                ld   a,(hl)
                add  a,4                ; 16 pixel = 4 bytes σε MODE 1
                ld   (hl),a
                pop  bc
                djnz tt_lp
                ret

if DEMO_MODE
;---------------------------------------------------------------------
; demo_mark — η λέξη DEMO κάτω δεξιά
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;
; Καλείται ΚΑΘΕ ΚΑΡΕ στο παιχνίδι, όχι μία φορά: η γραμμή 25 είναι μέσα στο
; πεδίο παιχνιδιού και ο ήρωας ή τα πλακίδια τη σβήνουν περνώντας από πάνω.
;
; Όλο το μπλοκ μπαίνει στο binary ΜΟΝΟ σε δισκέτα επίδειξης· η κανονική δεν
; πληρώνει ούτε ένα byte.
;---------------------------------------------------------------------
DEMO_COL        equ 36
DEMO_ROW        equ 25

demo_mark:      ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   h,DEMO_COL
                ld   l,DEMO_ROW
                ld   de,demo_txt
                ld   b,4
                jp   menu_puts

demo_txt:       db   "DEMO"
endif

;---------------------------------------------------------------------
; draw_banner — οποιοδήποτε κείμενο με τα γράμματα του τίτλου, ένα χρώμα
; IN:  HL = πίνακας δεικτών γραμμάτων, B = πλήθος,
;      A = στήλη byte, D = scanline, E = pen (2 ή 3)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;
; Ο ίδιος κώδικας με τον τίτλο. Το «GAME OVER» και το «THE END» ΠΡΕΠΕΙ να
; μοιάζουν με την αρχική οθόνη — μια δεύτερη γραμματοσειρά θα έκανε το τέλος
; να φαίνεται σαν άλλο πρόγραμμα.
;---------------------------------------------------------------------
draw_banner:    ld   (dt_col),a
                ld   (dt_ptr),hl
                ld   a,d
                ld   (dt_row),a
                ld   hl,font_x2_b       ; pen 2 (υλικό)
                ld   a,e
                cp   2
                jr   z,db_pen
                ld   hl,font_x2_a       ; pen 3 (ακμή)
db_pen:         ld   (dt_tab),hl
db_lp:          push bc
                ld   a,d
                ld   (dt_row),a
                ld   hl,(dt_ptr)
                ld   a,(hl)
                inc  hl
                ld   (dt_ptr),hl
                push de
                call draw_glyph
                pop  de
                ld   hl,dt_col
                ld   a,(hl)
                add  a,4
                ld   (hl),a
                pop  bc
                djnz db_lp
                ret

;---------------------------------------------------------------------
; draw_glyph — ένα γράμμα 8x8 σε διπλό μέγεθος (16x16 pixel)
; IN: A = δείκτης γράμματος, (dt_col) = στήλη byte, (dt_row) = scanline,
;     (dt_tab) = πίνακας επέκτασης του χρώματος
;---------------------------------------------------------------------
draw_glyph:     ld   l,a                ; *TITLE_H bytes ανά γράμμα (12 = 8+4)
                ld   h,0
                add  hl,hl
                add  hl,hl              ; x4
                ld   d,h
                ld   e,l
                add  hl,hl              ; x8
                add  hl,de              ; x12
                ld   de,font_glyphs
                add  hl,de
                ld   (dt_src),hl
                ld   a,TITLE_H
                ld   (dt_n),a

dg_row:         ld   hl,(dt_src)        ; κάθε γραμμή πηγής -> ΔΥΟ scanlines
                ld   a,(hl)
                ld   (dt_bits),a
                ld   b,2
dg_dup:         push bc
                ld   a,(dt_row)
                ld   b,a
                ld   a,(dt_col)
                ld   c,a
                call scr_addr
                ex   de,hl              ; DE = οθόνη
                ld   a,(dt_bits)
                rrca
                rrca
                rrca
                rrca
                and  15                 ; υψηλό nibble = τα 4 αριστερά pixel
                call dg_pair
                ld   a,(dt_bits)
                and  15
                call dg_pair
                ld   hl,dt_row
                inc  (hl)
                pop  bc
                djnz dg_dup

                ld   hl,(dt_src)
                inc  hl
                ld   (dt_src),hl
                ld   hl,dt_n
                dec  (hl)
                jr   nz,dg_row
                ret

; dg_pair — 4 bits μάσκας -> 2 bytes οθόνης στο DE
dg_pair:        add  a,a                ; δύο bytes ανά εγγραφή
                ld   l,a
                ld   h,0
                ld   bc,(dt_tab)
                add  hl,bc
                ld   a,(hl)
                ld   (de),a
                inc  de
                inc  hl
                ld   a,(hl)
                ld   (de),a
                inc  de
                ret

dt_col          db 0
dt_row          db 0
dt_n            db 0
dt_bits         db 0
dt_src          dw 0
dt_tab          dw 0
dt_ptr          dw 0
