#!/usr/bin/env python3
"""Κοινά εργαλεία γραφικών για το GRAVASSIST.

Ένα "frame" είναι πάντα λίστα από λίστες ακεραίων 0..3 (pen ανά pixel),
σε σειρά γραμμών: frame[y][x].  Δες docs/sprites.md.
"""

from PIL import Image

# --- Χρώματα-κλειδιά του PNG (δες docs/sprites.md §5) -----------------
PEN_RGB = [
    (0x00, 0x00, 0x80),   # pen 0 - διαφανές / φόντο
    (0xFF, 0xFF, 0xFF),   # pen 1 - ήρωας, κείμενο
    (0x00, 0xFF, 0x00),   # pen 2 - σώμα υλικού
    (0xFF, 0x80, 0x00),   # pen 3 - ακμές, κίνδυνος
]
GRID_RGB = (0xFF, 0x00, 0xFF)   # ματζέντα διαχωριστικό· αγνοείται στο import

SEP = 1   # pixels διαχωριστικού ανάμεσα στα κελιά


def nearest_pen(rgb):
    """Στρογγυλοποιεί ένα RGB στο πλησιέστερο pen (ευκλείδεια στο RGB)."""
    r, g, b = rgb[:3]
    best, best_d = 0, None
    for pen, (pr, pg, pb) in enumerate(PEN_RGB):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if best_d is None or d < best_d:
            best, best_d = pen, d
    return best


def blank(w, h):
    return [[0] * w for _ in range(h)]


# --- Sheet I/O --------------------------------------------------------
# Το κελί (col,row) ξεκινά στο pixel (col*(w+SEP), row*(h+SEP)).
# Ο εντοπισμός γίνεται ΜΟΝΟ με τη θέση, ποτέ με το χρώμα του πλέγματος,
# ώστε να μη χαλάει αν ζωγραφίσεις πάνω στις γραμμές.

def sheet_size(cell_w, cell_h, cols, rows):
    return (cols * (cell_w + SEP) + SEP, rows * (cell_h + SEP) + SEP)


def write_sheet(path, frames, cell_w, cell_h, cols):
    """Γράφει τα frames σε PNG sheet με ματζέντα πλέγμα."""
    rows = (len(frames) + cols - 1) // cols
    W, H = sheet_size(cell_w, cell_h, cols, rows)
    img = Image.new("RGB", (W, H), GRID_RGB)
    px = img.load()
    for i, fr in enumerate(frames):
        cx = (i % cols) * (cell_w + SEP) + SEP
        cy = (i // cols) * (cell_h + SEP) + SEP
        for y in range(cell_h):
            for x in range(cell_w):
                px[cx + x, cy + y] = PEN_RGB[fr[y][x]]
    img.save(path)
    return W, H


def read_sheet(path, cell_w, cell_h, cols, count):
    """Διαβάζει `count` frames από PNG sheet. Επιστρέφει λίστα frames."""
    img = Image.open(path).convert("RGB")
    px = img.load()
    W, H = img.size
    frames = []
    for i in range(count):
        cx = (i % cols) * (cell_w + SEP) + SEP
        cy = (i // cols) * (cell_h + SEP) + SEP
        if cx + cell_w > W or cy + cell_h > H:
            raise ValueError(
                f"{path}: το frame {i} πέφτει εκτός εικόνας ({W}x{H}). "
                f"Μη χαλάς τις διαστάσεις του sheet."
            )
        fr = blank(cell_w, cell_h)
        for y in range(cell_h):
            for x in range(cell_w):
                fr[y][x] = nearest_pen(px[cx + x, cy + y])
        frames.append(fr)
    return frames


# --- Έξοδος σε assembly ----------------------------------------------

def pack_row(row):
    """Μία γραμμή pixel -> bytes, ΤΕΣΣΕΡΑ pixel ανά byte.

    Ένα pen του MODE 1 είναι 0..3, δηλαδή δύο bits· τα δεδομένα κρατούσαν ένα
    ολόκληρο byte για καθένα και ο ήρωας μόνος του έπιανε 5.5 KB σε μηχάνημα
    που είχε μείνει με 11 ελεύθερα bytes. Πρώτο pixel στα bits 7-6, μετά 5-4,
    3-2, 1-0· η τελευταία τετράδα γεμίζει με pen 0, που είναι το διαφανές.

    Ο περιστροφέας δεν διαβάζει ΑΥΤΗ τη μορφή: το spr_transform ξεπακετάρει
    πρώτα το καρέ σε πρόχειρο buffer (spr_unpack, src/rotate.asm) και μετά
    δουλεύει όπως πάντα. Έτσι η συμπίεση δεν ακούμπησε καθόλου τον αλγόριθμο
    περιστροφής ούτε το tools/verify_rotate.py που τον φυλάει.
    """
    out = []
    for i in range(0, len(row), 4):
        quad = list(row[i:i + 4]) + [0, 0, 0]
        out.append((quad[0] << 6) | (quad[1] << 4) | (quad[2] << 2) | quad[3])
    return out


def unpack_row(data, width):
    """Το αντίστροφο του pack_row — για τον έλεγχο round-trip."""
    out = []
    for b in data:
        out += [(b >> 6) & 3, (b >> 4) & 3, (b >> 2) & 3, b & 3]
    return out[:width]


def to_asm(label, frames, cell_w, cell_h, title):
    """Παράγει πηγαίο rasm: 4 pixels ανά byte, γραμμή-γραμμή."""
    stride = (cell_w + 3) // 4
    out = [
        ";" + "=" * 69,
        f";  {title}",
        ";  ΠΑΡΑΓΕΤΑΙ ΑΥΤΟΜΑΤΑ από tools/sprites.py — ΜΗΝ το επεξεργάζεσαι.",
        f";  {len(frames)} frames, {cell_w}x{cell_h}, 4 pixels ανά byte",
        f";  ({stride} bytes ανά γραμμή), κανονική φορά βαρύτητας DOWN.",
        ";  Ξεπακετάρισμα + περιστροφή: src/rotate.asm",
        ";" + "=" * 69,
        "",
        f"{label}_w       equ {cell_w}",
        f"{label}_h       equ {cell_h}",
        f"{label}_frames  equ {len(frames)}",
        f"{label}_stride  equ {stride}",
        f"{label}_size    equ {stride * cell_h}",
        "",
        f"{label}:",
    ]
    for i, fr in enumerate(frames):
        out.append(f"                ; --- frame {i} ---")
        for row in fr:
            out.append("                db " + ",".join(
                str(v) for v in pack_row(row)))
    out.append("")
    return "\n".join(out)


def to_ascii(frame, chars=".#Oo"):
    """Απεικόνιση frame στο τερματικό για γρήγορο έλεγχο."""
    return "\n".join("".join(chars[v] for v in row) for row in frame)


# --- Γεωμετρία: ζωγραφική γραμμών σε πλέγμα pixels --------------------

def put(fr, x, y, pen):
    if 0 <= y < len(fr) and 0 <= x < len(fr[0]):
        fr[y][x] = pen


def line(fr, x0, y0, x1, y1, pen=1):
    """Bresenham. Οι συντεταγμένες στρογγυλοποιούνται σε ακέραιους."""
    x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        put(fr, x0, y0, pen)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def rect(fr, x0, y0, x1, y1, pen=1, fill=False):
    for y in range(round(y0), round(y1) + 1):
        for x in range(round(x0), round(x1) + 1):
            if fill or y in (round(y0), round(y1)) or x in (round(x0), round(x1)):
                put(fr, x, y, pen)
