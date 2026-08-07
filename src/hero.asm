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
FALL_V0         equ 256         ; αρχική  1.0 px/frame
FALL_ACCEL      equ 26          ; ~0.10 px/frame^2
FALL_VMAX       equ 1024        ; τερματική 4.0 px/frame

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
                call h_walk
                jr   hu_done
hu_still:       call h_slipping
                jr   c,hu_fall
                ld   a,HST_IDLE
                ld   (hero_state),a
                jr   hu_done
hu_fall:        call h_fall_steps
hu_done:        call h_support
                ld   (hero_prev),a
                ret

;---------------------------------------------------------------------
; h_land — προσγείωση· υπολογίζει ζημιά από το ύψος πτώσης
;---------------------------------------------------------------------
h_land:         ld   a,HST_IDLE
                ld   (hero_state),a
                ld   hl,FALL_V0         ; μηδενισμός ταχύτητας ΠΡΙΝ από τα
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
                jr   z,hfs_acc
                ld   hl,FALL_V0         ; νέα πτώση -> αρχική ταχύτητα
                ld   (hero_v),hl
                xor  a
                ld   (hero_facc),a

hfs_acc:        ld   hl,(hero_v)
                ld   de,FALL_ACCEL
                add  hl,de
                ld   a,h
                cp   FALL_VMAX/256
                jr   c,hfs_cap
                ld   hl,FALL_VMAX       ; τερματική ταχύτητα
hfs_cap:        ld   (hero_v),hl

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

h_d             db 0            ; κατεύθυνση βάδισης αυτού του frame
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
