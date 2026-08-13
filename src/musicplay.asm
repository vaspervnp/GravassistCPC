;=====================================================================
;  GRAVASSIST — music, streamed out of the upper RAM bank
;
;  The tune is a minute long and about four and a half kilobytes. The game has
;  a hundred bytes of main memory free, so the notes are NOT in main memory:
;  they sit in RAM block 7, put there at boot from build/TUNEnn.BIN, and this
;  reads them back a few at a time. What lives down here is the note table
;  (forty bytes, needed on every note) and four notes per channel.
;
;  THE FIRMWARE DOES THE TIMING. SOUND QUEUE holds a few notes per channel and
;  plays them on its own interrupt, so nothing here counts frames: every call
;  pushes notes until the queue says no. That is why the music does not slow
;  down when the game does — durations are hundredths of a second and the game
;  loop is anywhere between three and seven vsyncs.
;
;  THE LEAD KEEPS ITS PLACE BY THE CLOCK, not by where it left off. The AY has
;  three channels and the sound effects want all three (src/sfx.asm: actions,
;  movement, ambience), so in a room they all share channel B with the lead and
;  an effect flushes it to be heard at once. Flushing throws away lead notes the
;  player has already read out of the bank — and that is fine, because mus_lead
;  does not resume from its own state. It compares its position against the
;  firmware clock, drops every note that should already have finished, and
;  queues the one that belongs now. So an effect ducks the lead for as long as
;  it lasts and the lead comes back in step with bass and drums, with an error
;  that cannot accumulate because nothing is measured from the previous error.
;
;  The menu and the endings have no effects at all (tools/test_music.py proves
;  it), so there the three voices simply play.
;
;=====================================================================

SOUND_QUEUE     equ  #BCAA      ; HL = μπλοκ· CF=1 μπήκε, CF=0 γεμάτη ουρά
SOUND_RESET     equ  #BCA7      ; αδειάζει ΟΛΕΣ τις ουρές και σταματά τον ήχο

; Τα CAS_IN_* τα ορίζει ήδη το src/roomfile.asm — το rasm δεν δέχεται δεύτερο
; ορισμό, και ούτε πρέπει: μία διεύθυνση, ένα όνομα.

; Το κομμάτι ζει ΜΟΝΟ του στο τελευταίο μπλοκ, από την αρχή του παραθύρου. Το
; tools/roomfile.py κρατά τα σετ αιθουσών έξω από αυτό το μπλοκ (SETS_USABLE).
TUNE_ORG        equ  #C7        ; οργάνωση για το μπλοκ 7
TUNE_BASE       equ  #4000      ; πού φαίνεται μέσα στο παράθυρο

; Πόσες νότες ανά κανάλι κρατάμε στη βασική μνήμη. Μικρός αριθμός επίτηδες:
; όλο το επιχείρημα της τράπεζας είναι ότι τα δεδομένα ΔΕΝ ζουν εδώ κάτω. Ήταν
; 4· έγινε 2 για να πληρωθεί ο διακόπτης S, και δεν χάνεται τίποτα — η ουρά του
; firmware είναι τεσσάρων θέσεων και το κομμάτι θέλει οκτώ νότες το δευτερόλεπτο
; ανά κανάλι, ενώ ο βρόχος περνά από εδώ δώδεκα φορές. Το μόνο που αλλάζει είναι
; ότι το mus_fill τρέχει διπλάσιες φορές, αντιγράφοντας 6 bytes αντί για 12.
MUS_BUFN        equ  2
MUS_BUFB        equ  MUS_BUFN*3

; --- κατάσταση καναλιού ----------------------------------------------
; ΤΟ CH_BUF ΕΙΝΑΙ ΠΡΟΟΡΙΣΜΟΣ ΤΟΥ bank_copy, άρα ΟΛΗ η δομή πρέπει να ζει έξω
; από το #4000..#7FFF — δηλώνεται στο τέλος του main.asm, πάνω από το #8000,
; μαζί με τους άλλους buffers. Αν ζούσε εδώ, το LDIR θα έγραφε μέσα στην ίδια
; την τράπεζα από την οποία διαβάζει.
CH_POS          equ  0          ; dw: πού φτάσαμε μέσα στο κομμάτι
CH_LEFT         equ  2          ; νότες που μένουν στον buffer
CH_TAKE         equ  3          ; offset της επόμενης, σε bytes
CH_MASK         equ  4          ; ποιο κανάλι του AY (1, 2, 4)
CH_BUF          equ  5
CH_SIZE         equ  CH_BUF+MUS_BUFB

MUS_TRACKS      equ  3
MUS_LEADCH        equ  1          ; ο δείκτης του καναλιού που σιωπά στο παιχνίδι

;---------------------------------------------------------------------
; music_start — από την αρχή του κομματιού, και οι τρεις φωνές μαζί
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL, IX
;---------------------------------------------------------------------
music_start:    call SOUND_RESET
                call KL_TIME_PLEASE     ; από πού μετράει ο χρόνος του κομματιού
                ld   (tune_t0),hl
                ld   hl,0
                ld   (lead_pos),hl
                ld   ix,mus_chan
                ld   b,MUS_TRACKS
                ld   c,1                ; μάσκες καναλιών AY: 1, 2, 4
ms_init:        ld   (ix+CH_POS),0
                ld   (ix+CH_POS+1),0
                ld   (ix+CH_LEFT),0
                ld   (ix+CH_TAKE),0
                ld   (ix+CH_MASK),c
                sla  c
                ld   de,CH_SIZE
                add  ix,de
                djnz ms_init
                ret

;---------------------------------------------------------------------
; music_stop — σιωπή· και σβήνει ΚΑΙ τα εφέ, γι' αυτό δεν καλείται συχνά
;---------------------------------------------------------------------
music_stop:     jp   SOUND_RESET

;---------------------------------------------------------------------
; music_game / music_full — αν το κανάλι B το μοιράζεται με τα εφέ
;
;   ΔΕΝ ΑΛΛΑΖΟΥΝ ΦΩΝΕΣ ΠΙΑ: και οι τρεις παίζουν πάντα. Το μόνο που ορίζουν
;   είναι πού πηγαίνουν τα ηχητικά εφέ (sfx_chan του src/sfx.asm).
;
;   music_game: μέσα σε δωμάτιο — τα εφέ μαζεύονται στο B, πάνω στο lead, και
;               το αδειάζουν για να ακουστούν αμέσως· το mus_lead ξαναβρίσκει
;               τη θέση του από το ρολόι
;   music_full: μενού και τέλη — δεν παίζουν εφέ εκεί, οπότε το καθένα κρατά
;               το δικό του κανάλι αν ποτέ προστεθεί κάποιο
;---------------------------------------------------------------------
music_game:     ld   a,1
                jr   mg_set
music_full:     xor  a
mg_set:         ld   (mus_quiet),a
                ret

;---------------------------------------------------------------------
; music_toggle — η επιλογή M του μενού
; OUT: A = η νέα κατάσταση (0 = σιωπή)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IY
;---------------------------------------------------------------------
music_toggle:   ld   a,(music_on)
                xor  1
                ld   (music_on),a
                or   a
                jr   nz,mt_on
                call music_stop         ; σιωπή ΤΩΡΑ, όχι στην επόμενη νότα
                xor  a
                ret
mt_on:          call music_start
                ld   a,1
                ret

;---------------------------------------------------------------------
; music_step — σπρώχνει νότες σε κάθε κανάλι μέχρι να γεμίσει η ουρά
;
;   ΓΕΜΙΖΕΙ, ΔΕΝ ΣΤΑΖΕΙ. Η ουρά του firmware αδειάζει σε πραγματικό χρόνο ενώ
;   αυτός ο βρόχος τρέχει με όποιον ρυθμό τύχει· μία νότα ανά πέρασμα θα έκανε
;   τον ρυθμό να ακολουθεί τον βρόχο αντί για το ρολόι.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
music_step:     ld   a,(music_on)
                or   a
                ret  z
                ld   a,(tune_ok)
                or   a
                ret  z                  ; δεν φορτώθηκε: καμία προσποίηση

                ld   ix,mus_chan
                ld   iy,mus_tab
                ld   c,0                ; δείκτης καναλιού
mus_ch:         ld   a,c
                cp   MUS_LEADCH
                jr   nz,mus_go
                push bc                 ; το C είναι ο δείκτης καναλιού
                call mus_lead           ; χρονισμένο, όχι απλώς «γέμισε»
                pop  bc
                jr   mus_next

mus_go:         ld   b,MUS_BUFN         ; οροφή, όχι στόχος
mus_one:        push bc
                call mus_note
                pop  bc
                jr   nc,mus_next        ; γεμάτη ουρά: άσ' την ήσυχη
                djnz mus_one

mus_next:       ld   de,CH_SIZE
                add  ix,de
                ld   de,4
                push iy
                pop  hl
                add  hl,de
                push hl
                pop  iy
                inc  c
                ld   a,c
                cp   MUS_TRACKS
                jr   c,mus_ch
                ret

;---------------------------------------------------------------------
; mus_lead — το κανάλι B, οδηγημένο από το ρολόι και όχι από την ουρά
;
;   ΜΙΑ ΣΤΑΘΕΡΗ ΣΥΝΘΗΚΗ, ΚΑΙ ΤΙΠΟΤΑ ΑΛΛΟ: η θέση του lead μέσα στο κομμάτι
;   πρέπει να ισούται με τον χρόνο που πέρασε από την αρχή του. Από αυτό
;   προκύπτουν και τα δύο που χρειάζονται:
;
;     - Νότα που τελειώνει ΠΡΙΝ από το τώρα δεν παίζεται· καταναλώνεται και
;       χάνεται. Έτσι το lead «συνεχίζει από εκεί που θα ήταν», όχι από εκεί
;       που το άφησε το εφέ.
;     - Νότα πιο μπροστά από το παράθυρο MUS_LOOK δεν μπαίνει ακόμα, ώστε η
;       ουρά να μένει ρηχή και ένα εφέ να μη θάβει πολλή μουσική.
;
;   ΓΙ' ΑΥΤΟ ΤΟ ΑΔΕΙΑΣΜΑ ΤΗΣ ΟΥΡΑΣ ΔΕΝ ΧΡΕΙΑΖΕΤΑΙ ΚΑΜΙΑ ΛΟΓΙΣΤΙΚΗ. Το εφέ
;   πετάει ό,τι είχε μπει· ο επόμενος γεμισμός βλέπει ότι η θέση έμεινε πίσω
;   από το ρολόι, προσπερνά τις νότες που πέρασαν και ξαναπιάνει το μπάσο και
;   τα τύμπανα ακριβώς εκεί που πρέπει. Το σφάλμα δεν συσσωρεύεται επειδή δεν
;   μετριέται από την προηγούμενη κατάσταση αλλά από το ίδιο το ρολόι.
;
; IN:  IX = κατάσταση καναλιού, IY = (offset, μήκος)
; ΑΛΛΟΙΩΝΕΙ: τα πάντα εκτός IX, IY
;---------------------------------------------------------------------
MUS_LOOK        equ  120        ; 0,4 s σε 1/300 — ένα πέρασμα του βρόχου είναι
                                ; το πολύ 7 vsync (CPC_VSYNC_RUN), οπότε η ουρά
                                ; δεν στεγνώνει ούτε τρέχοντας

                ; ΤΥΛΙΓΜΑ ΤΟΥ ΚΥΚΛΟΥ, ΚΑΙ ΜΟΝΟ ΟΤΑΝ ΤΟ ΠΕΡΑΣΑΝ ΚΑΙ ΤΑ ΔΥΟ.
                ; Η θέση τρέχει μπροστά από το ρολόι κατά το παράθυρο MUS_LOOK,
                ; οπότε φτάνει πρώτη στο τέλος του κομματιού. Τυλίγοντας με βάση
                ; μόνο αυτήν, το tune_t0 προσπερνούσε το ρολόι και το «τώρα μείον
                ; t0» έβγαινε αρνητικό — δηλαδή, ανυπόγραφο, γύρω στις 65500. Το
                ; lead νόμιζε ότι είχε μείνει ένα ολόκληρο λεπτό πίσω και πετούσε
                ; τέσσερις νότες ανά πέρασμα ώσπου να ξαναπρολάβει: οκτώ χαμένες
                ; εγγραφές στη ραφή, μία φορά ανά κύκλο. Και τα δύο μεγέθη έχουν
                ; άφθονο περιθώριο πάνω από το TUNE_TICKS, οπότε η αναμονή είναι
                ; δωρεάν.
mus_lead:       ld   hl,(lead_pos)
                ld   de,TUNE_TICKS
                or   a
                sbc  hl,de
                jr   c,mld_wrapok       ; η θέση δεν έφτασε ακόμα στο τέλος
                push hl                 ; = lead_pos - TUNE_TICKS
                call KL_TIME_PLEASE
                ld   de,(tune_t0)
                or   a
                sbc  hl,de
                ld   de,TUNE_TICKS
                or   a
                sbc  hl,de
                pop  de                 ; DE = η νέα θέση
                jr   c,mld_wrapok       ; ο χρόνος δεν έφτασε: περίμενε
                ld   (lead_pos),de
                ld   hl,(tune_t0)
                ld   de,TUNE_TICKS
                add  hl,de
                ld   (tune_t0),hl

mld_wrapok:     call KL_TIME_PLEASE     ; HL = χαμηλή λέξη του μετρητή 1/300
                ld   de,(tune_t0)
                or   a
                sbc  hl,de
                jr   nc,mld_nowok
                ld   hl,0               ; ΠΟΤΕ αρνητικό: ένα «τώρα» πριν από την
mld_nowok:      ld   (mld_now),hl       ; αρχή θα σάρωνε το μισό κομμάτι
                ld   a,MUS_BUFN+2       ; οροφή περασμάτων, όχι στόχος
                ld   (mld_cnt),a

mld_lp:          call mus_fetch          ; A = δείκτης, C = ένταση, B = διάρκεια
                ld   (mld_idx),a
                ld   (mld_vol),bc        ; C -> mld_vol, B -> mld_dur

                ld   l,b                ; HL = διάρκεια x 3, σε 1/300
                ld   h,0
                ld   d,h
                ld   e,l
                add  hl,hl
                add  hl,de
                ld   de,(lead_pos)
                add  hl,de
                ld   (mld_end),hl        ; πού τελειώνει αυτή η νότα

                ld   de,(mld_now)
                or   a
                sbc  hl,de              ; end - now
                jr   c,mld_past          ; τελείωσε πριν από το τώρα: χάθηκε
                jr   z,mld_past

                ld   hl,(lead_pos)      ; αρχίζει πολύ μπροστά;
                ld   de,(mld_now)
                or   a
                sbc  hl,de
                jr   c,mld_play          ; έχει ήδη αρχίσει: μπαίνει τώρα
                ld   de,MUS_LOOK
                or   a
                sbc  hl,de
                ret  nc                 ; έξω από το παράθυρο: αρκετά για τώρα

mld_play:        ld   a,(mld_idx)
                ld   bc,(mld_vol)
                call mus_emit
                ret  nc                 ; γεμάτη ουρά: ξαναδοκιμάζει αργότερα
                jr   mld_adv

mld_past:        call mus_drop           ; θάφτηκε κάτω από ένα εφέ — σωστά

mld_adv:         ld   hl,(mld_end)
                ld   (lead_pos),hl
                ld   a,(mld_cnt)
                dec  a
                ld   (mld_cnt),a
                jr   nz,mld_lp
                ret

mld_now          dw   0
mld_end          dw   0
mld_idx          db   0
mld_vol          db   0
mld_dur          db   0
mld_cnt          db   0

;---------------------------------------------------------------------
; mus_note — μία νότα του καναλιού IX, γεμίζοντας πρώτα από την τράπεζα
; IN:  IX = κατάσταση καναλιού, IY = (offset, μήκος) του κομματιού
; OUT: CF=1 μπήκε στην ουρά, CF=0 η ουρά είναι γεμάτη
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
mus_note:       call mus_fetch
                ; πέφτει μέσα στο mus_emit

;---------------------------------------------------------------------
; mus_emit — χτίζει το μπλοκ και το δίνει στην ουρά
; IN:  A = δείκτης νότας, C = ένταση, B = διάρκεια, IX = κανάλι
; OUT: CF=1 μπήκε (και η νότα καταναλώθηκε), CF=0 γεμάτη ουρά
;---------------------------------------------------------------------
mus_emit:       or   a
                jr   z,mn_rest

                ; ΚΡΟΥΣΤΑ: δείκτης >= TUNE_NOISE σημαίνει σκέτος θόρυβος, και
                ; το υπόλοιπο είναι η περίοδος θορύβου του AY. Χωρίς αυτόν τον
                ; κλάδο ένα ταμπούρο (206) πέφτει στον δρόμο του τόνου, όπου το
                ; `dec a` και το `add a,a` ξεχειλίζουν τα 8 bit και διαβάζουν
                ; σκουπίδια ως περίοδο — συνεχής θόρυβος.
                cp   TUNE_NOISE
                jr   c,mn_tone
                sub  TUNE_NOISE
                ld   (snd_noise2),a
                xor  a
                ld   (snd_tone),a
                ld   (snd_tone+1),a
                jr   mn_emit

mn_tone:        dec  a                  ; 1..N -> θέση στον πίνακα περιόδων
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,tune_notes
                add  hl,de
                ld   a,(hl)
                ld   (snd_tone),a
                inc  hl
                ld   a,(hl)
                ld   (snd_tone+1),a
                xor  a
                ld   (snd_noise2),a
                jr   mn_emit

mn_rest:        xor  a
                ld   (snd_tone),a
                ld   (snd_tone+1),a
                ld   (snd_noise2),a

mn_emit:        ld   a,c
                ld   (snd_vol),a
                ld   a,b
                ld   (snd_dur),a
                xor  a
                ld   (snd_dur+1),a
                ld   a,(ix+CH_MASK)
                ld   (snd_block),a
                ld   hl,snd_block

                ; ΤΟ SOUND QUEUE ΧΑΛΑΕΙ ΤΟ IX. Το λέει το SOFT968 — «A, BC, DE,
                ; IX and other flags corrupt» — γιατί ο sound manager του
                ; firmware κρατά εκεί το δικό του channel block. Το δικό μας
                ; είναι κι αυτό στο IX και οι τρεις γραμμές μετά την κλήση το
                ; αποαναφοροποιούν. Το `pop` δεν πειράζει σημαίες, οπότε το
                ; `ret nc` βλέπει ακόμα το carry του SOUND QUEUE.
                push ix
                push iy
                call SOUND_QUEUE
                pop  iy
                pop  ix
                ret  nc                 ; γεμάτη: η νότα μένει για την επόμενη
                call mus_drop           ; πέρασε: προχώρα την τριάδα
                scf
                ret

;---------------------------------------------------------------------
; mus_fetch — η επόμενη νότα του καναλιού IX, ΧΩΡΙΣ να καταναλωθεί
; OUT: A = δείκτης, C = ένταση, B = διάρκεια
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
mus_fetch:      ld   a,(ix+CH_LEFT)
                or   a
                call z,mus_fill         ; άδειος buffer: φέρε τις επόμενες
                push ix
                pop  hl
                ld   de,CH_BUF
                add  hl,de
                ld   a,(ix+CH_TAKE)
                ld   e,a
                ld   d,0
                add  hl,de              ; HL -> η επόμενη τριάδα
                ld   a,(hl)             ; δείκτης νότας· 0 = παύση
                inc  hl
                ld   c,(hl)             ; ένταση
                inc  hl
                ld   b,(hl)             ; διάρκεια
                ret

;---------------------------------------------------------------------
; mus_drop — καταναλώνει την τρέχουσα νότα χωρίς να την παίξει
;---------------------------------------------------------------------
mus_drop:       ld   a,(ix+CH_TAKE)
                add  a,3
                ld   (ix+CH_TAKE),a
                dec  (ix+CH_LEFT)
                ret

;---------------------------------------------------------------------
; mus_fill — οι επόμενες MUS_BUFN νότες από την τράπεζα
;
;   Τυλίγει στο τέλος του κομματιού, ώστε ο κύκλος να είναι αδιόρατος χωρίς να
;   χρειάζεται τερματικό μέσα στα δεδομένα.
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
mus_fill:       ld   l,(iy+0)           ; offset του κομματιού μέσα στο blob
                ld   h,(iy+1)
                ld   de,TUNE_BASE
                add  hl,de
                ld   e,(ix+CH_POS)
                ld   d,(ix+CH_POS+1)
                add  hl,de              ; HL = πηγή, μέσα στο παράθυρο
                push hl

                ld   l,(iy+2)           ; πόσα bytes έχει το κομμάτι
                ld   h,(iy+3)
                ld   e,(ix+CH_POS)
                ld   d,(ix+CH_POS+1)
                or   a
                sbc  hl,de              ; HL = όσα μένουν

                ld   bc,MUS_BUFB        ; ένα buffer, ή ό,τι απέμεινε
                ld   a,h
                or   a
                jr   nz,mf_full
                ld   a,l
                cp   MUS_BUFB
                jr   nc,mf_full
                ld   c,l
                ld   b,0
mf_full:        pop  hl
                push bc
                push ix                 ; DE -> ο buffer του καναλιού
                pop  de
                ld   a,CH_BUF
                add  a,e
                ld   e,a
                ld   a,0
                adc  a,d
                ld   d,a
                ld   a,TUNE_ORG
                call bank_copy          ; ΜΟΝΟ εδώ ανοίγει το παράθυρο
                pop  bc

                ld   a,c                ; νότες = bytes / 3
                ld   e,3
                call mus_div
                ld   (ix+CH_LEFT),a
                ld   (ix+CH_TAKE),0

                ld   e,(ix+CH_POS)      ; προχώρα, τυλίγοντας στο τέλος
                ld   d,(ix+CH_POS+1)
                ld   l,c
                ld   h,0
                add  hl,de
                ld   e,(iy+2)
                ld   d,(iy+3)
                or   a
                sbc  hl,de
                jr   c,mf_keep          ; ακόμα μέσα στο κομμάτι
                ld   hl,0               ; έφτασε το τέλος: πάλι από την αρχή
                jr   mf_save
mf_keep:        add  hl,de
mf_save:        ld   (ix+CH_POS),l
                ld   (ix+CH_POS+1),h
                ret

; mus_div — A = A / E, για μικρές θετικές τιμές
mus_div:        ld   b,0
md_lp:          sub  e
                jr   c,md_done
                inc  b
                jr   md_lp
md_done:        ld   a,b
                ret

;---------------------------------------------------------------------
; tune_boot — το κομμάτι από τη δισκέτα στο μπλοκ 7, μία φορά στην εκκίνηση
;
;   Τα TUNEnn.BIN είναι κομμένα στο μέγεθος του set_buf επειδή από εκεί
;   περνάνε: το CAS_IN_DIRECT θέλει προορισμό στη βασική μνήμη και δεν υπάρχει
;   τεσσεράμισι κιλό ελεύθερο πουθενά. Οι θέσεις μέσα σε ένα μπλοκ είναι
;   συνεχόμενες, οπότε τα κομμάτια ξαναγίνονται ένα ενιαίο blob στην τράπεζα.
;
;   Αποτυχία σημαίνει σιωπή, όχι κρασάρισμα: το tune_ok μένει 0 και το
;   music_step γυρίζει αμέσως.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
tune_boot:      ld   b,TUNE_CHUNKS
                ld   hl,TUNE_BASE
                ld   (tb_dst),hl
                ld   a,'1'
                ld   (tune_digit),a
tb_lp:          push bc

                ld   hl,tune_fname
                ld   b,tune_fname_end-tune_fname
                ld   de,cas_buffer
                call CAS_IN_OPEN
                jr   nc,tb_fail
                ld   hl,set_buf
                call CAS_IN_DIRECT
                push af
                call CAS_IN_CLOSE
                pop  af
                jr   nc,tb_fail

                ld   de,(tb_dst)        ; στην τράπεζα, στη σειρά
                ld   a,TUNE_ORG
                ld   hl,set_buf
                ld   bc,TUNE_CHUNK
                call bank_fill
                ld   hl,(tb_dst)
                ld   de,TUNE_CHUNK
                add  hl,de
                ld   (tb_dst),hl

                ld   a,(tune_digit)     ; SMC: το όνομα είναι ΔΕΔΟΜΕΝΑ
                inc  a
                ld   (tune_digit),a
                pop  bc
                djnz tb_lp

                ld   a,1
                ld   (tune_ok),a
                ret

tb_fail:        pop  bc                 ; ένα κομμάτι λείπει -> καμία μουσική
                xor  a
                ld   (tune_ok),a
                ret

tb_dst          dw   0
tune_fname:     db   "TUNE0"
tune_digit:     db   "1"
                db   ".BIN"
tune_fname_end:

; Πού κάθεται κάθε φωνή μέσα στο blob και πόση είναι. Από το tools/genboss.py,
; ώστε ο player να μη γνωρίζει τίποτα για τη διάταξη των δεδομένων.
mus_tab:        dw   TUNE_BASS_OFF,  TUNE_BASS_LEN
                dw   TUNE_LEAD_OFF,  TUNE_LEAD_LEN
                dw   TUNE_DRUMS_OFF, TUNE_DRUMS_LEN

; Το μπλοκ των 9 bytes που θέλει το SOUND QUEUE. Ξαναγράφεται σε κάθε νότα.
snd_block:      db  0           ; κανάλι (bit 0-2) + σημαίες
                db  0           ; envelope έντασης — δεν χρησιμοποιούμε
                db  0           ; envelope τόνου
snd_tone:       dw  0           ; περίοδος τόνου
snd_noise2:     db  0           ; περίοδος θορύβου  (snd_block+5)
snd_vol:        db  0
snd_dur:        dw  0

music_on        db  1           ; η επιλογή M του μενού
tune_ok         db  0           ; 1 = το κομμάτι είναι στην τράπεζα
mus_quiet       db  0           ; 1 = τα εφέ μαζεύονται στο κανάλι B
tune_t0         dw  0           ; ρολόι 1/300 τη στιγμή που ξεκίνησε το κομμάτι
lead_pos        dw  0           ; πόσο κομμάτι έχει καταναλώσει το lead, σε 1/300
