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
          for (let x = 0; x < 8; x++) this.px(8 + i * 8 + x, y, pen);
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
          for (let u = 0; u < D.CELL; u++) this.px(88 + i * 8 + u, v, px[v][u]);
      }
      // Δύο ΞΕΧΩΡΙΣΤΑ βελάκια: η βαρύτητα του ΚΟΣΜΟΥ (την όρισε ο παίκτης,
      // την ακολουθούν τα κιβώτια) και η βαρύτητα του ΗΡΩΑ (γυρίζει μόνη της
      // σε κάθε γωνία). Ίδιες θέσεις με το src/main.asm: στήλες byte 68 και 72.
      for (const [bank, g, col] of [[0, hero.worldG, 68], [1, hero.g, 72]]) {
        const px = D.GRAV_PX[bank][g];
        for (let v = 0; v < 8; v++)
          for (let u = 0; u < 8; u++) this.px(col * 4 + u, v, px[v][u]);
      }
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

    /// Ο τίτλος του μενού. Ο Amstrad τον ζωγραφίζει pixel-pixel από δική του
    /// γραμματοσειρά· εδώ αρκεί canvas text στα ίδια χρώματα και στην ίδια
    /// θέση — το ζητούμενο είναι να δεις τη διάταξη χωρίς emulator.
    title() {
      const s = this.scale;
      this.ctx.textAlign = "center";
      this.ctx.font = "bold " + (26 * s) + "px monospace";
      const cx = (W / 2) * s, y = 34 * s;
      const grav = "GRAV", assist = "ASSIST";
      const wg = this.ctx.measureText(grav).width;
      const wa = this.ctx.measureText(assist).width;
      this.ctx.textAlign = "left";
      this.ctx.fillStyle = "#FF8000";
      this.ctx.fillText(grav, cx - (wg + wa) / 2, y);
      this.ctx.fillStyle = "#00FF00";
      this.ctx.fillText(assist, cx - (wg + wa) / 2 + wg, y);

      this.ctx.textAlign = "center";
      this.ctx.fillStyle = "#FFFFFF";
      this.ctx.font = (8 * s) + "px monospace";
      this.ctx.fillText("Press Space to start game", cx, 160 * s);
      this.ctx.fillText("REVIVE8BIT - 2026 - VASPER", cx, 184 * s);
      this.ctx.textAlign = "left";
    }

    /// Κείμενο σε γραμμή ΠΛΕΓΜΑΤΟΣ, μετά το flush.
    ///
    /// Ο Amstrad το τυπώνει με τη γραμματοσειρά του firmware, που δεν την
    /// έχουμε εδώ — το σχήμα των γραμμάτων διαφέρει. Η ΘΕΣΗ και η
    /// ΣΥΜΠΕΡΙΦΟΡΑ είναι ίδιες, και αυτές δοκιμάζει ο σχεδιαστής.
    text(msg, gridRow, col) {
      const x = col * 8 * this.scale;
      const y = (D.GRID_Y0 + gridRow * D.CELL + 7) * this.scale;
      this.ctx.font = (8 * this.scale) + "px monospace";
      this.ctx.textBaseline = "alphabetic";
      this.ctx.fillStyle = "#000080";
      this.ctx.fillRect(x - 2, y - 8 * this.scale,
                        msg.length * 8 * this.scale + 4, 9 * this.scale);
      this.ctx.fillStyle = "#FFFFFF";
      this.ctx.fillText(msg, x, y);
    }
  }

  window.GRAV_RENDER = { Screen, heroSprite, paraSprite, W, H };
})(window.GAME_DATA);
