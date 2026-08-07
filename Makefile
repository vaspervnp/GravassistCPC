# GRAVASSIST - Amstrad CPC 6128, MODE 1, Z80
ASM   = rasm
DISK  = iDSK
PY    = python3

SRC   = src/main.asm
DEPS  = src/rotate.asm
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

# Επαλήθευση του αλγορίθμου περιστροφής του src/rotate.asm
test:
	$(PY) tools/verify_rotate.py

clean:
	rm -rf build
	rm -f assets/*-export.png

.PHONY: all clean test sprites-init
