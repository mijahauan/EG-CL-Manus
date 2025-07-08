"""
Line of Identity Graphics Item for Existential Graphs

This module provides graphics items for lines of identity that properly
connect to predicate hooks and are always visible as required by EG theory.
"""

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPainterPath, QFont
from PySide6.QtCore import Qt, QPointF, QRectF
import math

class LineOfIdentityItem(QGraphicsItem):
    """
    Line of identity that properly connects to predicate hooks.
    Always visible and positioned to show variable connections.
    """
    
    def __init__(self, line_id, variable_name=None, parent=None):
        super().__init__(parent)
        self.line_id = line_id
        self.variable_name = variable_name or f"var_{line_id}"
        self.connected_hooks = []  # List of (predicate_item, hook_index) tuples
        
        # Visual properties
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(2)  # Above predicates but below hooks
        
        # Line appearance
        self.pen = QPen(QColor(0, 100, 200), 2)  # Blue line, 2px thick
        self.selected_pen = QPen(QColor(255, 100, 0), 3)  # Orange when selected
        
        # Connection points
        self.start_point = QPointF(0, 0)
        self.end_point = QPointF(30, 0)  # Default length
        
    def add_hook_connection(self, predicate_item, hook_index):
        """Add a connection to a predicate hook and update visual position."""
        self.connected_hooks.append((predicate_item, hook_index))
        self.update_visual_connection()
        
    def remove_hook_connection(self, predicate_item, hook_index):
        """Remove a connection to a predicate hook."""
        self.connected_hooks = [(p, h) for p, h in self.connected_hooks 
                               if not (p == predicate_item and h == hook_index)]
        self.update_visual_connection()
        
    def update_visual_connection(self):
        """Update the visual appearance based on connected hooks."""
        if len(self.connected_hooks) == 0:
            # No connections - default appearance
            self.start_point = QPointF(0, 0)
            self.end_point = QPointF(30, 0)
            
        elif len(self.connected_hooks) == 1:
            # Single connection - line extends from hook
            pred_item, hook_index = self.connected_hooks[0]
            hook_pos = pred_item.get_hook_scene_position(hook_index)
            
            # Position line at hook location
            self.setPos(hook_pos)
            
            # Extend line outward from predicate center
            pred_center = pred_item.sceneBoundingRect().center()
            direction = QPointF(hook_pos.x() - pred_center.x(), 
                              hook_pos.y() - pred_center.y())
            
            # Normalize and extend
            length = math.sqrt(direction.x()**2 + direction.y()**2)
            if length > 0:
                direction = QPointF(direction.x() / length * 25, 
                                  direction.y() / length * 25)
            else:
                direction = QPointF(25, 0)  # Default direction
                
            self.start_point = QPointF(0, 0)
            self.end_point = direction
            
        elif len(self.connected_hooks) >= 2:
            # Multiple connections - line spans between hooks
            pred1, hook1 = self.connected_hooks[0]
            pred2, hook2 = self.connected_hooks[1]
            
            # Get hook positions in scene coordinates
            hook1_pos = pred1.get_hook_scene_position(hook1)
            hook2_pos = pred2.get_hook_scene_position(hook2)
            
            # Position line at first hook
            self.setPos(hook1_pos)
            
            # Set end point relative to start
            self.start_point = QPointF(0, 0)
            self.end_point = QPointF(hook2_pos.x() - hook1_pos.x(), 
                                   hook2_pos.y() - hook1_pos.y())
        
        self.update()
        
    def boundingRect(self):
        """Return the bounding rectangle."""
        # Calculate bounds based on line endpoints
        min_x = min(self.start_point.x(), self.end_point.x()) - 10
        max_x = max(self.start_point.x(), self.end_point.x()) + 10
        min_y = min(self.start_point.y(), self.end_point.y()) - 10
        max_y = max(self.start_point.y(), self.end_point.y()) + 10
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        
    def paint(self, painter, option, widget):
        """Paint the line of identity."""
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Choose pen based on selection
        pen = self.selected_pen if self.isSelected() else self.pen
        painter.setPen(pen)
        
        # Draw the main line
        painter.drawLine(self.start_point, self.end_point)
        
        # Draw connection indicators at endpoints
        painter.setBrush(QBrush(pen.color()))
        painter.drawEllipse(self.start_point, 3, 3)
        if len(self.connected_hooks) >= 2:
            painter.drawEllipse(self.end_point, 3, 3)
        
        # Draw variable label at midpoint
        midpoint = QPointF((self.start_point.x() + self.end_point.x()) / 2, 
                          (self.start_point.y() + self.end_point.y()) / 2)
        
        # Set font for label
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 0, 0)))  # Black text
        
        # Draw label slightly offset from line
        label_pos = midpoint + QPointF(5, -8)
        painter.drawText(label_pos, self.variable_name)


class StandaloneLineOfIdentityItem(LineOfIdentityItem):
    """
    Standalone line of identity for simple predicates like (Cat x).
    Always visible and positioned near the predicate.
    """
    
    def __init__(self, line_id, variable_name, predicate_item=None, hook_index=0, parent=None):
        super().__init__(line_id, variable_name, parent)
        
        self.predicate_item = predicate_item
        self.hook_index = hook_index
        
        # Position near the predicate if provided
        if predicate_item:
            self.add_hook_connection(predicate_item, hook_index)
            
    def update_position_from_predicate(self):
        """Update position based on connected predicate."""
        if self.predicate_item:
            hook_pos = self.predicate_item.get_hook_scene_position(self.hook_index)
            self.setPos(hook_pos)
            
            # Extend line outward from predicate
            pred_center = self.predicate_item.sceneBoundingRect().center()
            direction = QPointF(hook_pos.x() - pred_center.x(), 
                              hook_pos.y() - pred_center.y())
            
            # Normalize and extend
            length = math.sqrt(direction.x()**2 + direction.y()**2)
            if length > 0:
                direction = QPointF(direction.x() / length * 20, 
                                  direction.y() / length * 20)
            else:
                direction = QPointF(20, 0)  # Default direction
                
            self.start_point = QPointF(0, 0)
            self.end_point = direction
            self.update()


# Example usage and testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
    import sys
    
    app = QApplication(sys.argv)
    
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    
    # Test line of identity
    line = LineOfIdentityItem("test_line", "x")
    line.setPos(50, 50)
    scene.addItem(line)
    
    # Test standalone line
    standalone = StandaloneLineOfIdentityItem("test_standalone", "y")
    standalone.setPos(100, 100)
    scene.addItem(standalone)
    
    view.show()
    view.setWindowTitle("Line of Identity Test")
    
    print("Line of Identity test - close window to exit")
    app.exec()
