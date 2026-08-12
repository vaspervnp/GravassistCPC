; ---------------------------------------------------------------------------
; endings.asm — οι δύο οθόνες που κλείνουν μια παρτίδα
;
;   GAME OVER  όταν μηδενίσει η ενέργεια
;   THE END    όταν περάσεις πόρτα δηλωμένη με προορισμό 0
;
; ΜΕ ΤΑ ΙΔΙΑ ΓΡΑΜΜΑΤΑ ΤΟΥ ΤΙΤΛΟΥ (draw_banner). Δεν είναι διακόσμηση: το τέλος
; πρέπει να μοιάζει με την αρχή, αλλιώς φαίνεται σαν να έσπασε κάτι.
;
; Η ΜΟΥΣΙΚΗ ΤΟΥ ΜΕΝΟΥ ΞΑΝΑΠΑΙΖΕΙ ΣΤΟ ΤΕΛΟΣ. Ο κύκλος κλείνει εκεί που άνοιξε,
; και δεν χρειάζεται δεύτερο κομμάτι στη μνήμη.
; ---------------------------------------------------------------------------

; Ο προορισμός πόρτας που σημαίνει «εδώ τελειώνει το παιχνίδι».
;
; ΟΧΙ 0: το 0 το γράφει και μια πόρτα ΧΩΡΙΣ δήλωση προορισμού, οπότε κάθε
; ξεχασμένη έξοδος θα τερμάτιζε το παιχνίδι. Το 255 δεν είναι ποτέ έγκυρος
; αριθμός αίθουσας.
;
; ΕΔΩ και όχι στο gamedefs.asm: εκείνο είναι ΠΑΡΑΓΟΜΕΝΟ από το genasm.py και
; ό,τι γράψεις εκεί με το χέρι χάνεται στο επόμενο build.
ROOM_END        equ 255

GO_X            equ 10          ; στήλη byte· 9 γράμματα x 4 bytes = 36
GO_Y            equ 56
END_X           equ 14          ; 7 γράμματα x 4 = 28
END_Y           equ 56
END_LINE        equ 16          ; γραμμή χαρακτήρων για τη μικρή γραμμή

; ---------------------------------------------------------------------------
; game_reset — καθαρή αρχή για νέα παρτίδα
; ΑΛΛΟΙΩΝΕΙ: AF,BC,DE,HL
;
; ΧΩΡΙΣ ΑΥΤΟ ΤΟ ΠΑΙΧΝΙΔΙ ΚΟΛΛΟΥΣΕ: η ενέργεια αρχικοποιείται ΜΟΝΟ κατά τη
; συναρμολόγηση (hero_energy db ENERGY_MAX). Μετά το GAME OVER έμενε 0, το
; main ξανάρχιζε, και το πρώτο κιόλας frame ξανάβρισκε μηδέν — ατέρμονη σειρά
; από οθόνες GAME OVER, που μοιάζει με κρέμασμα.
;
; Και δεν φτάνει η ενέργεια: χωρίς μηδενισμό του ημερολογίου, η νέα παρτίδα
; ξεκινά με ΟΛΕΣ τις αλλαγές της προηγούμενης — ανοιγμένες κλειδαριές,
; μαζεμένα κλειδιά — δηλαδή δεν είναι νέα παρτίδα.
; ---------------------------------------------------------------------------
game_reset:     ld   a,ENERGY_MAX
                ld   (hero_energy),a
                xor  a
                ld   (hero_carry),a
                ld   (hero_para),a
                ld   (hero_paraopen),a
                ld   (game_done),a
                ld   (jr_count),a       ; ημερολόγιο αλλαγών: άδειο
                ld   (trail_n),a        ; ίχνος επιστροφής: άδειο
                ld   (plate_prev),a
                ld   (crates_on),a
                ld   (world_g),a
                ld   hl,hero_keys       ; κανένα κλειδί στην τσέπη
                ld   b,ATTR_MAX
gr_keys:        ld   (hl),0
                inc  hl
                djnz gr_keys
                ld   hl,sealed          ; καμία σφραγισμένη πόρτα
                ld   b,32
gr_seal:        ld   (hl),0
                inc  hl
                djnz gr_seal
                call score_reset        ; 1000 πόντοι και άδειος χάρτης
                jp   sfx_reset

; ---------------------------------------------------------------------------
; game_over — μηδένισε η ενέργεια
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;
; Ο ήχος παίζει ΠΡΙΝ την αναμονή: αλλιώς θα ακουγόταν αφού ο παίκτης έχει ήδη
; πατήσει πλήκτρο, δηλαδή ποτέ.
; ---------------------------------------------------------------------------
game_over:      call eg_clear
                ld   hl,go_idx
                ld   b,GO_IDX_LEN
                ld   a,GO_X
                ld   d,GO_Y
                ld   e,3                ; pen 3 — το πορτοκαλί του τίτλου
                call draw_banner
                ld   hl,txt_retry
                call eg_sub
if DEMO_MODE
                call demo_mark
endif
                call sfx_reset
                ld   a,SFXID_OVER
                call sfx_play
                jp   eg_wait

; ---------------------------------------------------------------------------
; the_end — πέρασες πόρτα με προορισμό 0
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
; ---------------------------------------------------------------------------
the_end:        call eg_clear
                ld   hl,end_idx
                ld   b,END_IDX_LEN
                ld   a,END_X
                ld   d,END_Y
                ld   e,2                ; pen 2 — το πράσινο του υλικού
                call draw_banner
                ld   hl,txt_thanks
                call eg_sub
if DEMO_MODE
                call demo_mark
endif
                call sfx_reset
                call music_start        ; η ΙΔΙΑ μουσική με το μενού
eg_endlp:       call music_step
                call MC_WAIT_FLYBACK
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   nz,eg_endlp        ; NZ = πατημένο -> κράτα το πάτημα
eg_end2:        call music_step
                call MC_WAIT_FLYBACK
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   z,eg_end2
                jp   music_stop

; --- καθαρή οθόνη με την παλέτα του παιχνιδιού
eg_clear:       ld   a,1
                call SCR_SET_MODE       ; το MODE καθαρίζει την οθόνη
                jp   set_palette

; --- η μικρή γραμμή από κάτω, κεντραρισμένη· HL -> μήκος, μετά το κείμενο
eg_sub:         ld   a,(hl)             ; ΤΟ ΜΗΚΟΣ ΠΡΩΤΑ: το TXT_SET_PEN χαλάει
                inc  hl                 ; το HL, και ο προσομοιωτής δεν το
                ld   b,a                ; δείχνει — εκεί το firmware είναι RET
                push bc
                push hl
                ld   a,INK_HERO_PEN
                call TXT_SET_PEN
                pop  hl
                pop  bc
                ld   a,40
                sub  b
                srl  a
                inc  a                  ; στήλη ώστε να βγει κεντραρισμένο
                ex   de,hl              ; DE = κείμενο (το θέλει η menu_puts)
                ld   h,a
                ld   l,END_LINE
                jp   menu_puts

; --- αναμονή για SPACE, με το πλήκτρο ΑΦΗΜΕΝΟ πρώτα
;
; Χωρίς αυτό, το SPACE που κρατάς πατημένο τη στιγμή του θανάτου μετριέται
; και εδώ, και η οθόνη περνάει πριν προλάβεις να τη δεις.
eg_wait:        call MC_WAIT_FLYBACK
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   nz,eg_wait
eg_w2:          call MC_WAIT_FLYBACK
                ld   a,K_SPACE
                call KM_TEST_KEY
                jr   z,eg_w2
                ret

txt_retry:      db   24,"Press Space to try again"
txt_thanks:     db   11,"Press Space"
