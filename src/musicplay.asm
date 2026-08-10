;=====================================================================
;  GRAVASSIST — αναπαραγωγή μουσικής μέσω του firmware
;
;  Το SOUND QUEUE του firmware κρατά μερικές νότες ανά κανάλι και τις παίζει
;  στη σειρά με τη δική του διακοπή. Δεν χρειάζεται δικός μας χρονισμός: κάθε
;  frame προσπαθούμε να βάλουμε ΜΙΑ νότα ανά κανάλι· όταν η ουρά γεμίσει, η
;  κλήση αποτυγχάνει και ξαναδοκιμάζουμε το επόμενο frame. Η ουρά αδειάζει με
;  τον ρυθμό της μουσικής, άρα η μουσική παίζει με τον ρυθμό της — και δεν
;  κολλάει με τα frames, που είναι 50 Hz ενώ οι διάρκειες μετριούνται σε
;  εκατοστά του δευτερολέπτου.
;
;  Τα δεδομένα (src/music.asm) είναι 3 bytes ανά νότα και το μπλοκ των 9 bytes
;  που θέλει το firmware χτίζεται εδώ. Ολόκληρα μπλοκ στη μνήμη θα κόστιζαν
;  τριπλάσια, και ο χώρος αφαιρείται από τις αίθουσες.
;=====================================================================

SOUND_QUEUE     equ  #BCAA      ; HL = μπλοκ· CF=1 μπήκε, CF=0 γεμάτη ουρά
SOUND_RESET     equ  #BCA7      ; αδειάζει ΟΛΕΣ τις ουρές και σταματά τον ήχο

;---------------------------------------------------------------------
; music_start — ξεκινά τη μουσική του μενού από την αρχή
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
music_start:    call SOUND_RESET
                ld   hl,mus_bass
                ld   (mus_p_bass),hl
                ld   hl,mus_lead
                ld   (mus_p_lead),hl
                ld   hl,mus_pulse
                ld   (mus_p_pulse),hl
                ret

;---------------------------------------------------------------------
; music_stop — σιωπή· καλείται φεύγοντας από το μενού
;---------------------------------------------------------------------
music_stop:     jp   SOUND_RESET

;---------------------------------------------------------------------
; music_step — μία προσπάθεια ανά κανάλι· καλείται μία φορά ανά frame
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
music_step:     ld   hl,mus_p_bass
                ld   a,MUS_BASS_CH
                ld   (snd_chan),a
                ld   a,MUS_BASS_NZ
                ld   (snd_noise),a
                ld   de,mus_bass
                call mus_one

                ld   hl,mus_p_lead
                ld   a,MUS_LEAD_CH
                ld   (snd_chan),a
                ld   a,MUS_LEAD_NZ
                ld   (snd_noise),a
                ld   de,mus_lead
                call mus_one

                ld   hl,mus_p_pulse
                ld   a,MUS_PULSE_CH
                ld   (snd_chan),a
                ld   a,MUS_PULSE_NZ
                ld   (snd_noise),a
                ld   de,mus_pulse
                ; πέφτει μέσα

;---------------------------------------------------------------------
; mus_one — μία νότα ενός καναλιού
; IN: HL = δείκτης κατάστασης (dw), DE = αρχή της ροής,
;     (snd_chan), (snd_noise) = ρυθμισμένα
;---------------------------------------------------------------------
mus_one:        ld   (mus_st),hl
                ld   (mus_base),de
                ld   a,(hl)
                inc  hl
                ld   h,(hl)
                ld   l,a                ; HL = τρέχουσα νότα

                ld   a,(hl)             ; #FF = τέλος του κύκλου
                cp   #FF
                jr   nz,mo_have
                ld   hl,(mus_base)      ; ξανά από την αρχή
mo_have:        ld   (mus_cur),hl

                ; --- χτίσιμο του μπλοκ 9 bytes ---
                ld   a,(hl)             ; δείκτης νότας· 0 = παύση
                inc  hl
                ld   b,(hl)             ; ένταση
                inc  hl
                ld   c,(hl)             ; διάρκεια
                or   a                  ; το A κρατά ακόμα τον δείκτη νότας:
                jr   z,mo_rest          ; τα ld b/c,(hl) δεν το πειράζουν

                dec  a                  ; 1..N -> θέση στον πίνακα περιόδων
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,note_tab
                add  hl,de
                ld   a,(hl)
                ld   (snd_tone),a
                inc  hl
                ld   a,(hl)
                ld   (snd_tone+1),a
                ld   a,(snd_noise)
                ld   (snd_noise2),a
                jr   mo_vol

mo_rest:        xor  a                  ; παύση: χωρίς τόνο και χωρίς θόρυβο
                ld   (snd_tone),a
                ld   (snd_tone+1),a
                ld   (snd_noise2),a

mo_vol:         ld   a,b
                ld   (snd_vol),a
                ld   a,c
                ld   (snd_dur),a
                xor  a
                ld   (snd_dur+1),a
                ld   a,(snd_chan)
                ld   (snd_block),a

                ld   hl,snd_block
                call SOUND_QUEUE
                ret  nc                 ; γεμάτη ουρά: ξαναδοκίμασε το επόμενο

                ld   hl,(mus_cur)       ; προχώρα τρία bytes
                inc  hl
                inc  hl
                inc  hl
                ex   de,hl
                ld   hl,(mus_st)
                ld   (hl),e
                inc  hl
                ld   (hl),d
                ret

; Το μπλοκ που θέλει το SOUND QUEUE. Ξαναγράφεται σε κάθε νότα.
snd_block:      db  0           ; κανάλι (bit 0-2) + σημαίες
                db  0           ; envelope έντασης — δεν χρησιμοποιούμε
                db  0           ; envelope τόνου
snd_tone:       dw  0           ; περίοδος τόνου
snd_noise2:     db  0           ; περίοδος θορύβου  (snd_block+5)
snd_vol:        db  0
snd_dur:        dw  0

snd_chan        db  0
snd_noise       db  0
mus_st          dw  0
mus_base        dw  0
mus_cur         dw  0

mus_p_bass      dw  0
mus_p_lead      dw  0
mus_p_pulse     dw  0
