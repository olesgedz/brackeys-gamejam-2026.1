"""
Data models for the dialogue editor.
Independent of UI - pure Python data structures.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any
import uuid


class NodeType(Enum):
    """Types of dialogue nodes."""
    SAY = auto()
    CHOICE = auto()
    SET = auto()
    IF = auto()
    JUMP = auto()
    END = auto()
    SIGNAL = auto()


@dataclass
class NodePosition:
    """UI position for graph display."""
    x: float = 0.0
    y: float = 0.0


@dataclass
class ChoiceOption:
    """A single choice in a CHOICE node."""
    text: str = ""
    next: str = ""  # Node ID
    condition: Optional[str] = None


@dataclass
class DialogueNode:
    """A single node in the dialogue graph."""
    id: str = ""
    type: NodeType = NodeType.SAY
    
    # SAY fields
    speaker: str = ""
    text: str = ""
    
    # CHOICE fields
    choices: list[ChoiceOption] = field(default_factory=list)
    
    # SET fields (variable assignments)
    assignments: dict[str, Any] = field(default_factory=dict)
    
    # IF fields
    condition: str = ""
    then_node: str = ""
    else_node: str = ""
    
    # JUMP fields
    jump_target: str = ""
    
    # SIGNAL fields
    signal_name: str = ""
    signal_args: dict[str, Any] = field(default_factory=dict)
    
    # END fields
    outcome: str = ""
    
    # Common fields
    next: str = ""  # Next node ID (for SAY, SET, SIGNAL)
    
    # UI metadata
    ui_pos: NodePosition = field(default_factory=NodePosition)
    
    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:5]  # Short 5-char hex ID


@dataclass
class Character:
    """A character that can speak in dialogues."""
    id: str = ""
    name: str = ""
    portrait: str = ""  # Resource path
    color: str = "#ffffff"
    tags: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = f"char_{uuid.uuid4().hex[:8]}"
        if not self.name:
            self.name = self.id


@dataclass
class Dialogue:
    """A complete dialogue with nodes and characters."""
    id: str = ""
    title: str = ""
    start: str = ""  # Starting node ID
    characters: dict[str, Character] = field(default_factory=dict)
    nodes: dict[str, DialogueNode] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    
    # File path (for save/load)
    file_path: Optional[str] = None
    
    # Dirty flag
    is_modified: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = f"dialogue_{uuid.uuid4().hex[:8]}"
        if not self.title:
            self.title = self.id
    
    def add_node(self, node: DialogueNode) -> None:
        """Add a node to the dialogue."""
        self.nodes[node.id] = node
        self.is_modified = True
        
        # Set as start if first node
        if not self.start:
            self.start = node.id
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and clean up references."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.is_modified = True
            
            # Clean up references
            if self.start == node_id:
                self.start = ""
            
            for node in self.nodes.values():
                if node.next == node_id:
                    node.next = ""
                if node.then_node == node_id:
                    node.then_node = ""
                if node.else_node == node_id:
                    node.else_node = ""
                if node.jump_target == node_id:
                    node.jump_target = ""
                for choice in node.choices:
                    if choice.next == node_id:
                        choice.next = ""
    
    def add_character(self, character: Character) -> None:
        """Add a character to the dialogue."""
        self.characters[character.id] = character
        self.is_modified = True
    
    def remove_character(self, char_id: str) -> None:
        """Remove a character."""
        if char_id in self.characters:
            del self.characters[char_id]
            self.is_modified = True
    
    def get_all_node_ids(self) -> list[str]:
        """Get list of all node IDs."""
        return list(self.nodes.keys())
    
    def get_all_character_ids(self) -> list[str]:
        """Get list of all character IDs."""
        return list(self.characters.keys())
    
    def validate(self) -> list[str]:
        """Validate the dialogue structure. Returns list of errors."""
        errors = []
        
        if not self.id:
            errors.append("Dialogue missing 'id'")
        
        if not self.start:
            errors.append("Dialogue missing 'start' node")
        elif self.start not in self.nodes:
            errors.append(f"Start node '{self.start}' does not exist")
        
        # Check all node references
        for node_id, node in self.nodes.items():
            if node.next and node.next not in self.nodes:
                errors.append(f"Node '{node_id}': 'next' references unknown node '{node.next}'")
            
            if node.type == NodeType.CHOICE:
                for i, choice in enumerate(node.choices):
                    if choice.next and choice.next not in self.nodes:
                        errors.append(f"Node '{node_id}' choice {i}: references unknown node '{choice.next}'")
            
            if node.type == NodeType.IF:
                if node.then_node and node.then_node not in self.nodes:
                    errors.append(f"Node '{node_id}': 'then' references unknown node '{node.then_node}'")
                if node.else_node and node.else_node not in self.nodes:
                    errors.append(f"Node '{node_id}': 'else' references unknown node '{node.else_node}'")
            
            if node.type == NodeType.JUMP:
                if node.jump_target and node.jump_target not in self.nodes:
                    errors.append(f"Node '{node_id}': 'jump' references unknown node '{node.jump_target}'")
            
            # Check speaker exists
            if node.type == NodeType.SAY and node.speaker:
                if node.speaker not in self.characters:
                    errors.append(f"Node '{node_id}': speaker '{node.speaker}' not in characters")
        
        # Find unreachable nodes
        reachable = set()
        self._find_reachable(self.start, reachable)
        for node_id in self.nodes:
            if node_id not in reachable:
                errors.append(f"Node '{node_id}' is unreachable from start")
        
        return errors
    
    def _find_reachable(self, node_id: str, visited: set) -> None:
        """Recursively find all reachable nodes."""
        if not node_id or node_id in visited or node_id not in self.nodes:
            return
        
        visited.add(node_id)
        node = self.nodes[node_id]
        
        # Follow all outgoing edges
        if node.next:
            self._find_reachable(node.next, visited)
        
        for choice in node.choices:
            if choice.next:
                self._find_reachable(choice.next, visited)
        
        if node.then_node:
            self._find_reachable(node.then_node, visited)
        if node.else_node:
            self._find_reachable(node.else_node, visited)
        if node.jump_target:
            self._find_reachable(node.jump_target, visited)


@dataclass
class Project:
    """Collection of all dialogues in a project."""
    dialogues: dict[str, Dialogue] = field(default_factory=dict)
    root_path: str = ""
    
    def add_dialogue(self, dialogue: Dialogue) -> None:
        """Add a dialogue to the project."""
        self.dialogues[dialogue.id] = dialogue
    
    def remove_dialogue(self, dialogue_id: str) -> None:
        """Remove a dialogue from the project."""
        if dialogue_id in self.dialogues:
            del self.dialogues[dialogue_id]
    
    def get_dialogue(self, dialogue_id: str) -> Optional[Dialogue]:
        """Get a dialogue by ID."""
        return self.dialogues.get(dialogue_id)
