#!/usr/bin/env python3
"""
YAML to Dialogic 2 Converter

Converts YAML dialogue files to Dialogic 2 timeline format (.dtl).

Usage:
    python yaml_to_dialogic.py                      # Convert all
    python yaml_to_dialogic.py --validate           # Validate only
    python yaml_to_dialogic.py --dry-run            # Show what would be generated
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "dialogues"
OUT_DIR = PROJECT_ROOT / "dialogues_generated"
CHARACTERS_DIR = OUT_DIR / "characters"


class DialogueConverter:
    """Converts a single YAML dialogue to Dialogic 2 format."""
    
    def __init__(self, yaml_data: dict, source_file: str):
        self.data = yaml_data
        self.source_file = source_file
        self.errors: list[str] = []
        self.warnings: list[str] = []
        
        # Extract core data
        self.dialogue_id = yaml_data.get("id", "")
        self.title = yaml_data.get("title", self.dialogue_id)
        self.characters = yaml_data.get("characters", {})
        self.start_node = yaml_data.get("start", "")
        self.nodes = yaml_data.get("nodes", {})
    
    def validate(self) -> bool:
        """Validate the YAML structure. Returns True if valid."""
        if not self.dialogue_id:
            self.errors.append("Missing required field: 'id'")
        
        if not self.start_node:
            self.errors.append("Missing required field: 'start'")
        elif self.start_node not in self.nodes:
            self.errors.append(f"Start node '{self.start_node}' not found in nodes")
        
        if not self.nodes:
            self.errors.append("Missing required field: 'nodes' (or empty)")
        
        # Validate node references
        for node_id, node_data in self.nodes.items():
            self._validate_node(node_id, node_data)
        
        return len(self.errors) == 0
    
    def _validate_node(self, node_id: str, node: dict) -> None:
        """Validate a single node."""
        if not isinstance(node, dict):
            self.errors.append(f"Node '{node_id}' must be a dictionary")
            return
        
        # Check 'next' references
        next_node = node.get("next")
        if next_node and next_node not in self.nodes:
            self.errors.append(f"Node '{node_id}': 'next' references unknown node '{next_node}'")
        
        # Check choice references
        if "choice" in node:
            for i, choice in enumerate(node["choice"]):
                choice_next = choice.get("next")
                if choice_next and choice_next not in self.nodes:
                    self.errors.append(f"Node '{node_id}' choice {i}: references unknown node '{choice_next}'")
    
    def convert(self) -> str:
        """Convert to Dialogic 2 timeline text format (.dtl)."""
        lines = []
        
        # Process nodes in order starting from start_node
        visited = set()
        self._process_node_chain(self.start_node, lines, visited, indent=0)
        
        return '\n'.join(lines)
    
    def _process_node_chain(self, node_id: str, lines: list, visited: set, indent: int = 0) -> None:
        """Process a node and follow its chain."""
        if node_id in visited or node_id not in self.nodes:
            return
        visited.add(node_id)
        
        node = self.nodes[node_id]
        prefix = '\t' * indent
        
        # Process node content
        self._process_node_content(node, lines, prefix, visited, indent)
    
    def _process_node_content(self, node: dict, lines: list, prefix: str, visited: set, indent: int) -> None:
        """Process the content of a single node."""
        
        # Say event: "character: Text"
        if "say" in node:
            say_data = node["say"]
            if isinstance(say_data, dict):
                speaker = say_data.get("speaker", "")
                text = say_data.get("text", "")
            else:
                speaker = ""
                text = str(say_data)
            
            if speaker:
                lines.append(f"{prefix}{speaker}: {text}")
            else:
                lines.append(f"{prefix}{text}")
        
        # Choice event
        if "choice" in node:
            for choice in node["choice"]:
                choice_text = choice.get("text", "")
                choice_next = choice.get("next", "")
                
                lines.append(f"{prefix}- {choice_text}")
                
                # Process choice branch
                if choice_next and choice_next not in visited:
                    self._process_node_chain(choice_next, lines, visited, indent + 1)
            
            return  # Don't follow 'next' after choices
        
        # Set variables
        if "set" in node:
            for var_path, value in node["set"].items():
                if isinstance(value, bool):
                    val_str = "true" if value else "false"
                else:
                    val_str = str(value)
                lines.append(f"{prefix}[set {var_path} = {val_str}]")
        
        # End
        if node.get("end"):
            end_value = node.get("end")
            if end_value is True:
                lines.append(f"{prefix}[end]")
            else:
                lines.append(f"{prefix}[end {end_value}]")
            return
        
        # Jump
        if "jump" in node:
            lines.append(f"{prefix}[jump {node['jump']}]")
            return
        
        # Signal
        if "signal" in node:
            sig = node["signal"]
            if isinstance(sig, dict):
                sig_name = sig.get("name", "")
            else:
                sig_name = str(sig)
            lines.append(f"{prefix}[signal {sig_name}]")
        
        # Follow 'next' if present
        next_node = node.get("next")
        if next_node:
            self._process_node_chain(next_node, lines, visited, indent)
    
    def generate_characters(self) -> dict[str, str]:
        """Generate Dialogic 2 character resources (.dch). Returns {id: content}."""
        result = {}
        for char_id, char_data in self.characters.items():
            # Dialogic uses Godot's var_to_str format which requires @path
            # Format must match what dict_to_inst() expects
            portraits_dict = {}
            if "portrait" in char_data:
                portraits_dict["default"] = {
                    "scene": "",
                    "image": char_data["portrait"],
                }
            
            # Build the dict string in Godot's var_to_str format
            lines = [
                '{',
                '"@path": "res://addons/dialogic/Resources/character.gd",',
                '"@subpath": NodePath(""),',
                f'"display_name": "{char_data.get("name", char_id)}",',
                '"nicknames": [],',
                '"color": Color(1, 1, 1, 1),',
                '"description": "",',
                '"scale": 1.0,',
                '"offset": Vector2(0, 0),',
                '"mirror": false,',
                '"default_portrait": "",',
            ]
            
            # Add portraits
            if portraits_dict:
                portrait_str = '{'
                for pname, pdata in portraits_dict.items():
                    portrait_str += f'"{pname}": {{"scene": "", "image": "{pdata["image"]}"}}, '
                portrait_str = portrait_str.rstrip(', ') + '}'
                lines.append(f'"portraits": {portrait_str},')
            else:
                lines.append('"portraits": {},')
            
            lines.append('"custom_info": {}')
            lines.append('}')
            
            result[char_id] = '\n'.join(lines)
        
        return result


def convert_all(validate_only: bool = False, dry_run: bool = False) -> int:
    """Convert all YAML files. Returns exit code."""
    if not SRC_DIR.exists():
        print(f"ERROR: Source directory not found: {SRC_DIR}")
        return 1
    
    yaml_files = list(SRC_DIR.glob("*.yaml")) + list(SRC_DIR.glob("*.yml"))
    
    if not yaml_files:
        print(f"No YAML files found in {SRC_DIR}")
        return 0
    
    print(f"Found {len(yaml_files)} dialogue file(s)")
    
    # Ensure output directory exists
    if not dry_run and not validate_only:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
    
    total_errors = 0
    
    for yaml_file in yaml_files:
        print(f"\n--- {yaml_file.name} ---")
        
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"  ERROR: Invalid YAML: {e}")
            total_errors += 1
            continue
        
        if not data:
            print(f"  WARNING: Empty file, skipping")
            continue
        
        converter = DialogueConverter(data, yaml_file.name)
        
        # Validate
        if not converter.validate():
            for err in converter.errors:
                print(f"  ERROR: {err}")
            total_errors += len(converter.errors)
            continue
        
        for warn in converter.warnings:
            print(f"  WARNING: {warn}")
        
        if validate_only:
            print(f"  ✓ Valid")
            continue
        
        # Convert
        dtl_content = converter.convert()
        out_file = OUT_DIR / f"{converter.dialogue_id}.dtl"
        
        if dry_run:
            print(f"  Would generate: {out_file}")
            print("  --- Content preview ---")
            for line in dtl_content.split('\n')[:10]:
                print(f"    {line}")
            if dtl_content.count('\n') > 10:
                print(f"    ... ({dtl_content.count(chr(10)) - 10} more lines)")
        else:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(dtl_content)
            print(f"  ✓ Generated: {out_file.name}")
        
        # Generate characters
        characters = converter.generate_characters()
        for char_id, char_content in characters.items():
            char_file = CHARACTERS_DIR / f"{char_id}.dch"
            if dry_run:
                print(f"  Would generate character: {char_file.name}")
            else:
                with open(char_file, "w", encoding="utf-8") as f:
                    f.write(char_content)
                print(f"  ✓ Character: {char_file.name}")
    
    print(f"\n{'='*40}")
    if total_errors > 0:
        print(f"Completed with {total_errors} error(s)")
        return 1
    else:
        print("All dialogues converted successfully!")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Convert YAML dialogues to Dialogic 2 format")
    parser.add_argument("--validate", action="store_true", help="Validate only, don't generate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    
    args = parser.parse_args()
    
    exit_code = convert_all(validate_only=args.validate, dry_run=args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
