"""
Main window for the Dialogue Editor.
PySide6-based visual editor for YAML dialogues.
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
    QPainter, QWheelEvent, QMouseEvent
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
    
    NODE_WIDTH = 200
    NODE_HEIGHT = 80
    
    COLORS = {
        NodeType.SAY: QColor("#4a9eff"),
        NodeType.CHOICE: QColor("#ff9f4a"),
        NodeType.SET: QColor("#9f4aff"),
        NodeType.IF: QColor("#ffff4a"),
        NodeType.JUMP: QColor("#4aff9f"),
        NodeType.END: QColor("#ff4a4a"),
        NodeType.SIGNAL: QColor("#ff4aff"),
    }
    
    def __init__(self, node: DialogueNode, parent=None):
        super().__init__(0, 0, self.NODE_WIDTH, self.NODE_HEIGHT, parent)
        self.node = node
        self.setPos(node.ui_pos.x, node.ui_pos.y)
        
        # Make movable
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Styling
        color = self.COLORS.get(node.type, QColor("#888888"))
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        
        # Title text
        self.title_text = QGraphicsTextItem(self)
        self.title_text.setPos(5, 5)
        self.title_text.setDefaultTextColor(Qt.GlobalColor.white)
        font = QFont()
        font.setBold(True)
        self.title_text.setFont(font)
        
        # Content text
        self.content_text = QGraphicsTextItem(self)
        self.content_text.setPos(5, 25)
        self.content_text.setDefaultTextColor(Qt.GlobalColor.white)
        self.content_text.setTextWidth(self.NODE_WIDTH - 10)
        
        self.update_display()
    
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
            text = node.text[:50] + "..." if len(node.text) > 50 else node.text
            content = f"{speaker}: {text}"
        elif node.type == NodeType.CHOICE:
            content = f"{len(node.choices)} choices"
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
        
        self.content_text.setPlainText(content)
        
        # Update color
        color = self.COLORS.get(node.type, QColor("#888888"))
        self.setBrush(QBrush(color))
    
    def itemChange(self, change, value):
        """Handle position changes."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            self.node.ui_pos.x = pos.x()
            self.node.ui_pos.y = pos.y()
        return super().itemChange(change, value)
    
    def get_output_point(self) -> QPointF:
        """Get the connection output point."""
        return self.scenePos() + QPointF(self.NODE_WIDTH, self.NODE_HEIGHT / 2)
    
    def get_input_point(self) -> QPointF:
        """Get the connection input point."""
        return self.scenePos() + QPointF(0, self.NODE_HEIGHT / 2)


class ConnectionLine(QGraphicsLineItem):
    """Visual connection between nodes."""
    
    def __init__(self, start_item: NodeGraphicsItem, end_item: NodeGraphicsItem):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(Qt.GlobalColor.white, 2))
        self.update_position()
    
    def update_position(self):
        """Update line position based on node positions."""
        start = self.start_item.get_output_point()
        end = self.end_item.get_input_point()
        self.setLine(start.x(), start.y(), end.x(), end.y())


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
        
        # Scene background
        self.scene.setBackgroundBrush(QBrush(QColor("#2b2b2b")))
        
        # Items tracking
        self.node_items: dict[str, NodeGraphicsItem] = {}
        self.connection_lines: list[ConnectionLine] = []
        
        # Current dialogue
        self.dialogue: Optional[Dialogue] = None
    
    def wheelEvent(self, event: QWheelEvent):
        """Zoom with mouse wheel."""
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle selection."""
        super().mousePressEvent(event)
        
        item = self.itemAt(event.pos())
        if isinstance(item, NodeGraphicsItem):
            self.node_selected.emit(item.node.id)
        elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), NodeGraphicsItem):
            self.node_selected.emit(item.parentItem().node.id)
    
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
        
        # Clear old connections
        for line in self.connection_lines:
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
            
            # Choice connections
            for choice in node.choices:
                if choice.next and choice.next in self.node_items:
                    end_item = self.node_items[choice.next]
                    line = ConnectionLine(start_item, end_item)
                    line.setPen(QPen(QColor("#ff9f4a"), 2))  # Orange for choices
                    self.scene.addItem(line)
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
        self.scene.addItem(item)
        self.node_items[node.id] = item
    
    def remove_node(self, node_id: str):
        """Remove a node from the view."""
        if node_id in self.node_items:
            item = self.node_items[node_id]
            self.scene.removeItem(item)
            del self.node_items[node_id]
            self._create_connections()


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
        say_layout.addRow("Speaker:", self.speaker_combo)
        
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)
        self.text_edit.textChanged.connect(self._on_field_changed)
        say_layout.addRow("Text:", self.text_edit)
        
        layout.addWidget(self.say_group)
        
        # CHOICE fields
        self.choice_group = QGroupBox("Choices")
        choice_layout = QVBoxLayout(self.choice_group)
        
        self.choices_list = QListWidget()
        choice_layout.addWidget(self.choices_list)
        
        choice_buttons = QHBoxLayout()
        add_choice_btn = QPushButton("Add")
        add_choice_btn.clicked.connect(self._add_choice)
        remove_choice_btn = QPushButton("Remove")
        remove_choice_btn.clicked.connect(self._remove_choice)
        choice_buttons.addWidget(add_choice_btn)
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
        self.choices_list.clear()
        for choice in node.choices:
            self.choices_list.addItem(f"{choice.text} → {choice.next}")
        
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
                self.next_combo.addItem(node_id)
    
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
    
    def _add_choice(self):
        """Add a new choice."""
        if not self.current_node:
            return
        
        text, ok = QInputDialog.getText(self, "Add Choice", "Choice text:")
        if ok and text:
            choice = ChoiceOption(text=text)
            self.current_node.choices.append(choice)
            self.choices_list.addItem(f"{choice.text} → {choice.next}")
            self.node_changed.emit(self.current_node.id)
    
    def _remove_choice(self):
        """Remove selected choice."""
        if not self.current_node:
            return
        
        row = self.choices_list.currentRow()
        if row >= 0:
            del self.current_node.choices[row]
            self.choices_list.takeItem(row)
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
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)
        
        # Left panel: Dialogue browser
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
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
        
        open_action = QAction("Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
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
        
        add_say_action = QAction("Add SAY Node", self)
        add_say_action.setShortcut("N")
        add_say_action.triggered.connect(lambda: self._add_node(NodeType.SAY))
        edit_menu.addAction(add_say_action)
        
        add_choice_action = QAction("Add CHOICE Node", self)
        add_choice_action.setShortcut("C")
        add_choice_action.triggered.connect(lambda: self._add_node(NodeType.CHOICE))
        edit_menu.addAction(add_choice_action)
        
        delete_node_action = QAction("Delete Node", self)
        delete_node_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_node_action.triggered.connect(self._delete_selected_node)
        edit_menu.addAction(delete_node_action)
        
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
        
        toolbar.addAction("Open", self._open_project)
        toolbar.addAction("Save", self._save_current)
        toolbar.addSeparator()
        toolbar.addAction("+ SAY", lambda: self._add_node(NodeType.SAY))
        toolbar.addAction("+ CHOICE", lambda: self._add_node(NodeType.CHOICE))
        toolbar.addAction("+ END", lambda: self._add_node(NodeType.END))
        toolbar.addSeparator()
        toolbar.addAction("Validate", self._validate_current)
    
    def _setup_statusbar(self):
        """Setup status bar."""
        self.statusBar().showMessage("Ready")
    
    # ========== Actions ==========
    
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
                    saved += 1
                except Exception as e:
                    print(f"Error saving {dialogue.id}: {e}")
        
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
        """Add a new node to current dialogue."""
        if not self.current_dialogue:
            return
        
        node = DialogueNode(type=node_type)
        node.ui_pos.x = len(self.current_dialogue.nodes) * 250
        node.ui_pos.y = 0
        
        self.current_dialogue.add_node(node)
        self.graph_view.add_node(node, node.ui_pos.x, node.ui_pos.y)
        self.inspector._update_node_list()
        
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
                self.graph_view.load_dialogue(self.current_dialogue)
                self.inspector.set_dialogue(self.current_dialogue)
    
    def _on_node_selected(self, node_id: str):
        """Handle node selection in graph."""
        if self.current_dialogue and node_id in self.current_dialogue.nodes:
            node = self.current_dialogue.nodes[node_id]
            self.inspector.load_node(node)
    
    def _on_node_changed(self, node_id: str):
        """Handle node changes from inspector."""
        self.graph_view.refresh_node(node_id)
        if self.current_dialogue:
            self.current_dialogue.is_modified = True
            self._refresh_dialogue_tree()


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
