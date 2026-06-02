# ShatteredReach DevLog #1 — Playtest Feedback Analysis

> **Source**: `2026-05-30 14-38-29.mkv` — 13:32 recording, live playtest review  
> **Extracted by**: video-to-context pipeline (WhisperX + Qwen3-VL-8B)  
> **Date**: 2026-05-30

---

## Guiding Design Principle

> *"The complex nature of this game shouldn't come from the ship UI and figuring out all of your abilities — it should come from strategizing how to combine moves together and ships together to accomplish a goal that's a defensive and offensive."*  
> — 4:33

Everything in this document flows from this principle. If a UI element forces the player to **do math** instead of **make decisions**, it's a design problem.

---

## Current State of the UI

Based on 16 extracted screenshots with Qwen3-VL-8B visual descriptions, the current HUD consists of:

| Element | Position | State |
|---------|----------|-------|
| Left sidebar | Full left edge | Vertical panel with many horizontal bars (HP, shields, etc.) — always visible |
| Top-center panel | Upper center | Small rectangular window with progress bars and text |
| Top-right panel | Upper right | Target list with lock status |
| Bottom-center panel | Lower center | Large dark window with lists, sliders, buttons (command menu) |
| Sensor range rings | Over gameplay | Circular overlays around ships — always visible |
| Multiple info boxes | Scattered | Ship stats, parenthetical calculations, raw numbers |

**Speaker's reaction on first look** (0:30):

> *"I'm a brand new player. No context. I'm already confused looking at this menu. There's too much going on. Too little words. Too many tabs."*

---

## UI / HUD Design

**15 feedback items — 45% of all feedback. The #1 pain point.**

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 0:26 | **Information overload on first look** | "I'm already confused looking at this menu. Too much going on. Too many tabs." | Progressive disclosure — show only what's needed for the current action. Default view should be minimal. | 🔴 Critical |
| 2 | 0:46 | **Sensor rings always visible** | "They should be invisible unless I click on sensor something — any button related to sensors." | Sensor range rings → ability-toggled overlay. Only shown when hovering/clicking a sensor ability. | 🟠 High |
| 3 | 1:40 | **All ship HP bars always shown** | "Not necessary to provide all the tiny HP bars for everything — that's info you can find when you click on your ship." | HP bars hidden by default. Show only for selected ship, or as subtle health dot (🟢🟡🔴). | 🟠 High |
| 4 | 1:25 | **Ship menu is a big box** | "Sections should jut out, not a whole box. Like XCOM 2 character system." | Compact pop-out tabs that slide from the edge, not full rectangular panels. Reference: XCOM 2 soldier cards. | 🟠 High |
| 5 | 2:11 | **Multiple boxes scattered around screen** | "All these boxes can be condensed into one ability area at the bottom." | Single unified ability bar at bottom — merge all action/stats into one strip. | 🔴 Critical |
| 6 | 2:19 | **No grouping of related stats** | "Shields and armor can be in like defensive." | Group ship stats into categories: **Defensive** (shields, armor, hull), **Offensive** (weapons, power), **Movement** (thrust, turn). | 🟡 Medium |
| 7 | 2:46 | **Manual drag for power allocation** | "Instead of dragging, click it and it's a tick system." | Click-to-cycle power allocation (e.g., shields: low → medium → high), not drag sliders. | 🟡 Medium |
| 8 | 3:08 | **Raw numbers everywhere** | "Less actions, less focus, less points, less numbers." | Replace raw numbers with visual indicators (bars, icons, color codes). Show exact numbers only in detail pop-ups. | 🟠 High |
| 9 | 8:41 | **No click-to-open detail panels** | "No boxes — terminals that pop up on click." | Detail panels appear as floating terminals on click, not permanent screen furniture. | 🟠 High |
| 10 | 8:59 | **Parentheses and calculations visible** | "Too many parentheses, too many numbers, too many calculations on top of strategize." | Abstract math into visual language. Player should strategize, not calculate. | 🔴 Critical |
| 11 | 11:56 | **No clear HUD hierarchy** | "Current target should be top of UI, abilities at bottom, gameplay in center. That's how simple it needs to be." | **3-zone HUD**: Top = target info + turn phase. Bottom = ability bar. Center = unobstructed gameplay. | 🔴 Critical |
| 12 | 12:19 | **No turn phase indicator** | "Up here you can do: your turn, enemy turn." | Top bar: **YOUR TURN / ENEMY TURN** with turn counter. | 🟡 Medium |

### Proposed HUD Layout

```
┌─────────────────────────────────────────────┐
│  [YOUR TURN]  Turn 6 / 100  [Current Target] │  ← TOP: turn phase + target info
│                                             │
│                                             │
│            UNOBSTRUCTED GAMEPLAY             │  ← CENTER: hex grid + ships + space
│            (no permanent panels)             │
│                                             │
│                                             │
│ [Move] [Attack] [Fire] [Shield] [Sense]     │  ← BOTTOM: ability bar
└─────────────────────────────────────────────┘

Click ship → pop-up terminal with grouped stats (Defensive / Offensive / Movement)
Click ability → sub-options appear (e.g., Attack → weapon choices)
Hover sensor ability → sensor range rings appear temporarily
```

---

## Movement & Grid

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 3:17 | **Overlapping hex outlines** | "If ships get close, combine their geometrical outline into connected sections." | Merge adjacent friendly/enemy hex outlines into a shared border instead of overlapping rings. | 🟡 Medium |
| 2 | 5:53 | **No partial movement indication** | "Yellow zone = partial movement (can still act). Full turn = sprint." | Two-color movement preview: **Yellow** = partial move (actions remaining), **Blue** = full sprint (ends turn). | 🟠 High |
| 3 | 6:00 | **Action economy unclear** | "Partial move + fire, or full turn sprint." | Partial move costs 1 action (remaining actions available), sprint costs all actions. | 🟠 High |
| 4 | 8:09 | **Ship turning has no cost** | "Turning is going to have to take some sort of extra something." | Facing/rotation should consume part of movement budget or have a turning radius. Needs design discussion. | 🟡 Medium |

### Movement Zone Visualization

```
  Current:              Proposed:
  ┌─────────┐          ┌─────────┐
  │  Blue    │          │ Yellow  │ ← partial move (can still fire/ability)
  │  zone    │          │ zone    │
  │  only    │          ├─────────┤
  │         │          │  Blue   │ ← full sprint (ends turn)
  └─────────┘          │ zone    │
                       └─────────┘
```

---

## Combat & Weapons

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 9:25 | **Weapons buried in menus** | "Ability boxes like fire — different weapons appear as little boxes of abilities." | Each weapon = its own ability button. Click "Attack" → shows weapon sub-options. | 🟠 High |
| 2 | 9:55 | **Attack camera view** | "Zoom in on your ship, looking at the enemy." | Attack cinematic: camera positioned behind player ship, enemy in the sight line. | 🟡 Medium |
| 3 | 10:05 | **No hit chance system** | "70% chance to hit, 15% crit — penetrating shields or hull." | Percentage-based hit system. Always a non-zero chance (warfare = uncertainty). Crit = shield bypass or hull penetration. | 🔴 Critical |
| 4 | 10:26 | **No attack confirmation** | "It'll have a confirm — 70% chance to hit, 15% crit." | Attack flow: **Select weapon → Show hit%/crit% → Confirm → Execute cinematic.** | 🟠 High |
| 5 | 11:17 | **Batch fire via submit-order** | "Remove submit order — fire one at a time so player watches." | Sequential execution: each ship's attack plays out individually with its own cinematic. No batch resolution. | 🟠 High |
| 6 | 11:40 | **No suppressive fire** | "Idle flak — suppressive ability. If they move there's a chance to hit." | New ability: **Suppressive Fire** — creates a danger zone. Enemy ships moving through it take hit chance rolls. | 🟢 Low (new feature) |
| 7 | 12:52 | **No damage feedback during cinematic** | "Damage numbers should appear as you see the cinematics happening." | Floating damage numbers rise from the hit ship during attack cinematic. | 🟡 Medium |

### Proposed Attack Flow

```
1. Click [Attack] on ability bar
2. Select weapon (e.g., [Heavy Cannons] / [Flat Cannons])
3. Click target ship on hex grid
4. Confirmation overlay appears:
   ┌──────────────────────────┐
   │  ATTACK: Heavy Cannons   │
   │  Target: Architect Eternal│
   │  ─────────────────────── │
   │  Hit Chance: 70%         │
   │  Crit Chance: 15%        │
   │  Crit Effect: Shield Pen │
   │  ─────────────────────── │
   │  [CONFIRM]  [CANCEL]     │
   └──────────────────────────┘
5. Cinematic plays → damage numbers float up
6. Return to tactical view
```

---

## Cinematic & Animation

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 6:48 | **Cinematic plays for all actions** | "Cinematic playback should only happen during firing/ability actions, not movement." | Only trigger cinematic cam for attacks and abilities. Movement is instant or simple glide. | 🟠 High |
| 2 | 6:56 | **Dramatic final move has no cinematic** | "Unless their final action is a movement — cinematic for that." | If the final action in a turn is movement (e.g., sprint to cover), play a short cinematic. | 🟢 Low |
| 3 | 8:04 | **Jerky movement animation** | "Animation needs work — should glide into position." | Smooth interpolation for ship movement (ease-in/out glide, not instant teleport). | 🟡 Medium |

### Cinematic Trigger Rules

| Action Type | Cinematic? | Notes |
|-------------|-----------|-------|
| Movement (non-final) | ❌ No | Simple glide animation, player can keep issuing commands |
| Movement (final action) | ✅ Yes | Short cinematic if it's the dramatic end-of-turn action |
| Weapon fire | ✅ Yes | Full attack cinematic with damage numbers |
| Ability use | ✅ Yes | Depends on ability type |
| Idle / passive | ❌ No | No cinematic for doing nothing |

---

## Camera

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 3:49 | **Camera locks on unit selection** | "Even if you click on an opponent or a unit, you should still be able to manipulate your camera angle." | Decouple camera from selection. Clicking a unit selects it but doesn't lock camera. Player keeps free camera control at all times. | 🟠 High |

---

## Turn System

| # | Timestamp | Issue | Speaker's Words | Proposed Change | Priority |
|---|-----------|-------|-----------------|-----------------|----------|
| 1 | 5:01 | **Per-ship independent actions** | "Every single ship has multiple actions. They're not shared." | Each ship has its own action pool. Spending one ship's actions doesn't affect others. Same for enemy AI. | 🟠 High (confirm existing design) |
| 2 | 7:26 | **Can't queue actions during animation** | "Should be able to interact with other ships and queue up their actions while this guy's moving." | **Async input during animation**: while one ship's action plays out, the player can issue commands to other ships. Actions execute sequentially but input is non-blocking. | 🟡 Medium |

### Action Economy Model

```
Each ship per turn:
  ├── Action 1: Move (partial) or Sprint (full turn)
  ├── Action 2: Attack / Ability (if partial move used)
  └── Actions are per-ship, NOT shared across fleet

Movement options:
  ├── Partial Move (yellow zone) → costs 1 action → can still fire/ability
  └── Sprint (blue zone) → costs all actions → ends that ship's turn

Facing:
  └── Ship rotation consumes part of movement budget (TBD — needs design)
```

---

## What's Working (Keep)

| What | Timestamp | Speaker's Words |
|------|-----------|-----------------|
| **Hex grid visual design** | 5:46 | "This is exactly how we want the grid system to look." |
| **Combat visual effects** | 12:25 | "I like the effects, I know this will turn out good." |
| **Grid system concept** | 5:46 | Confirmed correct direction |

---

## Priority Summary

| Priority | Category | Items | Key Actions |
|----------|----------|-------|-------------|
| 🔴 Critical | UI/HUD | 4 items | 3-zone HUD layout, remove permanent boxes, hide raw numbers, progressive disclosure |
| 🟠 High | UI/HUD | 5 items | Sensor toggle, HP bars on click, pop-out terminals, ability bar, grouped stats |
| 🟠 High | Combat | 4 items | Hit chance system, attack confirm, sequential fire, weapon ability buttons |
| 🟠 High | Movement | 2 items | Two-color movement zones, partial/sprint action economy |
| 🟠 High | Camera | 1 item | Decouple camera from selection |
| 🟠 High | Turn System | 1 item | Confirm per-ship action economy |
| 🟡 Medium | UI/HUD | 2 items | Turn phase indicator, click-to-cycle power |
| 🟡 Medium | Movement | 2 items | Merged hex outlines, turning cost |
| 🟡 Medium | Combat | 2 items | Attack camera angle, damage numbers |
| 🟡 Medium | Cinematic | 1 item | Smooth glide animation |
| 🟡 Medium | Turn System | 1 item | Async input during animation |
| 🟢 Low | Combat | 1 item | Suppressive fire (new feature) |
| 🟢 Low | Cinematic | 1 item | Final-action movement cinematic |

---

## Decisions Needed

These items need team discussion before implementation:

| # | Decision | Options | Speaker's Preference |
|---|----------|---------|---------------------|
| D1 | **Ship turning cost** | (a) Costs movement budget, (b) Has turning radius, (c) Free rotation | "some sort of extra something" — needs design |
| D2 | **Suppressive fire: mechanic or flavor?** | (a) Full mechanic with zone + hit rolls, (b) Visual-only idle animation, (c) Skip for now | Speaker suggested it as a real mechanic ("note that down") |
| D3 | **How much info in the ability bar?** | (a) Weapon names only, (b) Weapon names + hit chance preview, (c) Full stats on hover | "little boxes of abilities like fire" — minimal by default |
| D4 | **Power allocation granularity** | (a) 3 ticks (low/med/high), (b) 5 ticks, (c) Continuous slider | "tick system" — discrete steps, not continuous |
| D5 | **When does enemy turn animate?** | (a) Full sequential cinematics, (b) Quick highlights only, (c) Skip enemy animation | Not addressed — needs team decision |

---

*This analysis was generated from the video recording using an automated pipeline: WhisperX (transcription) + Qwen3-VL-8B (visual description) + ffmpeg (frame extraction). The full extracted context (VTT with 133 speech cues + 16 visual context markers) is available in the project output directory.*
