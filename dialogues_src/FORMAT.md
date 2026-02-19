# Dialogue YAML Format

This is the single source of truth for all game dialogues.
Edit files here, then run the converter to generate Dialogic resources.

## Basic Structure

```yaml
id: unique_dialogue_id        # Required: used for lookup and filenames
title: "Human readable title"  # Optional: for editor display

characters:                    # Optional: define/reference characters
  guard:
	name: "Guard"
	portrait: "res://art/portraits/guard.png"
  hero:
	name: "Hero"

start: node_1                  # Required: entry point node

nodes:                         # Required: dialogue nodes
  node_1:
	# ... node content
```

## Node Types

### Say (NPC/Character speaks)

```yaml
node_1:
  say:
	speaker: guard           # Character ID
	text: "Halt! Who goes there?"
  next: node_2               # Next node (optional, auto-continues if omitted)
```

Shorthand:
```yaml
node_1:
  say: { speaker: guard, text: "Halt!" }
  next: node_2
```

### Choice (Player options)

```yaml
node_2:
  choice:
	- text: "I'm just a traveler."
	  next: node_friendly
	- text: "None of your business."
	  next: node_hostile
	- text: "[Run away]"
	  next: node_flee
	  if: flags.can_flee      # Conditional choice (v1)
```

### Set (Variables/Flags)

```yaml
node_3:
  set:
	flags.met_guard: true
	stats.reputation: -10
  next: node_4
```

### Conditional (If/Else)

```yaml
node_4:
  if: flags.has_key
  then: node_unlock
  else: node_locked
```

### End (Terminate dialogue)

```yaml
node_final:
  say: { speaker: guard, text: "Move along." }
  end: true
```

Or with outcome:
```yaml
node_final:
  end: "success"  # Outcome passed to dialogue_finished signal
```

### Jump (Go to another node)

```yaml
node_x:
  jump: node_1  # Useful for loops
```

### Signal (Emit custom event)

```yaml
node_reward:
  signal: 
	name: "give_item"
	args: { item: "key_rusty", count: 1 }
  next: node_continue
```

## Full Example

```yaml
id: intro_gate
title: "Intro at the Gate"

characters:
  guard:
	name: "Guard"
	portrait: "res://art/portraits/guard.png"
  player:
	name: "You"

start: guard_challenge

nodes:
  guard_challenge:
	say: { speaker: guard, text: "Stop! Who goes there?" }
	next: player_choice

  player_choice:
	choice:
	  - text: "Just a traveler passing through."
		next: friendly_response
	  - text: "None of your business."
		next: hostile_response

  friendly_response:
	say: { speaker: guard, text: "Hmm. Very well, but stay out of trouble." }
	set:
	  flags.met_guard: true
	  flags.guard_friendly: true
	end: "friendly"

  hostile_response:
	say: { speaker: guard, text: "Watch your tongue, stranger. I'll be keeping an eye on you." }
	set:
	  flags.met_guard: true
	  flags.guard_hostile: true
	end: "hostile"
```

## Localization (v2)

```yaml
nodes:
  node_1:
	say:
	  speaker: guard
	  text:
		en: "Hello!"
		ru: "Привет!"
		de: "Hallo!"
```

## Metadata / Tags (optional)

```yaml
id: intro_gate
tags: [intro, chapter1, required]
priority: 10
conditions:
  - not flags.intro_done
```
