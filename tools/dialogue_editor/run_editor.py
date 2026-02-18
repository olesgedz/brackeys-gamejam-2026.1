#!/usr/bin/env python3
"""
Dialogue Editor Launcher

Usage:
    python run_editor.py [path_to_dialogues_src]

Example:
    python run_editor.py ../../dialogues_src
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dialogue_editor.main_window import main, DialogueEditorWindow, DialogueYAMLLoader
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


def run():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark theme
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    window = DialogueEditorWindow()
    
    # Auto-open directory if provided
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if os.path.isdir(path):
            window.project = DialogueYAMLLoader.load_project(path)
            window._refresh_dialogue_tree()
            window.statusBar().showMessage(f"Opened: {path}")
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
