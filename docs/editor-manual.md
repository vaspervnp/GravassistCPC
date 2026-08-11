# GRAVASSIST level editor — user manual

The editor is a web application that runs on your own machine. You draw a room on a
40x24 grid, wire up its doors, teleporters, switches and locks, test it in the browser,
and build a real Amstrad `.dsk` from it.

This manual is written in English because the editor's interface is in English. The rest
of the project documentation is in Greek.

**Contents**

1. [Getting in](#1-getting-in)
2. [The screen](#2-the-screen)
3. [Drawing](#3-drawing)
4. [Cell types](#4-cell-types)
5. [Rooms](#5-rooms)
6. [Doors between rooms](#6-doors-between-rooms)
7. [Teleporters](#7-teleporters)
8. [Switches, pressure plates and gates](#8-switches-pressure-plates-and-gates)
9. [Keys and locks](#9-keys-and-locks)
10. [Gravity](#10-gravity)
11. [Saving](#11-saving)
12. [Testing in the browser](#12-testing-in-the-browser)
13. [Building the disk](#13-building-the-disk)
14. [The file format](#14-the-file-format)
15. [Limits](#15-limits)
16. [Sharing your rooms](#16-sharing-your-rooms)
17. [Administration](#17-administration)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Getting in

Open <http://localhost:5202>. **Signing in is mandatory** — there is no anonymous mode.
Signing in proves who you are; it does not by itself grant access.

There are two ways in, and they end up in exactly the same place:

- **Sign in with Google.**
- **Sign in with an email address.** No password: you type your address, a **six-digit
  code** arrives by email, you type it in. The code lasts 10 minutes, works once, and
  allows five wrong guesses before it is thrown away. This option only appears if the
  administrator has configured mail.

A new address can ask to join from the same form — that is how you register.

- If your account is **allowed**, you go straight to the editor.
- If it is not, you land on a **Waiting for approval** page. Your address is recorded so
  the administrator can see the request and approve it. Nothing is created for you until
  they do. See [§17](#17-administration).

Once you are in, you get **your own folder** under `levels/`, named after your account.
The first time it is created, every existing `*.txt` in the shared `levels/` folder is
copied into it, so you start from the current rooms rather than an empty page. From then
on your folder is yours alone — nobody else's saves touch it, and yours touch nobody
else's.

The header shows the absolute path of your folder, your name, and a **Sign out** link.
The session cookie lasts 14 days and renews as you work.

---

## 2. The screen

**Header** — title, your levels folder, your account.

**Six panels across the top:**

| Panel | What it is for |
|---|---|
| **File** | Open, create, copy, renumber, test, build, save. Also the room's **Start gravity**. |
| **Exits** | One row per door. Destination room, two-way flag, arrival point, arrival gravity. |
| **Switches & gates** | One row per switch, pressure plate and gate. Channel numbers. |
| **Keys & locks** | One row per key and lock. Identity numbers, and the `auto` flag. |
| **Teleporters** | One row per teleporter. Destination cell. |
| **Tools** | Brush / Eraser / Fill, Border, Clear, Undo, Redo, Grid, and the Pan arrows. |

**The grid** — 40 columns x 24 rows, the whole playfield. The game's HUD sits above the
playfield on the real machine; it is not part of the grid, so row 0 here is the topmost
playfield row.

**Below the grid** — the **status line** and the **hover readout**.

The status line is colour-coded and it is worth learning:

| Colour | Meaning |
|---|---|
| **Green** | It worked. |
| **Red** | It was refused. Nothing was written. |
| **Yellow** | It happened but with a caveat — or the editor is waiting for you to click on the grid. |
| **Grey-blue** | Neutral chatter. |

The readout under it shows, for whatever cell the pointer is over:
`col 12, row 7  ·  Solid '#'`.

**Cell types** — the palette, on the right of the grid. It is sticky and scrolls
independently.

**Level source text** — at the bottom, the raw 24x40 character map, exactly as it will be
written to disk. Useful for spotting a stray character.

---

## 3. Drawing

| Action | How |
|---|---|
| Paint | Left click, or click and drag |
| Erase | **Right click** — with any tool selected |
| Choose a cell type | Click it in the palette, **or press its character** (`#`, `/`, `k`, …) |
| Flood fill | **Fill** tool, then click. Right click floods with empty. |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y`, or the buttons |
| Cancel a pending pick | `Esc` |

One drag is **one** undo step, not one per cell. The undo stack holds 100 steps and
restores the wiring and the start gravity too, not just the cells. Opening a file clears
it.

**Tools**

- **Brush** — paints the selected cell type.
- **Eraser** — paints empty. Selecting a cell type from the palette switches you back to
  Brush automatically.
- **Fill** — 4-neighbour flood fill of the contiguous region you click on.

**Buttons**

- **Border** — draws a solid frame around the room.
- **Clear** — empties everything. **There is no confirmation**; `Ctrl+Z` is your only way
  back.
- **Grid** — toggles the grid lines. Purely visual.
- **Pan ← ↑ ↓ →** — shifts the *whole room* one cell, cells and every wiring coordinate
  that points at them. If anything would fall off the edge it refuses and tells you:
  *"Pan stopped: something would fall off the edge."* Nothing is ever lost silently.

**Keyboard**

Every cell type is bound to its own character; uppercase ones need `Shift`. The letter
keys also work by physical position, so a Greek keyboard layout does not break the
shortcuts. `Ctrl+Z` and `Ctrl+Y` are undo and redo. `Esc` cancels a destination pick.
There are no shortcuts for Save, Test or Build.

---

## 4. Cell types

Thirty types in five groups. The character is what appears in the `.txt` file and what
you press to select the type.

### Geometry

| Char | Name | Behaviour |
|---|---|---|
| `.` | Empty | Air — the hero passes through freely. |
| `#` | Solid | Full 8x8 material — floor, wall or ceiling. |
| `/` | Ramp ↗ | Solid bottom-right — floor rising to the right. |
| `\` | Ramp ↘ | Solid bottom-left — floor dropping to the right. |
| `7` | Ceiling ↘ | Solid top-right — ceiling dropping to the right. |
| `F` | Ceiling ↗ | Solid top-left — ceiling rising to the right. |

Ramps are drawn as triangles with the correct slope, not as letters, so you see the
geometry the hero will actually meet.

### Hazards

| Char | Name | Behaviour |
|---|---|---|
| `^` | Spikes ↑ | Points up, base at the bottom. Solid, but deadly from above. |
| `v` | Spikes ↓ | Points down, base at the top. |
| `<` | Spikes ← | Points left, base on the right. |
| `>` | Spikes → | Points right, base on the left. |

Spikes drain energy while you are in contact, not instantly.

### Surfaces & zones

| Char | Name | Behaviour |
|---|---|---|
| `-` | One-way ↑ | Solid only from above — you pass through going up from below. |
| `_` | One-way ↓ | Solid only from below — you pass through going down from above. |
| `[` | One-way ← | Solid only from the left — you pass through moving left. |
| `]` | One-way → | Solid only from the right — you pass through moving right. |
| `:` | Gravity-lock zone | Inside it gravity does **not** change and the hero does not turn — gravity is forced down. Not solid. |
| `%` | Fragile | Solid that collapses shortly after you step on it. |

### Items

| Char | Name | Behaviour |
|---|---|---|
| `X` | Exit | A door. Its destination is set in the **Exits** panel — see [§6](#6-doors-between-rooms). |
| `+` | Energy | Pickup: +2 energy. |
| `P` | Parachute | Pickup: cancels fall damage. |
| `k` | Key | Pickup: opens the locks with the matching identity. |
| `T` | Teleporter | Sends you to another cell of the **same** room. |
| `B` | Crate | **Not solid.** You walk through it, pick it up with the action key and drop it where you stand. Crates fall with gravity and stack on solids. |

### Mechanisms

| Char | Name | Behaviour |
|---|---|---|
| `@` | Start position | Where the player starts. The cell is empty in the game. **At most one per room.** |
| `K` | Lock | Solid until you have the matching key. |
| `\|` | Lock opened | The unlocked state: still visible, but you pass through it. |
| `G` | Gate | Solid while closed; opened by a switch or a pressure plate. |
| `g` | Gate opened | The open state: still visible, but you pass through it. |
| `S` | Switch | Toggle — permanently flips the state of its gates. Step on it again to close them. |
| `p` | Pressure plate | Active only while pressed by the hero or a crate. |
| `d` | Plate with crate | A crate is holding this plate down, so its gates stay open. |

`|`, `g` and `d` are the *opened / pressed* states. You normally paint `K`, `G` and `p`
and let the game switch them; paint the open forms only when you want a room to start
that way. They keep their wiring either way.

> **Note.** The palette tooltip for **Crate** still says "solid that can be pushed". That
> text is out of date — the behaviour in the table above is what the game does.

---

## 5. Rooms

A room is a file named **`room_<N>.txt`**. The number in the file name *is* the room
number — there is no separate registry — so renumbering means renaming, and every door
that points at the room has to follow. The editor does that for you.

| Button | What it does |
|---|---|
| **Open** | Loads the file selected in the dropdown. |
| **New** | A blank 40x24 level with a solid border. Not written to disk until you save. |
| **New room** | Creates `room_<N>.txt` with the next free number and writes it immediately, so other rooms can point at it straight away. |
| **Copy** | Copies the open room to the next free number. Its own doors and teleporters are kept — they point at *other* rooms and stay valid — but **nothing points at the copy yet**. |
| **Move** | Renumbers the room: renames the file **and rewrites every `exit` line in every other file that pointed at the old number**. Type the target in the `to #` box first. |

The next free number is always the smallest unused one starting at 1.

**Move requires a clean file.** If you have unsaved changes it refuses with *"Save first:
Move works on the files."* — it operates on what is on disk, not on your screen. Copy
will offer to proceed but warns you that the **saved** file is what gets copied.

Files whose name does not match `room_<N>.txt` are ordinary levels: you can draw and save
them, but they are not part of the room chain and cannot be built or renumbered.

**There is no delete button.** Remove a file from your folder by hand if you need to.

---

## 6. Doors between rooms

Paint `X` cells. **Orthogonally adjacent `X` cells count as one door** — a 1x2 doorway is
a single door with a single destination, not two.

Each door gets a row in the **Exits** panel:

| Field | Meaning |
|---|---|
| `room` | The destination room number. **Required** — a door without one blocks the save. |
| **two-way** | Tick this if the destination room has a door leading back here. |
| **arrival** `col` `row` | Where the player appears when arriving through this door. |
| **Arrival** button | Click it, then click on the grid to pick that cell. `Esc` or right click cancels. |
| gravity | The gravity the player arrives with. `— room` means "use the destination room's start gravity". |

The destination room number is drawn on the door cells in the grid, so you can read the
map at a glance; a red `?` means it is unset. Hovering a row outlines the door and draws
a green arrow to its arrival point.

**The arrival point belongs to the door you leave through**, and it applies in the room
you arrive in. Set it, or you will appear at the destination room's start marker, which
is usually not where you want to come out. A door with a missing destination room is an
**error**; a destination room that does not exist as a file yet is only a **warning** —
useful while you are still laying out the map.

Row colours: red borders mean no destination, yellow means the destination room has no
file yet, orange wash means the editor is waiting for your grid click.

---

## 7. Teleporters

Paint `T` cells; adjacent ones again count as one teleporter. A teleporter moves you to
another cell **of the same room** — it cannot cross rooms.

In the **Teleporters** panel, either type the destination column and row, or press
**Set** and click the target cell on the grid (`Esc` or right click cancels).

Each teleporter is numbered on the grid; a yellow `?` means it has no destination. A
teleporter without a destination is a **warning**, not an error — it will simply do
nothing in the game. A destination outside the grid is an **error**.

---

## 8. Switches, pressure plates and gates

The link is a **channel number**, not a position: a switch flips every gate on the same
channel, wherever it is in the room. Give the switch and its gates the same number.

- **Switch (`S`)** — a toggle. Stepping on it flips its gates; stepping on it again flips
  them back. It is not consumed.
- **Pressure plate (`p`)** — active only while it is pressed, by the hero **or by a
  crate**. Leaving a crate on a plate is how you hold a gate open while you walk away.
- **Gate (`G`)** — solid while closed. Opened by any switch or plate on its channel.

Channels run **1–7**. **Channel 0 means unwired** and writes nothing to the file.

Hover a row to see the connection: the group and all its peers on the same channel are
boxed in yellow and joined by dashed arrows. The channel number is drawn on the cells
themselves; value 0 draws nothing.

---

## 9. Keys and locks

Same mechanism, but the number is an **identity**: key 3 opens only lock 3.

Without identities, one key opens whatever it finds and you cannot enforce an order —
which is usually the whole puzzle. A key opens **every** lock sharing its identity, all
at once.

**Identity 0 means unwired**, and such a lock opens on its own. That is deliberate: a
level full of plain locks does not fall open to a single key.

**The `auto` checkbox** (locks only) makes a lock open the moment you step on it while
carrying the matching key, without pressing anything. The default is off — you press the
action key to unlock. When a key opens `auto` locks, the game says so when you pick it
up, in every room, including past the point where hints normally stop.

---

## 10. Gravity

Gravity has **8 directions**, numbered 0–7, starting at *down* and going clockwise:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| ↓ down | ↙ down-left | ← left | ↖ up-left | ↑ up | ↗ up-right | → right | ↘ down-right |

There are three places gravity is decided, in order of precedence:

1. **Start gravity** (File panel) — what applies when the player starts in this room at
   the `@` marker. Written as the `gravity` line in the file.
2. **Arrival gravity** (per door, Exits panel) — overrides the above when the player
   enters through that door. `— room` leaves it to the room.
3. **Gravity-lock zones** (`:`) — inside one, the player cannot turn and gravity is
   forced down, whatever the walls do.

---

## 11. Saving

Type a name in the `name.txt` box and press **Save**. The editor checks the level before
sending anything, and the server checks it again before writing.

**Errors — the save is refused and nothing is written:**

- more than one start marker `@`
- a door with no declared destination room
- a teleporter pointing outside the grid
- a row that is not exactly 40 valid characters, or a level that is not exactly 24 rows
- a comment line that looks like a level row (the parser would count it as a 25th row)

**Warnings — you are asked "Save anyway?" and may proceed:**

- no start marker in the room
- a door leading to a room whose file does not exist yet
- a teleporter with no destination

What the editor guarantees about the file it writes: your header comments are preserved
exactly, every level row is exactly 40 valid characters over exactly 24 rows, and an
invalid level is never written.

**Unsaved work.** The editor tracks a dirty flag. Open, New and New room ask before
discarding; Move refuses outright; closing the tab triggers the browser's own "leave
site?" warning. **Test and Build always use the saved file**, never what is on screen —
Test reminds you of this, Build does not.

---

## 12. Testing in the browser

**Test** opens the room in a new tab and plays it with the same physics model as the real
game.

| Keys | |
|---|---|
| `Q W E` / `A D` / `Z X C` | Set gravity — the 3x3 grid of directions |
| `M` `N` or `←` `→` | Walk |
| `Shift` | Run |
| `↑` `↓` or `Space` | Action, and enter doors |
| **Restart** button | Restores the pristine room |

**What it is not.** The browser physics is a hand transcription of the reference model in
`tools/physics.py`, so it can drift; a separate parity check exists for that. The
rendering is a canvas approximation of MODE 1, not real CPC output — no AY sound, no
loader, no CPC timing. In-game hints stop after room 10, exactly as on the real machine.

Test reads all the levels in **your** folder, so it always reflects your own work.

---

## 13. Building the disk

Open a `room_<N>.txt` and press **Build .dsk**. The build starts the game from that room.

The button assembles the whole game — sprites, tables, music, the rooms compressed into
room sets, `MAIN.BIN`, the BASIC loader and the splash screen — and packs them into an
Amstrad disk image. **When it finishes, the `.dsk` downloads automatically** as
`gravassist_room<N>.dsk`.

Builds are serialised: if someone else is building, yours waits its turn. The copy you
download is taken from your own build, so you never receive somebody else's disk.

If it fails, the status line shows the **last 40 lines** of the build output — the
assembler error is in there.

**Where the build tools live.** The assembler (`rasm`) and the disk tool (`iDSK`) are not
hard-coded. They are configured in **`toolchain.json`** at the repository root:

```json
{
  "dir": "/usr/local/bin",
  "rasm": "rasm",
  "idsk": "iDSK",
  "python": "python3"
}
```

`dir` is looked in first; anything not found there is taken from `PATH`. An absolute path
under `rasm` or `idsk` overrides `dir` entirely. Environment variables
(`GRAVASSIST_RASM`, `GRAVASSIST_IDSK`) beat the file, and `make ASM=… DISK=…` beats
everything. To see what will actually run:

```
make toolchain
```

**On the Amstrad or in an emulator:** insert the disk and type

```
RUN"GRAV"
```

The loader shows the splash screen, waits about 10 seconds or for a key press, then loads
and starts the game. If the splash file is missing it skips it and continues rather than
failing.

---

## 14. The file format

A level file is plain text: comment lines, exactly 24 rows of exactly 40 characters, then
the settings. **Comments start with `;`** — not with `#`, which is a solid cell.

A real example, header and footer only:

```
;   ROOM 2 — where room 1's exit leads.
;
;   Comments with ';'. 24 rows of EXACTLY 40 characters. Settings below.

gravity 0
exit 8 5 1 0 9 6 0
exit 25 15 3 0 24 16 0
tp 18 6 9 12
tp 9 12 18 6
plate 22 6 1
gate 24 7 1
```

**`gravity <0-7>`** — the room's start gravity.

**`exit <col> <row> <room> [<two-way> [<arrCol> <arrRow> [<arrGravity>]]]`**
One line per door group; `col`/`row` identify the group. The optional fields are
**positional** — to write an arrival point you must also write the two-way flag (`0` or
`1`). So `exit 8 5 1 0 9 6 0` reads: the door at column 8, row 5 leads to room 1, is not
two-way, puts the player at column 9 row 6, arriving with gravity 0.

**`tp <col> <row> <destCol> <destRow>`** — one line per teleporter group.

**`<sw|plate|gate|lock|key> <col> <row> <value>`** — one line per wired cell. For
switches, plates and gates the value is the channel; for keys and locks it is the
identity. **A value of 0 is never written** — 0 is the default and a line for it would be
noise. For a lock, `auto` adds 8 to the value, so `lock 12 4 11` is identity 3 with auto
opening.

Everything is matched loosely — case and spacing do not matter — so hand-written lines
are read back correctly. The editor rewrites all `exit`, `tp` and wiring lines from its
own state on every save; your comments survive untouched.

---

## 15. Limits

| | |
|---|---|
| Grid | 40 columns x 24 rows, fixed |
| Room numbers | 1–9999 |
| Start markers | at most one `@` per room |
| Channels / identities | 1–7 (0 = unwired) |
| Gravity directions | 0–7 |
| Rooms per set file | 40 |
| Room set files | up to 99, so about 3960 rooms in principle |
| Undo depth | 100 steps |

The real constraint is **memory, not room count**. Each set of 40 rooms must fit in the
CPC's buffer after compression. If it does not, the build fails and says so — the message
asks for fewer or sparser rooms. Rooms with large blocks of the same cell compress well;
rooms of scattered detail do not.

---

## 16. Sharing your rooms

Everything you draw is saved in **your own folder**. Nobody else sees it, and it is not
what `git` tracks. The shared `levels/` folder is the common set: it is what the
repository stores, and what every new account is seeded from.

Moving rooms between the two is a **separate permission** that the administrator grants
per account. If you have it, two extra buttons appear in the File panel:

| Button | Direction | What it does |
|---|---|---|
| **Publish** | yours → shared | Copies your rooms over the shared ones. |
| **Pull shared** | shared → yours | Replaces your rooms with the shared ones. |

Both **overwrite**, so neither runs blind: the editor first asks the server what would
change and shows you the file names, marked `new` or `changed`, before you confirm.
Neither ever deletes: a room that exists only on one side stays where it is. Only `.txt`
files move — your built `.dsk` stays in your folder.

**Pull replaces work you saved but did not publish.** That is what it is for — an account
with this permission works on the common set rather than keeping a private branch.

For the same reason, **signing in pulls automatically** if you have this permission: your
folder is aligned with the shared one at the moment you sign in, so you never start from a
stale copy and publish somebody else's work backwards. Accounts without the permission are
never touched — their folder is theirs.

Publishing does **not** commit anything to git. It writes the files; committing them is
still a separate step outside the editor.

---

## 17. Administration

One account is the **administrator**. It is always allowed and cannot be revoked —
otherwise one wrong click would lock out the only person who can unlock it.

The administrator sees an **Accounts** link in the header, leading to `/admin`:

- **Invite** an address — it can sign in immediately, and is emailed a link. If mail is
  not configured the invitation still stands; you just have to pass the link on yourself,
  and the screen says so.
- **Approve** an address that signed in and is waiting.
- **Revoke** an address — blocks it. It stays on the list as a "no", so asking again
  changes nothing.
- **Delete** an address — forgets it. If that address signs in again it appears as a
  fresh request. Use Revoke for someone you want kept out, Delete for tidying the list.

**Neither touches their folder under `levels/`.** No button on the admin screen destroys
anybody's levels; files are removed by hand, if and when you decide to. The administrator
can be neither revoked nor deleted.
- Send a **test message** to yourself, to check the mail settings without going through
  the sign-in form (whose answers are deliberately vague, so they cannot be used to
  discover which addresses exist).
- Turn **Publish** on or off for an address — see [§16](#16-sharing-your-rooms). Off by
  default: designing rooms in your own folder is not the same as overwriting what
  everybody sees. A revoked account cannot publish whatever its flag says, and the
  administrator can always publish.

Anyone who signs in without an invitation is recorded as waiting and sees the "Waiting for
approval" page. No folder is created for them until they are approved.

To everyone else `/admin` returns 404 rather than "forbidden": the existence of the page
is nobody else's business.

---

## 18. Troubleshooting

**The editor will not start**, and the console says the Google secrets are missing.
The client id and secret come from environment variables and nothing else — not from a
config file in the repo, because anything in a file there gets committed sooner or later.
Set them and restart. The editor deliberately refuses to start without them: coming up
unprotected would be worse than not coming up at all, because you would believe it was
protected.

Note that a **non-interactive shell does not read `~/.bashrc`**, so if you export the
variables there, a launcher that does not use a login shell will not see them.

**Sign-in bounces or fails at the last step.** The redirect URI registered in the Google
Cloud console must be exactly `<your address>/accounts/google`, and the secret must be
the client *secret*, not the client id.

**Nobody receives sign-in codes.** Mail needs five environment variables:
`gravassistSmtpHost`, `gravassistSmtpPort`, `gravassistSmtpUser`, `gravassistSmtpPass`
and `gravassistMailFrom`; optionally `gravassistMailName`, `gravassistBaseUrl` (the
public address used in invitation links) and **`gravassistSmtpTls=true`** to turn on
STARTTLS. TLS is **off by default**: without it the SMTP password and the sign-in codes
travel in clear text, which is fine for a relay on the same machine and not fine over a
network, so the editor writes a warning to its log when it happens. Restart the editor
afterwards, then press **Send me a test message** on the admin screen; if it
fails, the mail server's exact error is in the editor's console log.

Three things that usually go wrong: with Gmail you need an **App Password**, not your
normal password; use port **587**, because the built-in SMTP client does STARTTLS but not
implicit TLS on 465; and the *from* address usually has to match the SMTP account, or the
provider rejects the message or files it as spam.

**The build says `rasm: command not found`.** Run `make toolchain` — it prints the
resolved path of each tool and marks the ones it cannot find. Fix `dir` in
`toolchain.json`, or give an absolute path for that tool.

**"Save first: Move works on the files."** Renumbering operates on what is on disk. Save,
then move.

**A door drops me at the start marker instead of where I wanted.** The arrival point is a
property of the door you *leave* through. Set it on that door, in the room you are leaving.

**The test run behaves differently from the disk build.** They share the level files but
not the code: the browser physics is a transcription of the reference model. When they
disagree, the reference model and the Z80 build are the authority.

**My change did not appear in the test run.** Test and Build use the **saved** file, and
the generated data for the browser is produced by the build. Save first.

---

## See also

| Document | Contents |
|---|---|
| [../editor/README.md](../editor/README.md) | The editor's internals: how to add a cell type, configuration, API |
| [level-elements.md](level-elements.md) | Why these level elements were chosen |
| [concept-art.md](concept-art.md) | The visual reference the game is bound to |
| [../plan.md](../plan.md) | Game design and technical decisions |
