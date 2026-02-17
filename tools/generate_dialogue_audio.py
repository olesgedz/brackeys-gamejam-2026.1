#!/usr/bin/env python3
"""
Generate gibberish voice-overs for Dialogic dialogues.

Workflow:
1. Reads all .dtl (Dialogic timeline) files from dialogues/
2. Extracts text lines from each dialogue
3. Generates gibberish audio using gibberish_tts.py
4. Saves audio to sound/dialogues/
5. Updates .dtl files with audio paths

Usage:
    python generate_dialogue_audio.py
    python generate_dialogue_audio.py --dry-run
    python generate_dialogue_audio.py --dialogue dialogues/intro.dtl
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DIALOGUES_DIR = PROJECT_ROOT / "dialogues"
AUDIO_OUTPUT_DIR = PROJECT_ROOT / "sound" / "dialogues"
GIBBERISH_SCRIPT = PROJECT_ROOT / "tools" / "gibberish_tts.py"

# Voice presets for different character types (from gibberish_tts.py)
CHARACTER_PRESETS = {
    "default": "male1",
    "doctor": "male2",
    "nurse": "female1",
    "child": "child1",
    "old_man": "male4",
    "woman": "female2",
}


def parse_dtl_file(filepath: Path) -> list[dict]:
    """Parse a Dialogic .dtl timeline file and extract text events."""
    lines = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Dialogic 2 format: each line is an event
    # Text events look like: [text character="Name"]The text here[/text]
    # Or simpler format depending on version
    
    # Pattern for text events in Dialogic 2 format
    # Format: "character: text" or just "text"
    text_pattern = re.compile(r'^(?:(\w+):\s*)?(.+)$', re.MULTILINE)
    
    # Try to parse as JSON first (Dialogic saves in JSON)
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "events" in data:
            for i, event in enumerate(data["events"]):
                if event.get("event_name") == "dialogic_text_event" or "text" in event:
                    text = event.get("text", "")
                    character = event.get("character", "default")
                    if text.strip():
                        lines.append({
                            "index": i,
                            "text": text,
                            "character": character,
                            "event": event
                        })
        return lines
    except json.JSONDecodeError:
        pass
    
    # Fallback: parse as plain text format
    for i, line in enumerate(content.split("\n")):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        
        match = text_pattern.match(line)
        if match:
            character = match.group(1) or "default"
            text = match.group(2)
            if text.strip():
                lines.append({
                    "index": i,
                    "text": text,
                    "character": character.lower(),
                    "raw_line": line
                })
    
    return lines


def get_preset_for_character(character: str) -> str:
    """Get voice preset for a character name."""
    char_lower = character.lower()
    
    # Direct match
    if char_lower in CHARACTER_PRESETS:
        return CHARACTER_PRESETS[char_lower]
    
    # Fuzzy matching
    if "doctor" in char_lower or "dr" in char_lower:
        return CHARACTER_PRESETS["doctor"]
    if "nurse" in char_lower:
        return CHARACTER_PRESETS["nurse"]
    if "child" in char_lower or "kid" in char_lower or "boy" in char_lower or "girl" in char_lower:
        return CHARACTER_PRESETS["child"]
    if "old" in char_lower or "elder" in char_lower:
        return CHARACTER_PRESETS["old_man"]
    if "woman" in char_lower or "lady" in char_lower or "female" in char_lower:
        return CHARACTER_PRESETS["woman"]
    
    return CHARACTER_PRESETS["default"]


def generate_audio(text: str, output_path: Path, preset: str) -> bool:
    """Generate gibberish audio for text using gibberish_tts.py."""
    cmd = [
        sys.executable,
        str(GIBBERISH_SCRIPT),
        text,
        str(output_path),
        "--preset", preset
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"  Error generating audio: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  Timeout generating audio")
        return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False


def process_dialogue_file(filepath: Path, dry_run: bool = False) -> dict:
    """Process a single dialogue file and generate audio."""
    print(f"\nProcessing: {filepath.name}")
    
    lines = parse_dtl_file(filepath)
    if not lines:
        print("  No text lines found")
        return {"file": str(filepath), "lines": 0, "generated": 0}
    
    print(f"  Found {len(lines)} text lines")
    
    # Create output directory for this dialogue
    dialogue_name = filepath.stem
    output_dir = AUDIO_OUTPUT_DIR / dialogue_name
    
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    generated = 0
    audio_mapping = {}
    
    for line_data in lines:
        idx = line_data["index"]
        text = line_data["text"]
        character = line_data["character"]
        preset = get_preset_for_character(character)
        
        # Generate filename
        audio_filename = f"{dialogue_name}_{idx:03d}.wav"
        audio_path = output_dir / audio_filename
        res_path = f"res://sound/dialogues/{dialogue_name}/{audio_filename}"
        
        print(f"  [{idx}] {character}: \"{text[:50]}...\"")
        print(f"       -> {audio_filename} (preset: {preset})")
        
        if not dry_run:
            if generate_audio(text, audio_path, preset):
                generated += 1
                audio_mapping[idx] = res_path
            else:
                print(f"       FAILED!")
        else:
            generated += 1
            audio_mapping[idx] = res_path
    
    return {
        "file": str(filepath),
        "lines": len(lines),
        "generated": generated,
        "mapping": audio_mapping
    }


def main():
    parser = argparse.ArgumentParser(description="Generate gibberish audio for Dialogic dialogues")
    parser.add_argument("--dry-run", action="store_true", help="Don't generate audio, just show what would be done")
    parser.add_argument("--dialogue", type=str, help="Process only this dialogue file")
    parser.add_argument("--list-presets", action="store_true", help="Show available voice presets")
    
    args = parser.parse_args()
    
    if args.list_presets:
        print("Available character presets:")
        for char, preset in CHARACTER_PRESETS.items():
            print(f"  {char}: {preset}")
        return
    
    # Check dependencies
    if not GIBBERISH_SCRIPT.exists():
        print(f"Error: gibberish_tts.py not found at {GIBBERISH_SCRIPT}")
        sys.exit(1)
    
    # Ensure dialogues directory exists
    if not DIALOGUES_DIR.exists():
        print(f"Creating dialogues directory: {DIALOGUES_DIR}")
        DIALOGUES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find dialogue files
    if args.dialogue:
        dialogue_files = [Path(args.dialogue)]
    else:
        dialogue_files = list(DIALOGUES_DIR.glob("*.dtl")) + list(DIALOGUES_DIR.glob("*.json"))
    
    if not dialogue_files:
        print(f"No dialogue files found in {DIALOGUES_DIR}")
        print("Create .dtl or .json files with your dialogues first.")
        print("\nExample dialogue format (dialogues/example.json):")
        print('''
{
  "events": [
    {"event_name": "dialogic_text_event", "character": "doctor", "text": "The patient needs treatment."},
    {"event_name": "dialogic_text_event", "character": "nurse", "text": "I'll prepare the medicine."}
  ]
}
''')
        return
    
    print(f"Found {len(dialogue_files)} dialogue file(s)")
    if args.dry_run:
        print("DRY RUN - no audio will be generated\n")
    
    total_lines = 0
    total_generated = 0
    
    for filepath in dialogue_files:
        result = process_dialogue_file(filepath, dry_run=args.dry_run)
        total_lines += result["lines"]
        total_generated += result["generated"]
    
    print(f"\n{'='*50}")
    print(f"Total: {total_generated}/{total_lines} audio files generated")
    
    if not args.dry_run:
        print(f"Audio saved to: {AUDIO_OUTPUT_DIR}")
        print("\nNext steps:")
        print("1. Open Godot and reimport the audio files")
        print("2. In Dialogic, set audio paths for each text event")


if __name__ == "__main__":
    main()
