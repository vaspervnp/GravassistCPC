;=====================================================================
;  GRAVASSIST — οι πέντε μεγαλύτερες βαθμολογίες, στη δισκέτα
;
;  ΠΡΩΤΗ ΕΓΓΡΑΦΗ ΣΕ ΔΙΣΚΟ που κάνει το παιχνίδι. Ως τώρα μόνο διάβαζε, οπότε
;  εδώ μπαίνουν και οι τρεις κλήσεις CAS_OUT_*.
;
;  Η ΛΟΓΙΚΗ ΕΙΝΑΙ ΧΩΡΙΣΤΑ ΑΠΟ ΤΟΝ ΔΙΣΚΟ επίτηδες: το hs_place και το
;  hs_insert δουλεύουν πάνω στον πίνακα στη μνήμη και δοκιμάζονται στον
;  προσομοιωτή. Ο δίσκος δεν δοκιμάζεται από εδώ — στο tools/z80run.py όλο
;  το jumpblock του firmware είναι RET.
;
;  Η δισκέτα μπορεί να είναι προστατευμένη ή γεμάτη. Η αποτυχία εγγραφής ΔΕΝ
;  είναι σφάλμα του παιχνιδιού: ο πίνακας μένει σωστός στη μνήμη για αυτή τη
;  συνεδρία και απλώς δεν επιβιώνει. Καμία διακοπή, κανένα μήνυμα λάθους.
;=====================================================================

CAS_OUT_OPEN    equ  #BC8C      ; HL=όνομα, B=μήκος, DE=buffer 2K
CAS_OUT_DIRECT  equ  #BC98      ; HL=δεδομένα, DE=μήκος, BC=exec, A=τύπος
CAS_OUT_CLOSE   equ  #BC8F
CAS_OUT_ABANDON equ  #BC92
; KM READ CHAR: CF=1 και A = ο χαρακτήρας, αν υπάρχει πλήκτρο στην ουρά.
; ΔΕΝ περιμένει — γι' αυτό ο βρόχος του hs_ask ξαναρωτά.
KM_READ_CHAR    equ  #BB09

HS_VERSION      equ  1
HS_ENTRY        equ  2+HISCORE_NAME     ; dw σκορ + τρία γράμματα
HS_HDR_SZ       equ  4                  ; υπογραφή + έκδοση
HS_BYTES        equ  HS_HDR_SZ+HISCORE_MAX*HS_ENTRY
AMSDOS_BINARY   equ  2

;---------------------------------------------------------------------
; hs_reset — άδειος πίνακας: πέντε μηδενικά με όνομα NUL
;
;   ΜΗΔΕΝ ΚΑΙ ΟΧΙ ΑΡΝΗΤΙΚΟ: το μηδέν είναι ήδη αδύνατο να το πετύχεις (το
;   παιχνίδι τελειώνει μόλις το σκορ γίνει αρνητικό), οπότε κάθε πραγματική
;   παρτίδα μπαίνει στον πίνακα — που είναι το σωστό για άδεια δισκέτα.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_reset:       ld   ix,hs_table
                ld   b,HISCORE_MAX
hr_lp:          ld   (ix+0),0
                ld   (ix+1),0
                push bc
                push ix
                pop  de
                inc  de                 ; DE -> τα γράμματα της εγγραφής
                inc  de
                ld   hl,hs_nul
                ld   bc,HISCORE_NAME
                ldir
                pop  bc
                ld   de,HS_ENTRY
                add  ix,de
                djnz hr_lp
                ret

;---------------------------------------------------------------------
; hs_gt — CF=1 αν HL > DE, ΠΡΟΣΗΜΑΣΜΕΝΑ
;
;   Το sbc hl,de αφήνει carry για ΑΠΡΟΣΗΜΑ. Για προσημασμένα η απάντηση είναι
;   «πρόσημο XOR υπερχείλιση», και η υπερχείλιση διαβάζεται ΜΟΝΟ αμέσως μετά
;   το sbc — γι' αυτό το ld a,h (που δεν πειράζει flags) μπαίνει πρώτο.
;
; IN:  HL, DE      OUT: CF=1 αν HL > DE
; ΑΛΛΟΙΩΝΕΙ: AF, HL
;---------------------------------------------------------------------
hs_gt:          or   a
                sbc  hl,de
                ret  z                  ; ίσα: το sbc άφησε CF=0
                ld   a,h                ; κρατά S και P/V του sbc
                jp   po,hg_nov          ; P/V=0: καμία υπερχείλιση
                xor  #80                ; με υπερχείλιση το πρόσημο λέει ψέματα
hg_nov:         rla                     ; bit 7 -> CF· 1 = αρνητικό = HL < DE
                ccf
                ret

;---------------------------------------------------------------------
; hs_place — σε ποια θέση μπαίνει το σκορ HL;
; IN:  HL = σκορ
; OUT: CF=1 και A = δείκτης θέσης (0..HISCORE_MAX-1)· CF=0 δεν μπαίνει
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_place:       ld   (hs_score),hl
                ld   ix,hs_table
                ld   b,0
hp_lp:          ld   hl,(hs_score)
                ld   e,(ix+0)
                ld   d,(ix+1)
                call hs_gt
                jr   nc,hp_next
                ld   a,b
                scf
                ret
hp_next:        ld   de,HS_ENTRY
                add  ix,de
                inc  b
                ld   a,b
                cp   HISCORE_MAX
                jr   c,hp_lp
                or   a                  ; CF=0: δεν φτάνει για τον πίνακα
                ret

;---------------------------------------------------------------------
; hs_insert — βάζει το hs_score / hs_name στη θέση A, σπρώχνοντας κάτω
;
;   Η μετακίνηση γίνεται με LDDR από το ΤΕΛΟΣ: με LDIR προς τα εμπρός κάθε
;   εγγραφή θα έγραφε πάνω στην επόμενη πριν διαβαστεί, και ο πίνακας θα
;   γέμιζε με αντίγραφα της πρώτης.
;
; IN:  A = θέση, hs_score = σκορ, hs_name = τρία γράμματα
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_insert:      push af
                ; πόσες εγγραφές σπρώχνονται: (HISCORE_MAX-1) - θέση
                ld   b,a
                ld   a,HISCORE_MAX-1
                sub  b
                jr   z,hi_put           ; τελευταία θέση: τίποτα να σπρωχτεί
                ld   c,a                ; C = πλήθος εγγραφών
                ; BC = πλήθος bytes = εγγραφές x HS_ENTRY
                ld   hl,0
                ld   de,HS_ENTRY
hi_mul:         add  hl,de
                dec  c
                jr   nz,hi_mul
                ld   b,h
                ld   c,l
                ; HL = τελευταίο byte της ΠΗΓΗΣ, DE = του ΠΡΟΟΡΙΣΜΟΥ
                ld   hl,hs_table+(HISCORE_MAX-1)*HS_ENTRY-1
                ld   de,hs_table+HISCORE_MAX*HS_ENTRY-1
                lddr

hi_put:         pop  af
                ld   de,HS_ENTRY        ; IX -> η εγγραφή της θέσης A
                ld   b,a
                ld   hl,hs_table
                inc  b
hi_off:         dec  b
                jr   z,hi_got
                add  hl,de
                jr   hi_off
hi_got:         push hl
                pop  ix
                ld   de,(hs_score)
                ld   (ix+0),e
                ld   (ix+1),d
                push ix
                pop  de
                inc  de
                inc  de
                ld   hl,hs_name
                ld   bc,HISCORE_NAME
                ldir
                ret

;---------------------------------------------------------------------
; hs_load — διαβάζει το SCORES.BIN· ό,τι στραβώσει, άδειος πίνακας
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_load:        ld   hl,hs_fname
                ld   b,hs_fname_end-hs_fname
                ld   de,cas_buffer
                call CAS_IN_OPEN
                jr   nc,hl_bad
                ld   hl,hs_hdr
                call CAS_IN_DIRECT
                push af
                call CAS_IN_CLOSE
                pop  af
                jr   nc,hl_bad

                ld   hl,hs_hdr          ; υπογραφή 'GRH' + έκδοση
                ld   a,(hl)
                cp   'G'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   'R'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   'H'
                jr   nz,hl_bad
                inc  hl
                ld   a,(hl)
                cp   HS_VERSION
                ret  z
                ; ΛΑΘΟΣ Ή ΑΝΥΠΑΡΚΤΟ ΑΡΧΕΙΟ: άδειος πίνακας, χωρίς μήνυμα. Μια
                ; καινούρια δισκέτα δεν έχει SCORES.BIN και αυτό είναι το
                ; φυσιολογικό, όχι σφάλμα.
hl_bad:         jp   hs_reset

;---------------------------------------------------------------------
; hs_save — γράφει το SCORES.BIN
;
;   Ο buffer των 2 KB είναι η ΟΘΟΝΗ, όπως και στο διάβασμα των αιθουσών. Η
;   εγγραφή γίνεται στο τέλος της παρτίδας, ακριβώς πριν ξαναζωγραφιστεί το
;   μενού, οπότε το μόνο ορατό είναι ένα τρεμόπαιγμα.
;
;   ΑΠΟΤΥΧΙΑ ΔΕΝ ΕΙΝΑΙ ΣΦΑΛΜΑ: προστατευμένη ή γεμάτη δισκέτα σημαίνει απλώς
;   ότι ο πίνακας δεν επιβιώνει. Το CAS_OUT_ABANDON καθαρίζει το μισογραμμένο
;   αρχείο ώστε να μη μείνει σκουπίδι στον κατάλογο.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_save:        ld   hl,hs_fname
                ld   b,hs_fname_end-hs_fname
                ld   de,cas_buffer
                call CAS_OUT_OPEN
                ret  nc
                ld   hl,hs_hdr
                ld   de,HS_BYTES
                ld   bc,0               ; χωρίς διεύθυνση εκτέλεσης
                ld   a,AMSDOS_BINARY
                call CAS_OUT_DIRECT
                jr   nc,hv_bad
                jp   CAS_OUT_CLOSE
hv_bad:         jp   CAS_OUT_ABANDON

;---------------------------------------------------------------------
; hs_submit — το σκορ της παρτίδας στον πίνακα, αν φτάνει
; IN:  hs_name = τα τρία γράμματα (ή NUL)
; OUT: CF=1 αν μπήκε
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_submit:      ld   hl,(score)
                call hs_place
                ret  nc
                call hs_insert
                call hs_save
                scf
                ret

;---------------------------------------------------------------------
; hs_menu — ο πίνακας των πέντε, στο μενού
;
;   Μία γραμμή ανά θέση: «1. ABC  1234». Σταθερό πλάτος, ώστε να μη χρειάζεται
;   σβήσιμο όταν αλλάξει — το μενού γράφει τα στατικά του μία φορά.
;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
HS_ROW          equ  16         ; γραμμή κειμένου της κεφαλίδας
HS_COL          equ  14

hs_menu:        ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   h,HS_COL
                ld   l,HS_ROW
                ld   de,hs_title
                ld   b,hs_title_e-hs_title
                call menu_puts

                ld   ix,hs_table
                xor  a
                ld   (hm_i),a
hm_lp:          ld   a,(hm_i)
                add  a,'1'              ; κατάταξη: 1..5, όχι 0..4
                ld   (hs_line),a
                ld   a,'.'
                ld   (hs_line+1),a
                ld   a,' '
                ld   (hs_line+2),a

                push ix                 ; τα τρία γράμματα
                pop  hl
                inc  hl
                inc  hl
                ld   de,hs_line+3
                ld   bc,HISCORE_NAME
                ldir
                ld   a,' '
                ld   (hs_line+3+HISCORE_NAME),a

                ld   l,(ix+0)           ; και το σκορ, πέντε χαρακτήρες
                ld   h,(ix+1)
                push ix
                call score_digits_hl
                pop  ix
                ld   hl,score_txt
                ld   de,hs_line+4+HISCORE_NAME
                ld   bc,5
                ldir

                ld   a,(hm_i)           ; γραμμή = κεφαλίδα + 1 + θέση
                add  a,HS_ROW+1
                ld   l,a
                ld   h,HS_COL
                ld   de,hs_line
                ld   b,HS_LINE_W
                push ix
                call menu_puts
                pop  ix

                ld   de,HS_ENTRY
                add  ix,de
                ld   hl,hm_i
                inc  (hl)
                ld   a,(hl)
                cp   HISCORE_MAX
                jr   c,hm_lp
                ret

hm_i            db   0
HS_LINE_W       equ  4+HISCORE_NAME+5
hs_line         ds   HS_LINE_W
hs_title:       db   "HIGH SCORES"
hs_title_e:

;---------------------------------------------------------------------
; hs_ask — τρία γράμματα από τον παίκτη
;
;   ENTER τελειώνει νωρίτερα. Αν δεν δοθεί ΚΑΝΕΝΑ γράμμα, το όνομα γίνεται
;   NUL — η προδιαγραφή το λέει ρητά, και ένα κενό όνομα στον πίνακα δεν
;   ξεχωρίζει από κατεστραμμένο αρχείο.
;
; OUT: hs_name γεμάτο
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
ASK_ROW         equ  12
ASK_COL         equ  12

hs_ask:         ld   hl,hs_name         ; ξεκινά με κενά, όχι σκουπίδια
                ld   (hl),' '
                ld   de,hs_name+1
                ld   bc,HISCORE_NAME-1
                ldir
                xor  a
                ld   (ha_n),a

                ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                ld   h,ASK_COL
                ld   l,ASK_ROW
                ld   de,hs_prompt
                ld   b,hs_prompt_e-hs_prompt
                call menu_puts

ha_lp:          call hs_show
                call KM_READ_CHAR
                jr   nc,ha_lp           ; κανένα πλήκτρο ακόμα
                cp   13                 ; ENTER: τέλος, ό,τι δόθηκε
                jr   z,ha_done
                cp   'a'                ; πεζά -> κεφαλαία
                jr   c,ha_up
                cp   'z'+1
                jr   nc,ha_up
                sub  32
ha_up:          cp   'A'
                jr   c,ha_lp            ; μόνο γράμματα· τα υπόλοιπα αγνοούνται
                cp   'Z'+1
                jr   nc,ha_lp
                ld   e,a
                ld   a,(ha_n)
                cp   HISCORE_NAME
                jr   nc,ha_lp           ; γέμισε
                ld   c,a
                ld   b,0
                ld   hl,hs_name
                add  hl,bc
                ld   (hl),e
                ld   hl,ha_n
                inc  (hl)
                ld   a,(hl)
                cp   HISCORE_NAME
                jr   c,ha_lp

ha_done:        call hs_show
                ld   a,(ha_n)
                or   a
                ret  nz
                ld   hl,hs_nul          ; τίποτα δεν δόθηκε
                ld   de,hs_name
                ld   bc,HISCORE_NAME
                ldir
                ret

; hs_show — τα γράμματα όπως πληκτρολογούνται
hs_show:        ld   h,ASK_COL+hs_prompt_e-hs_prompt+1
                ld   l,ASK_ROW
                ld   de,hs_name
                ld   b,HISCORE_NAME
                jp   menu_puts

ha_n            db   0
hs_prompt:      db   "NAME:"
hs_prompt_e:

;---------------------------------------------------------------------
; hs_finish — τέλος παρτίδας: μπαίνει το σκορ στον πίνακα;
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
hs_finish:      ld   hl,(score)
                call hs_place
                ret  nc                 ; δεν έφτασε: τίποτα να ρωτήσουμε
                push af
                call hs_ask
                pop  af
                call hs_insert
                jp   hs_save

hs_nul:         db   "NUL"              ; όνομα όταν ο παίκτης δεν δώσει
hs_fname:       db   "SCORES.BIN"
hs_fname_end:

hs_score        dw   0                  ; το σκορ που κατατίθεται
hs_name         ds   HISCORE_NAME       ; τα γράμματά του

; ΚΕΦΑΛΗ ΚΑΙ ΠΙΝΑΚΑΣ ΣΥΝΕΧΟΜΕΝΑ, με αυτή τη σειρά: έτσι το αρχείο γράφεται
; και διαβάζεται ΕΠΙΤΟΠΟΥ, χωρίς δεύτερο buffer των 29 bytes και χωρίς
; αντιγραφή πριν από κάθε σώσιμο. Μην τα χωρίσεις.
hs_hdr:         db   'G','R','H',HS_VERSION
hs_table        ds   HISCORE_MAX*HS_ENTRY
