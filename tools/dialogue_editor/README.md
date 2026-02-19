# Mend Dialogue Editor

Visual editor for creating YAML-based dialogues with Dialogic 2 export.

## Quick Start

### Run the Editor

```bash
cd tools/dialogue_editor
uv run python run_editor.py
```

Or with manual venv:
```bash
cd tools/dialogue_editor
source .venv/bin/activate  # Linux/Mac
python run_editor.py
```

### Export to Dialogic

```bash
python tools/yaml_to_dialogic.py
```

This generates:
- `dialogues_generated/*.dtl` — Dialogic timelines
- `dialogues_generated/characters/*.dch` — Dialogic characters

### Test in Godot

1. Open Godot project
2. Run `scenes/dialogue_test.tscn`
3. Press SPACE to start dialogue

---

## Installation

### Requirements

- Python 3.10+
- PySide6
- PyYAML

### Install with uv (recommended)

```bash
cd tools/dialogue_editor
uv sync
```

### Install with pip

```bash
cd tools/dialogue_editor
pip install -r requirements.txt
```

Or manually:
```bash
pip install pyside6 pyyaml
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Continue (same speaker) |
| `Ctrl+M` | Reply (other speaker) |
| `Ctrl+B` | Add CHOICE node |
| `Ctrl+E` | Add END node |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save All |
| `Ctrl+O` | Open file |
| `Ctrl+Shift+O` | Open folder |
| `Delete` | Delete selected node |
| `F5` | Validate |
| `Mouse wheel` | Zoom |
| `Middle mouse drag` | Pan |

---

## YAML Format

### Basic Structure

```yaml
id: my_dialogue
title: "My Dialogue"

characters:
  player:
    name: "???"
  npc:
    name: "Villager"
    portrait: "res://art/portraits/villager.png"

start: a1b2c

nodes:
  a1b2c:
    say: { speaker: player, text: "Hello!" }
    next: d3e4f
  
  d3e4f:
    say: { speaker: npc, text: "Greetings, traveler." }
    next: 5f6a7
  
  5f6a7:
    choice:
      - text: "Ask about the village"
        next: b8c9d
      - text: "Say goodbye"
        next: e0f1a
  
  b8c9d:
    say: { speaker: npc, text: "This is Millbrook village." }
    end: true
  
  e0f1a:
    say: { speaker: player, text: "Farewell." }
    end: true
```

### Node Types

| Type | Description |
|------|-------------|
| `say` | Character speaks |
| `choice` | Player choices |
| `set` | Set variables |
| `if` | Conditional branch |
| `jump` | Jump to node |
| `signal` | Emit signal |
| `end` | End dialogue |

### Node IDs

Node IDs are 5-character hex strings: `a1b2c`, `f8a9b`, etc.

The editor generates these automatically when creating nodes.

---

## Choice Nodes

### Creating Choices

1. Add CHOICE node (`Ctrl+B`)
2. Click `+ Add` to add choice options
3. Double-click to edit text
4. Click `🔗 Link` to connect to existing node
5. Click `➕ New Node` to create and link a SAY node

### Link Dialog

- Shows only "orphan" nodes by default (no incoming connections)
- Check "Show all" to see connected nodes too
- Connected nodes marked with `●`

---

## Project Structure

```
dialogues/              # Working YAML files
dialogues_src/          # Source YAML (alternative)
dialogues_generated/    # Dialogic output (auto-generated)
  ├── *.dtl             # Timelines
  └── characters/
      └── *.dch         # Characters

tools/
  ├── dialogue_editor/  # This editor
  ├── yaml_to_dialogic.py  # Export script
  └── generate_dialogue_audio.py  # TTS generation
```

---

## Tips

### Workflow

1. Create characters first (left panel)
2. Start with `Ctrl+N` to add first line
3. Use `Ctrl+N` to continue same character
4. Use `Ctrl+M` to switch to another character
5. Add choices with `Ctrl+B`, end with `Ctrl+E`
6. Save with `Ctrl+S`
7. Export with `yaml_to_dialogic.py`

### Colors

- SAY nodes are colored by speaker (consistent colors per character)
- CHOICE nodes are orange
- END nodes are red
- Other nodes have distinct colors

### Connections

- Lines show dialogue flow
- Choice connections show the choice number (1, 2, 3...)
- Drag nodes to rearrange
- Connections update in real-time
