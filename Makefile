# GRAVASSIST - Amstrad CPC 6128, MODE 1, Z80
ASM   = rasm
DISK  = iDSK
PY    = python3

SRC   = src/main.asm
# ΟΛΕΣ οι αίθουσες, όχι μόνο μία: το src/rooms.asm τις ενσωματώνει όλες, οπότε
# αν εξαρτιόταν από ένα αρχείο, μια αλλαγή σε άλλη αίθουσα θα περνούσε
# απαρατήρητη και το «Χτίσιμο .dsk» θα έβγαζε δισκέτα με παλιά δεδομένα.
ROOMS = $(wildcard levels/room_*.txt)
DEPS  = src/rotate.asm src/level.asm src/hero.asm src/tables.asm src/rooms.asm \
        src/gamedefs.asm src/roomfile.asm src/menu.asm src/musicplay.asm src/music.asm
GFX   = src/gfx_hero.asm src/gfx_objects.asm
PNG   = assets/hero.png assets/objects.png
BAS   = src/loader.bas
SPLASH = assets/revive8b.scr
BIN   = build/main.bin
BASD  = build/grav.bas
DSK   = build/gravassist.dsk
# Ένα ROOMSnn.BIN ανά 40 αίθουσες. Τα ονόματα προκύπτουν από τους αριθμούς
# των αιθουσών, οπότε ρωτάμε το ίδιο εργαλείο που τα γράφει.
SETS  = $(shell $(PY) -c "import sys;sys.path.insert(0,'tools');import roomfile;\
        print(' '.join('build/'+n for _,n,_ in roomfile.all_sets()))" 2>/dev/null)

all: $(DSK)

# Τα sprites παράγονται από τα PNG — το PNG είναι η αυθεντία (docs/sprites.md)
$(GFX): $(PNG) tools/sprites.py tools/cpcgfx.py tools/stickman.py tools/placeholders.py
	$(PY) tools/sprites.py build

# Πίνακες γεωμετρίας + δωμάτιο: παράγονται από το ΙΔΙΟ μοντέλο με την
# προσομοίωση, ώστε Z80 και Python να μην μπορούν να αποκλίνουν αριθμητικά.
src/gamedefs.asm src/tables.asm src/rooms.asm: tools/genasm.py tools/physics.py $(ROOMS)
	$(PY) tools/genasm.py

# Η μουσική: νότες σε περιόδους του AY. Γεννιέται ώστε το src/music.asm να μην
# είναι 150 magic numbers που κανείς δεν μπορεί να διορθώσει.
src/music.asm: tools/genmusic.py
	$(PY) tools/genmusic.py

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

$(DSK): $(BIN) $(BASD) $(SETS) $(SPLASH)
	rm -f $(DSK)
	$(DISK) $(DSK) -n
	$(DISK) $(DSK) -i $(BIN)  -t 1 -c 4000 -e 4000 -f
	$(DISK) $(DSK) -i $(BASD) -t 0 -f
	@# Η οθόνη υποδοχής: MODE 0 με δική της παλέτα, 16 KB ωμά pixel. Φορτώνεται
	@# από τον BASIC loader στο #C000 πριν καν μπει το παιχνίδι στη μνήμη.
	$(DISK) $(DSK) -i $(SPLASH) -t 1 -c C000 -e C000 -f
	@for s in $(SETS); do \
	    $(DISK) $(DSK) -i $$s -t 1 -c 0000 -e 0000 -f; \
	done
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
	$(PY) tools/verify_rotate.py
	$(PY) tools/test_physics.py
	$(PY) tools/test_z80.py

# Δεδομένα και σενάριο ισοδυναμίας για το test run του editor.
# Άνοιξε μετά το /game/parity.html: συγκρίνει JavaScript και μοντέλο frame
# προς frame και δείχνει την πρώτη απόκλιση.
editor-data:
	$(PY) tools/genjs.py
	$(PY) tools/parity.py

# Οπτικό ίχνος της διαδρομής του ήρωα στο δοκιμαστικό δωμάτιο
trace:
	$(PY) tools/trace.py

clean:
	rm -rf build
	rm -f assets/*-export.png

.PHONY: all clean test trace sprites-init editor-data
