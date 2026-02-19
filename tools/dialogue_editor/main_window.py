"""
Main window for the Dialogue Editor.
PySide6-based visual editor for YAML dialogues.

Keyboard Shortcuts:
    Ctrl+N      - New SAY node (same speaker)
    Ctrl+M      - New SAY node (other speaker / reply)
    N           - Add SAY node
    C           - Add CHOICE node
    Delete      - Delete selected node
    Ctrl+S      - Save current dialogue
    Ctrl+Shift+S - Save all
    F5          - Validate
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QGraphicsEllipseItem,
    QDockWidget, QFormLayout, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QTabWidget, QScrollArea,
    QMenu, QMenuBar, QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QInputDialog, QGroupBox, QSpinBox, QColorDialog, QFrame
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QColor, QPen, QBrush, QFont,
    QPainter, QWheelEvent, QMouseEvent, QShortcut
)

from .models import (
    Project, Dialogue, DialogueNode, Character,
    NodeType, ChoiceOption, NodePosition
)
from .yaml_io import DialogueYAMLLoader, DialogueYAMLSaver


# ============================================================================
# GRAPH ITEMS
# ============================================================================

class NodeGraphicsItem(QGraphicsRectItem):
    """Visual representation of a dialogue node in the graph."""
    
    NODE_WIDTH = 400
    MIN_HEIGHT = 50
    LINE_HEIGHT = 18
    MAX_LINES = 3
    
    # Type-based colors (for non-SAY nodes)
    TYPE_COLORS = {
        NodeType.CHOICE: QColor("#ff9f4a"),
        NodeType.SET: QColor("#9f4aff"),
        NodeType.IF: QColor("#ffff4a"),
        NodeType.JUMP: QColor("#4aff9f"),
        NodeType.END: QColor("#ff4a4a"),
        NodeType.SIGNAL: QColor("#ff4aff"),
    }
    
    # Speaker-based colors for SAY nodes (will cycle through these)
    SPEAKER_COLORS = [
        QColor("#4a9eff"),  # Blue
        QColor("#ff6b9d"),  # Pink
        QColor("#50c878"),  # Green
        QColor("#dda0dd"),  # Plum
        QColor("#f0e68c"),  # Khaki
        QColor("#87ceeb"),  # Sky blue
        QColor("#ffa07a"),  # Light salmon
        QColor("#98fb98"),  # Pale green
    ]
    
    # Class-level speaker color mapping
    _speaker_color_map: dict = {}
    
    def __init__(self, node: DialogueNode, parent=None):
        super().__init__(0, 0, self.NODE_WIDTH, self.MIN_HEIGHT, parent)
        self.node = node
        self._height = self.MIN_HEIGHT
        self.setPos(node.ui_pos.x, node.ui_pos.y)
        self._graph_view = None  # Will be set by graph view
        
        # Make movable
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Styling
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        
        # Title text
        self.title_text = QGraphicsTextItem(self)
        self.title_text.setPos(5, 2)
        self.title_text.setDefaultTextColor(Qt.GlobalColor.white)
        font = QFont()
        font.setBold(True)
        self.title_text.setFont(font)
        
        # Content text
        self.content_text = QGraphicsTextItem(self)
        self.content_text.setPos(5, 20)
        self.content_text.setDefaultTextColor(Qt.GlobalColor.white)
        self.content_text.setTextWidth(self.NODE_WIDTH - 10)
        
        self.update_display()
    
    @classmethod
    def get_speaker_color(cls, speaker: str) -> QColor:
        """Get a consistent color for a speaker."""
        if not speaker:
            return QColor("#4a9eff")  # Default blue
        if speaker not in cls._speaker_color_map:
            color_index = len(cls._speaker_color_map) % len(cls.SPEAKER_COLORS)
            cls._speaker_color_map[speaker] = cls.SPEAKER_COLORS[color_index]
        return cls._speaker_color_map[speaker]
    
    def _truncate_lines(self, text: str, max_lines: int = 3) -> str:
        """Truncate text to max lines."""
        lines = text.split('\n')
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1][:40] + "..." if len(lines[-1]) > 40 else lines[-1] + "..."
        return '\n'.join(lines)
    
    def update_display(self):
        """Update the visual representation."""
        node = self.node
        
        # Title
        type_name = node.type.name
        self.title_text.setPlainText(f"[{type_name}] {node.id}")
        
        # Content preview
        content = ""
        if node.type == NodeType.SAY:
            speaker = node.speaker or "???"
            text = node.text[:80] + "..." if len(node.text) > 80 else node.text
            content = f"{speaker}: {text}"
        elif node.type == NodeType.CHOICE:
            # Show numbered choices
            choice_lines = []
            for i, choice in enumerate(node.choices[:self.MAX_LINES], 1):
                choice_text = choice.text[:50] + "..." if len(choice.text) > 50 else choice.text
                target = f" → {choice.next}" if choice.next else ""
                choice_lines.append(f"{i}. {choice_text}{target}")
            if len(node.choices) > self.MAX_LINES:
                choice_lines.append(f"... +{len(node.choices) - self.MAX_LINES} more")
            content = '\n'.join(choice_lines) if choice_lines else "(no choices)"
        elif node.type == NodeType.SET:
            content = ", ".join(f"{k}={v}" for k, v in list(node.assignments.items())[:2])
        elif node.type == NodeType.IF:
            content = f"if {node.condition}"
        elif node.type == NodeType.JUMP:
            content = f"→ {node.jump_target}"
        elif node.type == NodeType.END:
            content = f"END: {node.outcome}" if node.outcome else "END"
        elif node.type == NodeType.SIGNAL:
            content = f"signal: {node.signal_name}"
        
        # Truncate to max lines
        content = self._truncate_lines(content, self.MAX_LINES)
        self.content_text.setPlainText(content)
        
        # Calculate dynamic height
        line_count = content.count('\n') + 1
        content_height = line_count * self.LINE_HEIGHT
        self._height = max(self.MIN_HEIGHT, 25 + content_height)
        self.setRect(0, 0, self.NODE_WIDTH, self._height)
        
        # Update color based on type or speaker
        if node.type == NodeType.SAY:
            color = self.get_speaker_color(node.speaker)
        else:
            color = self.TYPE_COLORS.get(node.type, QColor("#888888"))
        self.setBrush(QBrush(color))
    
    def itemChange(self, change, value):
        """Handle position changes."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            self.node.ui_pos.x = pos.x()
            self.node.ui_pos.y = pos.y()
            # Notify graph view to update connections during drag
            if self._graph_view:
                self._graph_view.update_connections()
        return super().itemChange(change, value)
    
    def get_output_point(self) -> QPointF:
        """Get the connection output point (bottom center for top-to-bottom flow)."""
        return self.scenePos() + QPointF(self.NODE_WIDTH / 2, self._height)
    
    def get_input_point(self) -> QPointF:
        """Get the connection input point (top center for top-to-bottom flow)."""
        return self.scenePos() + QPointF(self.NODE_WIDTH / 2, 0)
    
    def get_choice_output_point(self, choice_index: int) -> QPointF:
        """Get output point for a specific choice (offset horizontally)."""
        # Spread choice outputs across the bottom
        num_choices = len(self.node.choices)
        if num_choices <= 1:
            return self.get_output_point()
        spacing = self.NODE_WIDTH / (num_choices + 1)
        x_offset = spacing * (choice_index + 1)
        return self.scenePos() + QPointF(x_offset, self._height)


class ConnectionLine(QGraphicsLineItem):
    """Visual connection between nodes with optional choice number label."""
    
    def __init__(self, start_item: NodeGraphicsItem, end_item: NodeGraphicsItem, 
                 choice_index: Optional[int] = None):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.choice_index = choice_index  # None for regular connections, 0-based for choices
        self.setPen(QPen(Qt.GlobalColor.white, 2))
        
        # Label for choice number
        self.label: Optional[QGraphicsTextItem] = None
        if choice_index is not None:
            self.label = QGraphicsTextItem(str(choice_index + 1))
            self.label.setDefaultTextColor(Qt.GlobalColor.white)
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            self.label.setFont(font)
        
        self.update_position()
    
    def update_position(self):
        """Update line position based on node positions."""
        if self.choice_index is not None:
            start = self.start_item.get_choice_output_point(self.choice_index)
        else:
            start = self.start_item.get_output_point()
        end = self.end_item.get_input_point()
        self.setLine(start.x(), start.y(), end.x(), end.y())
        
        # Update label position to middle of line
        if self.label:
            mid_x = (start.x() + end.x()) / 2 - 6
            mid_y = (start.y() + end.y()) / 2 - 8
            self.label.setPos(mid_x, mid_y)


# ============================================================================
# GRAPH VIEW
# ============================================================================

class NodeGraphView(QGraphicsView):
    """Graph view for displaying dialogue nodes."""
    
    node_selected = Signal(str)  # node_id
    node_double_clicked = Signal(str)  # node_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Scene background and large scene rect for unrestricted panning
        self.scene.setBackgroundBrush(QBrush(QColor("#2b2b2b")))
        self.scene.setSceneRect(-10000, -10000, 20000, 20000)
        
        # Items tracking
        self.node_items: dict[str, NodeGraphicsItem] = {}
        self.connection_lines: list[ConnectionLine] = []
        
        # Current dialogue
        self.dialogue: Optional[Dialogue] = None
        
        # Panning state
        self._panning = False
        self._pan_start = QPointF()
    
    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel."""
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle selection and panning."""
        # Middle mouse button - start panning
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        
        super().mousePressEvent(event)
        
        item = self.itemAt(event.pos())
        if isinstance(item, NodeGraphicsItem):
            self.node_selected.emit(item.node.id)
        elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), NodeGraphicsItem):
            self.node_selected.emit(item.parentItem().node.id)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle panning."""
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle end of panning."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double click for editing."""
        item = self.itemAt(event.pos())
        if isinstance(item, NodeGraphicsItem):
            self.node_double_clicked.emit(item.node.id)
        elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), NodeGraphicsItem):
            self.node_double_clicked.emit(item.parentItem().node.id)
        else:
            super().mouseDoubleClickEvent(event)
    
    def load_dialogue(self, dialogue: Dialogue):
        """Load a dialogue into the view."""
        self.dialogue = dialogue
        self.clear()
        
        # Create node items
        for node_id, node in dialogue.nodes.items():
            item = NodeGraphicsItem(node)
            item._graph_view = self  # Set reference for connection updates
            self.scene.addItem(item)
            self.node_items[node_id] = item
        
        # Create connections
        self._create_connections()
        
        # Fit to view
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def _create_connections(self):
        """Create connection lines between nodes."""
        if not self.dialogue:
            return
        
        # Clear old connections and their labels
        for line in self.connection_lines:
            if line.label:
                self.scene.removeItem(line.label)
            self.scene.removeItem(line)
        self.connection_lines.clear()
        
        # Create new connections
        for node_id, node in self.dialogue.nodes.items():
            start_item = self.node_items.get(node_id)
            if not start_item:
                continue
            
            # Direct next
            if node.next and node.next in self.node_items:
                end_item = self.node_items[node.next]
                line = ConnectionLine(start_item, end_item)
                self.scene.addItem(line)
                self.connection_lines.append(line)
            
            # Choice connections with numbered labels
            for i, choice in enumerate(node.choices):
                if choice.next and choice.next in self.node_items:
                    end_item = self.node_items[choice.next]
                    line = ConnectionLine(start_item, end_item, choice_index=i)
                    line.setPen(QPen(QColor("#ff9f4a"), 2))  # Orange for choices
                    self.scene.addItem(line)
                    if line.label:
                        self.scene.addItem(line.label)
                    self.connection_lines.append(line)
            
            # If/then/else
            if node.then_node and node.then_node in self.node_items:
                end_item = self.node_items[node.then_node]
                line = ConnectionLine(start_item, end_item)
                line.setPen(QPen(QColor("#4aff4a"), 2))  # Green for then
                self.scene.addItem(line)
                self.connection_lines.append(line)
            
            if node.else_node and node.else_node in self.node_items:
                end_item = self.node_items[node.else_node]
                line = ConnectionLine(start_item, end_item)
                line.setPen(QPen(QColor("#ff4a4a"), 2))  # Red for else
                self.scene.addItem(line)
                self.connection_lines.append(line)
            
            # Jump
            if node.jump_target and node.jump_target in self.node_items:
                end_item = self.node_items[node.jump_target]
                line = ConnectionLine(start_item, end_item)
                line.setPen(QPen(QColor("#4aff9f"), 2, Qt.PenStyle.DashLine))
                self.scene.addItem(line)
                self.connection_lines.append(line)
    
    def clear(self):
        """Clear the view."""
        self.scene.clear()
        self.node_items.clear()
        self.connection_lines.clear()
    
    def refresh_node(self, node_id: str):
        """Refresh a single node's display."""
        if node_id in self.node_items:
            self.node_items[node_id].update_display()
        self._create_connections()
    
    def add_node(self, node: DialogueNode, x: float = 0, y: float = 0):
        """Add a new node to the view."""
        node.ui_pos.x = x
        node.ui_pos.y = y
        item = NodeGraphicsItem(node)
        item._graph_view = self  # Set reference for connection updates
        self.scene.addItem(item)
        self.node_items[node.id] = item
    
    def update_connections(self):
        """Update connection line positions (called during node drag)."""
        for line in self.connection_lines:
            line.update_position()
    
    def remove_node(self, node_id: str):
        """Remove a node from the view."""
        if node_id in self.node_items:
            item = self.node_items[node_id]
            self.scene.removeItem(item)
            del self.node_items[node_id]
            self._create_connections()
    
    def get_selected_node_id(self) -> Optional[str]:
        """Get the currently selected node ID."""
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, NodeGraphicsItem):
                return item.node.id
        return None


# ============================================================================
# CHARACTER PANEL
# ============================================================================

class CharacterPanel(QWidget):
    """Panel for managing characters in a dialogue."""
    
    characters_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialogue: Optional[Dialogue] = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Character list
        self.char_list = QListWidget()
        self.char_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.char_list.itemDoubleClicked.connect(self._edit_character)
        layout.addWidget(self.char_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("+")
        add_btn.setMaximumWidth(30)
        add_btn.setToolTip("Add Character (Ctrl+Shift+C)")
        add_btn.clicked.connect(self._add_character)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✎")
        edit_btn.setMaximumWidth(30)
        edit_btn.setToolTip("Edit Character")
        edit_btn.clicked.connect(self._edit_character)
        btn_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("−")
        remove_btn.setMaximumWidth(30)
        remove_btn.setToolTip("Remove Character")
        remove_btn.clicked.connect(self._remove_character)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def set_dialogue(self, dialogue: Dialogue):
        """Set the current dialogue."""
        self.dialogue = dialogue
        self._refresh_list()
    
    def _refresh_list(self):
        """Refresh the character list."""
        self.char_list.clear()
        if not self.dialogue:
            return
        
        for char_id, char in self.dialogue.characters.items():
            display_name = f"{char_id}: {char.name}" if char.name != char_id else char_id
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, char_id)
            self.char_list.addItem(item)
    
    def _on_selection_changed(self):
        """Handle selection change."""
        pass
    
    def _add_character(self):
        """Add a new character."""
        if not self.dialogue:
            return
        
        char_id, ok = QInputDialog.getText(self, "Add Character", "Character ID:")
        if not ok or not char_id:
            return
        
        char_id = char_id.strip().lower().replace(" ", "_")
        
        if char_id in self.dialogue.characters:
            QMessageBox.warning(self, "Error", f"Character '{char_id}' already exists")
            return
        
        name, ok = QInputDialog.getText(self, "Add Character", "Display name:", text=char_id.title())
        if not ok:
            return
        
        character = Character(id=char_id, name=name or char_id)
        self.dialogue.characters[char_id] = character
        self.dialogue.is_modified = True
        
        self._refresh_list()
        self.characters_changed.emit()
    
    def _edit_character(self, item: Optional[QListWidgetItem] = None):
        """Edit selected character."""
        if not self.dialogue:
            return
        
        if item is None:
            item = self.char_list.currentItem()
        if not item:
            return
        
        char_id = item.data(Qt.ItemDataRole.UserRole)
        if char_id not in self.dialogue.characters:
            return
        
        char = self.dialogue.characters[char_id]
        
        name, ok = QInputDialog.getText(
            self, "Edit Character",
            f"Display name for '{char_id}':",
            text=char.name
        )
        if ok:
            char.name = name or char_id
            self.dialogue.is_modified = True
            self._refresh_list()
            self.characters_changed.emit()
    
    def _remove_character(self):
        """Remove selected character."""
        if not self.dialogue:
            return
        
        item = self.char_list.currentItem()
        if not item:
            return
        
        char_id = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Remove Character",
            f"Remove character '{char_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.dialogue.characters[char_id]
            self.dialogue.is_modified = True
            self._refresh_list()
            self.characters_changed.emit()


# ============================================================================
# INSPECTOR PANEL
# ============================================================================

class NodeInspector(QWidget):
    """Inspector panel for editing node properties."""
    
    node_changed = Signal(str)  # node_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialogue: Optional[Dialogue] = None
        self.current_node: Optional[DialogueNode] = None
        
        layout = QVBoxLayout(self)
        
        # Node info
        info_group = QGroupBox("Node")
        info_layout = QFormLayout(info_group)
        
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)
        info_layout.addRow("ID:", self.id_edit)
        
        self.type_combo = QComboBox()
        for nt in NodeType:
            self.type_combo.addItem(nt.name, nt)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        info_layout.addRow("Type:", self.type_combo)
        
        layout.addWidget(info_group)
        
        # SAY fields
        self.say_group = QGroupBox("Say")
        say_layout = QFormLayout(self.say_group)
        
        self.speaker_combo = QComboBox()
        self.speaker_combo.setEditable(True)
        self.speaker_combo.currentTextChanged.connect(self._on_field_changed)
        self.speaker_combo.activated.connect(self._on_speaker_selected)
        say_layout.addRow("Speaker:", self.speaker_combo)
        
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)
        self.text_edit.textChanged.connect(self._on_field_changed)
        say_layout.addRow("Text:", self.text_edit)
        
        layout.addWidget(self.say_group)
        
        # CHOICE fields
        self.choice_group = QGroupBox("Choices (double-click to edit)")
        choice_layout = QVBoxLayout(self.choice_group)
        
        self.choices_list = QListWidget()
        self.choices_list.itemDoubleClicked.connect(self._edit_choice)
        self.choices_list.itemSelectionChanged.connect(self._on_choice_selection_changed)
        choice_layout.addWidget(self.choices_list)
        
        choice_buttons = QHBoxLayout()
        add_choice_btn = QPushButton("+ Add")
        add_choice_btn.clicked.connect(self._add_choice)
        edit_choice_btn = QPushButton("✎ Edit")
        edit_choice_btn.clicked.connect(self._edit_selected_choice)
        self.link_choice_btn = QPushButton("🔗 Link")
        self.link_choice_btn.setToolTip("Set target node for selected choice")
        self.link_choice_btn.clicked.connect(self._link_choice)
        self.new_node_btn = QPushButton("➕ New Node")
        self.new_node_btn.setToolTip("Create new SAY node and link to this choice")
        self.new_node_btn.clicked.connect(self._create_and_link_choice_node)
        remove_choice_btn = QPushButton("− Remove")
        remove_choice_btn.clicked.connect(self._remove_choice)
        choice_buttons.addWidget(add_choice_btn)
        choice_buttons.addWidget(edit_choice_btn)
        choice_buttons.addWidget(self.link_choice_btn)
        choice_buttons.addWidget(self.new_node_btn)
        choice_buttons.addWidget(remove_choice_btn)
        choice_layout.addLayout(choice_buttons)
        
        layout.addWidget(self.choice_group)
        
        # Next node
        next_group = QGroupBox("Flow")
        next_layout = QFormLayout(next_group)
        
        self.next_combo = QComboBox()
        self.next_combo.setEditable(True)
        self.next_combo.currentTextChanged.connect(self._on_field_changed)
        next_layout.addRow("Next:", self.next_combo)
        
        layout.addWidget(next_group)
        
        # Spacer
        layout.addStretch()
        
        self._update_visibility()
    
    def set_dialogue(self, dialogue: Dialogue):
        """Set the current dialogue for character list."""
        self.dialogue = dialogue
        self._update_speaker_list()
        self._update_node_list()
    
    def load_node(self, node: DialogueNode):
        """Load a node for editing."""
        self.current_node = node
        
        # Block signals during load
        self.type_combo.blockSignals(True)
        self.speaker_combo.blockSignals(True)
        self.text_edit.blockSignals(True)
        self.next_combo.blockSignals(True)
        
        self.id_edit.setText(node.id)
        self.type_combo.setCurrentIndex(list(NodeType).index(node.type))
        self.speaker_combo.setCurrentText(node.speaker)
        self.text_edit.setPlainText(node.text)
        self.next_combo.setCurrentText(node.next)
        
        # Load choices
        self._refresh_choices_list()
        
        # Unblock signals
        self.type_combo.blockSignals(False)
        self.speaker_combo.blockSignals(False)
        self.text_edit.blockSignals(False)
        self.next_combo.blockSignals(False)
        
        self._update_visibility()
    
    def _update_visibility(self):
        """Show/hide fields based on node type."""
        if not self.current_node:
            self.say_group.hide()
            self.choice_group.hide()
            return
        
        node_type = self.current_node.type
        self.say_group.setVisible(node_type == NodeType.SAY)
        self.choice_group.setVisible(node_type == NodeType.CHOICE)
        
        # Update choice button states
        if node_type == NodeType.CHOICE:
            self._on_choice_selection_changed()
    
    def _update_speaker_list(self):
        """Update speaker dropdown with characters."""
        self.speaker_combo.clear()
        self.speaker_combo.addItem("")
        if self.dialogue:
            for char_id in self.dialogue.characters:
                self.speaker_combo.addItem(char_id)
    
    def _update_node_list(self):
        """Update next node dropdown."""
        self.next_combo.clear()
        self.next_combo.addItem("")
        if self.dialogue:
            for node_id in self.dialogue.nodes:
                self.next_combo.addItem(str(node_id))
    
    def _on_type_changed(self):
        """Handle type change."""
        if not self.current_node:
            return
        self.current_node.type = self.type_combo.currentData()
        self._update_visibility()
        self.node_changed.emit(self.current_node.id)
    
    def _on_field_changed(self):
        """Handle field changes."""
        if not self.current_node:
            return
        
        self.current_node.speaker = self.speaker_combo.currentText()
        self.current_node.text = self.text_edit.toPlainText()
        self.current_node.next = self.next_combo.currentText()
        
        if self.dialogue:
            self.dialogue.is_modified = True
        
        self.node_changed.emit(self.current_node.id)
    
    def _on_speaker_selected(self, index: int):
        """Handle speaker selection from dropdown - close popup and focus text."""
        self.speaker_combo.hidePopup()
        self.text_edit.setFocus()
    
    def _refresh_choices_list(self):
        """Refresh the choices list display."""
        self.choices_list.clear()
        if not self.current_node:
            return
        for i, choice in enumerate(self.current_node.choices, 1):
            target = f" → {choice.next}" if choice.next else " → ?"
            self.choices_list.addItem(f"{i}. {choice.text}{target}")
    
    def _add_choice(self):
        """Add a new choice."""
        if not self.current_node:
            return
        
        text, ok = QInputDialog.getText(self, "Add Choice", "Choice text:")
        if ok and text:
            choice = ChoiceOption(text=text)
            self.current_node.choices.append(choice)
            self._refresh_choices_list()
            if self.dialogue:
                self.dialogue.is_modified = True
            self.node_changed.emit(self.current_node.id)
    
    def _edit_choice(self, item):
        """Edit choice on double-click."""
        self._edit_selected_choice()
    
    def _edit_selected_choice(self):
        """Edit the selected choice text."""
        if not self.current_node:
            return
        
        row = self.choices_list.currentRow()
        if row < 0 or row >= len(self.current_node.choices):
            return
        
        choice = self.current_node.choices[row]
        text, ok = QInputDialog.getText(
            self, "Edit Choice", "Choice text:", 
            text=choice.text
        )
        if ok and text:
            choice.text = text
            self._refresh_choices_list()
            if self.dialogue:
                self.dialogue.is_modified = True
            self.node_changed.emit(self.current_node.id)
    
    def _on_choice_selection_changed(self):
        """Update button states based on choice selection."""
        row = self.choices_list.currentRow()
        has_selection = row >= 0 and self.current_node and row < len(self.current_node.choices)
        
        if has_selection:
            choice = self.current_node.choices[row]
            already_linked = bool(choice.next)
            self.new_node_btn.setEnabled(not already_linked)
            self.new_node_btn.setToolTip(
                "Already linked" if already_linked else "Create new SAY node and link to this choice"
            )
        else:
            self.new_node_btn.setEnabled(False)
    
    def _get_nodes_with_incoming(self) -> set:
        """Get set of node IDs that have incoming connections."""
        if not self.dialogue:
            return set()
        
        incoming = set()
        for node in self.dialogue.nodes.values():
            if node.next:
                incoming.add(node.next)
            for choice in node.choices:
                if choice.next:
                    incoming.add(choice.next)
            if node.then_node:
                incoming.add(node.then_node)
            if node.else_node:
                incoming.add(node.else_node)
            if node.jump_target:
                incoming.add(node.jump_target)
        return incoming
    
    def _link_choice(self):
        """Link selected choice to a target node."""
        if not self.current_node or not self.dialogue:
            return
        
        row = self.choices_list.currentRow()
        if row < 0 or row >= len(self.current_node.choices):
            QMessageBox.warning(self, "No Selection", "Select a choice first")
            return
        
        choice = self.current_node.choices[row]
        
        # Get nodes without incoming connections (orphans/entry points)
        nodes_with_incoming = self._get_nodes_with_incoming()
        
        # Build node list - orphans first, then option to show all
        # Convert to strings in case YAML parsed them as ints
        orphan_nodes = [str(nid) for nid in self.dialogue.nodes.keys() 
                       if nid not in nodes_with_incoming and nid != self.current_node.id]
        all_other_nodes = [str(nid) for nid in self.dialogue.nodes.keys() 
                          if nid != self.current_node.id and str(nid) not in orphan_nodes]
        
        # Create dialog with checkbox
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Link Choice")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"Target node for choice {row + 1}:"))
        
        show_all_cb = QCheckBox("Show all nodes (including already connected)")
        layout.addWidget(show_all_cb)
        
        node_combo = QComboBox()
        node_combo.addItem("(none)", "")
        for nid in orphan_nodes:
            node_combo.addItem(nid, nid)
        
        def update_combo():
            current = node_combo.currentData()
            node_combo.clear()
            node_combo.addItem("(none)", "")
            for nid in orphan_nodes:
                node_combo.addItem(nid, nid)
            if show_all_cb.isChecked():
                if orphan_nodes and all_other_nodes:
                    node_combo.insertSeparator(len(orphan_nodes) + 1)
                for nid in all_other_nodes:
                    node_combo.addItem(f"● {nid}", nid)
            # Restore selection
            idx = node_combo.findData(current)
            if idx >= 0:
                node_combo.setCurrentIndex(idx)
        
        show_all_cb.toggled.connect(update_combo)
        layout.addWidget(node_combo)
        
        # Set current value
        if choice.next:
            idx = node_combo.findData(choice.next)
            if idx < 0:
                # Not in orphans, need to show all
                show_all_cb.setChecked(True)
                idx = node_combo.findData(choice.next)
            if idx >= 0:
                node_combo.setCurrentIndex(idx)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            choice.next = node_combo.currentData() or ""
            self._refresh_choices_list()
            self._on_choice_selection_changed()
            if self.dialogue:
                self.dialogue.is_modified = True
            self.node_changed.emit(self.current_node.id)
    
    def _create_and_link_choice_node(self):
        """Create a new SAY node and link it to the selected choice."""
        if not self.current_node or not self.dialogue:
            return
        
        row = self.choices_list.currentRow()
        if row < 0 or row >= len(self.current_node.choices):
            return
        
        choice = self.current_node.choices[row]
        if choice.next:  # Already linked
            return
        
        # Create new SAY node
        from .models import DialogueNode, NodeType
        new_node = DialogueNode(type=NodeType.SAY)
        
        # Position below and offset by choice index
        base_x = self.current_node.ui_pos.x
        base_y = self.current_node.ui_pos.y + 100
        offset_x = (row - len(self.current_node.choices) / 2) * 150
        new_node.ui_pos.x = base_x + offset_x
        new_node.ui_pos.y = base_y
        
        # Link choice to new node
        choice.next = new_node.id
        
        # Add to dialogue
        self.dialogue.add_node(new_node)
        self.dialogue.is_modified = True
        
        # Refresh UI
        self._refresh_choices_list()
        self._on_choice_selection_changed()
        self.node_changed.emit(self.current_node.id)
        
        # Notify parent window to add the node to graph
        # This is a bit hacky but works
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        if parent and hasattr(parent, 'graph_view'):
            parent.graph_view.add_node(new_node, new_node.ui_pos.x, new_node.ui_pos.y)
            parent.graph_view._create_connections()
            parent.inspector._update_node_list()
    
    def _remove_choice(self):
        """Remove selected choice."""
        if not self.current_node:
            return
        
        row = self.choices_list.currentRow()
        if row >= 0 and row < len(self.current_node.choices):
            del self.current_node.choices[row]
            self._refresh_choices_list()
            if self.dialogue:
                self.dialogue.is_modified = True
            self.node_changed.emit(self.current_node.id)


# ============================================================================
# MAIN WINDOW
# ============================================================================

class DialogueEditorWindow(QMainWindow):
    """Main window for the Dialogue Editor."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dialogue Editor")
        self.setMinimumSize(1200, 800)
        
        self.project: Optional[Project] = None
        self.current_dialogue: Optional[Dialogue] = None
        self._last_active_node_id: Optional[str] = None
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        
        # Left panel: Dialogue browser + Characters
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Dialogues section
        left_layout.addWidget(QLabel("Dialogues"))
        
        self.dialogue_tree = QTreeWidget()
        self.dialogue_tree.setHeaderHidden(True)
        self.dialogue_tree.itemClicked.connect(self._on_dialogue_selected)
        left_layout.addWidget(self.dialogue_tree)
        
        # Dialogue buttons
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_dialogue)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_dialogue)
        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(delete_btn)
        left_layout.addLayout(btn_layout)
        
        # Characters section
        left_layout.addWidget(QLabel("Characters"))
        
        self.character_panel = CharacterPanel()
        self.character_panel.characters_changed.connect(self._on_characters_changed)
        left_layout.addWidget(self.character_panel)
        
        splitter.addWidget(left_panel)
        
        # Center: Node graph
        self.graph_view = NodeGraphView()
        self.graph_view.node_selected.connect(self._on_node_selected)
        splitter.addWidget(self.graph_view)
        
        # Right panel: Inspector
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        right_layout.addWidget(QLabel("Inspector"))
        
        self.inspector = NodeInspector()
        self.inspector.node_changed.connect(self._on_node_changed)
        right_layout.addWidget(self.inspector)
        
        splitter.addWidget(right_panel)
        
        # Set splitter sizes
        splitter.setSizes([200, 700, 300])
    
    def _setup_menu(self):
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_file_action = QAction("Open File...", self)
        open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        open_file_action.triggered.connect(self._open_file)
        file_menu.addAction(open_file_action)
        
        open_folder_action = QAction("Open Folder...", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self._open_project)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_current)
        file_menu.addAction(save_action)
        
        save_all_action = QAction("Save All", self)
        save_all_action.setShortcut("Ctrl+Shift+S")
        save_all_action.triggered.connect(self._save_all)
        file_menu.addAction(save_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        continue_action = QAction("Continue (Same Speaker)", self)
        continue_action.setShortcut("Ctrl+N")
        continue_action.triggered.connect(self._continue_same_speaker)
        edit_menu.addAction(continue_action)
        
        reply_action = QAction("Reply (Other Speaker)", self)
        reply_action.setShortcut("Ctrl+M")
        reply_action.triggered.connect(self._reply_other_speaker)
        edit_menu.addAction(reply_action)
        
        edit_menu.addSeparator()
        
        add_choice_action = QAction("Add CHOICE Node", self)
        add_choice_action.setShortcut("Ctrl+B")
        add_choice_action.triggered.connect(lambda: self._add_node(NodeType.CHOICE))
        edit_menu.addAction(add_choice_action)
        
        add_end_action = QAction("Add END Node", self)
        add_end_action.setShortcut("Ctrl+E")
        add_end_action.triggered.connect(lambda: self._add_node(NodeType.END))
        edit_menu.addAction(add_end_action)
        
        edit_menu.addSeparator()
        
        delete_node_action = QAction("Delete Node", self)
        delete_node_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_node_action.triggered.connect(self._delete_selected_node)
        edit_menu.addAction(delete_node_action)
        
        # Characters menu
        char_menu = menubar.addMenu("Characters")
        
        add_char_action = QAction("Add Character", self)
        add_char_action.setShortcut("Ctrl+Shift+C")
        add_char_action.triggered.connect(self.character_panel._add_character)
        char_menu.addAction(add_char_action)
        
        # Validate menu
        validate_menu = menubar.addMenu("Validate")
        
        validate_action = QAction("Validate Current", self)
        validate_action.setShortcut("F5")
        validate_action.triggered.connect(self._validate_current)
        validate_menu.addAction(validate_action)
    
    def _setup_toolbar(self):
        """Setup toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        toolbar.addAction("Open (Ctrl+O)", self._open_file)
        toolbar.addAction("Save (Ctrl+S)", self._save_current)
        toolbar.addSeparator()
        
        # Order: Continue, Reply, Choice, End
        continue_action = toolbar.addAction("Continue (Ctrl+N)", self._continue_same_speaker)
        continue_action.setToolTip("Continue dialogue with same speaker")
        
        reply_action = toolbar.addAction("Reply (Ctrl+M)", self._reply_other_speaker)
        reply_action.setToolTip("Reply from another speaker")
        
        toolbar.addSeparator()
        
        choice_action = toolbar.addAction("+ Choice (Ctrl+B)", lambda: self._add_node(NodeType.CHOICE))
        choice_action.setToolTip("Add CHOICE node with branching options")
        
        end_action = toolbar.addAction("+ End (Ctrl+E)", lambda: self._add_node(NodeType.END))
        end_action.setToolTip("Add END node to finish dialogue")
        
        toolbar.addSeparator()
        toolbar.addAction("Validate (F5)", self._validate_current)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready — Ctrl+N: continue same speaker | Ctrl+M: reply other speaker")
    
    def _setup_shortcuts(self):
        """Setup additional keyboard shortcuts."""
        # Shortcuts are already set up in menu actions
        pass
    
    # ========== Quick Node Creation ==========
    
    def _get_current_speaker(self) -> str:
        """Get the speaker of the currently selected or last active node."""
        if not self.current_dialogue:
            return ""
        
        # Try selected node first, then last active
        node_id = self.graph_view.get_selected_node_id() or self._last_active_node_id
        if node_id and node_id in self.current_dialogue.nodes:
            node = self.current_dialogue.nodes[node_id]
            if node.type == NodeType.SAY:
                return node.speaker
        
        return ""
    
    def _get_speaker_history(self) -> list[str]:
        """Get list of speakers in chronological order (by node chain from start)."""
        if not self.current_dialogue:
            return []
        
        speakers = []
        visited = set()
        
        # Walk from start node
        current = self.current_dialogue.start
        while current and current not in visited:
            visited.add(current)
            if current in self.current_dialogue.nodes:
                node = self.current_dialogue.nodes[current]
                if node.type == NodeType.SAY and node.speaker:
                    speakers.append(node.speaker)
                current = node.next
            else:
                break
        
        return speakers
    
    def _get_other_speaker(self) -> str:
        """Get the 'other' speaker for a reply.
        
        Logic:
        - If only 2 characters: return the one that's not current
        - If polylogue: return the last speaker different from current
        """
        if not self.current_dialogue:
            return ""
        
        current_speaker = self._get_current_speaker()
        characters = list(self.current_dialogue.characters.keys())
        
        # If exactly 2 characters, return the other one
        if len(characters) == 2:
            for char in characters:
                if char != current_speaker:
                    return char
        
        # For polylogue: find last different speaker
        history = self._get_speaker_history()
        for speaker in reversed(history):
            if speaker != current_speaker:
                return speaker
        
        # Fallback: first character that's not current
        for char in characters:
            if char != current_speaker:
                return char
        
        return ""
    
    def _add_node_after_selected(self, node_type: NodeType, speaker: str = "") -> Optional[DialogueNode]:
        """Add a new node after the currently selected one."""
        if not self.current_dialogue:
            self.statusBar().showMessage("No dialogue open")
            return None
        
        # Create new node
        node = DialogueNode(type=node_type)
        if speaker:
            node.speaker = speaker
        
        # Find the node to link from: selection > last active > none
        selected_id = self.graph_view.get_selected_node_id()
        link_from_id = selected_id or self._last_active_node_id
        
        if link_from_id and link_from_id in self.current_dialogue.nodes:
            link_from_node = self.current_dialogue.nodes[link_from_id]
            # Position below (top-to-bottom flow)
            node.ui_pos.x = link_from_node.ui_pos.x
            node.ui_pos.y = link_from_node.ui_pos.y + 85
            
            # Link: link_from -> new -> old_next
            old_next = link_from_node.next
            link_from_node.next = node.id
            node.next = old_next
            
            # Refresh the source node display
            self.graph_view.refresh_node(link_from_id)
        else:
            # No node to link from, position at top
            node.ui_pos.x = 0
            node.ui_pos.y = len(self.current_dialogue.nodes) * 85
        
        self.current_dialogue.add_node(node)
        self.current_dialogue.is_modified = True
        
        self.graph_view.add_node(node, node.ui_pos.x, node.ui_pos.y)
        self.graph_view._create_connections()
        self.inspector._update_node_list()
        
        # Select the new node and track it as last active
        if node.id in self.graph_view.node_items:
            self.graph_view.scene.clearSelection()
            self.graph_view.node_items[node.id].setSelected(True)
            self.inspector.load_node(node)
            self._last_active_node_id = node.id
        
        return node
    
    def _continue_same_speaker(self):
        """Add a new SAY node with the same speaker (Ctrl+N)."""
        speaker = self._get_current_speaker()
        node = self._add_node_after_selected(NodeType.SAY, speaker)
        if node:
            self.statusBar().showMessage(f"Added SAY node: {node.id} (speaker: {speaker or 'none'})")
    
    def _reply_other_speaker(self):
        """Add a new SAY node with a different speaker (Ctrl+M)."""
        speaker = self._get_other_speaker()
        node = self._add_node_after_selected(NodeType.SAY, speaker)
        if node:
            self.statusBar().showMessage(f"Added SAY node: {node.id} (speaker: {speaker or 'none'})")
    
    # ========== Actions ==========
    
    def _open_file(self):
        """Open a single YAML dialogue file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Dialogue File",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if path:
            try:
                dialogue = DialogueYAMLLoader.load_dialogue(path)
                if dialogue:
                    # Create a mini-project for this file
                    from pathlib import Path
                    folder = str(Path(path).parent)
                    self.project = Project(root_path=folder)
                    self.project.add_dialogue(dialogue)
                    self._refresh_dialogue_tree()
                    
                    # Auto-select the loaded dialogue
                    self.current_dialogue = dialogue
                    self.graph_view.load_dialogue(dialogue)
                    self.inspector.set_dialogue(dialogue)
                    self.character_panel.set_dialogue(dialogue)
                    
                    self.statusBar().showMessage(f"Opened: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open: {e}")
    
    def _open_project(self):
        """Open a project directory."""
        path = QFileDialog.getExistingDirectory(
            self, "Open Dialogues Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self.project = DialogueYAMLLoader.load_project(path)
            self._refresh_dialogue_tree()
            self.statusBar().showMessage(f"Opened: {path}")
    
    def _save_current(self):
        """Save current dialogue."""
        if not self.current_dialogue:
            return
        
        if not self.current_dialogue.file_path:
            # Need to get a path
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Dialogue",
                f"{self.current_dialogue.id}.yaml",
                "YAML Files (*.yaml *.yml)"
            )
            if not path:
                return
            self.current_dialogue.file_path = path
        
        try:
            DialogueYAMLSaver.save_dialogue(self.current_dialogue)
            self.current_dialogue.is_modified = False
            self._refresh_dialogue_tree()
            self.statusBar().showMessage(f"Saved: {self.current_dialogue.file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
    
    def _save_all(self):
        """Save all modified dialogues."""
        if not self.project:
            return
        
        saved = 0
        for dialogue in self.project.dialogues.values():
            if dialogue.is_modified and dialogue.file_path:
                try:
                    DialogueYAMLSaver.save_dialogue(dialogue)
                    dialogue.is_modified = False
                    saved += 1
                except Exception as e:
                    print(f"Error saving {dialogue.id}: {e}")
        
        self._refresh_dialogue_tree()
        self.statusBar().showMessage(f"Saved {saved} dialogue(s)")
    
    def _new_dialogue(self):
        """Create a new dialogue."""
        if not self.project:
            QMessageBox.warning(self, "Warning", "Open a project first")
            return
        
        name, ok = QInputDialog.getText(self, "New Dialogue", "Dialogue ID:")
        if ok and name:
            dialogue = Dialogue(id=name, title=name)
            dialogue.file_path = f"{self.project.root_path}/{name}.yaml"
            self.project.add_dialogue(dialogue)
            self._refresh_dialogue_tree()
    
    def _delete_dialogue(self):
        """Delete selected dialogue."""
        item = self.dialogue_tree.currentItem()
        if not item or not self.project:
            return
        
        dialogue_id = item.data(0, Qt.ItemDataRole.UserRole)
        if dialogue_id:
            reply = QMessageBox.question(
                self, "Delete",
                f"Delete dialogue '{dialogue_id}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.project.remove_dialogue(dialogue_id)
                self._refresh_dialogue_tree()
                self.graph_view.clear()
                self.current_dialogue = None
    
    def _add_node(self, node_type: NodeType):
        """Add a new node linked to the last active node."""
        node = self._add_node_after_selected(node_type)
        if node:
            self.statusBar().showMessage(f"Added {node_type.name} node: {node.id}")
    
    def _delete_selected_node(self):
        """Delete the selected node."""
        if not self.current_dialogue:
            return
        
        selected = self.graph_view.scene.selectedItems()
        for item in selected:
            if isinstance(item, NodeGraphicsItem):
                self.current_dialogue.remove_node(item.node.id)
                self.graph_view.remove_node(item.node.id)
                self.inspector._update_node_list()
    
    def _validate_current(self):
        """Validate current dialogue."""
        if not self.current_dialogue:
            return
        
        errors = self.current_dialogue.validate()
        if errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "\n".join(errors)
            )
        else:
            self.statusBar().showMessage("Validation passed ✓")
    
    # ========== Event Handlers ==========
    
    def _refresh_dialogue_tree(self):
        """Refresh the dialogue tree."""
        self.dialogue_tree.clear()
        if not self.project:
            return
        
        for dialogue_id, dialogue in self.project.dialogues.items():
            item = QTreeWidgetItem([dialogue.title or dialogue_id])
            item.setData(0, Qt.ItemDataRole.UserRole, dialogue_id)
            if dialogue.is_modified:
                item.setText(0, f"* {item.text(0)}")
            self.dialogue_tree.addTopLevelItem(item)
    
    def _on_dialogue_selected(self, item: QTreeWidgetItem):
        """Handle dialogue selection."""
        dialogue_id = item.data(0, Qt.ItemDataRole.UserRole)
        if dialogue_id and self.project:
            self.current_dialogue = self.project.get_dialogue(dialogue_id)
            if self.current_dialogue:
                self._last_active_node_id = None  # Reset on dialogue change
                self.graph_view.load_dialogue(self.current_dialogue)
                self.inspector.set_dialogue(self.current_dialogue)
                self.character_panel.set_dialogue(self.current_dialogue)
    
    def _on_node_selected(self, node_id: str):
        """Handle node selection in graph."""
        if self.current_dialogue and node_id in self.current_dialogue.nodes:
            node = self.current_dialogue.nodes[node_id]
            self.inspector.load_node(node)
            self._last_active_node_id = node_id
    
    def _on_node_changed(self, node_id: str):
        """Handle node changes from inspector."""
        self.graph_view.refresh_node(node_id)
        if self.current_dialogue:
            self.current_dialogue.is_modified = True
            self._refresh_dialogue_tree()
    
    def _on_characters_changed(self):
        """Handle character list changes."""
        self.inspector._update_speaker_list()
        self._refresh_dialogue_tree()
    
    def _has_unsaved_changes(self) -> bool:
        """Check if there are any unsaved changes."""
        if not self.project:
            return False
        for dialogue in self.project.dialogues.values():
            if dialogue.is_modified:
                return True
        return False
    
    def closeEvent(self, event):
        """Handle window close with unsaved changes warning."""
        if self._has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_all()
                event.accept()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark theme
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(palette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    window = DialogueEditorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
