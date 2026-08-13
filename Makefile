# GRAVASSIST - Amstrad CPC 6128, MODE 1, Z80
# Τα εργαλεία δεν είναι καρφωμένα: ο κατάλογός τους ορίζεται στο
# toolchain.json (δες tools/toolchain.py). Με `?=` κερδίζει πάντα ό,τι δώσεις
# στη γραμμή εντολών ή στο περιβάλλον: `make ASM=/opt/rasm2/rasm`.
PY   ?= $(shell python3 tools/toolchain.py python 2>/dev/null || echo python3)
ASM  ?= $(shell $(PY) tools/toolchain.py rasm 2>/dev/null || echo rasm)
DISK ?= $(shell $(PY) tools/toolchain.py idsk 2>/dev/null || echo iDSK)

SRC   = src/main.asm
# ΟΛΕΣ οι αίθουσες, όχι μόνο μία: το src/rooms.asm τις ενσωματώνει όλες, οπότε
# αν εξαρτιόταν από ένα αρχείο, μια αλλαγή σε άλλη αίθουσα θα περνούσε
# απαρατήρητη και το «Χτίσιμο .dsk» θα έβγαζε δισκέτα με παλιά δεδομένα.
ROOMS = $(wildcard levels/room_*.txt)
DEPS  = src/rotate.asm src/level.asm src/hero.asm src/tables.asm src/rooms.asm \
        src/gamedefs.asm src/roomfile.asm src/menu.asm src/musicplay.asm src/tune.asm \
        src/sfx.asm src/endings.asm
GFX   = src/gfx_hero.asm src/gfx_objects.asm
PNG   = assets/hero.png assets/objects.png
BAS   = src/loader.bas
SPLASH = assets/revive8b.scr
BIN   = build/main.bin
BASD  = build/grav.bas
# Standalone music audition: player + transcribed theme, org #8000 so it can
# page the bank without paging itself out. Nothing here is linked into the
# game — it exists to be heard before the music goes anywhere near it.
MUSBIN  = build/music.bin
MUSBAS  = build/music.bas
DSK   = build/gravassist.dsk
# Ένα ROOMSnn.BIN ανά 40 αίθουσες. Τα ονόματα προκύπτουν από τους αριθμούς
# των αιθουσών, οπότε ρωτάμε το ίδιο εργαλείο που τα γράφει.
SETS  = $(shell $(PY) -c "import sys;sys.path.insert(0,'tools');import roomfile;\
        print(' '.join('build/'+n for _,n,_ in roomfile.all_sets()))" 2>/dev/null)

# Τα δεδομένα του browser χτίζονται ΜΑΖΙ με τη δισκέτα, όχι με το χέρι.
# Ήταν phony στόχος χωρίς προϋποθέσεις, δηλαδή δεν έτρεχε ποτέ μόνος του:
# το data.js έμενε πίσω σιωπηλά και η δοκιμή στον browser έσκαγε με «λείπει
# η τάδε σταθερά» — μία σταθερά τη φορά, όποτε την ακουμπούσε ο κώδικας.
JSDATA = editor/wwwroot/game/data.js
PARITY = editor/wwwroot/game/parity-expected.json

all: $(DSK) $(JSDATA) $(PARITY)

# Τι εργαλεία θα χρησιμοποιηθούν και αν βρίσκονται.
.PHONY: toolchain
toolchain:
	@$(PY) tools/toolchain.py --all
	@echo "  (το Makefile θα τρέξει: ASM=$(ASM)  DISK=$(DISK)  PY=$(PY))"

# Τα sprites παράγονται από τα PNG — το PNG είναι η αυθεντία (docs/sprites.md)
$(GFX): $(PNG) tools/sprites.py tools/cpcgfx.py tools/stickman.py tools/placeholders.py
	$(PY) tools/sprites.py build

# Πίνακες γεωμετρίας + δωμάτιο: παράγονται από το ΙΔΙΟ μοντέλο με την
# προσομοίωση, ώστε Z80 και Python να μην μπορούν να αποκλίνουν αριθμητικά.
# ΚΑΙ ΤΟ roomfile.py: το gamedefs.asm ενσωματώνει το SET_ROOMS του, οπότε
# χωρίς αυτή την εξάρτηση μια αλλαγή εκεί άφηνε τον Z80 με τον ΠΑΛΙΟ αριθμό
# ενώ τα .BIN γράφονταν με τον νέο — ο φορτωτής διάβαζε τους πίνακες σε λάθος
# θέση και κρεμούσε μέσα στον αποσυμπιεστή.
src/gamedefs.asm src/tables.asm src/rooms.asm: tools/genasm.py tools/physics.py tools/roomfile.py $(ROOMS)
	$(PY) tools/genasm.py

# Η ΜΟΥΣΙΚΗ, ΔΥΟ ΚΟΜΜΑΤΙΑ ΑΠΟ ΤΗΝ ΙΔΙΑ ΓΕΝΝΗΤΡΙΑ: το src/tune.asm είναι ο
# πίνακας νοτών που μένει στη βασική μνήμη, και τα build/TUNEnn.BIN είναι οι
# ίδιες οι νότες, που πάνε στην τράπεζα μέσω της δισκέτας. Ένας κανόνας για τα
# δύο: τα παράγει η ίδια εκτέλεση και δεν επιτρέπεται να ξεσυγχρονιστούν.
src/tune.asm: tools/genboss.py tools/genmusic.py
	$(PY) tools/genboss.py

# Το rasm βγάζει το build/main.bin μέσω του `save` directive στο main.asm
# Ο πίνακας συμβόλων δεν είναι για debugging: από εκεί διαβάζει το
# roomfile.py πόσος χώρος ΠΡΑΓΜΑΤΙΚΑ περισσεύει για ένα σετ αιθουσών.
$(BIN): $(SRC) $(DEPS) $(GFX) | build
	$(ASM) $(SRC) -s -sa -os build/symbols.txt

# ASCII BASIC για το CPC: γραμμές με CR+LF, τερματισμός με &1A (EOF)
$(BASD): $(BAS) | build
	sed 's/$$/\r/' $(BAS) > $(BASD)
	printf '\032' >> $(BASD)

# Τα σετ αιθουσών. Δικός τους κανόνας και δικός τους παραγωγός: αν κρέμονταν
# από το src/rooms.asm, ένα `make clean` θα έσβηνε τα .BIN χωρίς να τα
# ξαναφτιάξει — το rooms.asm θα ήταν ήδη ενημερωμένο — και η δισκέτα θα
# έβγαινε ΧΩΡΙΣ αίθουσες.
# ΜΕΤΑ το binary: η χωρητικότητα βγαίνει από τα σύμβολά του.
$(SETS): tools/roomfile.py tools/physics.py $(ROOMS) $(BIN) | build
	$(PY) tools/roomfile.py

$(MUSBIN): src/musictest.asm src/music_boss.asm | build
	$(ASM) src/musictest.asm

src/music_boss.asm: src/tune.asm

$(MUSBAS): src/musicloader.bas | build
	sed 's/$$/\r/' src/musicloader.bas > $(MUSBAS)
	printf '\032' >> $(MUSBAS)

$(DSK): $(BIN) $(BASD) $(SETS) $(SPLASH) $(MUSBIN) $(MUSBAS) src/tune.asm
	rm -f $(DSK)
	$(DISK) $(DSK) -n
	$(DISK) $(DSK) -i $(BIN)  -t 1 -c 4000 -e 4000 -f
	$(DISK) $(DSK) -i $(BASD) -t 0 -f
	@# Η οθόνη υποδοχής: MODE 0 με δική της παλέτα, 16 KB ωμά pixel. Φορτώνεται
	@# από τον BASIC loader στο #C000 πριν καν μπει το παιχνίδι στη μνήμη.
	$(DISK) $(DSK) -i $(SPLASH) -t 1 -c C000 -e C000 -f
	@# RUN"MUSIC" from BASIC plays the theme on its own.
	$(DISK) $(DSK) -i $(MUSBIN) -t 1 -c 8000 -e 8000 -f
	$(DISK) $(DSK) -i $(MUSBAS) -t 0 -f
	@# Η ΜΟΥΣΙΚΗ ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ. Ωμά bytes, χωρίς διεύθυνση φόρτωσης: το
	@# tune_boot τα διαβάζει στον set_buf και τα σπρώχνει στο μπλοκ 7.
	@# ΞΑΝΑΠΑΡΑΓΟΝΤΑΙ ΕΔΩ, για τον ίδιο λόγο με τα σετ: το src/tune.asm ζει
	@# έξω από το build/, οπότε μετά από `make clean` ο κανόνας του δεν θα
	@# ξανάτρεχε και η δισκέτα θα έβγαινε με παιχνίδι αλλά χωρίς μουσική.
	$(PY) tools/genboss.py
	@for t in build/TUNE*.BIN; do \
	    [ -e "$$t" ] || { echo "ΣΦΑΛΜΑ: δεν παρήχθη κανένα TUNEnn.BIN."; exit 1; }; \
	    $(DISK) $(DSK) -i $$t -t 1 -c 0000 -e 0000 -f; \
	done
	@# ΤΑ ΣΕΤ ΞΑΝΑΠΑΡΑΓΟΝΤΑΙ ΕΔΩ, ΣΤΗΝ ΕΚΤΕΛΕΣΗ. Το $$(SETS) υπολογίζεται με
	@# $$(shell) ΚΑΤΑ ΤΗΝ ΑΝΑΓΝΩΣΗ του Makefile και με το stderr κρυμμένο: αν
	@# το roomfile.py αποτύχει — π.χ. οι αίθουσες δεν χωρούν στον buffer του
	@# CPC — η λίστα βγαίνει ΚΕΝΗ, ο βρόχος δεν τρέχει καμία φορά, και η
	@# δισκέτα φεύγει χωρίς αίθουσες με exit 0. Το παιχνίδι το ανακαλύπτει
	@# στον emulator: «ROOMS01.BIN not found».
	$(PY) tools/roomfile.py
	@sets=$$(ls build/ROOMS*.BIN 2>/dev/null); \
	if [ -z "$$sets" ]; then \
	    echo "ΣΦΑΛΜΑ: δεν παρήχθη κανένα ROOMSnn.BIN."; \
	    echo "        Η δισκέτα θα έβγαινε ΧΩΡΙΣ αίθουσες."; \
	    exit 1; \
	fi; \
	for s in $$sets; do \
	    $(DISK) $(DSK) -i $$s -t 1 -c 0000 -e 0000 -f; \
	done
	@$(PY) tools/checkdsk.py $(DSK)
	@echo "----------------------------------------------"
	@echo "  Έτοιμο: $(DSK)"
	@echo "  Στον emulator:  RUN\"GRAV\""
	@echo "----------------------------------------------"

build:
	mkdir -p build

# Ξαναφτιάχνει τα PNG από τις γεννήτριες. ΠΡΟΣΟΧΗ: σβήνει ό,τι έχεις ζωγραφίσει.
sprites-init:
	$(PY) tools/sprites.py init --force

# Επαληθεύσεις: αλγόριθμος περιστροφής + μοντέλο φυσικής
test:
	$(PY) tools/check_names.py
	$(PY) tools/verify_rotate.py
	$(PY) tools/test_physics.py
	$(PY) tools/test_z80.py
	$(PY) tools/test_music.py
	@# Ο έλεγχος του προσωπικού φακέλου θέλει .NET, που δεν είναι στο PATH.
	@if [ -x "$$HOME/.dotnet/dotnet" ]; then \
	    "$$HOME/.dotnet/dotnet" run --project editor.Tests -v q --nologo; \
	else \
	    echo "  ΠΑΡΑΛΕΙΨΗ editor.Tests: δεν βρέθηκε ~/.dotnet/dotnet"; \
	fi

# Δεδομένα και σενάριο ισοδυναμίας για το test run του editor.
# Άνοιξε μετά το /game/parity.html: συγκρίνει JavaScript και μοντέλο frame
# προς frame και δείχνει την πρώτη απόκλιση.
editor-data: $(JSDATA) $(PARITY)

$(JSDATA): tools/genjs.py tools/physics.py
	$(PY) tools/genjs.py

# ΜΕΤΑ το data.js: το parity τρέχει την ίδια JavaScript που το διαβάζει.
$(PARITY): tools/parity.py tools/physics.py editor/wwwroot/game/physics.js $(JSDATA)
	$(PY) tools/parity.py

# Οπτικό ίχνος της διαδρομής του ήρωα στο δοκιμαστικό δωμάτιο
trace:
	$(PY) tools/trace.py

clean:
	rm -rf build
	rm -f assets/*-export.png

.PHONY: all clean test trace sprites-init editor-data
