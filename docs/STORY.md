# Le-Mond Roguelike — Story Design Doc

Narrative bible + implementation-ready content spec (v1.0). Grounded against the
current code (`core/dungeon.py`, `game.py`, `core/combat.py`, `core/spells.py`,
`core/affixes.py`, `core/loot.py`, `i18n.py`, `locales/`). English content here is
the source of truth; Russian is localized in the JSON files.

> Engineering keystone: the existing respawn line `msg.death_box` ("the power of
> Le-Mond returns you to the start of the level") is **load-bearing lore** — the
> respawn IS the first clue of the twist. Keep its wording.

---

## 1. World & Lore Bible

**The City: Le-Mond** — a fog-drowned metropolis of pale stone, once the seat of
the **Conclave of Antiquaries**, scholars who believed the world is a single
living text: to read it completely is to be able to *edit* it. They were right,
and they were fools.

**The Catastrophe (the "Unwriting").** The Conclave built the **Concordance**: an
engine of sigil-galleries spiralling *downward* (hence the descent) meant to read
the whole world at once. When they switched it on, it read everything — and began
overwriting. Reality near the engine started accepting edits from anyone who got
close enough and willed hard enough. The city didn't explode; it *forgot how to
stay finished*. The fog rolled in to fill the gaps where the world had become
un-decided.

**"The Power" — the twist.** Rumor: limitless power to rule the world. Truth: the
Concordance lets you rewrite reality by writing yourself into it — but to edit the
world you must first *be read*: copied into the city's memory and deleted from
outside it. Everyone who "seizes the power" gets exactly what they asked for —
an unkillable, world-editing fixture of Le-Mond — and can never leave, because the
version of them that *wanted* things has been overwritten. **The respawn is the
twist, foreshadowed from turn one:** the hero can't die because Le-Mond has already
begun reading him; every "death and return" is the engine saving a checkpoint.

**The Darkness.** Not a demon — the engine's overflow: the discarded drafts, the
deleted versions of everyone it ever read, compressed into a hungry fog. It wants
only to *finish reading the world* (an unfinished read is an open wound). It turns
adventurers into monsters because a half-read person is a draft with the edges torn
off. Neither evil nor good — an incomplete operation that will consume the world to
complete itself.

**Rosmund the Far-Descended** (the thread uncovered through notes): the greatest
adventurer to enter Le-Mond. He came for power, got deeper than anyone, and figured
out the twist before reaching the engine. He tried to *outsmart* it — to read the
engine first and edit it so one will could persist intact. He half-succeeded: he is
the single exception, a will that persists without being a fixture — but he can
never re-ascend (his "outside" self is gone) and his edit is unstable, slowly being
un-written. He didn't vanish; he's still down there, becoming fog one sentence at a
time. The hero meets **Rosmund's Shade** at the bottom.

**Gildar the Sealbearer** (Inquisition leader): old, iron-faithed. The Inquisition
quarantined Le-Mond for centuries because the city is a wound that must never finish
reading. Doctrine: the world must stay unfinished — that's what free will is. Goal:
collapse the engine and seal Le-Mond forever, whatever the cost. Not a villain; the
man willing to be hated to keep the world un-rewritten. Flaw: he'd burn a thousand
to be sure of one. Lost a daughter to the fog.

**Sando the Open-Eyed** (cult leader): once an Antiquary's apprentice who survived
the Unwriting and welcomed it. The Cult believes the fog is *completion*, not
destruction — a finished world is perfect and painless. Goal: let the Darkness
finish. Charismatic, warm, at peace, which makes him more disturbing than Gildar.
Flaw: he mistakes the end of *wanting* for the end of pain.

**The Hero — Gustav**, a young scholar of secret sciences and antiquities. Came for
the rumored power — to matter, to not be one more forgotten footnote. Arc:
curiosity → ambition → the dawning realization (through notes, musings, his own
un-deaths) that he is already being read → a final choice about what limitless power
is worth when the price is your self.

---

## 2. Story structure by depth

Beats are gated to **depth bands**, not specific floors, and surface through
randomly-placed notes/inscriptions/musings/NPCs, so the story accretes across runs
rather than resetting on death.

- **Act I — The Outskirts (d1–3).** Eerie wonder. Others' leftovers; the rumor of
  power; first mention of Rosmund and "the Darkness". The hero notices he respawns.
  Inquisition warnings & cult sigils as wall inscriptions. Darkness cosmetic only.
- **Act II — The Reading Halls (d4–7).** Dread + faction conflict. The catastrophe
  is revealed (the Concordance, the Unwriting); Inquisition & Cult both operate
  here; Rosmund's descent notes. **Gildar** parley. Corruption mechanic activates.
- **Act III — The Unwritten Depths (d8–11).** Reality breaking down; looping
  corridors; dead-language inscriptions. The **twist** is spelled out; the hero
  connects it to his un-deaths. **Sando** in person. Corruption builds faster.
- **Act IV — The Heart / The Concordance (d12+).** The engine-galleries. The full
  truth; **Rosmund's Shade** — the hinge of all endings. Maximum Darkness.

---

## 3. Endings (5)

Gated by lightweight run flags: `inq_favor`, `cult_favor`, `rosmund_understood`
(read ≥4 Rosmund notes), `artifacts_of_will` (Rosmund-tied gold artifacts held),
and the final dialogue choice. All resolve at the Heart.

1. **Seize the Power** (Pyrrhic/horror) — choose "I will rule"; become a fixture of
   Le-Mond, omnipotent inside, gone outside.
2. **Destroy the Engine** (bittersweet) — `rosmund_understood` + not high
   `cult_favor`; the engine collapses, the Darkness dissipates, the hero can finally
   leave/die. Gildar's doctrine vindicated.
3. **Side with the Inquisition / Seal It** (grim duty) — high `inq_favor`; help
   Gildar seal the city with you inside as the last warden.
4. **Side with the Cult / Let It Finish** (seductive bad-end) — high `cult_favor` +
   low corruption resistance; let the Darkness finish. Calm, and that's the horror.
5. **Rosmund's Redemption** (true/secret) — `rosmund_understood` +
   `artifacts_of_will ≥ 2` + "Finish what you started"; complete his edit, someone
   walks out of Le-Mond intact. Hard to reach by design.

---

## 4. Content (English source; localize RU in JSON)

Namespaces: `note.*`, `inscr.*`, `muse.*`, `artifact.*`, `dlg.*`. Each note/inscr
carries a depth band for placement gating (stored in the content table, not the
display string). The full ready-to-paste text lives with the implementation in the
locale files; the canonical pools and their band tags live in `core/lore.py`.

- **22 explorer notes** (`note.01`–`note.22`) across the four bands, telling
  Rosmund's thread and foreshadowing the twist.
- **9 wall inscriptions** (`inscr.01`–`inscr.09`), terser and ominous; some in the
  dead tongue (`VEN-OS LE-MOND` etc.) with an italic gloss.
- **16 hero musings** (`muse.<trigger>.*`) on triggers: depth-band change, gold
  artifact found, low HP, kill-streak, first fog, respawn-reveal, near-ending.
- **7 unique gold artifacts** (`artifact.*`): The First Draft (+1 all skills);
  Rosmund's Unwritten Blade (always-on lifesteal +2 sharp, will-relic); The
  Scholar's Eye (reveals secret rooms + exit, will-relic); Gildar's Sealbearer's
  Ward (pauses corruption); Sando's Open Eye (free spells <25% HP, +corruption);
  The Last Checkpoint (respawn at exit once/floor); The Concordance Quill (+50%
  damage <25% HP).
- **Dialogue** for Gildar (Act II parley), Sando (Act III recruit), and Rosmund's
  Shade (Act IV hinge) — 3–5 nodes each, 2–3 choices, each nudging an ending.

---

## 5. The Darkness — mechanic

Chase-pressure + a corruption meter, on the existing tile grid and per-tick timer
(`monster_turn_acc` / `MONSTER_TURN_INTERVAL`). **No pathfinding required** (pursuit
AI is backlog).

- **Corruption** `0–100` on the hero, HUD bar. Activates at depth ≥ 4 (cosmetic
  before). Ambient gain `max(0, depth-3) * 0.25`/tick, doubled inside fog.
  Descending removes a flat 15. Thresholds: ≥40 −1 FOV; ≥70 −1 damage + extra fog;
  ≥90 small per-tick chance to "convert" (a respawn event, never below d4, never a
  one-shot at full HP). 100 at the Heart with high cult favor → Ending E4.
- **Fog** as a parallel `dungeon.fog` set (translucent overlay, not terrain). Seeded
  at gen for depth ≥ 4: `depth-3` tiles at the floors farthest from ENTRY (reuse
  `farthest_from`). Spreads each tick with `min(0.5, 0.1 + 0.04*(depth-3))` chance
  to an adjacent non-wall tile — creep from the deep end toward the exit.
- **Fog-spawned enemies**: reuse `generate_monster`, tag `cultist`/`shadow`, +10% hp,
  spawn from off-screen fog tiles under the floor cap.

---

## 6. Implementation phasing

**MVP-now** (no new gameplay systems; content + one overlay):
- `core/lore.py`: pools of notes/inscriptions keyed by band, deterministic pick.
- Secret rooms in gen holding a note/inscription/artifact.
- Hero musings on already-available triggers.
- Unique gold artifacts as flagged drops; properties hook existing rules.
- Note-reading overlay (reuse `message_box`).
- All §4 keys in `en.json` + `ru.json`.

**Later** (new systems, some depend on the monster-AI backlog):
- Faction NPCs (cult/Inquisition) as monster reskins (light).
- Named-character dialogue (Gildar/Sando/Rosmund) — needs a choice-dialogue overlay
  + run `flags`. Dialogue encounters use the existing NPC-tile pattern, NOT pursuit.
- The Darkness mechanic (corruption field, fog layer, HUD bar).
- Endings + ending screen; codex/journal (quality-of-life).
- Named characters *as bosses* and any active chasing enemy depend on pursuit AI.
