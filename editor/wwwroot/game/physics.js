// GRAVASSIST — φυσική για το test run του editor.
//
// ΜΕΤΑΓΡΑΦΗ του tools/physics.py, συνάρτηση προς συνάρτηση. Το Python είναι η
// αναφορά· αν αλλάξει εκεί κάτι, πρέπει να αλλάξει και εδώ.
//
// Καμία γεωμετρία δεν υπολογίζεται εδώ: οι πίνακες βαρύτητας, οι ιδιότητες των
// κελιών και τα σχήματα των ραμπών έρχονται από το data.js, που παράγεται από
// το ίδιο το μοντέλο. Ό,τι μένει είναι ροή ελέγχου — και αυτή ελέγχεται από το
// tools/parity.py, που τρέχει τα δύο αντίγραφα με τα ίδια δεδομένα και συγκρίνει
// τροχιά προς τροχιά.
(function (D) {
  "use strict";

  const T = {};                                  // ονόματα τύπων -> κωδικοί
  D.TYPE_NAMES.forEach((n, i) => { T[n] = i; });

  const K = D.K;
  const gtab = (g, b) => D.GTAB[g][b + D.GSPAN];
  const rtab = (g, a) => D.RTAB[g][a + D.RSPAN];

  // Ξεχωριστά στρογγυλοποιημένες τιμές, ΑΘΡΟΙΣΜΕΝΕΣ — όπως ακριβώς το physics.off
  // και ο Z80. Η στρογγυλοποίηση του αθροίσματος θα έδινε άλλο pixel.
  function off(g, a, b) {
    const r = rtab(g, a), gg = gtab(g, b);
    return [r[0] + gg[0], r[1] + gg[1]];
  }

  class Room {
    constructor(cells, teleports, attrs) {
      this.cells = cells.map(r => r.slice());
      this.probeG = 0;
      // Ιδιότητα ανά κελί: κανάλι για διακόπτες/πόρτες, ταυτότητα για
      // κλειδιά/κλειδαριές. Η πόρτα ΔΕΝ είναι πια καθολική σημαία — κάθε
      // κελί κρατά την κατάστασή του, όπως και στον Amstrad.
      this.attrs = attrs || {};           // "c,r" -> 0..ATTR_MAX-1
      this.teleports = teleports || {};   // "c,r" -> [dc, dr]
    }
    attr(c, r) { return this.attrs[c + "," + r] || 0; }
    gateCells(channel) {
      const out = [];
      for (const k in this.attrs) {
        if (this.attrs[k] !== channel) continue;
        const [c, r] = k.split(",").map(Number);
        const v = this.cell(c, r);
        if (v === T.GATE || v === T.GATE_OPEN) out.push([c, r]);
      }
      return out;
    }
    cell(c, r) {
      if (c < 0 || r < 0 || c >= D.COLS || r >= D.ROWS) return T.SOLID;
      return this.cells[r][c];
    }
    solidAt(px, py) {
      py -= D.GRID_Y0;
      if (py < 0) return true;
      const t = this.cell(Math.floor(px / D.CELL), Math.floor(py / D.CELL));
      const mask = D.RAMP_MASK[t];
      if (mask) return !!mask[((py % D.CELL) + D.CELL) % D.CELL][((px % D.CELL) + D.CELL) % D.CELL];
      if (D.PROPS[t] & D.F.ONEWAY) return (D.FACING[t] + 4) % 8 === this.probeG;
      return !!(D.PROPS[t] & D.F.SOLID);
    }
  }

  class Hero {
    constructor(room, x, y, g) {
      this.room = room; this.x = x; this.y = y; this.g = g;
      this.fallDist = 0; this.state = "FALL"; this.prevSupport = T.EMPTY;
      this.fallV = K.FALL_V0; this.fallAcc = 0;
      this.energy = K.ENERGY_MAX;
      // ΕΝΑΣ ΜΕΤΡΗΤΗΣ ΑΝΑ ΤΑΥΤΟΤΗΤΑ: το κλειδί 3 ανοίγει μόνο την κλειδαριά 3.
      this.keys = new Array(K.ATTR_MAX).fill(0);
      this.spikeTick = 0; this.prevCell = null; this.prevBody = null;
      this.plateOn = {};                // κανάλι -> πατημένο; (ΑΚΜΗ)
      this.parachute = 0; this.paraOpen = 0; this.won = false;
      this.crateTick = 0; this.walkAcc = 0; this.worldG = g; this.cratesOn = false;
      this.face = 1; this.carry = 0; this.warp = false;
    }

    // --- πρωτογενείς έλεγχοι ---------------------------------------
    at(a, b) {
      const [dx, dy] = off(this.g, a, b);
      this.room.probeG = this.g;
      return this.room.solidAt(this.x + dx, this.y + dy);
    }
    groundDepth(a) {
      for (let k = 0; k < K.SCAN_MAX; k++) if (this.at(a, k)) return k;
      return null;
    }
    wallAhead(d) { return this.at(K.WALL_A * d, 0) || this.at(K.WALL_A * d, -4); }
    tilt(d) {
      const f = this.groundDepth(K.FOOT_A * d), b = this.groundDepth(-K.FOOT_A * d);
      return (f === null || b === null) ? null : f - b;
    }
    stable() {
      const t = this.tilt(1);
      if (t === null || Math.abs(t) > 1) return false;
      const k = this.groundDepth(0);
      return k !== null && k <= K.FEET_B + 2;
    }
    supportCell() {
      const k = this.groundDepth(0);
      if (k === null) return null;
      const gg = gtab(this.g, k);
      return [Math.floor((this.x + gg[0]) / D.CELL),
              Math.floor((this.y + gg[1] - D.GRID_Y0) / D.CELL)];
    }
    supportType() {
      const sc = this.supportCell();
      return sc ? this.room.cell(sc[0], sc[1]) : T.EMPTY;
    }
    bodyCell() {
      return [Math.floor(this.x / D.CELL), Math.floor((this.y - D.GRID_Y0) / D.CELL)];
    }
    slipping() {
      const st = this.supportType();
      if (st === T.EMPTY) return false;
      const rg = D.RAMP_GRAVITY[st];
      if (rg !== undefined) return this.g !== rg;
      return this.g % 2 === 1;
    }
    noflip() { const [c, r] = this.bodyCell(); return !!(D.PROPS[this.room.cell(c, r)] & D.F.NOFLIP); }

    // --- κίνηση -----------------------------------------------------
    step(vec, n) { this.x += vec[0] * n; this.y += vec[1] * n; }
    snap() {
      const gs = D.GSTEP[this.g];
      for (let i = 0; i < K.SCAN_MAX; i++) {
        const k = this.groundDepth(0);
        if (k === null) return false;
        if (Math.abs(k - K.FEET_B) <= 1) return true;
        const s = k > K.FEET_B ? 1 : -1;
        this.x += gs[0] * s; this.y += gs[1] * s;
      }
      return false;
    }
    pivotTo(newg) {
      const k = this.groundDepth(0);
      if (k === null) return false;
      const gg = gtab(this.g, k);
      const cx = this.x + gg[0], cy = this.y + gg[1];
      const ng = gtab(newg, K.FEET_B);
      this.g = newg;
      this.x = cx - ng[0]; this.y = cy - ng[1];
      return this.snap();
    }
    corner(steps, d, ox, oy, og) {
      const e = off(this.g, K.WALL_A * d, K.FEET_B);
      const cx = this.x + e[0], cy = this.y + e[1];
      const newg = ((this.g + steps) % 8 + 8) % 8;
      const nr = rtab(newg, K.WALL_A * d), ng = gtab(newg, K.FEET_B);
      this.g = newg;
      this.x = cx + nr[0] - ng[0]; this.y = cy + nr[1] - ng[1];
      if (this.snap() && !this.slipping()) return true;
      this.x = ox; this.y = oy; this.g = og;
      return false;
    }
    align(d) {
      const st = this.supportType();
      if (st === T.EMPTY) return false;
      const rg = D.RAMP_GRAVITY[st];
      if (rg !== undefined) {
        if (this.g === rg) return true;
        const sv = [this.x, this.y, this.g];
        if (this.pivotTo(rg) && !this.slipping()) return true;
        [this.x, this.y, this.g] = sv;
        return false;
      }
      const flatSolid = (D.PROPS[st] & D.F.SOLID) && D.RAMP_GRAVITY[st] === undefined;
      if (flatSolid && this.g % 2 && D.RAMP_GRAVITY[this.prevSupport] !== undefined) {
        for (const cand of [((this.g - 1) % 8 + 8) % 8, (this.g + 1) % 8]) {
          const sv = [this.x, this.y, this.g];
          if (this.pivotTo(cand) && !this.slipping()
              && !this.at(0, 0) && !this.at(0, -K.FEET_B)) return true;
          [this.x, this.y, this.g] = sv;
        }
      }
      return false;
    }
    doWalk(d) {
      this.state = "WALK"; this.face = d;
      const ox = this.x, oy = this.y, og = this.g;
      // ΜΕΣΑ ΣΕ ΖΩΝΗ ΚΛΕΙΔΩΜΑΤΟΣ ΚΑΜΙΑ ΣΤΡΟΦΗ: ο τοίχος σε σταματά, η άκρη σε
      // ρίχνει, η βαρύτητα μένει κάτω.
      const locked = this.noflip();
      if (this.wallAhead(d)) {
        if (locked) return;
        this.corner(-2 * d, d, ox, oy, og); return;
      }
      const rs = D.RSTEP[this.g];
      this.x += rs[0] * d; this.y += rs[1] * d;
      if (this.groundDepth(0) === null) {
        if (locked) { this.doFall(); return; }
        this.x = ox; this.y = oy;
        this.corner(2 * d, d, ox, oy, og);
        return;
      }
      this.snap();
      if (!locked) this.align(d);
      // Αν μετά την ευθυγράμμιση ακόμα γλιστράει ΚΑΙ δεν είναι μετάβαση σε νέο
      // κελί στήριξης, δεν κούμπωσε πουθενά: πέφτει.
      if (this.slipping() && this.prevSupport === this.supportType()) this.doFall();
    }
    doFall() {
      this.state = "FALL";
      const gs = D.GSTEP[this.g];
      if (!this.at(0, K.FEET_B)) {
        this.x += gs[0]; this.y += gs[1]; this.fallDist++;
        return true;
      }
      // ΠΡΟΣΟΧΗ στις λεπτομέρειες: κλίση 0 δίνει slide = -1, όχι 0· και ο
      // έλεγχος γίνεται στο ΩΜΟ pixel (solidAt), όχι μέσω probe του ήρωα.
      const t = this.tilt(1);
      let slide = t === null ? 0 : (t > 0 ? 1 : -1);
      if (slide === 0) slide = this.at(K.FOOT_A, K.FEET_B) ? -1 : 1;
      const rs = D.RSTEP[this.g];
      const nx = this.x + rs[0] * slide, ny = this.y + rs[1] * slide;
      if (!this.room.solidAt(nx, ny)) { this.x = nx; this.y = ny; }
      this.snap();
      return false;
    }
    fallStep() {
      if (this.state !== "FALL") { this.fallV = K.FALL_V0; this.fallAcc = 0; }
      if (this.parachute && !this.paraOpen && this.fallDist >= K.FALL_SAFE) this.paraOpen = 1;
      this.fallV = Math.min(this.fallV + K.FALL_ACCEL, K.FALL_VMAX);
      if (this.paraOpen) this.fallV = K.PARA_V;
      this.fallAcc += this.fallV;
      const steps = this.fallAcc >> 8;
      this.fallAcc &= 0xFF;
      for (let i = 0; i < steps; i++) if (!this.doFall()) return;
    }
    land() {
      this.state = "IDLE";
      if (this.paraOpen) { this.parachute--; this.paraOpen = 0; }
      else if (this.fallDist > K.FALL_SAFE)
        this.hurt(1 + Math.floor((this.fallDist - K.FALL_SAFE) / 12));
      this.fallDist = 0; this.fallV = K.FALL_V0; this.fallAcc = 0;
    }
    hurt(n) { this.energy = Math.max(0, this.energy - n); }

    // --- αντικείμενα ------------------------------------------------
    crateStep() {
      if (!this.cratesOn) return;
      if (++this.crateTick < K.CRATE_TICKS) return;
      this.crateTick = 0;
      const [dx, dy] = D.GSTEP[this.worldG];
      const cells = [];
      for (let r = 0; r < D.ROWS; r++)
        for (let c = 0; c < D.COLS; c++)
          if (this.room.cells[r][c] === T.CRATE) cells.push([c, r]);
      // Τα πιο μακριά κατά τη βαρύτητα πρώτα, αλλιώς μια στοίβα δεν ξεκολλάει.
      cells.sort((a, b) => (b[0] * dx + b[1] * dy) - (a[0] * dx + a[1] * dy));
      for (const [c, r] of cells) {
        const nc = c + dx, nr = r + dy;
        if (nc < 0 || nr < 0 || nc >= D.COLS || nr >= D.ROWS) continue;
        if (this.room.cells[nr][nc] !== T.EMPTY) continue;
        this.room.cells[r][c] = T.EMPTY;
        this.room.cells[nr][nc] = T.CRATE;
      }
    }
    touchObjects() {
      const [col, row] = this.bodyCell();
      const t = this.room.cell(col, row);
      if (D.PROPS[t] & D.F.PICKUP) {
        this.room.cells[row][col] = T.EMPTY;
        if (t === T.ENERGY) this.energy = Math.min(K.ENERGY_MAX, this.energy + K.ENERGY_PICK);
        else if (t === T.PARACHUTE) this.parachute++;
        else if (t === T.KEY) this.keys[this.room.attr(col, row)]++;
      } else if (t === T.SWITCH && (col + "," + row) !== this.prevBody) {
        // ΤΟ ΠΑΤΑΣ, ΔΕΝ ΤΟ ΞΟΔΕΥΕΙΣ: γυρίζει κάθε πόρτα του καναλιού του και
        // μένει εκεί. Ακμή και όχι κράτημα, αλλιώς οι πόρτες ανοιγοκλείνουν
        // 50 φορές το δευτερόλεπτο.
        this.toggleGates(this.room.attr(col, row));
      }
      this.prevBody = col + "," + row;

      // ΕΥΘΡΑΥΣΤΟ: καταρρέει μόλις φύγεις από πάνω του, ώστε να το περνάς
      // ακριβώς μία φορά. Το F_FRAGILE υπήρχε αλλά κανείς δεν το κοιτούσε.
      const sc = this.supportCell();
      const key = sc ? sc[0] + "," + sc[1] : null;
      if (this.prevCell !== null && key !== this.prevCell) {
        const [pc, pr] = this.prevCell.split(",").map(Number);
        if (D.PROPS[this.room.cell(pc, pr)] & D.F.FRAGILE) {
          this.room.cells[pr][pc] = T.EMPTY;
        }
      }
      this.prevCell = key;

      const st = this.supportType();
      if ((D.PROPS[st] & D.F.DEADLY) && (D.FACING[st] + 4) % 8 === this.g) {
        // Ζημιά ανά SPIKE_TICKS frames, όχι σε κάθε frame: αλλιώς η ενέργεια
        // εξατμιζόταν πριν προλάβεις να φύγεις.
        if (this.spikeTick === 0) this.hurt(K.SPIKE_DMG);
        this.spikeTick = (this.spikeTick + 1) % K.SPIKE_TICKS;
      } else {
        this.spikeTick = 0;
      }
    }
    /// Ανοίγει την κλειδαριά και ΟΛΕΣ όσες μοιράζονται την ταυτότητά της.
    /// Η ταυτότητα 0 = ακαλωδίωτη και ανοίγει μόνη της, αλλιώς κάθε πίστα με
    /// πολλές απλές κλειδαριές θα ξεκλείδωνε ολόκληρη με ένα κλειδί.
    openLocks(cell, ident) {
      this.room.cells[cell[1]][cell[0]] = T.LOCK_OPEN;
      if (!ident) return;
      for (const k in this.room.attrs) {
        if (this.room.attrs[k] !== ident) continue;
        const [c, r] = k.split(",").map(Number);
        if (this.room.cell(c, r) === T.LOCK) this.room.cells[r][c] = T.LOCK_OPEN;
      }
    }

    /// Οι πλάκες πίεσης κρατούν ανοιχτές τις πύλες του καναλιού τους. Το
    /// κιβώτιο πάνω τους (PLATE_DOWN) τις κρατά πατημένες χωρίς εσένα.
    platesStep() {
      const [bc, br] = this.bodyCell();
      const held = new Set(), chans = new Set();
      for (const k in this.room.attrs) {
        const [c, r] = k.split(",").map(Number);
        const v = this.room.cell(c, r);
        if (v !== T.PLATE && v !== T.PLATE_DOWN) continue;
        const ch = this.room.attrs[k];
        chans.add(ch);
        if (v === T.PLATE_DOWN || (c === bc && r === br)) held.add(ch);
      }
      for (const ch of chans) {
        const want = held.has(ch);
        if (this.plateOn[ch] === want) continue;
        this.plateOn[ch] = want;
        this.setGates(ch, want);
      }
    }

    setGates(channel, opened) {
      for (const [c, r] of this.room.gateCells(channel))
        this.room.cells[r][c] = opened ? T.GATE_OPEN : T.GATE;
    }

    toggleGates(channel) {
      for (const [c, r] of this.room.gateCells(channel)) {
        this.room.cells[r][c] = this.room.cells[r][c] === T.GATE ? T.GATE_OPEN : T.GATE;
      }
    }
    aheadCell() {
      const rs = D.RSTEP[this.g];
      return [Math.floor((this.x + rs[0] * this.face * D.CELL) / D.CELL),
              Math.floor((this.y + rs[1] * this.face * D.CELL - D.GRID_Y0) / D.CELL)];
    }
    use() {
      const sc = this.supportCell();
      const st = sc ? this.room.cell(sc[0], sc[1]) : T.EMPTY;
      // ΤΟ ΚΛΕΙΔΙ ΤΑΙΡΙΑΖΕΙ Ή ΔΕΝ ΑΝΟΙΓΕΙ — αλλιώς ο σχεδιαστής δεν μπορεί
      // να επιβάλει σειρά, που είναι όλο το puzzle.
      // Η πόρτα πρώτη, και από το κελί του ΣΩΜΑΤΟΣ: στην πόρτα στέκεσαι
      // ΜΕΣΑ, δεν την πατάς.
      const [ec, er] = this.bodyCell();
      if (this.room.cell(ec, er) === T.EXIT) { this.won = true; return true; }

      const kid = sc ? this.room.attr(sc[0], sc[1]) : 0;
      if (st === T.LOCK && this.keys[kid]) {
        this.keys[kid]--;
        this.openLocks(sc, kid);
        return true;
      }
      const [col, row] = this.bodyCell();
      if (this.room.cell(col, row) === T.TELEPORT) return this.teleport(col, row);
      if (this.carry) return this.drop();
      // Από το κελί ΤΟΥ ΣΩΜΑΤΟΣ: το κιβώτιο δεν είναι στερεό, οπότε δεν
      // στέκεσαι ποτέ πάνω του — στέκεσαι ΜΕΣΑ του.
      const bt = this.room.cell(col, row);
      if (bt === T.CRATE) { this.room.cells[row][col] = T.EMPTY; this.carry = 1; return true; }
      if (bt === T.PLATE_DOWN) {
        this.room.cells[row][col] = T.PLATE; this.carry = 1; return true;
      }
      return false;
    }
    drop() {
      // ΕΚΕΙ ΠΟΥ ΣΤΕΚΕΣΑΙ, όχι μπροστά: το κιβώτιο δεν είναι στερεό και δεν
      // σε εμποδίζει να μείνεις στο ίδιο κελί.
      const [c, r] = this.bodyCell();
      if (c < 0 || r < 0 || c >= D.COLS || r >= D.ROWS) return false;
      // ΠΑΝΩ ΣΕ ΠΛΑΚΑ η πλάκα δεν χάνεται: γίνεται πατημένη. Αν το κιβώτιο
      // έγραφε πάνω της, δεν θα υπήρχε τρόπος να το πάρεις πίσω.
      const v = this.room.cells[r][c];
      if (v === T.PLATE) this.room.cells[r][c] = T.PLATE_DOWN;
      else if (v === T.EMPTY) this.room.cells[r][c] = T.CRATE;
      else return false;
      this.carry = 0; return true;
    }
    // Στο ΔΗΛΩΜΕΝΟ κελί. Αδήλωτη τηλεμεταφορά δεν κάνει τίποτα — παλιά έψαχνε
    // "τον άλλον στο δωμάτιο", που δούλευε μόνο με ακριβώς δύο.
    teleport(col, row) {
      const d = this.room.teleports[col + "," + row];
      if (!d) return false;
      this.x = d[0] * D.CELL + D.CELL / 2;
      this.y = D.GRID_Y0 + d[1] * D.CELL + D.CELL / 2;
      this.warp = true;
      return true;
    }
    setGravity(g) { this.worldG = g; this.g = g; this.cratesOn = true; }

    // Η σειρά και οι πρόωροι τερματισμοί είναι ΑΚΡΙΒΩΣ του physics.py.update.
    // Στην πτώση το prevSupport ΔΕΝ ενημερώνεται — αυτό κρατά τη μνήμη ότι
    // ερχόμασταν από ράμπα, που χρειάζεται το align.
    update(walk, run) {
      walk = walk | 0;
      // ΖΩΝΗ ΚΛΕΙΔΩΜΑΤΟΣ: η βαρύτητα γίνεται ΚΑΤΩ και μένει εκεί — νησίδα
      // «κανονικού» παιχνιδιού μέσα στο δωμάτιο.
      if (this.noflip() && this.g !== 0) { this.g = 0; this.state = "FALL"; }
      this.platesStep();
      this.crateStep();
      this.touchObjects();
      const k = this.groundDepth(0);
      if (k === null || k > K.FEET_B + 2) { this.fallStep(); return; }
      if (this.state === "FALL") this.land();
      if (walk) {
        // Η ταχύτητα ΔΕΝ γίνεται μεγαλύτερο βήμα: τόσα βήματα του ενός pixel
        // όσα λέει ο συσσωρευτής, αλλιώς προσπερνιούνται γωνίες και ράμπες.
        this.walkAcc += K.WALK_V * (run ? 2 : 1);
        const steps = this.walkAcc >> 8;
        this.walkAcc &= 0xFF;
        for (let i = 0; i < steps; i++) this.doWalk(walk);
      }
      else if (this.slipping()) this.fallStep();
      else this.state = "IDLE";
      this.prevSupport = this.supportType();
    }
  }

  window.GRAV = { T, Room, Hero, off };
})(window.GAME_DATA);
