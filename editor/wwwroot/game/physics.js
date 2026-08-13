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

  // Ζεύγη «κλειστό -> ανοιχτό» για κάθε στόχο καλωδίωσης. «Ανοιχτό» σημαίνει
  // το ίδιο και για τα τρία είδη: δεν σε εμποδίζει πια.
  const OPEN_OF = {
    [T.GATE]: T.GATE_OPEN,
    [T.LOCK]: T.LOCK_OPEN,
    [T.SPIKE_U]: T.SPIKE_U_OFF, [T.SPIKE_L]: T.SPIKE_L_OFF,
    [T.SPIKE_D]: T.SPIKE_D_OFF, [T.SPIKE_R]: T.SPIKE_R_OFF,
  };
  const SHUT_OF = {};
  for (const k in OPEN_OF) SHUT_OF[OPEN_OF[k]] = +k;

  class Room {
    constructor(cells, teleports, attrs, turretArg) {
      this.cells = cells.map(r => r.slice());
      this.probeG = 0;
      // Ιδιότητα ανά κελί: κανάλι για διακόπτες/πόρτες, ταυτότητα για
      // κλειδιά/κλειδαριές. Η πόρτα ΔΕΝ είναι πια καθολική σημαία — κάθε
      // κελί κρατά την κατάστασή του, όπως και στον Amstrad.
      this.attrs = attrs || {};           // "c,r" -> 0..ATTR_MAX-1
      this.teleports = teleports || {};   // "c,r" -> [dc, dr]
      // Πυργίσκοι: "c,r" -> [φόρτιση, αυτόματο διάστημα] σε δευτερόλεπτα.
      this.turretArg = turretArg || {};
    }
    // ΜΟΝΟ τα χαμηλά 3 bits: το bit 3 είναι η σημαία «ανοίγει μόνη της».
    attr(c, r) { return (this.attrs[c + "," + r] || 0) & 7; }
    autoLock(c, r) { return !!((this.attrs[c + "," + r] || 0) & K.LOCK_AUTO); }
    hasAutoLock(ident) {
      for (const k in this.attrs) {
        const v = this.attrs[k];
        if ((v & 7) !== ident || !(v & K.LOCK_AUTO)) continue;
        const [c, r] = k.split(",").map(Number);
        const cv = this.cell(c, r);
        if (cv === T.LOCK || cv === T.LOCK_OPEN) return true;
      }
      return false;
    }
    // ΕΝΑΣ κόσμος αριθμών: κάθε ενεργοποιητής (διακόπτης, πλάκα, κλειδί)
    // δρα σε κάθε στόχο (πύλη, κλειδαριά, αγκάθια) με τον ίδιο αριθμό.
    targetCells(channel) {
      const out = [];
      if (!channel) return out;         // 0 = ακαλωδίωτο
      for (const k in this.attrs) {
        if ((this.attrs[k] & 7) !== channel) continue;
        const [c, r] = k.split(",").map(Number);
        if (OPEN_OF[this.cell(c, r)] !== undefined ||
            SHUT_OF[this.cell(c, r)] !== undefined) out.push([c, r]);
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
      // --- πυργίσκοι, μεταγραφή του tools/physics.py ---
      // Το ρολόι είναι σε VSYNC και όχι σε ενημερώσεις: μια ενημέρωση κοστίζει
      // 3, 4 ή 7 ανάλογα με το τι κάνει ο παίκτης, οπότε μόνο έτσι σημαίνουν
      // τα «5 δευτερόλεπτα» το ίδιο με τον Amstrad, που διαβάζει το ρολόι του
      // firmware. Ο ίδιος κανόνας που χρησιμοποιεί ο cpcClock του run.js.
      this.clock = 0;
      this.arrows = [];                 // {x, y, dx, dy, gone}
      this.turretReady = {};            // "c,r" -> ρολόι από το οποίο ξαναρίχνει
      this.keyAutoMsg = false;
      this.parachute = 0; this.paraOpen = 0; this.won = false;
      this.crateTick = 0; this.walkAcc = 0; this.worldG = g; this.cratesOn = false;
      this.face = 1; this.carry = 0; this.warp = false;
      // Ήχοι που «γεννήθηκαν» σε αυτό το καρέ. Ο run.js τα παίζει και τα
      // αδειάζει· το μοντέλο δεν ξέρει τίποτα για ήχο.
      this.sfx = []; this.stepPx = 0; this.crateMoved = false;
      // ΣΥΜΒΑΝΤΑ ΓΙΑ ΤΟ ΣΚΟΡ, χωριστά από τον ήχο. Ο ίδιος διαχωρισμός με τον
      // Amstrad: το hero.asm ανιχνεύει, το score.asm βαθμολογεί. Ο ήχος δεν
      // αρκεί ως σήμα — τα κλειδιά και τα κιβώτια δεν κάνουν θόρυβο, και το
      // «plate» παίζει και όταν την πατάς εσύ, όχι μόνο με κιβώτιο.
      this.events = [];
      this.hurtLeft = 0;
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
      if (this.paraOpen) {
        this.parachute--; this.paraOpen = 0;
        this.events.push("paraland");
      }
      else if (this.fallDist > K.FALL_SAFE) {
        this.events.push("landhard");
        this.hurt(1 + Math.floor((this.fallDist - K.FALL_SAFE) / 12));
      }
      this.fallDist = 0; this.fallV = K.FALL_V0; this.fallAcc = 0;
    }
    // Άτρωτος για HURT_FRAMES καρέ μετά από κάθε χτύπημα: αλλιώς η ζημιά
    // ερχόταν ξανά όσο ακουμπούσες και η ενέργεια εξατμιζόταν.
    hurt(n) {
      if (this.hurtLeft) return;
      this.energy = Math.max(0, this.energy - n);
      this.hurtLeft = K.HURT_FRAMES;
      this.sfx.push("hurt");
    }

    // --- αντικείμενα ------------------------------------------------
    crateStep() {
      if (!this.cratesOn) return;
      if (++this.crateTick < K.CRATE_TICKS) return;
      this.crateTick = 0;
      const [dx, dy] = D.GSTEP[this.worldG];
      const cells = [];
      let moved = false;
      for (let r = 0; r < D.ROWS; r++)
        for (let c = 0; c < D.COLS; c++)
          if (this.room.cells[r][c] === T.CRATE) cells.push([c, r]);
      // Τα πιο μακριά κατά τη βαρύτητα πρώτα, αλλιώς μια στοίβα δεν ξεκολλάει.
      cells.sort((a, b) => (b[0] * dx + b[1] * dy) - (a[0] * dx + a[1] * dy));
      for (const [c, r] of cells) {
        const nc = c + dx, nr = r + dy;
        if (nc < 0 || nr < 0 || nc >= D.COLS || nr >= D.ROWS) continue;
        // ΚΑΙ ΠΑΝΩ ΣΕ ΠΛΑΚΑ: το κιβώτιο που πέφτει την πατάει, όπως κι αν
        // το άφηνες εκεί με το χέρι.
        const dest = this.room.cells[nr][nc];
        if (dest !== T.EMPTY && dest !== T.PLATE) continue;
        this.room.cells[r][c] = T.EMPTY;
        this.room.cells[nr][nc] = dest === T.PLATE ? T.PLATE_DOWN : T.CRATE;
        moved = true;
      }
      // Η ΑΚΜΗ, ακριβώς όπως στο src/hero.asm: ο πίνακας κελιών δεν έχει πού
      // να κρατήσει «έπεφτα» ανά κιβώτιο, οπότε ο ήχος είναι ένας για όλα.
      if (this.crateMoved && !moved) this.sfx.push("thud");
      this.crateMoved = moved;
    }
    touchObjects() {
      const [col, row] = this.bodyCell();
      const t = this.room.cell(col, row);
      if (D.PROPS[t] & D.F.PICKUP) {
        this.room.cells[row][col] = T.EMPTY;
        if (t === T.ENERGY) this.energy = Math.min(K.ENERGY_MAX, this.energy + K.ENERGY_PICK);
        else if (t === T.PARACHUTE) this.parachute++;
        else if (t === T.KEY) {
          const kid = this.room.attr(col, row);
          this.keys[kid]++;
          this.events.push("key");
          // Το μήνυμα βγαίνει ΜΑΖΕΥΟΝΤΑΣ το κλειδί: εκεί μαθαίνεις ότι δεν θα
          // χρειαστεί να πατήσεις τίποτα.
          if (this.room.hasAutoLock(kid)) this.keyAutoMsg = true;
        }
      } else if ((D.PROPS[t] & D.F.SWITCH) &&
                 (col + "," + row) !== this.prevBody &&
                 (D.FACING[t] + 4) % 8 === this.g) {
        // ΜΙΑ ΣΗΜΑΙΑ, ΟΧΙ ΟΚΤΩ ΣΥΓΚΡΙΣΕΙΣ, και μόνο από τη δική του πλευρά —
        // ίδιος κανόνας με τα αγκάθια. Περνώντας μπροστά από διακόπτη
        // ταβανιού με βαρύτητα κάτω δεν συμβαίνει τίποτα.
        // Και δείχνει την κατάστασή του: off <-> on.
        this.room.cells[row][col] = D.SWITCH_FLIP[t];
        // ΤΟ ΠΑΤΑΣ, ΔΕΝ ΤΟ ΞΟΔΕΥΕΙΣ: γυρίζει κάθε πόρτα του καναλιού του και
        // μένει εκεί. Ακμή και όχι κράτημα, αλλιώς οι πόρτες ανοιγοκλείνουν
        // 50 φορές το δευτερόλεπτο.
        this.sfx.push("switch");
        this.events.push("switch");
        this.toggleTargets(this.room.attr(col, row));
      }
      this.prevBody = col + "," + row;

      // ΑΥΤΟΜΑΤΗ ΚΛΕΙΔΑΡΙΑ: ανοίγει μόλις την πατήσεις με το κλειδί της.
      const asc = this.supportCell();
      if (asc && this.room.cell(asc[0], asc[1]) === T.LOCK &&
          this.room.autoLock(asc[0], asc[1])) {
        const kid = this.room.attr(asc[0], asc[1]);
        if (this.keys[kid]) { this.keys[kid]--; this.openLocks(asc, kid); }
      }

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
      this.sfx.push("unlock");
      this.events.push("lock");
      const here = this.room.cells[cell[1]][cell[0]];
      this.room.cells[cell[1]][cell[0]] =
        OPEN_OF[here] !== undefined ? OPEN_OF[here] : T.LOCK_OPEN;
      if (!ident) return;
      // ΚΑΙ ΠΥΛΕΣ, ΜΟΝΙΜΑ: ο διακόπτης γυρίζει, η πλάκα κρατά όσο πατιέται,
      // το κλειδί ανοίγει και ξοδεύεται.
      this.setTargets(ident, true);
    }

    /// Οι πλάκες πίεσης κρατούν ανοιχτές τις πύλες του καναλιού τους. Το
    /// κιβώτιο πάνω τους (PLATE_DOWN) τις κρατά πατημένες χωρίς εσένα.
    // --- ΠΥΡΓΙΣΚΟΙ -----------------------------------------------------
    heroBox() {
      if (this.g === 0 || this.g === 4) return [K.WALL_A, K.FEET_B];
      if (this.g === 2 || this.g === 6) return [K.FEET_B, K.WALL_A];
      return [K.FEET_B, K.FEET_B];
    }

    arrowHitsHero(ax, ay) {
      const [hw, hh] = this.heroBox();
      return Math.abs(ax - this.x) <= hw && Math.abs(ay - this.y) <= hh;
    }

    // Οι μονόδρομες μετράνε ΠΑΝΤΑ στερεές για βέλος: το solidAt τις κρίνει από
    // τη φορά της βαρύτητας του ελέγχου, που για ένα βέλος δεν σημαίνει τίποτα.
    arrowBlocked(px, py) {
      if (px < 0 || py < D.GRID_Y0) return true;
      const c = Math.floor(px / D.CELL);
      const r = Math.floor((py - D.GRID_Y0) / D.CELL);
      if (c >= D.COLS || r >= D.ROWS) return true;
      const t = this.room.cells[r][c];
      const mask = D.RAMP_MASK[t];
      if (mask) return !!mask[(py - D.GRID_Y0) % D.CELL][px % D.CELL];
      return !!(D.PROPS[t] & (D.F.SOLID | D.F.ONEWAY));
    }

    arrowDamage(gone) {
      const third = Math.floor(K.TURRET_RANGE / 3);
      if (gone < third) return K.ARROW_DMG[0];
      if (gone < 2 * third) return K.ARROW_DMG[1];
      return K.ARROW_DMG[2];
    }

    // ΕΝΑ PIXEL ΤΗ ΦΟΡΑ, ποτέ πήδημα των έξι: αλλιώς ένα βέλος περνάει μέσα
    // από τοίχο λεπτότερο από έξι pixel και προσπερνά τον ήρωα.
    arrowsStep() {
      const alive = [];
      for (const a of this.arrows) {
        let dead = false;
        for (let i = 0; i < K.ARROW_STEP; i++) {
          a.x += a.dx; a.y += a.dy; a.gone++;
          if (a.gone >= K.TURRET_RANGE) { dead = true; break; }
          if (this.arrowHitsHero(a.x, a.y)) {
            this.hurt(this.arrowDamage(a.gone));
            this.sfx.push("hurt");
            dead = true; break;
          }
          if (this.arrowBlocked(a.x, a.y)) { dead = true; break; }
        }
        if (!dead) alive.push(a);
      }
      this.arrows = alive;
    }

    // ΑΠΟ ΤΟ ΣΤΟΜΙΟ, ΟΧΙ ΑΠΟ ΤΟ ΚΕΝΤΡΟ: ο πυργίσκος είναι στερεός.
    turretLos(sx, sy, dx, dy) {
      let x = sx, y = sy;
      for (let i = 0; i < K.TURRET_RANGE; i++) {
        if (this.arrowHitsHero(x, y)) return true;
        if (this.arrowBlocked(x, y)) return false;
        x += dx; y += dy;
      }
      return false;
    }

    turretStep() {
      if (this.arrows.length >= K.TURRET_MAX) return;
      // Ο πίνακας χτίζεται ΜΙΑ φορά ανά αίθουσα: το πλέγμα είναι 960 κελιά και
      // ο έλεγχος γίνεται σε κάθε ενημέρωση.
      if (!this.room.turrets) {
        this.room.turrets = [];
        for (let r = 0; r < D.ROWS; r++)
          for (let c = 0; c < D.COLS; c++) {
            const t = this.room.cells[r][c];
            // ΚΑΙ ΟΙ ΣΒΗΣΤΟΙ: ο διακόπτης τους ανάβει μέσα στην παρτίδα και
            // η λίστα χτίζεται μία φορά.
            if (t === T.TURRET_V || t === T.TURRET_H
                || t === T.TURRET_V_OFF || t === T.TURRET_H_OFF)
              this.room.turrets.push([c, r]);
          }
      }
      for (const [c, r] of this.room.turrets) {
        const t = this.room.cells[r][c];
        if (t === T.TURRET_V_OFF || t === T.TURRET_H_OFF) continue;
        const key = c + "," + r;
        if (this.clock < (this.turretReady[key] || 0)) continue;
        // ΔΥΟ ΤΡΟΠΟΙ: αυτόματα=0 ρίχνει μόνο όταν σε βλέπει, με τη φόρτισή
        // του· αυτόματα>0 ρίχνει με ρυθμό, χωρίς οπτική επαφή ή εμβέλεια.
        const [cool, auto] = this.room.turretArg[key] || [K.TURRET_COOL, 0];
        const cx = c * D.CELL + (D.CELL >> 1);
        const cy = D.GRID_Y0 + r * D.CELL + (D.CELL >> 1);
        let d, dx, dy;
        if (t === T.TURRET_V) { d = this.y - cy; dx = 0; dy = d > 0 ? 1 : -1; }
        else { d = this.x - cx; dx = d > 0 ? 1 : -1; dy = 0; }
        if (d === 0) { dx = t === T.TURRET_V ? 0 : 1; dy = t === T.TURRET_V ? 1 : 0; }
        const sx = cx + dx * ((D.CELL >> 1) + 1);
        const sy = cy + dy * ((D.CELL >> 1) + 1);
        if (!auto) {
          if (d === 0 || Math.abs(d) > K.TURRET_RANGE) continue;
          if (!this.turretLos(sx, sy, dx, dy)) continue;
        }
        this.arrows.push({ x: sx, y: sy, dx: dx, dy: dy, gone: 0 });
        this.turretReady[key] = this.clock + (auto || cool) * 50;
        if (this.arrows.length >= K.TURRET_MAX) return;
      }
    }

    platesStep() {
      const [bc, br] = this.bodyCell();
      const held = new Set(), chans = new Set();
      for (const k in this.room.attrs) {
        const [c, r] = k.split(",").map(Number);
        const v = this.room.cell(c, r);
        if (v !== T.PLATE && v !== T.PLATE_DOWN) continue;
        const ch = this.room.attrs[k] & 7;
        chans.add(ch);
        if (v === T.PLATE_DOWN || (c === bc && r === br)) held.add(ch);
      }
      for (const ch of chans) {
        const want = held.has(ch);
        if (this.plateOn[ch] === want) continue;
        this.plateOn[ch] = want;
        if (want) this.sfx.push("plate");
        this.setTargets(ch, want);
      }
    }

    setTargets(channel, opened) {
      let changed = false;
      for (const [c, r] of this.room.targetCells(channel)) {
        const cur = this.room.cells[r][c];
        const want = opened ? (OPEN_OF[cur] !== undefined ? OPEN_OF[cur] : cur)
                            : (SHUT_OF[cur] !== undefined ? SHUT_OF[cur] : cur);
        if (want === cur) continue;
        // ΜΟΝΟ ΤΟ ΑΝΟΙΓΜΑ ΠΛΗΡΩΝΕΙ: το κλείσιμο της πύλης όταν φεύγεις από
        // την πλάκα δεν είναι πρόοδος.
        if (opened && cur === T.GATE) this.events.push("gate");
        this.room.cells[r][c] = want;
        changed = true;
      }
      // ΕΝΑΣ ήχος ανά ενέργεια, όχι ένας ανά στόχο: τέσσερις πύλες στο ίδιο
      // κανάλι θα έδιναν ριπή από τέσσερα «άνοιξε».
      if (changed) this.sfx.push("gate");
    }

    toggleTargets(channel) {
      let changed = false;
      for (const [c, r] of this.room.targetCells(channel)) {
        const cur = this.room.cells[r][c];
        const want = OPEN_OF[cur] !== undefined ? OPEN_OF[cur] : SHUT_OF[cur];
        if (want === undefined) continue;
        if (cur === T.GATE) this.events.push("gate");
        this.room.cells[r][c] = want;
        changed = true;
      }
      if (changed) this.sfx.push("gate");
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
      // ΚΑΙ Η ΠΥΛΗ: στέκεσαι πάνω της και πατάς ενεργοποίηση, όπως στο
      // λουκέτο. Το κλειδί άνοιγε ήδη πύλες του καναλιού του ξεκλειδώνοντας
      // λουκέτο — το να μην ανοίγει αυτήν που πατάς ήταν ασυνέπεια.
      if ((st === T.LOCK || st === T.GATE) && this.keys[kid]) {
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
      if (bt === T.CRATE) {
        this.room.cells[row][col] = T.EMPTY; this.carry = 1;
        this.events.push("crate"); return true;
      }
      if (bt === T.PLATE_DOWN) {
        this.room.cells[row][col] = T.PLATE; this.carry = 1;
        this.events.push("crate"); return true;
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
      if (v === T.PLATE) {
        this.room.cells[r][c] = T.PLATE_DOWN;
        this.events.push("plate");
      }
      else if (v === T.EMPTY) this.room.cells[r][c] = T.CRATE;
      else return false;
      this.carry = 0; this.sfx.push("drop"); return true;
    }
    // Στο ΔΗΛΩΜΕΝΟ κελί. Αδήλωτη τηλεμεταφορά δεν κάνει τίποτα — παλιά έψαχνε
    // "τον άλλον στο δωμάτιο", που δούλευε μόνο με ακριβώς δύο.
    teleport(col, row) {
      const d = this.room.teleports[col + "," + row];
      if (!d) return false;
      this.x = d[0] * D.CELL + D.CELL / 2;
      this.y = D.GRID_Y0 + d[1] * D.CELL + D.CELL / 2;
      this.warp = true;
      this.sfx.push("tele");
      return true;
    }
    setGravity(g) { this.worldG = g; this.g = g; this.cratesOn = true; }

    // Η σειρά και οι πρόωροι τερματισμοί είναι ΑΚΡΙΒΩΣ του physics.py.update.
    // Στην πτώση το prevSupport ΔΕΝ ενημερώνεται — αυτό κρατά τη μνήμη ότι
    // ερχόμασταν από ράμπα, που χρειάζεται το align.
    update(walk, run) {
      walk = walk | 0;
      // Το κόστος αυτής της ενημέρωσης σε vsync, ΜΕ ΤΟΝ ΙΔΙΟ ΚΑΝΟΝΑ που
      // χρησιμοποιεί ο cpcClock του run.js. Από εδώ βγαίνει η φόρτιση.
      this.clock += walk ? (run ? K.CPC_VSYNC_RUN : K.CPC_VSYNC_WALK)
                         : K.CPC_VSYNC_IDLE;
      // ΖΩΝΗ ΚΛΕΙΔΩΜΑΤΟΣ: η βαρύτητα γίνεται ΚΑΤΩ και μένει εκεί — νησίδα
      // «κανονικού» παιχνιδιού μέσα στο δωμάτιο.
      if (this.noflip() && this.g !== 0) { this.g = 0; this.state = "FALL"; }
      this.events.length = 0;
      // ΤΟ ΑΔΕΙΑΣΜΑ ΠΡΩΤΑ. Ήταν μετά το platesStep(), που σημαίνει ότι οι
      // ήχοι «πλάκα» και «πύλη» σβήνονταν στην ίδια γραμμή που γεννιόντουσαν
      // — οι πλάκες ήταν βουβές στη δοκιμή του browser.
      this.sfx.length = 0;
      this.platesStep();
      if (this.hurtLeft) this.hurtLeft--;
      this.crateStep();
      // ΠΑΝΩ ΑΠΟ ΤΗΝ ΠΡΟΩΡΗ ΕΞΟΔΟ στο fallStep, όπως το crateStep: ένα βέλος
      // σε βρίσκει και στον αέρα.
      this.arrowsStep();
      this.turretStep();
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
        for (let i = 0; i < steps; i++) {
          this.doWalk(walk);
          // ΑΝΑ 32 PIXEL. Ο αριθμός δεν είναι αυθαίρετος: στον Amstrad ο ήχος
          // δένεται στα δύο καρέ επαφής του οκτάκαρου κύκλου βάδισης, που
          // διαρκεί 64 px — δηλαδή ένα πάτημα ανά 32 px. Ανά κελί (8 px) ο
          // browser έβγαζε 15 βήματα το δευτερόλεπτο, πενταπλάσια από το
          // παιχνίδι, και ακουγόταν σαν πολυβόλο.
          if (++this.stepPx >= 32) { this.stepPx = 0; this.sfx.push("step"); }
        }
      }
      else if (this.slipping()) this.fallStep();
      else this.state = "IDLE";
      this.prevSupport = this.supportType();
    }
  }

  window.GRAV = { T, Room, Hero, off };
})(window.GAME_DATA);
