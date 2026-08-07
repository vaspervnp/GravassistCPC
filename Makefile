# GRAVASSIST - Amstrad CPC 6128, MODE 1, Z80
ASM   = rasm
DISK  = iDSK
PY    = python3

SRC   = src/main.asm
DEPS  = src/rotate.asm src/level.asm src/hero.asm src/tables.asm src/rooms.asm src/gamedefs.asm
GFX   = src/gfx_hero.asm src/gfx_objects.asm
PNG   = assets/hero.png assets/objects.png
BAS   = src/loader.bas
BIN   = build/main.bin
BASD  = build/grav.bas
DSK   = build/gravassist.dsk

all: $(DSK)

# Τα sprites παράγονται από τα PNG — το PNG είναι η αυθεντία (docs/sprites.md)
$(GFX): $(PNG) tools/sprites.py tools/cpcgfx.py tools/stickman.py tools/placeholders.py
	$(PY) tools/sprites.py build

# Πίνακες γεωμετρίας + δωμάτιο: παράγονται από το ΙΔΙΟ μοντέλο με την
# προσομοίωση, ώστε Z80 και Python να μην μπορούν να αποκλίνουν αριθμητικά.
src/gamedefs.asm src/tables.asm src/rooms.asm: tools/genasm.py tools/physics.py levels/test.txt
	$(PY) tools/genasm.py

# Το rasm βγάζει το build/main.bin μέσω του `save` directive στο main.asm
$(BIN): $(SRC) $(DEPS) $(GFX) | build
	$(ASM) $(SRC)

# ASCII BASIC για το CPC: γραμμές με CR+LF, τερματισμός με &1A (EOF)
$(BASD): $(BAS) | build
	sed 's/$$/\r/' $(BAS) > $(BASD)
	printf '\032' >> $(BASD)

$(DSK): $(BIN) $(BASD)
	rm -f $(DSK)
	$(DISK) $(DSK) -n
	$(DISK) $(DSK) -i $(BIN)  -t 1 -c 4000 -e 4000 -f
	$(DISK) $(DSK) -i $(BASD) -t 0 -f
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
