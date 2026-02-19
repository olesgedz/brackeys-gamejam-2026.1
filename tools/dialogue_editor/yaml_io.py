"""
YAML IO for dialogue files.
Handles loading, saving, and round-trip preservation.
"""

import os
from pathlib import Path
from typing import Optional, Any

import yaml

from .models import (
    Project, Dialogue, DialogueNode, Character,
    NodeType, ChoiceOption, NodePosition
)


class DialogueYAMLLoader:
    """Load dialogues from YAML files."""
    
    @staticmethod
    def load_project(root_path: str) -> Project:
        """Load all dialogues from a directory."""
        project = Project(root_path=root_path)
        
        src_dir = Path(root_path)
        if not src_dir.exists():
            return project
        
        for yaml_file in list(src_dir.glob("*.yaml")) + list(src_dir.glob("*.yml")):
            try:
                dialogue = DialogueYAMLLoader.load_dialogue(str(yaml_file))
                if dialogue:
                    dialogue.file_path = str(yaml_file)
                    project.add_dialogue(dialogue)
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")
        
        return project
    
    @staticmethod
    def load_dialogue(file_path: str) -> Optional[Dialogue]:
        """Load a single dialogue from a YAML file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data:
            return None
        
        dialogue = Dialogue(
            id=data.get("id", ""),
            title=data.get("title", ""),
            start=str(data.get("start", "")) if data.get("start") else "",
            tags=data.get("tags", []),
            file_path=file_path,
        )
        
        # Load characters
        for char_id, char_data in data.get("characters", {}).items():
            if isinstance(char_data, dict):
                character = Character(
                    id=char_id,
                    name=char_data.get("name", char_id),
                    portrait=char_data.get("portrait", ""),
                    color=char_data.get("color", "#ffffff"),
                    tags=char_data.get("tags", []),
                )
            else:
                character = Character(id=char_id, name=str(char_data))
            dialogue.characters[char_id] = character
        
        # Load nodes (convert IDs to strings in case YAML parsed them as ints)
        for node_id, node_data in data.get("nodes", {}).items():
            node_id_str = str(node_id)
            node = DialogueYAMLLoader._parse_node(node_id_str, node_data)
            dialogue.nodes[node_id_str] = node
        
        dialogue.is_modified = False
        return dialogue
    
    @staticmethod
    def _parse_node(node_id: str, data: dict) -> DialogueNode:
        """Parse a node from YAML data."""
        node = DialogueNode(id=node_id)
        
        # Determine type and parse accordingly
        if "say" in data:
            node.type = NodeType.SAY
            say_data = data["say"]
            if isinstance(say_data, dict):
                node.speaker = say_data.get("speaker", "")
                node.text = say_data.get("text", "")
            else:
                node.text = str(say_data)
        
        elif "choice" in data:
            node.type = NodeType.CHOICE
            for choice_data in data["choice"]:
                choice = ChoiceOption(
                    text=choice_data.get("text", ""),
                    next=str(choice_data.get("next", "")) if choice_data.get("next") else "",
                    condition=choice_data.get("if"),
                )
                node.choices.append(choice)
        
        elif "set" in data:
            node.type = NodeType.SET
            node.assignments = data["set"]
        
        elif "if" in data:
            node.type = NodeType.IF
            node.condition = str(data["if"])
            node.then_node = str(data.get("then", "")) if data.get("then") else ""
            node.else_node = str(data.get("else", "")) if data.get("else") else ""
        
        elif "jump" in data:
            node.type = NodeType.JUMP
            node.jump_target = str(data["jump"]) if data.get("jump") else ""
        
        elif "signal" in data:
            node.type = NodeType.SIGNAL
            sig = data["signal"]
            if isinstance(sig, dict):
                node.signal_name = sig.get("name", "")
                node.signal_args = sig.get("args", {})
            else:
                node.signal_name = str(sig)
        
        # Check for end
        if "end" in data:
            node.type = NodeType.END
            if data["end"] != True:
                node.outcome = str(data["end"])
        
        # Common fields
        if "next" in data:
            node.next = str(data["next"]) if data["next"] else ""
        
        # UI position (if stored)
        if "ui" in data:
            ui = data["ui"]
            node.ui_pos = NodePosition(
                x=ui.get("x", 0),
                y=ui.get("y", 0),
            )
        
        return node


class DialogueYAMLSaver:
    """Save dialogues to YAML files."""
    
    @staticmethod
    def save_dialogue(dialogue: Dialogue, file_path: Optional[str] = None) -> str:
        """Save a dialogue to YAML. Returns the file path."""
        path = file_path or dialogue.file_path
        if not path:
            raise ValueError("No file path specified")
        
        data = DialogueYAMLSaver._dialogue_to_dict(dialogue)
        
        yaml_str = yaml.dump(
            data,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        
        dialogue.file_path = path
        dialogue.is_modified = False
        return path
    
    @staticmethod
    def _dialogue_to_dict(dialogue: Dialogue) -> dict:
        """Convert dialogue to dictionary for YAML serialization."""
        data = {
            "id": dialogue.id,
        }
        
        if dialogue.title and dialogue.title != dialogue.id:
            data["title"] = dialogue.title
        
        if dialogue.tags:
            data["tags"] = dialogue.tags
        
        # Characters
        if dialogue.characters:
            data["characters"] = {}
            for char_id, char in dialogue.characters.items():
                char_data = {"name": char.name}
                if char.portrait:
                    char_data["portrait"] = char.portrait
                if char.color and char.color != "#ffffff":
                    char_data["color"] = char.color
                if char.tags:
                    char_data["tags"] = char.tags
                data["characters"][char_id] = char_data
        
        # Start node
        data["start"] = dialogue.start
        
        # Nodes
        data["nodes"] = {}
        for node_id, node in dialogue.nodes.items():
            node_data = DialogueYAMLSaver._node_to_dict(node)
            data["nodes"][node_id] = node_data
        
        return data
    
    @staticmethod
    def _node_to_dict(node: DialogueNode) -> dict:
        """Convert a node to dictionary."""
        data = {}
        
        # Type-specific content
        if node.type == NodeType.SAY:
            data["say"] = {
                "speaker": node.speaker,
                "text": node.text,
            }
        
        elif node.type == NodeType.CHOICE:
            choices = []
            for choice in node.choices:
                choice_data = {
                    "text": choice.text,
                    "next": choice.next,
                }
                if choice.condition:
                    choice_data["if"] = choice.condition
                choices.append(choice_data)
            data["choice"] = choices
        
        elif node.type == NodeType.SET:
            data["set"] = node.assignments
        
        elif node.type == NodeType.IF:
            data["if"] = node.condition
            if node.then_node:
                data["then"] = node.then_node
            if node.else_node:
                data["else"] = node.else_node
        
        elif node.type == NodeType.JUMP:
            data["jump"] = node.jump_target
        
        elif node.type == NodeType.SIGNAL:
            if node.signal_args:
                data["signal"] = {
                    "name": node.signal_name,
                    "args": node.signal_args,
                }
            else:
                data["signal"] = node.signal_name
        
        elif node.type == NodeType.END:
            data["end"] = node.outcome if node.outcome else True
        
        # Next (for non-branching nodes)
        if node.next and node.type not in (NodeType.CHOICE, NodeType.IF, NodeType.JUMP, NodeType.END):
            data["next"] = node.next
        
        # UI position (always save to preserve layout)
        data["ui"] = {
            "x": round(node.ui_pos.x, 1),
            "y": round(node.ui_pos.y, 1),
        }
        
        return data


def validate_yaml_file(file_path: str) -> list[str]:
    """Validate a YAML dialogue file. Returns list of errors."""
    errors = []
    
    try:
        dialogue = DialogueYAMLLoader.load_dialogue(file_path)
        if dialogue:
            errors = dialogue.validate()
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
    except Exception as e:
        errors.append(f"Error: {e}")
    
    return errors
