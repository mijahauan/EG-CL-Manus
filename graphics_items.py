"""
Graphics Items for Existential Graphs
Addresses all remaining issues with hook positioning and containment validation.
"""

from PySide6.QtWidgets import (QGraphicsItem, QGraphicsEllipseItem, QGraphicsTextItem, 
                              QGraphicsPathItem, QGraphicsRectItem)
from PySide6.QtGui import QPen, QBrush, QPainterPath, QColor, QPainter, QPolygonF
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject
from line_of_identity_item import LineOfIdentityItem, StandaloneLineOfIdentityItem
import math

class InteractionMode:
    CONSTRAINED = "constrained"
    FREE = "free"

class ConstraintValidator:
    """Enhanced validator that prevents all invalid movements."""
    
    @staticmethod
    def is_position_valid(item, new_position, mode, editor):
        """Check if a position is valid with comprehensive validation."""
        if mode == InteractionMode.FREE:
            return True
            
        if mode == InteractionMode.CONSTRAINED:
            return ConstraintValidator._check_complete_containment_and_context(item, new_position, editor)
        
        return True
    
    @staticmethod
    def _check_complete_containment_and_context(item, new_position, editor):
        """Check complete containment including all connected elements."""
        # Get current context
        current_context = editor.get_parent_context(item.node_id)
        if not current_context or current_context == 'SA':
            return True  # Root level - no constraints
        
        # Find the parent cut graphics item
        parent_cut_item = ConstraintValidator._find_cut_item(item.scene(), current_context)
        if not parent_cut_item:
            return True  # No parent cut found
        
        # Calculate complete bounding area at new position WITHOUT triggering itemChange
        old_pos = item.pos()
        
        # Temporarily disable validation to avoid recursion
        item._validation_disabled = True
        item.setPos(new_position)  # Temporarily move
        
        # Calculate bounds including hooks and connected elements
        complete_bounds = item.sceneBoundingRect()
        
        # Include hook positions if this is a predicate
        if hasattr(item, 'hooks'):
            for hook in item.hooks.values():
                hook_scene_rect = hook.sceneBoundingRect()
                complete_bounds = complete_bounds.united(hook_scene_rect)
        
        # Include connected ligatures
        if hasattr(item, 'connected_ligatures'):
            for ligature in item.connected_ligatures:
                lig_rect = ligature.sceneBoundingRect()
                complete_bounds = complete_bounds.united(lig_rect)
        
        # Restore original position
        item.setPos(old_pos)
        item._validation_disabled = False
        
        # Check if completely contained within parent cut
        parent_rect = parent_cut_item.sceneBoundingRect()
        margin = 5  # Small margin for visual clarity
        valid_rect = parent_rect.adjusted(margin, margin, -margin, -margin)
        
        # Must be completely contained
        is_contained = valid_rect.contains(complete_bounds)
        
        # Additional check: prevent moving into more nested contexts
        if is_contained:
            target_context = ConstraintValidator._find_deepest_cut_at_position(
                item.scene(), new_position, current_context
            )
            if target_context and target_context != current_context:
                # Check if target is more nested than current
                if ConstraintValidator._is_more_nested(target_context, current_context, editor):
                    return False  # Cannot move to more nested context
        
        return is_contained
    
    @staticmethod
    def _find_cut_item(scene, cut_id):
        """Find a cut graphics item by ID."""
        if not scene:
            return None
        for item in scene.items():
            if hasattr(item, 'cut_id') and item.cut_id == cut_id:
                return item
        return None
    
    @staticmethod
    def _find_deepest_cut_at_position(scene, position, exclude_cut=None):
        """Find the deepest cut that contains the given position."""
        if not scene:
            return None
            
        deepest_cut = None
        deepest_level = -1
        
        for item in scene.items():
            if (hasattr(item, 'cut_id') and 
                item.cut_id != exclude_cut and
                item.sceneBoundingRect().contains(position)):
                
                # Estimate nesting level (simple heuristic)
                level = ConstraintValidator._estimate_cut_level(item)
                if level > deepest_level:
                    deepest_level = level
                    deepest_cut = item.cut_id
        
        return deepest_cut
    
    @staticmethod
    def _estimate_cut_level(cut_item):
        """Estimate the nesting level of a cut."""
        # Simple heuristic: smaller cuts are likely more nested
        rect = cut_item.sceneBoundingRect()
        return 1000 - (rect.width() * rect.height())  # Smaller = higher level
    
    @staticmethod
    def _is_more_nested(context1, context2, editor):
        """Check if context1 is more nested than context2."""
        current = context1
        while current and current != 'SA':
            if current == context2:
                return True  # context1 is nested within context2
            current = editor.get_parent_context(current)
        return False

class HookItem(QGraphicsEllipseItem):
    """Hook item - very small and properly positioned."""
    
    def __init__(self, owner_id, hook_index, parent=None):
        # Very small hook size - 3x3 pixels
        super().__init__(-1.5, -1.5, 3, 3, parent)
        self.owner_id = owner_id
        self.hook_index = hook_index
        self.connected = False
        self.highlighted = False
        
        # Visual styling - subtle but visible
        self.update_appearance()
        self.setZValue(5)  # Above everything else
        
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
            self.setPen(QPen(QColor(255, 165, 0), 1))   # Orange border
        elif self.connected:
            self.setBrush(QBrush(QColor(100, 200, 100))) # Light green when connected
            self.setPen(QPen(QColor(0, 128, 0), 1))     # Dark green border
        else:
            self.setBrush(QBrush(QColor(150, 150, 150))) # Light gray when unconnected
            self.setPen(QPen(QColor(100, 100, 100), 1))  # Gray border

class PredicateItem(QGraphicsItem):
    """Predicate item with perfect hook positioning and validation."""
    
    def __init__(self, predicate_id, label, hook_count, x, y, editor=None, parent=None):
        super().__init__(parent)
        self.predicate_id = predicate_id
        self.node_id = predicate_id
        self.editor = editor
        self.mode = InteractionMode.CONSTRAINED
        
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(2)
        
        # Create text item
        self.text = QGraphicsTextItem(label, self)
        font = self.text.font()
        font.setPointSize(12)
        font.setBold(True)
        self.text.setFont(font)
        
        # Calculate text bounds for hook positioning
        self.text_rect = self.text.boundingRect()
        
        # Hook positioning on invisible circle
        self.hook_radius = max(self.text_rect.width(), self.text_rect.height()) / 2 + 12
        self.hooks = {}
        self.create_hooks_on_circle(hook_count)
        
        # Connected elements
        self.connected_ligatures = set()
        self.connected_lines = set()
        
    def create_hooks_on_circle(self, hook_count):
        """Create hooks positioned on an invisible circle around the predicate."""
        if hook_count == 0:
            return
            
        center_x = self.text_rect.center().x()
        center_y = self.text_rect.center().y()
        
        for i in range(hook_count):
            # Calculate angle for this hook
            if hook_count == 1:
                angle = 0  # Single hook to the right
            elif hook_count == 2:
                # Two hooks: left and right
                angle = math.pi if i == 0 else 0
            else:
                # Multiple hooks: evenly distributed
                angle = (2 * math.pi * i) / hook_count
            
            # Calculate position on circle
            hook_x = center_x + self.hook_radius * math.cos(angle)
            hook_y = center_y + self.hook_radius * math.sin(angle)
            
            hook = HookItem(self.predicate_id, i + 1, self)
            hook.setPos(hook_x, hook_y)
            self.hooks[i + 1] = hook
    
    def get_hook_scene_position(self, hook_index):
        """Get the scene position of a specific hook."""
        if hook_index in self.hooks:
            hook = self.hooks[hook_index]
            return hook.scenePos()
        return self.scenePos()
    
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        
    def add_connected_ligature(self, ligature_item):
        """Add a ligature connection."""
        self.connected_ligatures.add(ligature_item)
        
    def remove_connected_ligature(self, ligature_item):
        """Remove a ligature connection."""
        self.connected_ligatures.discard(ligature_item)
    
    def add_connected_line(self, line_item):
        """Add a line of identity connection."""
        self.connected_lines.add(line_item)
        
    def remove_connected_line(self, line_item):
        """Remove a line of identity connection."""
        self.connected_lines.discard(line_item)
        
    def itemChange(self, change, value):
        """Handle item changes with constraint validation."""
        if change == QGraphicsItem.ItemPositionChange:
            # Skip validation if disabled (to prevent recursion)
            if hasattr(self, '_validation_disabled') and self._validation_disabled:
                return value
                
            # Constraint validation including all connected elements
            if not ConstraintValidator.is_position_valid(self, value, self.mode, self.editor):
                return self.pos()  # Reject the movement
                
        elif change == QGraphicsItem.ItemPositionHasChanged:
            # Update all connected elements
            for ligature in self.connected_ligatures:
                if hasattr(ligature, 'update_path'):
                    ligature.update_path()
            
            for line in self.connected_lines:
                if hasattr(line, 'update_position_from_hooks'):
                    line.update_position_from_hooks()
                
        return super().itemChange(change, value)
    
    def boundingRect(self):
        """Return the bounding rectangle including hooks and safety margin."""
        # Start with text bounds
        bounds = self.text_rect
        
        # Expand to include hook circle with margin
        hook_bounds = QRectF(
            self.text_rect.center().x() - self.hook_radius - 5,
            self.text_rect.center().y() - self.hook_radius - 5,
            2 * (self.hook_radius + 5),
            2 * (self.hook_radius + 5)
        )
        
        return bounds.united(hook_bounds)
    
    def paint(self, painter, option, widget):
        """Paint the predicate item."""
        # Draw selection highlight if selected
        if self.isSelected():
            rect = self.boundingRect()
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.setBrush(QBrush(QColor(0, 120, 215, 30)))
            painter.drawRect(rect)
        
        # Debug: draw hook circle (can be enabled for debugging)
        if hasattr(self, 'show_hook_circle') and self.show_hook_circle:
            painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.DotLine))
            painter.setBrush(QBrush(Qt.transparent))
            center = self.text_rect.center()
            painter.drawEllipse(
                center.x() - self.hook_radius,
                center.y() - self.hook_radius,
                2 * self.hook_radius,
                2 * self.hook_radius
            )

class CutItem(QGraphicsEllipseItem):
    """Cut item with enhanced containment validation."""
    
    def __init__(self, cut_id, x, y, width, height, editor=None, parent=None):
        super().__init__(x, y, width, height, parent)
        self.cut_id = cut_id
        self.node_id = cut_id
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
            self.setPen(QPen(QColor(0, 255, 0), 3))
            self.setBrush(QBrush(QColor(0, 255, 0, 30)))
        else:
            self.setPen(QPen(QColor(0, 0, 0), 2))
            self.setBrush(QBrush(Qt.transparent))
    
    def itemChange(self, change, value):
        """Handle item changes with constraint validation."""
        if change == QGraphicsItem.ItemPositionChange:
            if not ConstraintValidator.is_position_valid(self, value, self.mode, self.editor):
                return self.pos()
                
        return super().itemChange(change, value)

class LigatureItem(QGraphicsPathItem):
    """Ligature item with proper hook-to-hook connections."""
    
    def __init__(self, ligature_id, editor=None, parent=None):
        super().__init__(parent)
        self.ligature_id = ligature_id
        self.editor = editor
        self.mode = InteractionMode.CONSTRAINED
        
        # Connected hooks - list of (predicate_item, hook_index) tuples
        self.connected_hooks = []
        
        # Visual styling
        self.setPen(QPen(QColor(0, 0, 0), 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setZValue(1)
        
        # Colors
        self.selected_color = QColor(255, 0, 0)
        self.normal_color = QColor(0, 0, 0)
        self.hover_color = QColor(0, 0, 255)
        
    def set_mode(self, mode):
        """Set the interaction mode."""
        self.mode = mode
        
    def connect_to_hook(self, predicate_item, hook_index):
        """Connect this ligature to a specific predicate hook."""
        connection = (predicate_item, hook_index)
        if connection not in self.connected_hooks:
            self.connected_hooks.append(connection)
            
            # Update hook visual state
            if hook_index in predicate_item.hooks:
                predicate_item.hooks[hook_index].set_connected(True)
            
            # Add to predicate's connected ligatures
            if hasattr(predicate_item, 'add_connected_ligature'):
                predicate_item.add_connected_ligature(self)
                
        self.update_path()
        
    def disconnect_from_hook(self, predicate_item, hook_index):
        """Disconnect this ligature from a specific predicate hook."""
        connection = (predicate_item, hook_index)
        if connection in self.connected_hooks:
            self.connected_hooks.remove(connection)
            
            # Update hook visual state
            if hook_index in predicate_item.hooks:
                predicate_item.hooks[hook_index].set_connected(False)
            
            # Remove from predicate's connected ligatures
            if hasattr(predicate_item, 'remove_connected_ligature'):
                predicate_item.remove_connected_ligature(self)
                
        self.update_path()
        
    def update_path(self):
        """Update the ligature path based on connected hooks."""
        if len(self.connected_hooks) < 2:
            self.setPath(QPainterPath())
            return
            
        # Get hook positions in scene coordinates
        hook_positions = []
        for predicate_item, hook_index in self.connected_hooks:
            scene_pos = predicate_item.get_hook_scene_position(hook_index)
            local_pos = self.mapFromScene(scene_pos)
            hook_positions.append(local_pos)
        
        # Create path connecting hooks
        path = QPainterPath()
        
        if len(hook_positions) == 2:
            # Direct connection between two hooks
            start_pos = hook_positions[0]
            end_pos = hook_positions[1]
            
            # Use straight line for now (could be enhanced with curves)
            path.moveTo(start_pos)
            path.lineTo(end_pos)
        else:
            # Multiple hooks - create path through all
            path.moveTo(hook_positions[0])
            for pos in hook_positions[1:]:
                path.lineTo(pos)
        
        self.setPath(path)
        
    def paint(self, painter, option, widget):
        """Paint the ligature with state-dependent colors."""
        if self.isSelected():
            pen = QPen(self.selected_color, 3)
        elif self.isUnderMouse():
            pen = QPen(self.hover_color, 2)
        else:
            pen = QPen(self.normal_color, 2)
            
        painter.setPen(pen)
        painter.drawPath(self.path())

# Example usage and testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
    import sys
    
    app = QApplication(sys.argv)
    
    # Create test scene
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    
    # Create test items with corrections
    pred1 = PredicateItem("pred1", "Cat", 1, 0, 0)
    pred2 = PredicateItem("pred2", "On", 2, 150, 0)
    pred3 = PredicateItem("pred3", "Mat", 1, 300, 0)
    
    scene.addItem(pred1)
    scene.addItem(pred2)
    scene.addItem(pred3)
    
    # Create ligatures with proper hook connections
    ligature1 = LigatureItem("lig1")
    ligature1.connect_to_hook(pred1, 1)  # Cat to On's first hook
    ligature1.connect_to_hook(pred2, 1)
    scene.addItem(ligature1)
    
    ligature2 = LigatureItem("lig2")
    ligature2.connect_to_hook(pred3, 1)  # Mat to On's second hook
    ligature2.connect_to_hook(pred2, 2)
    scene.addItem(ligature2)
    
    # Create lines of identity
    line1 = StandaloneLineOfIdentityItem("line1", "x", pred1, 1)
    scene.addItem(line1)
    
    line2 = StandaloneLineOfIdentityItem("line2", "y", pred3, 1)
    scene.addItem(line2)
    
    view.show()
    view.fitInView(scene.itemsBoundingRect())
    
    print("Graphics Items test")
    print("Should show: Cat(x) connected to On, Mat(y) connected to On")
    print("With visible lines of identity for x and y")
    
    app.exec()
