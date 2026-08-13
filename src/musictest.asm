;=====================================================================
;  GRAVASSIST — MUSIC.BIN: the Boss Time theme, on its own
;
;  A standalone binary so the music can be heard before it goes anywhere
;  near the game. RUN"MUSIC" from BASIC; any key stops it.
;
;  IT PLAYS OUT OF THE UPPER BANK, which is the point: this is the same
;  arrangement the game would use, so if it works here it works there. The
;  data is copied into block 4 at startup and then STREAMED back a few notes
;  at a time — it is never all in main memory at once.
;
;  ORG #8000, AND THAT IS NOT A PREFERENCE. Banks page into #4000..#7FFF. A
;  player living there would page itself out on the first note. Everything
;  that runs while the window is open must sit above it — here the whole
;  program does, which is why this file needs no separate stub.
;
;  Only the firmware jumpblock (#B800+) and the screen are touched otherwise,
;  so this cannot disturb the game's build in any way.
;=====================================================================

                org  #8000

SOUND_QUEUE     equ  #BCAA      ; HL = block; CF=1 queued, CF=0 queue full
SOUND_RESET     equ  #BCA7
KM_READ_CHAR    equ  #BB09      ; CF=1 and A = key, if one is waiting
TXT_OUTPUT      equ  #BB5A
SCR_SET_MODE    equ  #BC0E

; Gate array: A15=0, A14=1. `out (c),c` with B=#7F writes the byte that is
; also the low half of the port — exactly what the 6128 ROM itself does.
GA_PORT_HI      equ  #7F
ORG_BASE        equ  #C0
ORG_BANK0       equ  #C4        ; block 4 at #4000..#7FFF
BANK_WIN        equ  #4000

; How many notes are held in main memory per channel. Small on purpose: the
; whole argument for the bank is that the data does NOT live down here.
BUF_NOTES       equ  10
BUF_BYTES       equ  BUF_NOTES*3

start:          ld   a,1
                call SCR_SET_MODE
                ld   hl,msg_play
                call puts

                call bank_probe
                ld   a,(bank_ok)
                or   a
                jr   nz,mt_have
                ld   hl,msg_no64
                call puts
                jp   mt_wait            ; 64K machine: say so, do not pretend

mt_have:        call bank_load          ; the three tracks into block 4
                call SOUND_RESET
                call chan_init

mt_loop:        call chan_step
                call KM_READ_CHAR
                jr   nc,mt_loop
                call SOUND_RESET
mt_wait:        ld   hl,msg_done
                call puts
                ret

;---------------------------------------------------------------------
; bank_probe — are there really second 64 KB?
;
;   Writes a marker through the window, switches away, writes a different one
;   at the same address, switches back and compares. On a 64K machine the OUT
;   is ignored, both writes land in the same byte, and the marker is gone.
;   The byte belongs to this program, so it is put back either way.
;
; OUT: bank_ok = 1 if the banks answer
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
bank_probe:     xor  a
                ld   (bank_ok),a
                di
                ld   hl,BANK_WIN
                ld   d,(hl)             ; whatever is there now
                ld   bc,GA_PORT_HI*256+ORG_BANK0
                out  (c),c
                ld   (hl),#A5
                ld   bc,GA_PORT_HI*256+ORG_BASE
                out  (c),c
                ld   (hl),#5A
                ld   bc,GA_PORT_HI*256+ORG_BANK0
                out  (c),c
                ld   e,(hl)
                ld   bc,GA_PORT_HI*256+ORG_BASE
                out  (c),c
                ld   (hl),d
                ei
                ld   a,e
                cp   #A5
                ret  nz
                ld   a,1
                ld   (bank_ok),a
                ret

;---------------------------------------------------------------------
; bank_put / bank_get — the only two routines that open the window
;
;   ONLY LDIR RUNS WITH THE WINDOW OPEN. No call, no jump into #4000..#7FFF,
;   no firmware. DI around it because the sound queue is serviced on the
;   interrupt and we hand the firmware nothing while the map is unusual.
;
; IN:  HL = source, DE = destination, BC = count
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
bank_put:                               ; main memory -> bank
bank_get:                               ; bank -> main memory (same code)
                di
                push bc
                ld   bc,GA_PORT_HI*256+ORG_BANK0
                out  (c),c
                pop  bc
                ldir
                ld   bc,GA_PORT_HI*256+ORG_BASE
                out  (c),c
                ei
                ret

;---------------------------------------------------------------------
; bank_load — the three tracks into block 4, one after another
;
;   Their addresses inside the bank are recorded in chan_src, so the player
;   never needs to know where anything ended up.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
bank_load:      ld   ix,boss_tab
                ld   iy,chan_src
                ld   hl,BANK_WIN
                ld   (bl_dst),hl
                ld   b,BOSS_TRACKS
bl_lp:          push bc
                ld   l,(ix+0)           ; where the track is in main memory
                ld   h,(ix+1)
                ld   c,(ix+2)           ; and how long it is
                ld   b,(ix+3)
                ld   de,(bl_dst)
                ld   (iy+0),e           ; remember the bank address…
                ld   (iy+1),d
                ld   (iy+2),c           ; …and the length, for the wrap
                ld   (iy+3),b
                push bc
                push de
                call bank_put
                pop  de
                pop  bc
                ex   de,hl              ; next track starts after this one
                add  hl,bc
                ld   (bl_dst),hl
                ld   de,4
                add  ix,de
                push iy
                pop  hl
                add  hl,de
                push hl
                pop  iy
                pop  bc
                djnz bl_lp
                ret

bl_dst          dw   0

;---------------------------------------------------------------------
; chan_init — every channel at the start of its track, buffers empty
;---------------------------------------------------------------------
chan_init:      ld   ix,chan
                ld   b,BOSS_TRACKS
                ld   c,0
ci_lp:          ld   (ix+CH_POS),0      ; offset into the track
                ld   (ix+CH_POS+1),0
                ld   (ix+CH_LEFT),0     ; nothing buffered yet
                ld   a,c
                inc  a
                ld   (ix+CH_MASK),a     ; channels 1, 2, 4 — bit per channel
                cp   3
                jr   nz,ci_ok
                ld   (ix+CH_MASK),4
ci_ok:          ld   c,a
                ld   de,CH_SIZE
                add  ix,de
                djnz ci_lp
                ret

;---------------------------------------------------------------------
; chan_step — push notes at every channel until its queue says no
;
;   FILL, DO NOT DRIP. The firmware queue empties in real time while this
;   loop runs at whatever speed it happens to run at; one note per pass makes
;   the rhythm follow our loop instead of the clock.
; ΑΛΛΟΙΩΝΕΙ: τα πάντα
;---------------------------------------------------------------------
chan_step:      ld   ix,chan
                ld   iy,chan_src
                ld   b,BOSS_TRACKS
cs_lp:          push bc
                ld   b,BUF_NOTES        ; ceiling, not a target
cs_one:         push bc
                call chan_note
                pop  bc
                jr   nc,cs_next         ; queue full: leave it alone
                djnz cs_one
cs_next:        ld   de,CH_SIZE
                add  ix,de
                ld   de,4
                push iy
                pop  hl
                add  hl,de
                push hl
                pop  iy
                pop  bc
                djnz cs_lp
                ret

;---------------------------------------------------------------------
; chan_note — one note of the channel at IX, refilling from the bank first
; OUT: CF=1 queued, CF=0 the firmware queue is full
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
chan_note:      ld   a,(ix+CH_LEFT)
                or   a
                call z,chan_fill        ; buffer empty: fetch the next few

                push ix                 ; IX+CH_BUF is where the notes are
                pop  hl
                ld   de,CH_BUF
                add  hl,de
                ld   a,(ix+CH_TAKE)
                ld   e,a
                ld   d,0
                add  hl,de              ; HL -> the next triple

                ld   a,(hl)             ; note index; 0 = rest
                inc  hl
                ld   c,(hl)             ; volume
                inc  hl
                ld   b,(hl)             ; duration
                or   a
                jr   z,cn_rest

                dec  a                  ; 1..N -> position in the table
                add  a,a
                ld   l,a
                ld   h,0
                ld   de,boss_notes
                add  hl,de
                ld   a,(hl)
                ld   (snd_tone),a
                inc  hl
                ld   a,(hl)
                ld   (snd_tone+1),a
                xor  a
                ld   (snd_noise),a
                ; A drum is a noise index dressed as a very low note: the kick
                ; is a tone, the snare is noise. One channel, both sounds.
                jr   cn_emit
cn_rest:        xor  a
                ld   (snd_tone),a
                ld   (snd_tone+1),a
                ld   (snd_noise),a
cn_emit:        ld   a,c
                ld   (snd_vol),a
                ld   a,b
                ld   (snd_dur),a
                xor  a
                ld   (snd_dur+1),a
                ld   a,(ix+CH_MASK)
                ld   (snd_block),a
                ld   hl,snd_block
                call SOUND_QUEUE
                ret  nc                 ; full: the note stays for next time

                ld   a,(ix+CH_TAKE)     ; consumed: step over the triple
                add  a,3
                ld   (ix+CH_TAKE),a
                dec  (ix+CH_LEFT)
                scf
                ret

;---------------------------------------------------------------------
; chan_fill — the next BUF_NOTES notes out of the bank
;
;   Wraps at the end of the track, so the loop is seamless without anyone
;   having to write a terminator into the data.
; ΑΛΛΟΙΩΝΕΙ: AF, BC, DE, HL
;---------------------------------------------------------------------
chan_fill:      ld   l,(iy+0)           ; bank address of this track
                ld   h,(iy+1)
                ld   e,(ix+CH_POS)
                ld   d,(ix+CH_POS+1)
                add  hl,de              ; HL = where we are, inside the window

                ld   c,(iy+2)           ; how many bytes are left in the track
                ld   b,(iy+3)
                push hl
                ex   de,hl
                ld   l,c
                ld   h,b
                ld   e,(ix+CH_POS)
                ld   d,(ix+CH_POS+1)
                or   a
                sbc  hl,de              ; HL = remaining
                pop  de
                ex   de,hl              ; HL = source, DE = remaining

                ld   bc,BUF_BYTES       ; take a bufferful, or the rest
                ld   a,d
                or   a
                jr   nz,cf_full
                ld   a,e
                cp   BUF_BYTES
                jr   nc,cf_full
                ld   c,e
                ld   b,0
cf_full:        push bc
                push ix
                pop  de
                ld   a,CH_BUF
                add  a,e
                ld   e,a
                ld   a,0
                adc  a,d
                ld   d,a                ; DE -> the channel's buffer
                call bank_get
                pop  bc

                ld   a,c                ; notes fetched = bytes / 3
                ld   e,3
                call div_e
                ld   (ix+CH_LEFT),a
                ld   (ix+CH_TAKE),0

                ld   e,(ix+CH_POS)      ; advance, wrapping at the end
                ld   d,(ix+CH_POS+1)
                ld   l,c
                ld   h,0
                add  hl,de
                ld   e,(iy+2)
                ld   d,(iy+3)
                or   a
                sbc  hl,de
                jr   c,cf_keep          ; still inside the track
                ld   hl,0               ; reached the end: back to the start
                jr   cf_save
cf_keep:        add  hl,de
cf_save:        ld   (ix+CH_POS),l
                ld   (ix+CH_POS+1),h
                ret

; div_e — A = A / E, for small positive values
div_e:          ld   b,0
de_lp:          sub  e
                jr   c,de_done
                inc  b
                jr   de_lp
de_done:        ld   a,b
                ret

;---------------------------------------------------------------------
; puts — a zero terminated string through the firmware
;---------------------------------------------------------------------
puts:           ld   a,(hl)
                or   a
                ret  z
                push hl
                call TXT_OUTPUT
                pop  hl
                inc  hl
                jr   puts

msg_play:       db   "BOSS TIME - from the upper bank", 13, 10
                db   "any key to stop", 13, 10, 0
msg_no64:       db   "no second 64K on this machine", 13, 10, 0
msg_done:       db   13, 10, "stopped", 13, 10, 0

; --- channel state ---------------------------------------------------
CH_POS          equ  0          ; offset reached inside the track (dw)
CH_LEFT         equ  2          ; notes still in the buffer
CH_TAKE         equ  3          ; byte offset of the next one
CH_MASK         equ  4          ; which AY channel
CH_BUF          equ  5
CH_SIZE         equ  CH_BUF+BUF_BYTES

bank_ok         db   0          ; 1 = the banks answered
chan            ds   CH_SIZE*3
chan_src        ds   4*3        ; bank address + length, per track

; The 9 byte block the firmware SOUND QUEUE wants.
snd_block:      db   0          ; channel and flags
                db   0          ; volume envelope - unused
                db   0          ; tone envelope - unused
snd_tone:       dw   0
snd_noise:      db   0
snd_vol:        db   0
snd_dur:        dw   0

                include "music_boss.asm"

prog_end
                save 'build/music.bin', #8000, prog_end-#8000
