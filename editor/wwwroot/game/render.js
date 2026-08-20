// GRAVASSIST — απεικόνιση σε canvas, με τα ίδια γραφικά και την ίδια παλέτα
// με τον Amstrad. Τα pixel arrays έρχονται από το data.js (πηγή: tools/).
//
// Η οθόνη είναι 320x200 σε MODE 1, μεγεθυμένη ακέραια. Ακέραιο scale επίτηδες:
// με παρεμβολή τα pixel art γραφικά θολώνουν και χάνεται το νόημα του ελέγχου.
(function (D) {
  "use strict";

  const W = D.COLS * D.CELL, H = 200;

  // Οι δέσμες έχουν 0 και 45 μοίρες· οι υπόλοιπες φορές είναι περιστροφές των
  // 90, δηλαδή ακριβές index remap — ίδια λογική με το src/rotate.asm.
  function rot90(px, times) {
    let g = px;
    for (let i = 0; i < ((times % 4) + 4) % 4; i++) {
      const h = g.length, w = g[0].length;
      const o = [];
      for (let y = 0; y < w; y++) {
        const row = [];
        for (let x = 0; x < h; x++) row.push(g[h - 1 - x][y]);
        o.push(row);
      }
      g = o;
    }
    return g;
  }

  function unpack(bank) {
    return bank.frames.map(s => {
      const rows = [];
      for (let y = 0; y < bank.h; y++)
        rows.push([...s.slice(y * bank.w, (y + 1) * bank.w)].map(Number));
      return rows;
    });
  }

  const HERO = unpack(D.HERO), HERO45 = unpack(D.HERO45);
  const PARA = unpack(D.PARA), PARA45 = unpack(D.PARA45);

  function heroSprite(g, frame) {
    return g % 2 ? rot90(HERO45[frame], g >> 1) : rot90(HERO[frame], g >> 1);
  }
  // ΤΟ ΒΕΛΟΣ, ίδιο σχήμα με το src/turret.asm: έντεκα pixel, ουρά σε pen 1
  // και μύτη σε pen 3. Ήταν επτά pixel όλα πορτοκαλί — το χρώμα που το concept
  // art δίνει στους κινδύνους — αλλά πορτοκαλί είναι και οι ακμές κάθε
  // πλακιδίου, οπότε η σφαίρα χανόταν πάνω τους. Λευκή ουρά για να φαίνεται,
  // πορτοκαλί μύτη γιατί αυτή είναι το επικίνδυνο άκρο.
  const ARROW_DOWN = [
    [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0],
    [3, 3, 3], [3, 3, 3], [0, 3, 0],
  ];
  const flipRows = m => m.slice().reverse();
  const transpose = m => m[0].map((_, x) => m.map(r => r[x]));

  function arrowSprite(dx, dy) {
    if (!dx) return dy > 0 ? ARROW_DOWN : flipRows(ARROW_DOWN);
    const right = transpose(ARROW_DOWN);
    return dx > 0 ? right : right.map(r => r.slice().reverse());
  }

  function paraSprite(g, frame) {
    return g % 2 ? rot90(PARA45[frame], g >> 1) : rot90(PARA[frame], g >> 1);
  }

  class Screen {
    constructor(canvas, scale) {
      this.scale = scale || 3;
      canvas.width = W * this.scale;
      canvas.height = H * this.scale;
      this.ctx = canvas.getContext("2d");
      this.ctx.imageSmoothingEnabled = false;
      this.img = this.ctx.createImageData(W, H);
      this.rgb = D.PALETTE.map(h => [
        parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16),
        parseInt(h.slice(5, 7), 16)]);
      this.buf = new Uint8Array(W * H);
      this.tmp = document.createElement("canvas");
      this.tmp.width = W; this.tmp.height = H;
      this.tctx = this.tmp.getContext("2d");
    }
    clear() { this.buf.fill(0); }
    px(x, y, pen) {
      if (x < 0 || y < 0 || x >= W || y >= H) return;
      this.buf[y * W + x] = pen;
    }
    tiles(room) {
      for (let r = 0; r < D.ROWS; r++)
        for (let c = 0; c < D.COLS; c++) {
          const px = D.TILE_PX[room.cells[r][c]];
          for (let v = 0; v < D.CELL; v++)
            for (let u = 0; u < D.CELL; u++)
              this.px(c * D.CELL + u, D.GRID_Y0 + r * D.CELL + v, px[v][u]);
        }
    }
    /// Κινούμενη πλατφόρμα: το πλακίδιό της, επαναλαμβανόμενο σε όλο το
    /// ορθογώνιο. ΘΕΣΗ ΣΕ PIXEL και όχι σε κελιά — εκεί είναι η διαφορά της
    /// από κάθε άλλο υλικό, και γι' αυτό δεν την πιάνει το tiles().
    platform(p) {
      const px = D.TILE_PX[p.moving ? D.TYPE_NAMES.indexOf("PLATFORM")
                                    : D.TYPE_NAMES.indexOf("PLATFORM_OFF")];
      for (let v = 0; v < p.h; v++)
        for (let u = 0; u < p.w; u++)
          this.px(p.x + u, p.y + v, px[v % D.CELL][u % D.CELL]);

      // Ο ΕΠΙΒΑΤΗΣ ΜΑΖΙ ΤΗΣ. Ο διακόπτης που ταξιδεύει πάνω στην πλατφόρμα
      // έχει φύγει από το πλέγμα στη φόρτωση, ώστε να κινείται ανά pixel —
      // οπότε το tiles() δεν τον ζωγραφίζει πια και χωρίς αυτό εδώ δούλευε
      // κανονικά αλλά ήταν ΑΟΡΑΤΟΣ.
      if (p.rider === null || p.rider === undefined) return;
      const rp = D.TILE_PX[p.rider];
      for (let v = 0; v < D.CELL; v++)
        for (let u = 0; u < D.CELL; u++)
          if (rp[v][u]) this.px(p.x + p.rdx + u, p.y - D.CELL + v, rp[v][u]);
    }
    sprite(px, cx, cy) {                 // κεντραρισμένο, pen 0 = διαφανές
      const h = px.length, w = px[0].length;
      const x0 = Math.round(cx - w / 2), y0 = Math.round(cy - h / 2);
      for (let y = 0; y < h; y++)
        for (let x = 0; x < w; x++)
          if (px[y][x]) this.px(x0 + x, y0 + y, px[y][x]);
    }
    hud(hero) {
      for (let i = 0; i < D.K.ENERGY_MAX; i++) {
        const pen = i < hero.energy ? (hero.energy < 3 ? 3 : 2) : 0;
        for (let y = 2; y < 6; y++)
          for (let x = 0; x < 8; x++)
            this.px(D.HUD.energy * 4 + i * 8 + x, y, pen);
      }
      const inv = [];
      // Άθροισμα όλων των ταυτοτήτων: το HUD δείχνει ΠΟΣΑ κλειδιά έχεις,
      // όχι ποια — για το ποια υπάρχει ο editor.
      const nkeys = hero.keys.reduce((a, b) => a + b, 0);
      for (let i = 0; i < nkeys; i++) inv.push(19);
      for (let i = 0; i < hero.parachute; i++) inv.push(18);
      if (hero.carry) inv.push(25);
      for (let i = 0; i < 10; i++) {
        const px = D.TILE_PX[i < inv.length ? inv[i] : 0];
        for (let v = 0; v < D.CELL; v++)
          for (let u = 0; u < D.CELL; u++)
            this.px(D.HUD.inv * 4 + i * 8 + u, v, px[v][u]);
      }
      // Δύο ΞΕΧΩΡΙΣΤΑ βελάκια: η βαρύτητα του ΚΟΣΜΟΥ (την όρισε ο παίκτης,
      // την ακολουθούν τα κιβώτια) και η βαρύτητα του ΗΡΩΑ (γυρίζει μόνη της
      // σε κάθε γωνία). Κολλητά στη δεξιά άκρη, όπως στο src/main.asm.
      const glyph = (art, col) => {
        for (let v = 0; v < 8; v++)
          for (let u = 0; u < 8; u++) this.px(col * 4 + u, v, art[v][u]);
      };
      for (const [bank, g, col] of [[0, hero.worldG, D.HUD.grav_w],
                                    [1, hero.g, D.HUD.grav_h]])
        glyph(D.GRAV_PX[bank][g], col);
      // …και τα δύο σταθερά σύμβολα που λένε τι μετράει ο αριθμός δίπλα τους.
      glyph(D.HUD_BOLT_PX, D.HUD.bolt);
      glyph(D.HUD_STAR_PX, D.HUD.star);
    }
    flush() {
      const d = this.img.data;
      for (let i = 0; i < this.buf.length; i++) {
        const c = this.rgb[this.buf[i]];
        d[i * 4] = c[0]; d[i * 4 + 1] = c[1]; d[i * 4 + 2] = c[2]; d[i * 4 + 3] = 255;
      }
      this.tctx.putImageData(this.img, 0, 0);
      this.ctx.imageSmoothingEnabled = false;
      this.ctx.drawImage(this.tmp, 0, 0, W * this.scale, H * this.scale);
    }

    /// Ο τίτλος του μενού με ΤΑ ΙΔΙΑ pixel που ζωγραφίζει ο Amstrad: οι
    /// μάσκες των γραμμάτων έρχονται από την ίδια πηγή (tools/genasm.py) και
    /// γράφονται στον ίδιο buffer με τα πλακίδια. Καλείται ΠΡΙΝ το flush.
    title() {
      const T = D.TITLE, f = T.frame;
      // Οι οριζόντιες πλευρές ξεκινούν ΕΝΑ byte μέσα από τη γωνία και οι
      // κάθετες δύο scanlines χαμηλότερα: οι γωνίες βγαίνουν κομμένες, όπως
      // στο concept art. Το χρώμα αλλάζει στη μέση, μαζί με τα γράμματα.
      const fpen = x => (x < f.mid ? T.pens[0] : T.pens[1]);
      for (let x = f.x0 + 4; x < f.x1; x++)
        for (const y of [f.y0, f.y0 + 1, f.y1 - 1, f.y1]) this.px(x, y, fpen(x));
      for (let y = f.y0 + 2; y < f.y1 - 1; y++)
        for (let k = 0; k < 4; k++) {
          this.px(f.x0 + k, y, T.pens[0]);
          this.px(f.x1 + k, y, T.pens[1]);
        }

      let x = T.x;
      for (let i = 0; i < T.text.length; i++) {
        const rows = T.glyphs[T.text[i]];
        const pen = T.pens[i < T.split ? 0 : 1];
        for (let v = 0; v < rows.length; v++)
          for (let u = 0; u < 8; u++) {
            if (rows[v][u] !== "#") continue;
            for (let dy = 0; dy < T.scale; dy++)
              for (let dx = 0; dx < T.scale; dx++)
                this.px(x + u * T.scale + dx, T.y + v * T.scale + dy, pen);
          }
        x += 8 * T.scale;
      }
    }

    /// Οι γραμμές κειμένου του μενού. Αυτές ο Amstrad τις τυπώνει με τη
    /// γραμματοσειρά του firmware, που δεν την έχουμε — canvas text, ίδιες
    /// θέσεις. Καλείται ΜΕΤΑ το flush.
    menuText(lines) {
      const s = this.scale;
      this.ctx.font = (8 * s) + "px monospace";
      this.ctx.textBaseline = "alphabetic";
      this.ctx.fillStyle = "#FFFFFF";
      for (const [col, row, text] of lines)
        this.ctx.fillText(text, (col - 1) * 8 * s, (row * 8 - 1) * s);
    }

    /// Κείμενο σε γραμμή ΠΛΕΓΜΑΤΟΣ, μετά το flush.
    ///
    /// Ο Amstrad το τυπώνει με τη γραμματοσειρά του firmware, που δεν την
    /// έχουμε εδώ — το σχήμα των γραμμάτων διαφέρει. Η ΘΕΣΗ και η
    /// ΣΥΜΠΕΡΙΦΟΡΑ είναι ίδιες, και αυτές δοκιμάζει ο σχεδιαστής.
    /// Κείμενο στο πλέγμα ΤΟΥ FIRMWARE: στήλη και γραμμή ΑΠΟ ΤΟ 1, όπως τα
    /// παίρνει το TXT_SET_CURSOR (H = στήλη, L = γραμμή) — και όπως τα δίνουν
    /// το src/score.asm και το hint_draw.
    ///
    /// ΤΟ ΑΠΟ ΤΟ 1 ΔΕΝ ΕΙΝΑΙ ΛΕΠΤΟΜΕΡΕΙΑ: με 0-based όλα έπεφταν οκτώ pixel
    /// δεξιά, και το σκορ — που ο Amstrad το βάζει στη γραμμή 1, δηλαδή στο
    /// HUD — έμπαινε μέσα στο πλέγμα.
    text(msg, textRow, col) {
      const x = (col - 1) * 8 * this.scale;
      const top = (textRow - 1) * D.CELL * this.scale;
      const y = top + 7 * this.scale;
      this.ctx.font = (8 * this.scale) + "px monospace";
      this.ctx.textBaseline = "alphabetic";
      this.ctx.fillStyle = "#000080";
      this.ctx.fillRect(x, top, msg.length * 8 * this.scale, D.CELL * this.scale);
      this.ctx.fillStyle = "#FFFFFF";
      this.ctx.fillText(msg, x, y);
    }
  }

  window.GRAV_RENDER = { Screen, heroSprite, paraSprite, arrowSprite, W, H };
})(window.GAME_DATA);
