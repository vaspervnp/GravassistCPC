;=====================================================================
;  GRAVASSIST — φυσική ήρωα
;
;  ΜΕΤΑΓΡΑΦΗ του tools/physics.py, ρουτίνα προς ρουτίνα. Το Python είναι η
;  αναφορά και είναι επαληθευμένο (make test)· αν αλλάξει κάτι εκεί, πρέπει
;  να αλλάξει και εδώ. Οι πίνακες γεωμετρίας παράγονται από το ίδιο μοντέλο
;  (tools/genasm.py -> src/tables.asm), οπότε τα δύο δεν μπορούν να
;  αποκλίνουν αριθμητικά.
;
;  Θέση = ΚΕΝΤΡΟ του σώματος σε pixels, 16-bit προσημασμένα.
;=====================================================================

FEET_B          equ 6           ; απόσταση πέλματος από το κέντρο
FOOT_A          equ 2           ; μισό άνοιγμα ποδιών
WALL_A          equ 3           ; μισό πλάτος κορμού
SCAN_MAX        equ 14          ; πόσο βαθιά ψάχνουμε έδαφος
NO_GROUND       equ 255

;--- Επιτάχυνση πτώσης (8.8 σταθερή υποδιαστολή: 256 = 1 pixel/frame) ---
; Μεγέθη για οθόνη 200 pixel στα 50 Hz. Πτώση όλης της οθόνης (192 px) σε
; 54 frames = 1.08 δευτ.· το ασφαλές όριο των 36 px σε 19 frames.
; Οι σταθερές πτώσης (FALL_V0/ACCEL/VMAX/PARA_V) παράγονται από το μοντέλο

HST_IDLE        equ 0
HST_WALK        equ 1
HST_FALL        equ 2

;=====================================================================
; hero_update — ένα frame
;   IN: A = κατεύθυνση βάδισης: -1 πίσω, 0 ακίνητος, +1 μπροστά
;=====================================================================
hero_update:    ld   (h_d),a
                or   a                  ; κατεύθυνση για τη μέτρηση κλίσης:
                jr   nz,hu_td           ; όταν στέκεται, χρησιμοποιούμε +1
                ld   a,1
hu_td:          ld   (h_td),a
                call crate_step         ; τα κιβώτια πέφτουν κι αυτά
                call h_touch            ; και στον αέρα: μαζεύεις πέφτοντας

                xor  a
                call h_ground
                cp   NO_GROUND
                jr   z,hu_fall
                cp   FEET_B+3           ; πολύ μακριά -> ελεύθερη πτώση
                jr   nc,hu_fall

                ld   a,(hero_state)
                cp   HST_FALL
                call z,h_land

                ; Το ΠΕΡΠΑΤΗΜΑ ευθυγραμμίζει τη βαρύτητα με την επιφάνεια. Ο
                ; έλεγχος γλιστρήματος γίνεται ΜΕΤΑ — ανάποδα, ο ήρωας θα
                ; γλιστρούσε στο πρώτο pixel κάθε ράμπας πριν κουμπώσει.
                ld   a,(h_d)
                or   a
                jr   z,hu_still

                ; Η ταχύτητα ΔΕΝ γίνεται μεγαλύτερο βήμα: εκτελούνται τόσα
                ; βήματα του ΕΝΟΣ pixel όσα λέει ο συσσωρευτής. Γωνίες και
                ; ράμπες ανιχνεύονται ανά pixel — με βήμα 3 θα προσπερνιόνταν.
                ld   a,(walk_acc)
                ld   l,a
                ld   h,0
                ld   de,WALK_V
                add  hl,de
                ld   a,(hero_run)
                or   a
                jr   z,hu_wacc
                add  hl,de              ; τρέξιμο: διπλάσιος ρυθμός
hu_wacc:        ld   a,l
                ld   (walk_acc),a       ; κρατάμε μόνο το κλάσμα
                ld   a,h
                or   a
                jr   z,hu_done
                ld   b,a
hu_wlp:         push bc
                call h_walk
                pop  bc
                djnz hu_wlp
                jr   hu_done
hu_still:       call h_slipping
                jr   c,hu_fall
                ld   a,HST_IDLE
                ld   (hero_state),a
                jr   hu_done
hu_fall:        call h_fall_steps
hu_done:        call h_support
                ld   (hero_prev),a
                call h_crumble
                jp   h_track

;---------------------------------------------------------------------
; h_crumble — το εύθραυστο κελί καταρρέει μόλις ο ήρωας φύγει από πάνω του
;
;   Το F_FRAGILE υπήρχε στον πίνακα ιδιοτήτων από την αρχή, αλλά κανείς δεν
;   το κοιτούσε: το πάτωμα δεν κατέρρεε ποτέ. Η κατάρρευση γίνεται στην
;   ΑΝΑΧΩΡΗΣΗ και όχι στο πάτημα, ώστε να το περνάς ακριβώς μία φορά.
;
;   Το cell_ptr μετά το h_support δείχνει στο κελί στήριξης.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
h_crumble:      ld   a,(cell_col)       ; ποιο κελί πατάμε ΤΩΡΑ;
                ld   b,a
                ld   a,(cell_row)
                ld   c,a
                ld   hl,cr_prev
                ld   a,(hl)
                cp   #FF
                jr   z,hc_save          ; πρώτο frame: δεν υπάρχει "πριν"
                cp   b
                jr   nz,hc_left
                inc  hl
                ld   a,(hl)
                cp   c
                ret  z                  ; ίδιο κελί: ακόμα πάνω του

hc_left:        push bc                 ; άλλαξε κελί: ήταν εύθραυστο το παλιό;
                ld   a,(cr_prev)
                ld   c,a
                ld   a,(cr_prev+1)
                ld   b,a
                push bc
                call cell_addr
                ld   a,(hl)
                ld   e,a
                ld   d,0
                push hl
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                pop  hl
                and  F_FRAGILE
                jr   z,hc_pop
                xor  a                  ; ναι: εξαφανίζεται και ξαναζωγραφίζεται
                call cell_set
                pop  bc
                push bc
                call draw_tile
hc_pop:         pop  bc
                pop  bc

hc_save:        ld   a,(cell_col)
                ld   (cr_prev),a
                ld   a,(cell_row)
                ld   (cr_prev+1),a
                ret

cr_prev         db #FF,#FF              ; κελί στήριξης του προηγούμενου frame
sw_prev         db #FF,#FF              ; κελί διακόπτη του προηγούμενου frame
spike_tick      db 0

;---------------------------------------------------------------------
; h_touch — αντιδράσεις σε ό,τι ακουμπάει το σώμα (μία φορά ανά frame)
;   Το κελί στο ΚΕΝΤΡΟ του σώματος αποφασίζει για τα αντικείμενα· τα αγκάθια
;   κρίνονται από το κελί ΣΤΗΡΙΞΗΣ, γιατί πονάνε μόνο όταν τα πατήσεις.
;---------------------------------------------------------------------
h_touch:        ld   bc,(hero_x)
                ld   de,(hero_y)
                call cell_at
                ld   (h_cell),a
                ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                and  F_PICKUP
                jr   z,ht_nopick

                call h_take             ; σβήσε το κελί και ξαναζωγράφισέ το
                ld   a,(h_cell)
                cp   T_PARACHUTE
                jr   nz,ht_np1
                ld   hl,hero_para       ; ΠΛΗΘΟΣ: μπορείς να έχεις πολλά
                inc  (hl)
                ld   a,1
                ld   (hud_dirty),a
                jr   ht_spikes
ht_np1:         cp   T_KEY
                jr   nz,ht_np2
                ld   a,(cell_col)
                ld   b,a
                ld   a,(cell_row)
                ld   c,a
                call cell_attr
                ld   e,a
                ld   d,0
                ld   hl,hero_keys
                add  hl,de
                inc  (hl)
                ld   a,1
                ld   (hud_dirty),a
                jr   ht_spikes
ht_np2:         ld   a,(hero_energy)    ; ενέργεια
                add  a,ENERGY_PICK
                cp   ENERGY_MAX+1
                jr   c,ht_esave
                ld   a,ENERGY_MAX
ht_esave:       ld   (hero_energy),a
                ld   a,1
                ld   (hud_dirty),a
                jr   ht_spikes

ht_nopick:      ld   a,(h_cell)
                cp   T_EXIT
                jr   nz,ht_nosw
                call exit_dest          ; ποια αίθουσα; 0 = καμία
                or   a
                jr   z,ht_spikes
                ld   (pending_room),a
                jr   ht_spikes

                ; ΔΙΑΚΟΠΤΗΣ. Πυροδοτεί στην ΑΚΜΗ — μόλις μπεις στο κελί, όχι
                ; όσο στέκεσαι πάνω του: αλλιώς οι πόρτες ανοιγοκλείνουν 50
                ; φορές το δευτερόλεπτο και δεν ελέγχονται. Και ΔΕΝ ξοδεύεται:
                ; το ξαναπατάς για να τις ξανακλείσεις.
ht_nosw:        cp   T_SWITCH
                jr   nz,ht_swclr
                ld   a,(cell_col)
                ld   b,a
                ld   a,(cell_row)
                ld   c,a
                ld   hl,sw_prev         ; ίδιο κελί με το προηγούμενο frame;
                ld   a,b
                cp   (hl)
                jr   nz,ht_swfire
                inc  hl
                ld   a,c
                cp   (hl)
                jr   z,ht_spikes        ; ναι: μη ξαναπυροδοτήσεις
ht_swfire:      ld   a,b
                ld   (sw_prev),a
                ld   a,c
                ld   (sw_prev+1),a
                push bc
                call cell_attr          ; A = κανάλι του διακόπτη
                call gate_toggle
                pop  bc
                jr   ht_spikes
ht_swclr:       ld   a,#FF              ; έφυγες από τον διακόπτη
                ld   (sw_prev),a

ht_spikes:      call h_support          ; αγκάθια: μόνο από τη μύτη
                ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                and  F_DEADLY
                ret  z
                ld   hl,tile_facing
                add  hl,de
                ld   a,(hl)
                add  a,4
                and  7
                ld   hl,hero_g
                cp   (hl)
                jr   z,ht_hurt
ht_nospike:     xor  a                  ; δεν πατάς αγκάθι: ο μετρητής μηδενίζει
                ld   (spike_tick),a     ; ώστε το επόμενο χτύπημα να είναι άμεσο
                ret

                ; ΖΗΜΙΑ ΑΝΑ SPIKE_TICKS FRAMES, όχι σε κάθε frame. Με ζημιά
                ; κάθε frame η ενέργεια εξατμιζόταν σε κλάσμα δευτερολέπτου —
                ; το να πατήσεις αγκάθι ήταν στην πράξη θάνατος.
ht_hurt:        ld   hl,spike_tick
                ld   a,(hl)
                or   a
                jr   nz,ht_tick
                ld   a,(hero_energy)
                sub  SPIKE_DMG
                jr   nc,ht_hset
                xor  a
ht_hset:        ld   (hero_energy),a
                ld   a,1
                ld   (hud_dirty),a
                ld   hl,spike_tick
ht_tick:        inc  (hl)
                ld   a,(hl)
                cp   SPIKE_TICKS
                ret  c
                ld   (hl),0
                ret

; rl_arrival — τοποθετεί τον ήρωα στο σημείο άφιξης της πόρτας που γυρίζει
;   στην αίθουσα (from_room), ΚΑΙ ρυθμίζει τη φορά βαρύτητας. Αν δεν υπάρχει
;   τέτοια πόρτα, μένει το σημείο εκκίνησης της αίθουσας.
;
;   Ο πίνακας έχει 4 bytes ανά εγγραφή: αίθουσα, col, row, βαρύτητα. Η
;   βαρύτητα έρχεται ΛΥΜΕΝΗ από το tools/genasm.py — αν ο σχεδιαστής δεν τη
;   δήλωσε, εκεί έχει ήδη μπει η αρχική φορά της αίθουσας, ώστε εδώ να μη
;   χρειάζεται κανένας κανόνας.
;---------------------------------------------------------------------
rl_arrival:     ld   hl,(room_arr)
ra_lp:          ld   a,(hl)
                cp   #FF
                ret  z
                ld   b,a
                ld   a,(from_room)
                cp   b
                jr   z,ra_found
                inc  hl                 ; προσπέρασε αίθουσα, col, row, βαρύτητα
                inc  hl
                inc  hl
                inc  hl
                jr   ra_lp

ra_found:       inc  hl                 ; -> col
                push hl
                inc  hl                 ; -> row
                inc  hl                 ; -> βαρύτητα
                ld   a,(hl)
                ld   (hero_g),a         ; μπαίνεις με τη φορά της πόρτας, όχι
                ld   (world_g),a        ; με την αρχική φορά της αίθουσας
                pop  hl
                jp   hero_to_cell       ; HL -> col, row


;---------------------------------------------------------------------
; hero_to_cell — βάζει τον ήρωα στο ΚΕΝΤΡΟ του κελιού (HL)=col, (HL+1)=row
;
;   Ο πολλαπλασιασμός col*8 ΔΕΝ γίνεται σε 8 bits: η στήλη φτάνει το 39 και
;   39*8 = 312 > 255. Με 'add a,a' το αποτέλεσμα τύλιγε στο 56 και ο ήρωας
;   προσγειωνόταν στην αριστερή άκρη της οθόνης αντί για τον προορισμό του.
;   Η γραμμή χωράει (23*8+12 = 196) αλλά γίνεται κι αυτή σε 16 bits, ώστε να
;   μην ξαναγεννηθεί το ίδιο σφάλμα αν μεγαλώσει το πλέγμα.
;
; IN:  HL=δείκτης σε δύο bytes (col, row)
; OUT: hero_x, hero_y στο κέντρο του κελιού
; ΑΛΛΟΙΩΝΕΙ: AF, C, DE, HL   (η γραμμή φυλάγεται στο C — ΟΧΙ στο D, που το
;            χαλάει το 'ld de,...' λίγο πιο κάτω)
;---------------------------------------------------------------------
hero_to_cell:   ld   a,(hl)             ; col -> κέντρο κελιού
                inc  hl
                ld   c,(hl)             ; row (κράτα το πριν χαλάσει το HL)
                ld   l,a
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl              ; col*8, σε 16 bits
                ld   de,LVL_CELL/2
                add  hl,de
                ld   (hero_x),hl
                ld   l,c
                ld   h,0
                add  hl,hl
                add  hl,hl
                add  hl,hl              ; row*8
                ld   de,LVL_Y0+LVL_CELL/2
                add  hl,de
                ld   (hero_y),hl
                ret

;---------------------------------------------------------------------
; exit_dest — προορισμός της εξόδου στο κελί (cell_col, cell_row)
;   OUT: A = αριθμός αίθουσας, 0 αν δεν δηλώθηκε
;
;   Ο πίνακας έχει ΟΛΑ τα κελιά κάθε ομάδας, όχι μόνο το πρώτο: γειτονικές
;   έξοδοι είναι μία πόρτα και η ομαδοποίηση έγινε ήδη στην παραγωγή, οπότε
;   εδώ αρκεί γραμμική αναζήτηση χωρίς λογική γειτνίασης.
;---------------------------------------------------------------------
exit_dest:      ld   hl,(room_exits)
ed_lp:          ld   a,(hl)
                cp   #FF
                jr   z,ed_none
                ld   b,a                ; col
                inc  hl
                ld   c,(hl)             ; row
                inc  hl
                ld   a,(cell_col)
                cp   b
                jr   nz,ed_next
                ld   a,(cell_row)
                cp   c
                jr   nz,ed_next
                ld   a,(hl)             ; αίθουσα προορισμού
                inc  hl
                ld   b,a
                ld   a,(hl)
                ld   (exit_two),a       ; διπλής κατεύθυνσης;
                ld   a,b
                ret
ed_next:        inc  hl                 ; προσπέρασε αίθουσα και σημαία
                inc  hl
                jr   ed_lp
ed_none:        xor  a
                ld   (exit_two),a
                ret

exit_two        db 0

;---------------------------------------------------------------------
; room_load — φορτώνει την αίθουσα με αριθμό A
;
;   Η αίθουσα ζει συμπιεσμένη μέσα σε ένα σετ των 40 (ROOMSnn.BIN). Αν το
;   σωστό σετ είναι ήδη στη μνήμη — δηλαδή σχεδόν πάντα — η «φόρτωση» είναι
;   σκέτο ξεδίπλωμα του RLE στον cell_buf· αλλιώς προηγείται ανάγνωση από τη
;   δισκέτα.
;
;   Οι τρεις πίνακες (έξοδοι, αφίξεις, τηλεμεταφορές) ΔΕΝ αντιγράφονται: οι
;   δείκτες δείχνουν μέσα στο ίδιο το σετ, που μένει στη μνήμη.
;---------------------------------------------------------------------
room_load:      ld   (cur_room),a
                push af

                dec  a                  ; ποιο σετ; (αίθουσα-1)/SET_ROOMS + 1
                ld   b,0
rl_set:         inc  b
                sub  SET_ROOMS
                jr   nc,rl_set
                ld   a,(set_cur)
                cp   b
                jr   z,rl_have          ; ήδη φορτωμένο: ούτε άγγιγμα στον δίσκο
                ld   a,b
                call set_load
                jr   c,rl_have

                pop  af                 ; ο δίσκος απέτυχε: κράτα ό,τι παίζει
                ret                     ; αντί να δείξεις σκουπίδια

rl_have:        pop  af
                call room_find
                ret  nc                 ; το σετ δεν έχει τέτοια αίθουσα

                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                inc  hl
                ld   (hero_x),de
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                inc  hl
                ld   (hero_y),de
                ld   a,(hl)
                inc  hl
                ld   (hero_g),a
                ld   (world_g),a

                ld   (room_exits),hl    ; οι τρεις πίνακες είναι στη σειρά, ο
                call skip_tab           ; καθένας ως το #FF του
                ld   (room_arr),hl
                call skip_tab
                ld   (room_tps),hl
                call skip_tab
                ld   (room_attrs),hl    ; ο τέταρτος πίνακας: ιδιότητες κελιών
                call skip_attr

                push hl                 ; HL -> τα RLE κελιά
                pop  ix
                ld   de,cell_buf
                call rle_unpack
                ld   hl,cell_buf
                ld   (level_ptr),hl
                call jr_apply           ; ξαναφέρε ό,τι είχε αλλάξει ο παίκτης

                ; Πόρτα διπλής κατεύθυνσης: ο ήρωας εμφανίζεται στο σημείο
                ; άφιξης της πόρτας που γυρίζει πίσω, όχι στο σημείο εκκίνησης
                ; της αίθουσας. Το σημείο το ορίζει ο σχεδιαστής στη γραμμή
                ; 'exit' — το αυτόματο «διπλανό κελί» δεν ξέρει προς τα πού
                ; τραβάει η βαρύτητα και γλιστρούσε πίσω μέσα στην πόρτα.
                ld   a,(exit_two)
                or   a
                call nz,rl_arrival

                xor  a                  ; καθαρή αρχή στη νέα αίθουσα
                ld   (crates_on),a
                ld   (hero_paraopen),a
                ld   (last_valid),a     ; μην ενώσεις με ορθογώνιο άλλης αίθουσας
                ld   (hero_carry),a
                ld   a,HST_FALL
                ld   (hero_state),a
                ld   a,1
                ld   (hud_dirty),a
                jp   render_room

room_exits      dw 0
room_tps        dw 0
room_arr        dw 0
cur_room        db 0
from_room       db 0
pending_room    db 0

;---------------------------------------------------------------------
; h_use — ενεργοποίηση αντικειμένου (πλήκτρο ΚΑΤΩ ή SPACE)
;
;   Ένα πλήκτρο για όλα, με σαφή σειρά προτεραιότητας: αν κουβαλάς κιβώτιο το
;   αφήνεις (με γεμάτα χέρια τίποτα άλλο δεν έχει νόημα), αλλιώς ενεργεί στο
;   κελί που ΠΑΤΑΣ, αλλιώς σε αυτό που ΚΟΙΤΑΣ.
;---------------------------------------------------------------------
h_use:          call h_support          ; ΟΛΑ κρίνονται από το κελί που ΠΑΤΑΣ:
                ld   (h_cell),a         ; με τον ήρωα σε τοίχους και ταβάνια το
                                        ; "μπροστά" δεν προβλέπεται εύκολα, το
                                        ; "από κάτω μου" ναι.
                cp   T_LOCK
                jr   nz,hu_notlock
                ; ΤΟ ΚΛΕΙΔΙ ΤΑΙΡΙΑΖΕΙ Ή ΔΕΝ ΑΝΟΙΓΕΙ. Χωρίς ταυτότητες ένα
                ; κλειδί άνοιγε ό,τι έβρισκε και ο σχεδιαστής δεν μπορούσε να
                ; επιβάλει σειρά — που είναι όλο το puzzle.
                ld   a,(cell_col)
                ld   b,a
                ld   a,(cell_row)
                ld   c,a
                call cell_attr
                ld   e,a
                ld   d,0
                ld   hl,hero_keys
                add  hl,de
                ld   a,(hl)
                or   a
                jr   z,hu_notlock       ; λάθος κλειδί: συνέχισε στα υπόλοιπα
                dec  (hl)
                ld   a,1
                ld   (hud_dirty),a
                ld   hl,(cell_ptr)      ; ΔΕΝ εξαφανίζεται: γίνεται ανοιγμένη
                ld   a,T_LOCK_OPEN      ; πόρτα. Ο παίκτης βλέπει τι ξεκλείδωσε
                call cell_set
                jp   hu_redraw          ; και περνά από μέσα.

hu_notlock:     ld   bc,(hero_x)        ; τηλεμεταφορά: κρίνεται από το κελί του
                ld   de,(hero_y)        ; ΣΩΜΑΤΟΣ, όχι των ποδιών
                call cell_at
                cp   T_TELEPORT
                jp   z,h_teleport

                ld   a,(hero_carry)     ; με γεμάτα χέρια, άφησε
                or   a
                jr   nz,hu_drop

                ld   a,(h_cell)         ; αλλιώς, σήκωσε ό,τι πατάς
                cp   T_CRATE
                ret  nz
                ld   a,1
                ld   (hero_carry),a
                ld   (hud_dirty),a
                call h_support          ; ξανά, ώστε το cell_ptr να δείχνει στο
                jp   hu_clear           ; κελί στήριξης (το χάλασε το cell_at)

hu_clear:       ld   hl,(cell_ptr)      ; άδειασε το κελί και ξαναζωγράφισέ το
                ld   a,T_EMPTY
                call cell_set
                jp   hu_redraw

hu_drop:        call h_ahead            ; άφημα: στο κελί μπροστά, αν είναι κενό
                or   a                  ; (το κελί στήριξης είναι στερεό και το
                ret  nz                 ; κελί του σώματος το πιάνει ο ήρωας)
                ld   hl,(cell_ptr)
                ld   a,T_CRATE
                call cell_set
                xor  a
                ld   (hero_carry),a
                inc  a
                ld   (hud_dirty),a
hu_redraw:      ld   a,(cell_col)
                ld   c,a
                ld   a,(cell_row)
                ld   b,a
                jp   draw_tile

; h_ahead — τύπος του κελιού ΜΠΡΟΣΤΑ, κατά τη φορά που κοιτάει ο ήρωας
h_ahead:        ld   a,(hero_g)         ; βήμα ενός κελιού κάθετα στη βαρύτητα
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,rstep
                add  hl,de
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                ld   a,(hero_face)
                inc  a
                jr   z,ha_neg
                ld   a,c
                jr   ha_x
ha_neg:         ld   a,c
                neg
ha_x:           add  a,a                ; x LVL_CELL
                add  a,a
                add  a,a
                call h_sext
                ld   hl,(hero_x)
                add  hl,de
                push hl
                ld   a,(hero_face)
                inc  a
                jr   z,ha_negy
                ld   a,b
                jr   ha_y
ha_negy:        ld   a,b
                neg
ha_y:           add  a,a
                add  a,a
                add  a,a
                call h_sext
                ld   hl,(hero_y)
                add  hl,de
                ex   de,hl
                pop  bc
                jp   cell_at

;---------------------------------------------------------------------
; h_teleport — στο ταίρι του. Η φορά βαρύτητας ΔΙΑΤΗΡΕΙΤΑΙ: αλλιώς η
;   τηλεμεταφορά θα ήταν και κρυφό flip, απρόβλεπτο για τον παίκτη.
;---------------------------------------------------------------------
h_teleport:     ld   hl,(room_tps)
tp_lp:          ld   a,(hl)
                cp   #FF
                ret  z                  ; αδήλωτη: δεν κάνει τίποτα
                ld   b,a                ; col
                inc  hl
                ld   c,(hl)             ; row
                inc  hl
                ld   a,(cell_col)
                cp   b
                jr   nz,tp_next
                ld   a,(cell_row)
                cp   c
                jr   z,tp_found
tp_next:        inc  hl                 ; προσπέρασε dcol, drow
                inc  hl
                jr   tp_lp

tp_found:       call hero_to_cell       ; HL -> dcol, drow
                ld   a,1
                ld   (hero_warp),a      ; η σχεδίαση σβήνει ΡΗΤΑ την παλιά θέση
                ret


;---------------------------------------------------------------------
; crate_step — τα κιβώτια πέφτουν προς την ΤΡΕΧΟΥΣΑ φορά βαρύτητας
;
;   Κίνηση ανά ΚΕΛΙ, όχι ανά pixel: το κιβώτιο γεμίζει ακριβώς ένα κελί και η
;   κατά κελί κίνηση κρατά τα puzzles καθαρά, χωρίς δεύτερο σώμα με δική του
;   φυσική pixel.
;
;   Η ΦΟΡΑ ΣΑΡΩΣΗΣ είναι κρίσιμη. Το κιβώτιο μετακινείται κατά
;   delta = dy*40 + dx θέσεις στον πίνακα. Αν σαρώναμε προς την ίδια φορά, ένα
;   κιβώτιο που μόλις μετακινήθηκε θα το ξανασυναντούσαμε και θα κινούνταν
;   δεύτερη φορά στο ίδιο πέρασμα. Σαρώνουμε αντίθετα από το πρόσημο του delta,
;   οπότε προσγειώνεται πάντα σε κελί που έχουμε ήδη προσπεράσει.
;---------------------------------------------------------------------
crate_step:     ld   a,(crates_on)      ; ακίνητα μέχρι ο παίκτης να αλλάξει φορά:
                or   a                  ; αλλιώς θα έπεφταν μόλις φορτώσει η
                ret  z                  ; πίστα και θα χανόταν η τοποθέτησή τους
                ld   hl,crate_tick
                inc  (hl)
                ld   a,(hl)
                cp   CRATE_TICKS
                ret  c
                ld   (hl),0

                ; ΤΗ ΦΟΡΑ ΤΟΥ ΠΑΙΚΤΗ, όχι του ήρωα: η δική του γυρίζει αυτόματα
                ; σε κάθε γωνία που περπατάει, και τα κιβώτια θα άλλαζαν
                ; κατεύθυνση κάθε φορά που στρίβει.
                ld   a,(world_g)
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,gstep
                add  hl,de
                ld   a,(hl)
                ld   (cs_dx),a
                inc  hl
                ld   a,(hl)
                ld   (cs_dy),a

                ld   a,(cs_dy)          ; πρόσημο του delta -> φορά σάρωσης
                bit  7,a
                jr   nz,cs_asc
                or   a
                jr   nz,cs_desc
                ld   a,(cs_dx)
                bit  7,a
                jr   nz,cs_asc
cs_desc:        ld   a,-1
                ld   (cs_step),a
                ld   a,LVL_ROWS-1
                jr   cs_go
cs_asc:         ld   a,1
                ld   (cs_step),a
                xor  a
cs_go:          ld   (cs_row),a
                ld   a,LVL_ROWS
                ld   (cs_rn),a

cs_rowlp:       ld   a,(cs_step)
                bit  7,a
                jr   z,cs_c0
                ld   a,LVL_COLS-1
                jr   cs_c0set
cs_c0:          xor  a
cs_c0set:       ld   (cs_col),a
                ld   a,LVL_COLS
                ld   (cs_cn),a

cs_collp:       ld   a,(cs_row)
                ld   b,a
                ld   a,(cs_col)
                ld   c,a
                call cell_addr
                ld   a,(hl)
                cp   T_CRATE
                jr   nz,cs_next

                ld   a,(cs_col)         ; προορισμός, με έλεγχο ορίων
                ld   e,a
                ld   a,(cs_dx)
                add  a,e
                cp   LVL_COLS           ; αρνητικό -> >=128 -> πιάνεται κι αυτό
                jr   nc,cs_next
                ld   c,a
                ld   a,(cs_row)
                ld   e,a
                ld   a,(cs_dy)
                add  a,e
                cp   LVL_ROWS
                jr   nc,cs_next
                ld   b,a

                push hl                 ; HL = δείκτης παλιού κελιού
                push bc
                call cell_addr
                ld   a,(hl)
                or   a
                jr   nz,cs_blocked      ; ο δρόμος κλειστός
                ld   a,T_CRATE
                call cell_set
                pop  bc
                push bc
                call draw_tile
                pop  bc
                pop  hl
                ld   a,T_EMPTY
                call cell_set
                ld   a,(cs_row)
                ld   b,a
                ld   a,(cs_col)
                ld   c,a
                call draw_tile
                jr   cs_next
cs_blocked:     pop  bc
                pop  hl

cs_next:        ld   a,(cs_col)
                ld   hl,cs_step
                add  a,(hl)
                ld   (cs_col),a
                ld   hl,cs_cn
                dec  (hl)
                jr   nz,cs_collp

                ld   a,(cs_row)
                ld   hl,cs_step
                add  a,(hl)
                ld   (cs_row),a
                ld   hl,cs_rn
                dec  (hl)
                jp   nz,cs_rowlp        ; jp: ο βρόχος ξεπερνά το εύρος του jr
                ret

crate_tick      db 0
cs_dx           db 0
cs_dy           db 0
cs_step         db 0
cs_row          db 0
cs_col          db 0
cs_rn           db 0
cs_cn           db 0

;---------------------------------------------------------------------
; h_track — καταγράφει τη θέση σε κυκλικό buffer STUCK_FRAMES θέσεων
;   Μία φορά ανά frame, στο τέλος του hero_update.
;---------------------------------------------------------------------
h_track:        call h_hist_ptr
                ld   de,(hero_x)
                ld   (hl),e
                inc  hl
                ld   (hl),d
                inc  hl
                ld   de,(hero_y)
                ld   (hl),e
                inc  hl
                ld   (hl),d
                ld   a,(h_hidx)
                inc  a
                cp   STUCK_FRAMES
                jr   c,htr_save
                xor  a
htr_save:       ld   (h_hidx),a
                ret

; HL = h_hist + h_hidx*4 — η θέση που δείχνει ο δείκτης είναι η ΠΑΛΑΙΟΤΕΡΗ,
; γιατί εκεί πρόκειται να γραφτεί η επόμενη.
h_hist_ptr:     ld   a,(h_hidx)
                add  a,a
                add  a,a
                ld   e,a
                ld   d,0
                ld   hl,h_hist
                add  hl,de
                ret

;---------------------------------------------------------------------
; h_stuck — έμεινε ουσιαστικά ακίνητος τα τελευταία STUCK_FRAMES frames;
;   OUT: CY = ναι (καμία μετατόπιση > STUCK_PX σε ΚΑΝΕΝΑΝ από τους δύο άξονες)
;
;   Δικλείδα για τον κανόνα "καμία αλλαγή φοράς στον αέρα": χωρίς αυτήν, ένας
;   ήρωας που γλιστράει ατέρμονα ή σφηνώνει δεν θα ξανάπαιρνε ποτέ τον έλεγχο.
;---------------------------------------------------------------------
h_stuck:        call h_hist_ptr
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                inc  hl
                push hl
                ld   hl,(hero_x)
                or   a
                sbc  hl,de
                call h_absle
                pop  hl
                ret  nc                 ; κινήθηκε πολύ στον x -> όχι ακίνητος
                ld   e,(hl)
                inc  hl
                ld   d,(hl)
                ld   hl,(hero_y)
                or   a
                sbc  hl,de
                ; πέφτει στο h_absle

; h_absle — CY αν |HL| <= STUCK_PX
h_absle:        bit  7,h
                jr   z,hab_pos
                xor  a                  ; HL = -HL
                sub  l
                ld   l,a
                sbc  a,a
                sub  h
                ld   h,a
hab_pos:        ld   a,h
                or   a
                ret  nz                 ; > 255 px -> NC
                ld   a,l
                cp   STUCK_PX+1
                ret

h_hidx          db 0
h_hist          ds STUCK_FRAMES*4, 0

;---------------------------------------------------------------------
; h_noflip — είναι μέσα σε ζώνη όπου απαγορεύεται η αλλαγή βαρύτητας;
;   OUT: CY = απαγορεύεται
h_noflip:       ld   (h_nfa),a          ; ΟΧΙ push af: το pop θα επανέφερε ΚΑΙ τα
                ld   bc,(hero_x)        ; flags, σβήνοντας το αποτέλεσμα του AND.
                ld   de,(hero_y)        ; (Αυτό έκανε να δουλεύει μόνο η φορά 0:
                call cell_at            ;  τα flags έλεγαν "Z" μόνο για A=0.)
                ld   e,a
                ld   d,0
                ld   hl,tile_props
                add  hl,de
                ld   a,(hl)
                and  F_NOFLIP
                ld   a,(h_nfa)          ; το ld ΔΕΝ πειράζει flags
                ret  z                  ; NC = επιτρέπεται
                scf
                ret

h_nfa           db 0

; h_take — αδειάζει το κελί που μόλις διάβασε το cell_at και το ξαναζωγραφίζει
h_take:         ld   hl,(cell_ptr)
                ld   a,T_EMPTY
                call cell_set
                ld   a,(cell_col)
                ld   c,a
                ld   a,(cell_row)
                ld   b,a
                jp   draw_tile

;---------------------------------------------------------------------
; h_land — προσγείωση· υπολογίζει ζημιά από το ύψος πτώσης
;---------------------------------------------------------------------
h_land:         ld   a,HST_IDLE
                ld   (hero_state),a
                ld   a,(hero_paraopen)  ; προσγείωση με αλεξίπτωτο: μία χρήση,
                or   a                  ; καμία ζημιά
                jr   z,hl_nopara
                ld   hl,hero_para       ; καταναλώνεται ΕΝΑ, όχι όλα
                dec  (hl)
                xor  a
                ld   (hero_paraopen),a
                inc  a
                ld   (hud_dirty),a
                dec  a
                ld   hl,0
                ld   (hero_fall),hl
                ld   hl,FALL_V0
                ld   (hero_v),hl
                ld   (hero_facc),a
                ret
hl_nopara:      ld   hl,FALL_V0         ; μηδενισμός ταχύτητας ΠΡΙΝ από τα
                ld   (hero_v),hl        ; πρόωρα ret της ασφαλούς πτώσης
                xor  a
                ld   (hero_facc),a
                ld   hl,(hero_fall)
                ld   de,0
                ld   (hero_fall),de
                ld   de,FALL_SAFE
                or   a
                sbc  hl,de
                ret  c                  ; <= 36 px -> ασφαλής
                ret  z

                ld   b,1                ; ζημιά = 1 + περίσσεια/12
                ld   de,12
hl_div:         or   a
                sbc  hl,de
                jr   c,hl_dmg
                inc  b
                jr   hl_div
hl_dmg:         ld   a,(hero_energy)
                sub  b
                jr   nc,hl_set
                xor  a                  ; 0 = θάνατος
hl_set:         ld   (hero_energy),a
                ret

;---------------------------------------------------------------------
; h_walk — ένα pixel βάδισης, με τους δύο κανόνες γωνίας
;   τοίχος μπροστά   -> -2 βήματα (κοίλη γωνία)
;   χάθηκε το έδαφος -> +2 βήματα (κυρτή γωνία)
;   ράμπα            -> +-1 βήμα, μέσω h_align
;---------------------------------------------------------------------
h_walk:         ld   a,HST_WALK
                ld   (hero_state),a
                ld   a,(h_d)
                ld   (hero_face),a
                call h_save

                call h_wall
                jr   nc,hw_move
                ld   a,(h_d)            ; ΚΟΙΛΗ: στρίψε αντίθετα
                add  a,a
                neg
                ld   (h_steps),a
                jp   h_corner

hw_move:        ld   a,(h_d)
                ld   (h_sd),a
                call h_stepr            ; ένα pixel μπροστά

                xor  a
                call h_ground
                cp   NO_GROUND
                jr   nz,hw_ground
                call h_restore          ; ΚΥΡΤΗ: τέλος πλατώματος
                ld   a,(h_d)
                add  a,a
                ld   (h_steps),a
                jp   h_corner

hw_ground:      call h_snap
                call h_align
                call h_slipping
                ret  nc
                call h_support          ; δεν κούμπωσε και δεν είναι μετάβαση
                ld   hl,hero_prev
                cp   (hl)
                ret  nz
                jp   h_fall

;---------------------------------------------------------------------
; h_fall — πτώση προς τη βαρύτητα, ή γλίστρημα κατά μήκος της επιφάνειας
;---------------------------------------------------------------------
h_fall:         ld   a,HST_FALL
                ld   (hero_state),a
                xor  a
                ld   b,FEET_B
                call h_at
                jr   c,hf_contact

                ld   a,1                ; ελεύθερος -> πέφτε
                call h_stepg
                ld   hl,(hero_fall)
                inc  hl
                ld   (hero_fall),hl
                scf                     ; CY = ήταν ελεύθερη πτώση
                ret

hf_contact:     call h_tilt             ; ακουμπάει: γλίστρα προς το ακάλυπτο
                jr   c,hf_probe         ; πέλμα
                or   a
                jr   z,hf_probe
                bit  7,a
                ld   a,1
                jr   z,hf_slide
                ld   a,-1
                jr   hf_slide
hf_probe:       ld   a,FOOT_A
                ld   b,FEET_B
                call h_at
                ld   a,1
                jr   nc,hf_slide
                ld   a,-1
hf_slide:       ld   (h_sd),a
                call h_save
                call h_stepr
                xor  a
                ld   b,0
                call h_at               ; μπήκε σε υλικό; -> ακύρωσε
                jr   nc,hf_ok
                call h_restore
hf_ok:          call h_snap
                or   a                  ; NC = ακούμπησε ή γλίστρησε
                ret

;---------------------------------------------------------------------
; h_fall_steps — ένα frame πτώσης, με επιτάχυνση μέχρι τερματική ταχύτητα
;
; Η ταχύτητα ΔΕΝ μετατρέπεται σε βήμα πολλών pixel: εκτελούνται τόσα βήματα
; του ΕΝΟΣ pixel όσα λέει η ταχύτητα. Γωνίες, ακμές και ράμπες ανιχνεύονται
; ανά pixel — με βήμα 4 pixel ο ήρωας θα περνούσε μέσα από λεπτά πατώματα.
;
; Το γλίστρημα μένει σταθερό στο 1 px/frame: είναι κίνηση κατά μήκος
; επιφάνειας, όχι πτώση, και η προβλεψιμότητά του μετράει σε puzzle game.
;---------------------------------------------------------------------
h_fall_steps:   ld   a,(hero_state)
                cp   HST_FALL
                jr   z,hfs_para         ; ήδη πέφτει: μόνο ο ΜΗΔΕΝΙΣΜΟΣ ταχύτητας
                ld   hl,FALL_V0         ; παραλείπεται, όχι ο έλεγχος παρακάτω
                ld   (hero_v),hl
                xor  a
                ld   (hero_facc),a

hfs_para:       ; ΑΛΕΞΙΠΤΩΤΟ: ανοίγει μόνο αν το κουβαλάς ΚΑΙ η πτώση έχει ήδη
                ; ξεπεράσει τις 3 φορές το ύψος του ήρωα. Αν άνοιγε σε κάθε
                ; πτώση, ένα σκαλοπάτι δύο pixel θα το κατανάλωνε.
                ld   a,(hero_para)
                or   a
                jr   z,hfs_acc
                ld   a,(hero_paraopen)
                or   a
                jr   nz,hfs_slow
                ld   hl,(hero_fall)
                ld   de,FALL_SAFE
                or   a
                sbc  hl,de
                jr   c,hfs_acc
                ld   a,1
                ld   (hero_paraopen),a
hfs_slow:       ld   hl,PARA_V          ; σταθερή, αργή κάθοδος
                ld   (hero_v),hl
                jr   hfs_frac

hfs_acc:        ld   hl,(hero_v)
                ld   de,FALL_ACCEL
                add  hl,de
                ld   a,h
                cp   FALL_VMAX/256
                jr   c,hfs_cap
                ld   hl,FALL_VMAX       ; τερματική ταχύτητα
hfs_cap:        ld   (hero_v),hl
hfs_frac:       ld   hl,(hero_v)

                ld   a,(hero_facc)      ; κλάσμα + ταχύτητα -> ακέραια βήματα
                ld   e,a
                ld   d,0
                add  hl,de
                ld   a,l
                ld   (hero_facc),a
                ld   a,h
                or   a
                ret  z
                ld   b,a
hfs_lp:         push bc
                call h_fall
                pop  bc
                ret  nc                 ; ακούμπησε -> μην κάνεις άλλα βήματα
                djnz hfs_lp
                ret

;---------------------------------------------------------------------
; h_align — ευθυγραμμίζει τη βαρύτητα με την επιφάνεια, ΔΙΑΒΑΖΟΝΤΑΣ το κελί
;   OUT: CY = έγινε ευθυγράμμιση
;---------------------------------------------------------------------
h_align:        call h_support
                or   a
                ret  z                  ; κενό -> τίποτα

                ld   e,a
                ld   d,0
                ld   hl,ramp_grav
                add  hl,de
                ld   a,(hl)
                cp   NO_GROUND
                jr   z,ha_flat

                ld   hl,hero_g          ; ΡΑΜΠΑ: μία μόνο φορά στέκεται πάνω της
                cp   (hl)
                jr   nz,ha_try
                scf
                ret                     ; ήδη σωστή

                ; ΕΠΙΠΕΔΟ ΣΤΕΡΕΟ: ευθυγράμμιση μόνο αν ερχόμαστε ΑΠΟ ράμπα,
                ; αλλιώς η διαγώνια βαρύτητα του παίκτη θα "ίσιωνε" μόνη της
                ; και δεν θα γλιστρούσε ποτέ.
ha_flat:        ld   a,(hero_g)
                rrca
                jr   nc,ha_no           ; ορθή φορά -> εντάξει
                ld   a,(hero_prev)
                cp   T_RAMP_DR
                jr   c,ha_no            ; δεν ήταν ράμπα
                ld   a,(hero_g)
                dec  a
                and  7
                call ha_try
                ret  c
                ld   a,(hero_g)
                inc  a
                and  7
                call ha_try
                ret  c
ha_no:          or   a
                ret

; ha_try — δοκιμάζει τη φορά στο A· κρατιέται μόνο αν ο ήρωας μένει όρθιος
;          και εκτός υλικού
ha_try:         ld   (h_tmp),a
                call h_save
                ld   a,(h_tmp)
                call h_pivot
                jr   nc,ha_undo
                call h_slipping
                jr   c,ha_undo
                xor  a
                ld   b,0
                call h_at
                jr   c,ha_undo
                xor  a
                ld   b,-FEET_B
                call h_at
                jr   c,ha_undo
                scf
                ret
ha_undo:        call h_restore
                or   a
                ret

;---------------------------------------------------------------------
; h_corner — στροφή 90 μοιρών ΤΥΛΙΓΟΝΤΑΣ γύρω από την ακμή
;   IN: (h_steps) = +-2, (h_d) = φορά βάδισης, αποθηκευμένη θέση από h_save
;
;   C          = κέντρο + WALL_A*d*R_παλιό + FEET_B*G_παλιό
;   νέο κέντρο = C + WALL_A*d*R_νέο - FEET_B*G_νέο
;---------------------------------------------------------------------
h_corner:       call h_wall_a           ; A = WALL_A * d
                ld   b,FEET_B
                call h_point
                ld   (h_cx),bc
                ld   (h_cy),de

                ld   a,(hero_g)
                ld   hl,h_steps
                add  a,(hl)
                and  7
                ld   (hero_g),a

                call h_wall_a
                add  a,RTAB_OFF
                ld   hl,rtab
                call h_tabptr
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                ld   (h_nr),bc

                ld   a,FEET_B+GTAB_OFF
                ld   hl,gtab
                call h_tabptr
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                ld   (h_ng),bc

                ld   a,(h_nr)           ; x = cx + nr.x - ng.x
                ld   hl,h_ng
                sub  (hl)
                call h_sext
                ld   hl,(h_cx)
                add  hl,de
                ld   (hero_x),hl
                ld   a,(h_nr+1)         ; y = cy + nr.y - ng.y
                ld   hl,h_ng+1
                sub  (hl)
                call h_sext
                ld   hl,(h_cy)
                add  hl,de
                ld   (hero_y),hl

                call h_snap
                jr   nc,hc_fail
                call h_slipping
                jr   c,hc_fail
                scf
                ret
hc_fail:        call h_restore
                or   a
                ret

; A = WALL_A * (h_d)
h_wall_a:       ld   a,(h_d)
                ld   b,a
                add  a,a
                add  a,b
                ret

;---------------------------------------------------------------------
; h_pivot — αλλάζει φορά περιστρέφοντας ΓΥΡΩ ΑΠΟ ΤΟ ΣΗΜΕΙΟ ΕΠΑΦΗΣ
;   IN: A = νέα φορά    OUT: CY = πέτυχε
;---------------------------------------------------------------------
h_pivot:        ld   (h_newg),a
                xor  a
                call h_ground
                cp   NO_GROUND
                jr   z,hp_fail
                ld   b,a                ; B = βάθος επαφής
                xor  a
                call h_point            ; BC,DE = σημείο επαφής
                ld   (h_cx),bc
                ld   (h_cy),de

                ld   a,(h_newg)
                ld   (hero_g),a
                ld   a,FEET_B+GTAB_OFF
                ld   hl,gtab
                call h_tabptr
                ld   c,(hl)
                inc  hl
                ld   b,(hl)

                ld   a,c                ; κέντρο = επαφή - FEET_B*G_νέο
                neg
                call h_sext
                ld   hl,(h_cx)
                add  hl,de
                ld   (hero_x),hl
                ld   a,b
                neg
                call h_sext
                ld   hl,(h_cy)
                add  hl,de
                ld   (hero_y),hl
                jp   h_snap
hp_fail:        or   a
                ret

;---------------------------------------------------------------------
; h_snap — κάθισε τα πέλματα πάνω στην επιφάνεια
;   OUT: CY = πέτυχε
;   Ανοχή +-1 pixel: με διαγώνια βαρύτητα το μετρημένο βάθος πηδάει 5->7
;   λόγω στρογγυλοποίησης και ακριβές 6 δεν επιτυγχάνεται ποτέ.
;---------------------------------------------------------------------
h_snap:         ld   a,SCAN_MAX
                ld   (h_cnt),a
hs_loop:        xor  a
                call h_ground
                cp   NO_GROUND
                jr   z,hs_fail
                sub  FEET_B
                jr   z,hs_ok
                cp   1
                jr   z,hs_ok
                cp   #FF
                jr   z,hs_ok
                bit  7,a
                ld   a,1                ; βάθος > 6 -> κατέβα
                jr   z,hs_step
                ld   a,-1               ; βάθος < 6 -> ανέβα
hs_step:        call h_stepg
                ld   hl,h_cnt
                dec  (hl)
                jr   nz,hs_loop
hs_fail:        or   a
                ret
hs_ok:          scf
                ret

;---------------------------------------------------------------------
; h_slipping — γλιστράει; (η βαρύτητα δεν είναι κάθετη στην επιφάνεια)
;   OUT: CY = γλιστράει
;---------------------------------------------------------------------
h_slipping:     call h_support
                or   a
                jr   z,hsl_no           ; κενό: πτώση, όχι γλίστρημα
                ld   e,a
                ld   d,0
                ld   hl,ramp_grav
                add  hl,de
                ld   a,(hl)
                cp   NO_GROUND
                jr   z,hsl_flat
                ld   hl,hero_g          ; ράμπα: μόνο η δική της φορά στέκεται
                cp   (hl)
                jr   z,hsl_no
                scf
                ret
hsl_flat:       ld   a,(hero_g)         ; στερεό: μόνο ορθές φορές στέκονται
                rrca
                ret  c
hsl_no:         or   a
                ret

;---------------------------------------------------------------------
; h_support — τύπος κελιού που στηρίζει τα πέλματα (ΣΤΟ ΜΕΤΡΗΜΕΝΟ βάθος)
;   OUT: A = τύπος (0 αν δεν ακουμπάει)
;---------------------------------------------------------------------
h_support:      xor  a
                call h_ground
                cp   NO_GROUND
                jr   z,hsu_none
                ld   b,a
                xor  a
                call h_point
                jp   cell_at
hsu_none:       xor  a
                ret

;---------------------------------------------------------------------
; h_tilt — διαφορά βάθους εδάφους μπροστά/πίσω
;   OUT: NC και A = κλίση (προσημασμένη)· CY αν λείπει έδαφος
;---------------------------------------------------------------------
h_tilt:         ld   a,(h_td)
                add  a,a                ; FOOT_A * d
                call h_ground
                cp   NO_GROUND
                jr   z,ht_none
                ld   (h_tmp),a
                ld   a,(h_td)
                add  a,a
                neg
                call h_ground
                cp   NO_GROUND
                jr   z,ht_none
                ld   b,a
                ld   a,(h_tmp)
                sub  b
                or   a                  ; καθαρίζει το carry, κρατά το A
                ret
ht_none:        scf
                ret

;---------------------------------------------------------------------
; h_wall — εμπόδιο στο ύψος του ΚΟΡΜΟΥ (όχι των ποδιών: αλλιώς κάθε ράμπα
;          θα έμοιαζε με τοίχο)
;   OUT: CY = τοίχος
;---------------------------------------------------------------------
h_wall:         call h_wall_a
                ld   (h_tmp),a
                ld   b,0
                call h_at
                ret  c
                ld   a,(h_tmp)
                ld   b,-4
                jp   h_at

;---------------------------------------------------------------------
; h_ground — βάθος εδάφους στη στήλη A (πλάγια απόσταση)
;   OUT: A = 0..SCAN_MAX-1 ή NO_GROUND
;---------------------------------------------------------------------
h_ground:       ld   (h_ga),a
                ld   c,0
hg_loop:        ld   a,(h_ga)
                ld   b,c
                push bc
                call h_at
                pop  bc
                jr   c,hg_hit
                inc  c
                ld   a,c
                cp   SCAN_MAX
                jr   nz,hg_loop
                ld   a,NO_GROUND
                ret
hg_hit:         ld   a,c
                ret

;---------------------------------------------------------------------
; h_at — στερεό στο τοπικό σημείο (A = πλάγια, B = προς τα πόδια);
;---------------------------------------------------------------------
h_at:           call h_point
                jp   solid_at

;---------------------------------------------------------------------
; h_point — τοπικές συντεταγμένες -> θέση στον κόσμο
;   IN:  A = a (πλάγια, προσημασμένο), B = b (προς τα πόδια, προσημασμένο)
;   OUT: BC = x, DE = y
;   Αθροίζει ΔΥΟ ξεχωριστά στρογγυλοποιημένες τιμές από τους πίνακες — όπως
;   ακριβώς και το μοντέλο (physics.off), ώστε να συμφωνούν στο pixel.
;---------------------------------------------------------------------
h_point:        ld   (h_pa),a
                ld   a,b
                ld   (h_pb),a

                ld   a,(h_pa)
                add  a,RTAB_OFF
                ld   hl,rtab
                call h_tabptr
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                ld   (h_pd),bc

                ld   a,(h_pb)
                add  a,GTAB_OFF
                ld   hl,gtab
                call h_tabptr
                ld   c,(hl)
                inc  hl
                ld   b,(hl)

                ld   a,(h_pd)           ; dx = rtab.x + gtab.x
                add  a,c
                call h_sext
                ld   hl,(hero_x)
                add  hl,de
                push hl
                ld   a,(h_pd+1)         ; dy = rtab.y + gtab.y
                add  a,b
                call h_sext
                ld   hl,(hero_y)
                add  hl,de
                ex   de,hl              ; DE = y
                pop  bc                 ; BC = x
                ret

; h_tabptr — HL = πίνακας + g*TAB_ROW + A*2
h_tabptr:       push hl
                ld   e,a
                ld   d,0
                ld   a,(hero_g)
                ld   l,a
                ld   h,0
                add  hl,hl              ; g*2
                add  hl,hl              ; *4
                add  hl,hl              ; *8
                add  hl,hl              ; *16
                add  hl,hl              ; *32
                add  hl,hl              ; *64 = TAB_ROW
                add  hl,de
                add  hl,de
                pop  de
                add  hl,de
                ret

;---------------------------------------------------------------------
; Βήματα ενός pixel
;---------------------------------------------------------------------
h_stepg:        ld   (h_sgn),a          ; κατά τη βαρύτητα, πρόσημο στο A
                ld   hl,gstep
                jr   h_step
h_stepr:        ld   a,(h_sd)           ; κάθετα, πρόσημο στο (h_sd)
                ld   (h_sgn),a
                ld   hl,rstep
h_step:         ld   a,(hero_g)
                add  a,a
                ld   e,a
                ld   d,0
                add  hl,de
                ld   c,(hl)
                inc  hl
                ld   b,(hl)
                ld   a,(h_sgn)
                inc  a
                jr   z,hst_neg
                ld   a,c
                call h_addx
                ld   a,b
                jp   h_addy
hst_neg:        ld   a,c
                neg
                call h_addx
                ld   a,b
                neg
                jp   h_addy

h_addx:         call h_sext
                ld   hl,(hero_x)
                add  hl,de
                ld   (hero_x),hl
                ret
h_addy:         call h_sext
                ld   hl,(hero_y)
                add  hl,de
                ld   (hero_y),hl
                ret

; h_sext — DE = επέκταση προσήμου του A
h_sext:         ld   e,a
                add  a,a
                sbc  a,a
                ld   d,a
                ret

;---------------------------------------------------------------------
; Αποθήκευση / επαναφορά θέσης (για ακυρωμένες κινήσεις)
;---------------------------------------------------------------------
h_save:         ld   hl,(hero_x)
                ld   (h_ox),hl
                ld   hl,(hero_y)
                ld   (h_oy),hl
                ld   a,(hero_g)
                ld   (h_og),a
                ret
h_restore:      ld   hl,(h_ox)
                ld   (hero_x),hl
                ld   hl,(h_oy)
                ld   (hero_y),hl
                ld   a,(h_og)
                ld   (hero_g),a
                ret

;--- κατάσταση --------------------------------------------------------
hero_x          dw 0
hero_y          dw 0
hero_g          db 0
hero_state      db HST_FALL
hero_fall       dw 0
hero_v          dw FALL_V0      ; ταχύτητα πτώσης, 8.8
hero_facc       db 0            ; κλάσμα pixel που μεταφέρεται στο επόμενο frame
hero_energy     db ENERGY_MAX
hero_prev       db 0            ; κελί στήριξης του προηγούμενου frame
hero_keys       ds ATTR_MAX     ; ΕΝΑΣ μετρητής ανά ταυτότητα κλειδιού
hero_face       db 1            ; τελευταία φορά βάδισης
hero_carry      db 0            ; κουβαλάει κιβώτιο
world_g         db 0            ; η φορά που ΟΡΙΣΕ ο παίκτης (τα κιβώτια)
crates_on       db 0            ; 0 μέχρι την πρώτη αλλαγή φοράς
hero_warp       db 0            ; έγινε τηλεμεταφορά αυτό το frame
hero_para       db 0            ; κουβαλάει αλεξίπτωτο
hero_paraopen   db 0            ; ανοιγμένο αυτή τη στιγμή
hero_won        db 0
h_cell          db 0

h_d             db 0            ; κατεύθυνση βάδισης αυτού του frame
hero_run        db 0            ; κρατημένο SHIFT
walk_acc        db 0            ; κλάσμα pixel βάδισης
h_td            db 1            ; κατεύθυνση για τη μέτρηση κλίσης
h_sd            db 1            ; πρόσημο για το h_stepr
h_sgn           db 1
h_steps         db 0
h_newg          db 0
h_cnt           db 0
h_ga            db 0
h_pa            db 0
h_pb            db 0
h_pd            dw 0
h_tmp           db 0
h_cx            dw 0
h_cy            dw 0
h_nr            dw 0
h_ng            dw 0
h_ox            dw 0
h_oy            dw 0
h_og            db 0
