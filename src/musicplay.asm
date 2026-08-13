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
;  loop is anywhere between two and seven vsyncs.
;
;  WHY THE LEAD GOES QUIET IN THE GAME. The AY has three channels and the
;  sound effects want all three (src/sfx.asm: actions, movement, ambience).
;  Sharing them with music has exactly one honest solution, because the wrong
;  one is tempting: an effect COULD set the queue's flush bit and be heard at
;  once, but flushing throws away the music notes already queued on that
;  channel while the player has already counted them as played — so that
;  channel would run ahead of the other two, permanently, a little more with
;  every footstep. Instead the lead is dropped while a room is being played:
;  bass and drums keep the groove, channel B belongs to the effects, and
;  nothing drifts. The menu plays all three, and that is safe for a reason
;  worth writing down: menu_show clears ml_dir, so the demo hero walks without
;  footstep effects, and the bare arena has nothing else to make a sound. A Z80
;  run of the whole menu loop makes exactly zero calls to sfx_play. Put anything
;  audible in the menu and the lead will start slipping behind the other two.
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
; όλο το επιχείρημα της τράπεζας είναι ότι τα δεδομένα ΔΕΝ ζουν εδώ κάτω.
MUS_BUFN        equ  4
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
MUS_LEAD        equ  1          ; ο δείκτης του καναλιού που σιωπά στο παιχνίδι

;---------------------------------------------------------------------
; music_start — από την αρχή του κομματιού, και οι τρεις φωνές μαζί
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL, IX
;---------------------------------------------------------------------
music_start:    call SOUND_RESET
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
; music_game / music_full — ποιες φωνές παίζουν
;
;   music_game: μπάσο και τύμπανα· το κανάλι B μένει στα εφέ (δες την κεφαλίδα)
;   music_full: και οι τρεις — το μενού και τα τέλη, όπου δεν παίζουν εφέ
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
mus_ch:         ld   a,(mus_quiet)      ; παίζει αυτή η φωνή τώρα;
                or   a
                jr   z,mus_go
                ld   a,c
                cp   MUS_LEAD
                jr   z,mus_next         ; στο παιχνίδι το B ανήκει στα εφέ

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
; mus_note — μία νότα του καναλιού IX, γεμίζοντας πρώτα από την τράπεζα
; IN:  IX = κατάσταση καναλιού, IY = (offset, μήκος) του κομματιού
; OUT: CF=1 μπήκε στην ουρά, CF=0 η ουρά είναι γεμάτη
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
mus_note:       ld   a,(ix+CH_LEFT)
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
                or   a
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

                ld   a,(ix+CH_TAKE)     ; πέρασε: προχώρα την τριάδα
                add  a,3
                ld   (ix+CH_TAKE),a
                dec  (ix+CH_LEFT)
                scf
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
mus_quiet       db  0           ; 1 = το κανάλι B ανήκει στα εφέ
