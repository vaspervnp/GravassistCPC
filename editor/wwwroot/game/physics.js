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
    constructor(cells) {
      this.cells = cells.map(r => r.slice());
      this.probeG = 0;
      this.gateOpen = false;
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
      if (t === T.GATE) return !this.gateOpen;
      return !!(D.PROPS[t] & D.F.SOLID);
    }
  }

  class Hero {
    constructor(room, x, y, g) {
      this.room = room; this.x = x; this.y = y; this.g = g;
      this.fallDist = 0; this.state = "FALL"; this.prevSupport = T.EMPTY;
      this.fallV = K.FALL_V0; this.fallAcc = 0;
      this.energy = K.ENERGY_MAX; this.keys = 0;
      this.parachute = 0; this.paraOpen = 0; this.won = false;
      this.crateTick = 0; this.worldG = g; this.cratesOn = false;
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
      if (this.wallAhead(d)) { this.corner(-2 * d, d, ox, oy, og); return; }
      const rs = D.RSTEP[this.g];
      this.x += rs[0] * d; this.y += rs[1] * d;
      if (this.groundDepth(0) === null) {
        this.x = ox; this.y = oy;
        this.corner(2 * d, d, ox, oy, og);
        return;
      }
      this.snap();
      this.align(d);
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
        else if (t === T.KEY) this.keys++;
      } else if (t === T.EXIT) {
        this.won = true;
      } else if (t === T.SWITCH) {
        this.room.gateOpen = !this.room.gateOpen;
        this.room.cells[row][col] = T.EMPTY;
      }
      const st = this.supportType();
      if ((D.PROPS[st] & D.F.DEADLY) && (D.FACING[st] + 4) % 8 === this.g) this.hurt(K.SPIKE_DMG);
    }
    aheadCell() {
      const rs = D.RSTEP[this.g];
      return [Math.floor((this.x + rs[0] * this.face * D.CELL) / D.CELL),
              Math.floor((this.y + rs[1] * this.face * D.CELL - D.GRID_Y0) / D.CELL)];
    }
    use() {
      const sc = this.supportCell();
      const st = sc ? this.room.cell(sc[0], sc[1]) : T.EMPTY;
      if (st === T.LOCK && this.keys) {
        this.keys--; this.room.cells[sc[1]][sc[0]] = T.LOCK_OPEN; return true;
      }
      const [col, row] = this.bodyCell();
      if (this.room.cell(col, row) === T.TELEPORT) return this.teleport(col, row);
      if (this.carry) return this.drop();
      if (st === T.CRATE) { this.room.cells[sc[1]][sc[0]] = T.EMPTY; this.carry = 1; return true; }
      return false;
    }
    drop() {
      const [c, r] = this.aheadCell();
      if (c < 0 || r < 0 || c >= D.COLS || r >= D.ROWS) return false;
      if (this.room.cells[r][c] !== T.EMPTY) return false;
      this.room.cells[r][c] = T.CRATE; this.carry = 0; return true;
    }
    teleport(col, row) {
      for (let r = 0; r < D.ROWS; r++)
        for (let c = 0; c < D.COLS; c++)
          if ((c !== col || r !== row) && this.room.cells[r][c] === T.TELEPORT) {
            this.x = c * D.CELL + D.CELL / 2;
            this.y = D.GRID_Y0 + r * D.CELL + D.CELL / 2;
            this.warp = true;
            return true;
          }
      return false;
    }
    setGravity(g) { this.worldG = g; this.g = g; this.cratesOn = true; }

    // Η σειρά και οι πρόωροι τερματισμοί είναι ΑΚΡΙΒΩΣ του physics.py.update.
    // Στην πτώση το prevSupport ΔΕΝ ενημερώνεται — αυτό κρατά τη μνήμη ότι
    // ερχόμασταν από ράμπα, που χρειάζεται το align.
    update(walk) {
      walk = walk | 0;
      this.crateStep();
      this.touchObjects();
      const k = this.groundDepth(0);
      if (k === null || k > K.FEET_B + 2) { this.fallStep(); return; }
      if (this.state === "FALL") this.land();
      if (walk) this.doWalk(walk);
      else if (this.slipping()) this.fallStep();
      else this.state = "IDLE";
      this.prevSupport = this.supportType();
    }
  }

  window.GRAV = { T, Room, Hero, off };
})(window.GAME_DATA);
