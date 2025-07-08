"""
Enhanced Graphics Items for Existential Graphs
Implements moveable ligatures with constraint-aware behavior and flexible routing.
"""

from PySide6.QtWidgets import (QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem, 
                              QGraphicsPathItem, QGraphicsRectItem)
from PySide6.QtGui import QPen, QBrush, QPainterPath, QColor, QPainter, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject
import math

class InteractionMode:
    CONSTRAINED = "constrained"
    FREE = "free"

class ConstraintValidator:
    """Validates movement constraints for existential graphs."""
    
    @staticmethod
    def is_position_valid(item, new_position, mode, editor):
        """Check if a position is valid for the given item and mode."""
        if mode == InteractionMode.FREE:
            return True
            
        if mode == InteractionMode.CONSTRAINED:
            return ConstraintValidator._check_containment_constraints(item, new_position, editor)
        
        return True
    
    @staticmethod
    def _check_containment_constraints(item, new_position, editor):
        """Check if the new position respects containment constraints."""
        if not hasattr(item, 'node_id') or not editor:
            return True
            
        # Get the parent context for this item
        parent_context = editor.get_parent_context(item.node_id)
        if not parent_context or parent_context == 'SA':
            return True  # Root level - no constraints
            
        # Find the parent cut graphics item
        parent_cut_item = None
        scene = item.scene()
        if scene:
            for scene_item in scene.items():
                if (hasattr(scene_item, 'cut_id') and 
                    scene_item.cut_id == parent_context):
                    parent_cut_item = scene_item
                    break
        
        if not parent_cut_item:
            return True  # No parent cut found
            
        # Check if new position is within parent cut bounds (with margin)
        cut_rect = parent_cut_item.boundingRect()
        cut_scene_rect = parent_cut_item.mapRectToScene(cut_rect)
        margin = 20
        valid_rect = cut_scene_rect.adjusted(margin, margin, -margin, -margin)
        
        return valid_rect.contains(new_position)

class EnhancedHookItem(QGraphicsEllipseItem):
    """Enhanced hook item with connection state visualization."""
    
    def __init__(self, owner_id, hook_index, x, y, parent=None):
        super().__init__(-4, -4, 8, 8, parent)
        self.setPos(x, y)
        self.owner_id = owner_id
        self.hook_index = hook_index
        self.connected = False
        self.highlighted = False
        
        # Visual styling
        self.update_appearance()
        self.setZValue(3)  # Above other items
        
    def set_connected(self, connected):
        """Set the connection state."""
        self.connected = connected
        self.update_appearance()
        
    def set_highlighted(self, highlighted):
        """Set the highlight state."""
        self.highlighted = highlighted
        self.update_appearance()
        
    def update_appearance(self):
        """Update visual appearance based on state."""
        if self.highlighted:
            self.setBrush(QBrush(QColor(255, 255, 0)))  # Yellow when highlighted
            self.setPen(QPen(QColor(255, 165, 0), 2))   # Orange border
        elif self.connected:
            self.setBrush(QBrush(QColor(0, 255, 0)))    # Green when connected
            self.setPen(QPen(QColor(0, 128, 0), 1))     # Dark green border
        else:
            self.setBrush(QBrush(QColor(128, 128, 128))) # Gray when unconnected
            self.setPen(QPen(QColor(64, 64, 64), 1))    # Dark gray border

class EnhancedPredicateItem(QGraphicsItem):
    """Enhanced predicate item with constraint-aware movement."""
    
    def __init__(self, predicate_id, label, hook_count, x, y, editor=None, parent=None):
        super().__init__(parent)
        self.predicate_id = predicate_id
        self.node_id = predicate_id  # For constraint validation
        self.editor = editor
        self.mode = InteractionMode.CONSTRAINED
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(2)
        
        # Create text item
        self.text = QGraphicsTextItem(label, self)
        self.text.setFont(self.text.font())
        
        # Create hooks
        self.hooks = {}
        self.create_hooks(hook_count)
        
        # Connected ligatures
        self.connected_ligatures = set()
        
    def create_hooks(self, hook_count):
        """Create hook items for this predicate."""
        text_rect = self.text.boundingRect()
        
        for i in range(1, hook_count + 1):
            # Position hooks along the bottom edge
            hook_x = (i / (hook_count + 1)) * text_rect.width()
            hook_y = text_rect.height() + 5
            
            hook = EnhancedHookItem(self.predicate_id, i, hook_x, hook_y, self)
            self.hooks[i] = hook
    
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        
    def add_connected_ligature(self, ligature_item):
        """Add a ligature that's connected to this predicate."""
        self.connected_ligatures.add(ligature_item)
        
    def remove_connected_ligature(self, ligature_item):
        """Remove a ligature connection."""
        self.connected_ligatures.discard(ligature_item)
        
    def itemChange(self, change, value):
        """Handle item changes with constraint validation."""
        if change == QGraphicsItem.ItemPositionChange:
            # Validate the new position
            if not ConstraintValidator.is_position_valid(self, value, self.mode, self.editor):
                return self.pos()  # Reject the movement
                
        elif change == QGraphicsItem.ItemPositionHasChanged:
            # Update connected ligatures
            for ligature in self.connected_ligatures:
                ligature.update_path()
                
        return super().itemChange(change, value)
    
    def boundingRect(self):
        """Return the bounding rectangle."""
        return self.childrenBoundingRect()
    
    def paint(self, painter, option, widget):
        """Paint the predicate item."""
        # Draw selection highlight if selected
        if self.isSelected():
            rect = self.boundingRect()
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.setBrush(QBrush(QColor(0, 120, 215, 30)))
            painter.drawRect(rect)

class EnhancedCutItem(QGraphicsEllipseItem):
    """Enhanced cut item with resize handles and visual feedback."""
    
    def __init__(self, cut_id, x, y, width, height, editor=None, parent=None):
        super().__init__(x, y, width, height, parent)
        self.cut_id = cut_id
        self.node_id = cut_id  # For constraint validation
        self.editor = editor
        self.mode = InteractionMode.CONSTRAINED
        
        # Visual styling
        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setBrush(QBrush(Qt.transparent))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(0)  # Behind other items
        
        # Drop highlight state
        self.drop_highlighted = False
        
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        
    def set_drop_highlighted(self, highlighted):
        """Set drop highlight state."""
        self.drop_highlighted = highlighted
        self.update_appearance()
        
    def update_appearance(self):
        """Update visual appearance based on state."""
        if self.drop_highlighted:
            self.setPen(QPen(QColor(0, 255, 0), 3))  # Green highlight
            self.setBrush(QBrush(QColor(0, 255, 0, 30)))
        else:
            self.setPen(QPen(QColor(0, 0, 0), 2))
            self.setBrush(QBrush(Qt.transparent))
    
    def itemChange(self, change, value):
        """Handle item changes with constraint validation."""
        if change == QGraphicsItem.ItemPositionChange:
            # Validate the new position
            if not ConstraintValidator.is_position_valid(self, value, self.mode, self.editor):
                return self.pos()  # Reject the movement
                
        return super().itemChange(change, value)

class FlexibleLigatureItem(QGraphicsPathItem):
    """
    Flexible ligature item that can be moved and pulls connected predicates.
    Implements Bézier curve routing to avoid overlaps.
    """
    
    def __init__(self, ligature_id, editor=None, parent=None):
        super().__init__(parent)
        self.ligature_id = ligature_id
        self.editor = editor
        self.mode = InteractionMode.CONSTRAINED
        
        # Connected items
        self.connected_items = []  # List of (item, hook_index) tuples
        self.control_points = []   # Bézier control points
        
        # Visual styling
        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(1)  # Between cuts and predicates
        
        # Selection state
        self.selected_color = QColor(255, 0, 0)
        self.normal_color = QColor(0, 0, 0)
        self.hover_color = QColor(0, 0, 255)
        
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        
    def connect_to_item(self, item, hook_index):
        """Connect this ligature to a predicate item."""
        connection = (item, hook_index)
        if connection not in self.connected_items:
            self.connected_items.append(connection)
            if hasattr(item, 'add_connected_ligature'):
                item.add_connected_ligature(self)
        self.update_path()
        
    def disconnect_from_item(self, item, hook_index):
        """Disconnect this ligature from a predicate item."""
        connection = (item, hook_index)
        if connection in self.connected_items:
            self.connected_items.remove(connection)
            if hasattr(item, 'remove_connected_ligature'):
                item.remove_connected_ligature(self)
        self.update_path()
        
    def update_path(self):
        """Update the ligature path based on connected items."""
        if len(self.connected_items) < 2:
            self.setPath(QPainterPath())
            return
            
        # Get connection points
        points = []
        for item, hook_index in self.connected_items:
            if hasattr(item, 'hooks') and hook_index in item.hooks:
                hook = item.hooks[hook_index]
                point = hook.scenePos()
                points.append(point)
            else:
                # Fallback to item center
                point = item.scenePos()
                points.append(point)
        
        if len(points) < 2:
            self.setPath(QPainterPath())
            return
            
        # Create path with Bézier curves for flexibility
        path = QPainterPath()
        start_point = self.mapFromScene(points[0])
        path.moveTo(start_point)
        
        if len(points) == 2:
            # Simple curve between two points
            end_point = self.mapFromScene(points[1])
            
            # Calculate control points for smooth curve
            mid_x = (start_point.x() + end_point.x()) / 2
            mid_y = (start_point.y() + end_point.y()) / 2
            
            # Add some curvature
            offset = 30
            control1 = QPointF(start_point.x() + offset, mid_y)
            control2 = QPointF(end_point.x() - offset, mid_y)
            
            path.cubicTo(control1, control2, end_point)
        else:
            # Multiple points - create smooth path through all
            for i in range(1, len(points)):
                end_point = self.mapFromScene(points[i])
                path.lineTo(end_point)
        
        self.setPath(path)
        
    def mousePressEvent(self, event):
        """Handle mouse press for ligature movement."""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.original_positions = {}
            
            # Store original positions of connected items
            for item, _ in self.connected_items:
                self.original_positions[item] = item.pos()
                
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move for ligature dragging."""
        if hasattr(self, 'drag_start_pos'):
            # Calculate movement delta
            delta = event.pos() - self.drag_start_pos
            scene_delta = self.mapToScene(delta) - self.mapToScene(QPointF(0, 0))
            
            # Move connected items if in appropriate mode
            if self.mode == InteractionMode.FREE or self._can_move_connected_items(scene_delta):
                for item, _ in self.connected_items:
                    new_pos = self.original_positions[item] + scene_delta
                    
                    # Validate position if in constrained mode
                    if (self.mode == InteractionMode.FREE or 
                        ConstraintValidator.is_position_valid(item, new_pos, self.mode, self.editor)):
                        item.setPos(new_pos)
            
            # Update the ligature path
            self.update_path()
            
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if hasattr(self, 'drag_start_pos'):
            delattr(self, 'drag_start_pos')
            delattr(self, 'original_positions')
            
        super().mouseReleaseEvent(event)
        
    def _can_move_connected_items(self, delta):
        """Check if connected items can be moved by the given delta."""
        for item, _ in self.connected_items:
            new_pos = item.pos() + delta
            if not ConstraintValidator.is_position_valid(item, new_pos, self.mode, self.editor):
                return False
        return True
        
    def paint(self, painter, option, widget):
        """Paint the ligature with state-dependent colors."""
        # Set color based on state
        if self.isSelected():
            pen = QPen(self.selected_color, 3)
        elif self.isUnderMouse():
            pen = QPen(self.hover_color, 2)
        else:
            pen = QPen(self.normal_color, 2)
            
        painter.setPen(pen)
        painter.drawPath(self.path())
        
    def shape(self):
        """Return a more generous shape for easier selection."""
        # Create a thicker path for hit testing
        path = self.path()
        if path.isEmpty():
            return path
            
        # Create a polygon from the path for easier clicking
        stroker_path = QPainterPath()
        
        # Simple approach: create rectangles along the path
        length = path.length()
        if length > 0:
            steps = max(10, int(length / 10))
            for i in range(steps):
                t = i / steps
                point = path.pointAtPercent(t)
                rect = QRectF(point.x() - 5, point.y() - 5, 10, 10)
                stroker_path.addRect(rect)
                
        return stroker_path
        
    def boundingRect(self):
        """Return bounding rectangle with some padding."""
        path_rect = self.path().boundingRect()
        return path_rect.adjusted(-10, -10, 10, 10)

class LigatureManager:
    """Manages ligature creation and routing for the canvas."""
    
    def __init__(self, scene, editor):
        self.scene = scene
        self.editor = editor
        self.ligatures = {}  # Maps ligature IDs to graphics items
        
    def create_ligature(self, ligature_id, connections):
        """Create a new ligature graphics item."""
        ligature_item = FlexibleLigatureItem(ligature_id, self.editor)
        
        # Connect to predicate items
        for pred_id, hook_index in connections:
            pred_item = self._find_predicate_item(pred_id)
            if pred_item:
                ligature_item.connect_to_item(pred_item, hook_index)
                
        self.scene.addItem(ligature_item)
        self.ligatures[ligature_id] = ligature_item
        
        return ligature_item
        
    def update_ligature(self, ligature_id):
        """Update an existing ligature."""
        if ligature_id in self.ligatures:
            self.ligatures[ligature_id].update_path()
            
    def remove_ligature(self, ligature_id):
        """Remove a ligature."""
        if ligature_id in self.ligatures:
            ligature_item = self.ligatures[ligature_id]
            
            # Disconnect from all items
            for item, hook_index in ligature_item.connected_items[:]:
                ligature_item.disconnect_from_item(item, hook_index)
                
            self.scene.removeItem(ligature_item)
            del self.ligatures[ligature_id]
            
    def set_mode(self, mode):
        """Set interaction mode for all ligatures."""
        for ligature in self.ligatures.values():
            ligature.set_mode(mode)
            
    def _find_predicate_item(self, predicate_id):
        """Find a predicate graphics item by ID."""
        for item in self.scene.items():
            if (hasattr(item, 'predicate_id') and 
                item.predicate_id == predicate_id):
                return item
        return None

# Example usage and testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
    import sys
    
    app = QApplication(sys.argv)
    
    # Create test scene
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    
    # Create test items
    pred1 = EnhancedPredicateItem("pred1", "Cat", 1, 0, 0)
    pred2 = EnhancedPredicateItem("pred2", "Animal", 1, 100, 0)
    
    scene.addItem(pred1)
    scene.addItem(pred2)
    
    # Create ligature
    ligature = FlexibleLigatureItem("lig1")
    ligature.connect_to_item(pred1, 1)
    ligature.connect_to_item(pred2, 1)
    scene.addItem(ligature)
    
    view.show()
    print("Enhanced graphics items test - close window to exit")
    
    app.exec()
