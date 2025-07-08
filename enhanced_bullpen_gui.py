#!/usr/bin/env python3
"""
Enhanced Bullpen GUI for Existential Graphs
Complete integration with CLIF parser, EG renderer, and moveable ligatures.
Implements the bullpen concept for graph composition and visual adjustment.
"""

import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                              QWidget, QGraphicsView, QGraphicsScene, QToolBar, 
                              QStatusBar, QLabel, QTextEdit, QPushButton, QSplitter,
                              QGroupBox, QLineEdit, QMessageBox, QComboBox, QCheckBox,
                              QSlider, QSpinBox, QTabWidget, QTextBrowser)
from PySide6.QtCore import Qt, QPointF, Signal, QRectF, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence, QPainter, QPen, QBrush, QColor

from eg_editor import EGEditor
from clif_parser import ClifParser, ClifParserError
from eg_renderer import EGRenderer
from enhanced_graphics_items import InteractionMode
from eg_model import GraphModel, Cut, Predicate, LineOfIdentity, Ligature

class BullpenCanvas(QGraphicsView):
    """Enhanced canvas for the bullpen with full interaction capabilities."""
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # Set scene size
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Initialize components
        self.editor = None
        self.renderer = None
        self.mode = InteractionMode.CONSTRAINED
        
        # Visual styling
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
            }
        """)
        
        # Grid settings
        self.show_grid = True
        self.grid_size = 50
        
    def set_editor(self, editor):
        """Set the EG editor and initialize renderer."""
        self.editor = editor
        self.renderer = EGRenderer(self.scene, editor)
        
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        if self.renderer:
            self.renderer.set_mode(mode)
        self.update_status()
        
    def update_status(self):
        """Update visual status indicators."""
        # Could add visual mode indicators to the canvas
        pass
        
    def clear_canvas(self):
        """Clear all items from the canvas."""
        if self.renderer:
            self.renderer.clear()
    
    def render_clif_result(self, parse_result):
        """Render a parsed CLIF expression."""
        if self.renderer:
            success = self.renderer.render_from_parse_result(parse_result)
            if success:
                self.fit_content()
            return success
        return False
        
    def render_model(self, graph_model):
        """Render from a graph model."""
        if self.renderer:
            success = self.renderer.render_from_model(graph_model)
            if success:
                self.fit_content()
            return success
        return False
        
    def fit_content(self):
        """Fit the view to show all content."""
        if self.scene.items():
            self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
    def set_grid_visible(self, visible):
        """Set grid visibility."""
        self.show_grid = visible
        self.scene.update()
        
    def drawBackground(self, painter, rect):
        """Draw background with optional grid."""
        super().drawBackground(painter, rect)
        
        if self.show_grid:
            # Draw grid
            painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DotLine))
            
            # Calculate grid lines
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            
            # Draw vertical lines
            x = left
            while x < rect.right():
                painter.drawLine(x, rect.top(), x, rect.bottom())
                x += self.grid_size
                
            # Draw horizontal lines
            y = top
            while y < rect.bottom():
                painter.drawLine(rect.left(), y, rect.right(), y)
                y += self.grid_size

class ClifInputPanel(QWidget):
    """Enhanced panel for CLIF expression input and parsing."""
    
    parse_requested = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("CLIF Expression Input")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Input area with syntax highlighting (basic)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            "Enter CLIF expression here...\n\n"
            "Examples:\n"
            "• (Cat x)\n"
            "• (On cat mat)\n"
            "• (exists (x y) (and (Cat x) (Mat y) (On x y)))\n"
            "• (not (Cat x))"
        )
        self.input_text.setMaximumHeight(150)
        self.input_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.input_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.parse_button = QPushButton("Parse & Display")
        self.parse_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.parse_button.clicked.connect(self.on_parse_clicked)
        button_layout.addWidget(self.parse_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.on_clear_clicked)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # Examples dropdown
        examples_layout = QHBoxLayout()
        examples_layout.addWidget(QLabel("Examples:"))
        
        self.examples_combo = QComboBox()
        self.examples_combo.addItems([
            "Select an example...",
            "(Cat x)",
            "(On cat mat)", 
            "(exists (x y) (and (Cat x) (Mat y) (On x y)))",
            "(not (Cat x))",
            "(and (Cat x) (Dog y))",
            "(exists (x) (and (Cat x) (not (Dog x))))",
            "(= x y)"
        ])
        self.examples_combo.currentTextChanged.connect(self.on_example_selected)
        examples_layout.addWidget(self.examples_combo)
        
        layout.addLayout(examples_layout)
        
        # Validation feedback
        self.feedback_label = QLabel("")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.feedback_label)
    
    def on_parse_clicked(self):
        """Handle parse button click."""
        clif_text = self.input_text.toPlainText().strip()
        if clif_text:
            self.parse_requested.emit(clif_text)
        else:
            self.feedback_label.setText("Please enter a CLIF expression.")
    
    def on_clear_clicked(self):
        """Handle clear button click."""
        self.input_text.clear()
        self.feedback_label.clear()
    
    def on_example_selected(self, text):
        """Handle example selection."""
        if text and text != "Select an example...":
            self.input_text.setPlainText(text)
            self.feedback_label.clear()
            
    def set_feedback(self, message, is_error=False):
        """Set feedback message."""
        color = "#dc3545" if is_error else "#28a745"
        self.feedback_label.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.feedback_label.setText(message)

class ControlPanel(QWidget):
    """Control panel for interaction modes and visual settings."""
    
    mode_changed = Signal(str)
    grid_toggled = Signal(bool)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Interaction Mode
        mode_group = QGroupBox("Interaction Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Constrained", "Free"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        mode_description = QLabel(
            "Constrained: Preserves logical structure\n"
            "Free: Allows unrestricted positioning"
        )
        mode_description.setStyleSheet("color: #666; font-size: 10px;")
        mode_layout.addWidget(mode_description)
        
        layout.addWidget(mode_group)
        
        # Visual Settings
        visual_group = QGroupBox("Visual Settings")
        visual_layout = QVBoxLayout(visual_group)
        
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.grid_toggled.emit)
        visual_layout.addWidget(self.grid_checkbox)
        
        layout.addWidget(visual_group)
        
        # Ligature Settings
        ligature_group = QGroupBox("Ligature Behavior")
        ligature_layout = QVBoxLayout(ligature_group)
        
        ligature_info = QLabel(
            "• Drag ligatures to move connected predicates\n"
            "• Ligatures automatically route around obstacles\n"
            "• Constraints apply based on interaction mode"
        )
        ligature_info.setStyleSheet("color: #666; font-size: 10px;")
        ligature_layout.addWidget(ligature_info)
        
        layout.addWidget(ligature_group)
        
        layout.addStretch()
        
    def on_mode_changed(self, mode_text):
        """Handle mode change."""
        mode = InteractionMode.CONSTRAINED if mode_text == "Constrained" else InteractionMode.FREE
        self.mode_changed.emit(mode)

class InfoPanel(QWidget):
    """Information panel showing graph details and CLIF translation."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for different info types
        self.tabs = QTabWidget()
        
        # Graph Info Tab
        self.graph_info = QTextBrowser()
        self.graph_info.setMaximumHeight(150)
        self.tabs.addTab(self.graph_info, "Graph Info")
        
        # CLIF Translation Tab
        self.clif_translation = QTextBrowser()
        self.clif_translation.setMaximumHeight(150)
        self.clif_translation.setFont(QFont("Courier", 10))
        self.tabs.addTab(self.clif_translation, "CLIF Translation")
        
        # Parse Details Tab
        self.parse_details = QTextBrowser()
        self.parse_details.setMaximumHeight(150)
        self.parse_details.setFont(QFont("Courier", 9))
        self.tabs.addTab(self.parse_details, "Parse Details")
        
        layout.addWidget(self.tabs)
        
    def update_graph_info(self, editor):
        """Update graph information display."""
        if not editor:
            self.graph_info.clear()
            return
            
        info = []
        model = editor.model
        
        # Count objects
        predicates = sum(1 for obj in model.objects.values() if isinstance(obj, Predicate))
        cuts = sum(1 for obj in model.objects.values() if isinstance(obj, Cut))
        ligatures = sum(1 for obj in model.objects.values() if isinstance(obj, Ligature))
        lines = sum(1 for obj in model.objects.values() if isinstance(obj, LineOfIdentity))
        
        info.append(f"<h4>Graph Statistics</h4>")
        info.append(f"<b>Predicates:</b> {predicates}<br>")
        info.append(f"<b>Cuts:</b> {cuts}<br>")
        info.append(f"<b>Ligatures:</b> {ligatures}<br>")
        info.append(f"<b>Lines of Identity:</b> {lines}<br>")
        
        self.graph_info.setHtml("".join(info))
        
    def update_clif_translation(self, clif_text):
        """Update CLIF translation display."""
        self.clif_translation.setPlainText(clif_text or "No CLIF expression")
        
    def update_parse_details(self, parse_result):
        """Update parse details display."""
        if not parse_result:
            self.parse_details.clear()
            return
            
        details = []
        if parse_result.get('success', False):
            details.append("Parse Status: SUCCESS\n\n")
            details.append(f"Result Type: {parse_result['result'].get('type', 'unknown')}\n")
            
            if 'variable_map' in parse_result:
                details.append("\nVariable Mappings:\n")
                for var, line_id in parse_result['variable_map'].items():
                    details.append(f"  {var} -> {line_id[:8]}...\n")
        else:
            details.append("Parse Status: FAILED\n\n")
            details.append(f"Error: {parse_result.get('error', 'Unknown error')}\n")
            
        self.parse_details.setPlainText("".join(details))

class EnhancedBullpenMainWindow(QMainWindow):
    """Enhanced main window for the Bullpen EG editor."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Existential Graphs Bullpen - Enhanced Edition")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize backend
        self.editor = EGEditor()
        self.parser = ClifParser(self.editor)
        self.current_clif = ""
        self.parse_result = None
        
        # Setup UI
        self.setup_ui()
        self.setup_toolbar()
        self.setup_status_bar()
        self.setup_connections()
        
        # Auto-update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_info_displays)
        self.update_timer.start(1000)  # Update every second
        
    def setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        # CLIF input
        self.clif_panel = ClifInputPanel()
        left_layout.addWidget(self.clif_panel)
        
        # Control panel
        self.control_panel = ControlPanel()
        left_layout.addWidget(self.control_panel)
        
        # Info panel
        self.info_panel = InfoPanel()
        left_layout.addWidget(self.info_panel)
        
        # Right panel - Canvas
        right_panel = QGroupBox("Bullpen Canvas")
        right_layout = QVBoxLayout(right_panel)
        
        self.canvas = BullpenCanvas()
        self.canvas.set_editor(self.editor)
        right_layout.addWidget(self.canvas)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)  # Canvas takes more space
        
    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = self.addToolBar("Main")
        
        # File actions
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.on_new)
        toolbar.addAction(new_action)
        
        toolbar.addSeparator()
        
        # View actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.on_zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.on_zoom_out)
        toolbar.addAction(zoom_out_action)
        
        fit_action = QAction("Fit to View", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.on_fit_to_view)
        toolbar.addAction(fit_action)
        
        toolbar.addSeparator()
        
        # Mode actions
        constrained_action = QAction("Constrained Mode", self)
        constrained_action.setShortcut("Ctrl+1")
        constrained_action.triggered.connect(lambda: self.set_mode(InteractionMode.CONSTRAINED))
        toolbar.addAction(constrained_action)
        
        free_action = QAction("Free Mode", self)
        free_action.setShortcut("Ctrl+2")
        free_action.triggered.connect(lambda: self.set_mode(InteractionMode.FREE))
        toolbar.addAction(free_action)
    
    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready - Enter a CLIF expression to begin")
        
        # Add permanent widgets
        self.mode_label = QLabel("Mode: Constrained")
        self.status_bar.addPermanentWidget(self.mode_label)
        
        self.objects_label = QLabel("Objects: 0")
        self.status_bar.addPermanentWidget(self.objects_label)
        
    def setup_connections(self):
        """Setup signal connections."""
        self.clif_panel.parse_requested.connect(self.on_parse_clif)
        self.control_panel.mode_changed.connect(self.set_mode)
        self.control_panel.grid_toggled.connect(self.canvas.set_grid_visible)
        
    def on_parse_clif(self, clif_text):
        """Handle CLIF parsing request."""
        try:
            self.status_bar.showMessage("Parsing CLIF expression...")
            
            # Create new editor for fresh parsing
            self.editor = EGEditor()
            self.parser = ClifParser(self.editor)
            self.canvas.set_editor(self.editor)
            self.current_clif = clif_text
            
            # Parse the expression
            result = self.parser.parse(clif_text)
            self.parse_result = result
            
            if result['success']:
                # Render on canvas
                success = self.canvas.render_clif_result(result)
                if success:
                    self.clif_panel.set_feedback(f"Successfully parsed and rendered: {clif_text[:30]}...")
                    self.status_bar.showMessage("Parse and render successful")
                else:
                    self.clif_panel.set_feedback("Parsed successfully but render failed", True)
                    self.status_bar.showMessage("Render failed")
            else:
                error_msg = result.get('error', 'Unknown error')
                self.clif_panel.set_feedback(f"Parse error: {error_msg}", True)
                QMessageBox.warning(self, "Parse Error", f"Failed to parse CLIF expression:\n{error_msg}")
                self.status_bar.showMessage("Parse failed")
                
        except Exception as e:
            self.clif_panel.set_feedback(f"Unexpected error: {str(e)}", True)
            QMessageBox.critical(self, "Error", f"Unexpected error:\n{str(e)}")
            self.status_bar.showMessage("Error occurred")
            
        # Update info displays
        self.update_info_displays()
    
    def set_mode(self, mode):
        """Set interaction mode."""
        self.canvas.set_mode(mode)
        mode_text = "Constrained" if mode == InteractionMode.CONSTRAINED else "Free"
        self.mode_label.setText(f"Mode: {mode_text}")
        self.control_panel.mode_combo.setCurrentText(mode_text)
        self.status_bar.showMessage(f"Switched to {mode_text} mode")
    
    def update_info_displays(self):
        """Update information displays."""
        self.info_panel.update_graph_info(self.editor)
        self.info_panel.update_clif_translation(self.current_clif)
        self.info_panel.update_parse_details(self.parse_result)
        
        # Update object count
        if self.editor:
            count = len(self.editor.model.objects) - 1  # Exclude sheet of assertion
            self.objects_label.setText(f"Objects: {count}")
    
    def on_new(self):
        """Handle new document."""
        self.canvas.clear_canvas()
        self.clif_panel.input_text.clear()
        self.clif_panel.feedback_label.clear()
        self.editor = EGEditor()
        self.parser = ClifParser(self.editor)
        self.canvas.set_editor(self.editor)
        self.current_clif = ""
        self.parse_result = None
        self.update_info_displays()
        self.status_bar.showMessage("New document created")
    
    def on_zoom_in(self):
        """Handle zoom in."""
        self.canvas.scale(1.2, 1.2)
    
    def on_zoom_out(self):
        """Handle zoom out."""
        self.canvas.scale(0.8, 0.8)
    
    def on_fit_to_view(self):
        """Handle fit to view."""
        self.canvas.fit_content()

def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Existential Graphs Bullpen")
    app.setApplicationVersion("2.0")
    app.setApplicationDisplayName("EG Bullpen - Enhanced Edition")
    
    # Set application style
    app.setStyleSheet("""
        QMainWindow {
            background-color: #ffffff;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px 12px;
            background-color: #f8f9fa;
        }
        QPushButton:hover {
            background-color: #e9ecef;
        }
        QPushButton:pressed {
            background-color: #dee2e6;
        }
    """)
    
    # Create and show main window
    window = EnhancedBullpenMainWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
