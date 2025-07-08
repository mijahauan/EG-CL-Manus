"""
Existential Graph Renderer
Converts parsed CLIF expressions to visual EG representations using enhanced graphics items.
"""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QGraphicsScene
from enhanced_graphics_items import (EnhancedPredicateItem, EnhancedCutItem, 
                                   FlexibleLigatureItem, LigatureManager)
from eg_model import GraphModel, Cut, Predicate, LineOfIdentity, Ligature
import math

class EGRenderer:
    """
    Renders existential graphs from parsed CLIF expressions or graph models.
    Handles layout, positioning, and visual optimization.
    """
    
    def __init__(self, scene, editor):
        self.scene = scene
        self.editor = editor
        self.graphics_items = {}  # Maps object IDs to graphics items
        self.ligature_manager = LigatureManager(scene, editor)
        
        # Layout parameters
        self.predicate_spacing = 120
        self.cut_padding = 40
        self.vertical_spacing = 80
        
    def clear(self):
        """Clear all rendered items."""
        self.scene.clear()
        self.graphics_items.clear()
        self.ligature_manager = LigatureManager(self.scene, self.editor)
        
    def render_from_parse_result(self, parse_result):
        """Render from a CLIF parser result."""
        if not parse_result.get('success', False):
            return False
            
        self.clear()
        
        # Render the main expression
        root_result = parse_result['result']
        self._render_expression_tree(root_result, QPointF(0, 0))
        
        # Create ligatures based on variable connections
        self._create_ligatures_from_variables(parse_result.get('variable_map', {}))
        
        # Optimize layout
        self._optimize_layout()
        
        return True
        
    def render_from_model(self, graph_model):
        """Render from a graph model directly."""
        self.clear()
        
        # Render all objects in the model
        self._render_model_objects(graph_model)
        
        # Optimize layout
        self._optimize_layout()
        
        return True
        
    def _render_expression_tree(self, expr_result, position):
        """Render an expression tree recursively."""
        expr_type = expr_result.get('type', '')
        
        if expr_type == 'constant':
            return self._render_constant(expr_result, position)
        elif expr_type == 'predicate':
            return self._render_predicate(expr_result, position)
        elif expr_type == 'and':
            return self._render_conjunction(expr_result, position)
        elif expr_type == 'not':
            return self._render_negation(expr_result, position)
        elif expr_type == 'exists':
            return self._render_existential(expr_result, position)
        elif expr_type == 'equality':
            return self._render_equality(expr_result, position)
            
        return None
        
    def _render_constant(self, expr_result, position):
        """Render a constant predicate."""
        pred_id = expr_result['predicate_id']
        name = expr_result['name']
        
        pred_item = EnhancedPredicateItem(
            pred_id, name, 1, position.x(), position.y(), self.editor
        )
        
        self.scene.addItem(pred_item)
        self.graphics_items[pred_id] = pred_item
        
        return pred_item
        
    def _render_predicate(self, expr_result, position):
        """Render a predicate with arguments."""
        pred_id = expr_result['predicate_id']
        name = expr_result['name']
        arity = expr_result['arity']
        
        pred_item = EnhancedPredicateItem(
            pred_id, name, arity, position.x(), position.y(), self.editor
        )
        
        self.scene.addItem(pred_item)
        self.graphics_items[pred_id] = pred_item
        
        return pred_item
        
    def _render_conjunction(self, expr_result, position):
        """Render conjunction - place predicates horizontally."""
        conjuncts = expr_result['conjuncts']
        rendered_items = []
        
        # Calculate total width needed
        total_width = len(conjuncts) * self.predicate_spacing
        start_x = position.x() - total_width / 2
        
        for i, conjunct in enumerate(conjuncts):
            item_pos = QPointF(start_x + i * self.predicate_spacing, position.y())
            item = self._render_expression_tree(conjunct, item_pos)
            if item:
                rendered_items.append(item)
                
        return rendered_items
        
    def _render_negation(self, expr_result, position):
        """Render negation as a cut."""
        cut_id = expr_result['cut_id']
        
        # Render the negated content first to determine cut size
        inner_items = []
        if 'negated' in expr_result:
            inner_item = self._render_expression_tree(expr_result['negated'], position)
            if inner_item:
                if isinstance(inner_item, list):
                    inner_items.extend(inner_item)
                else:
                    inner_items.append(inner_item)
        
        # Calculate cut bounds based on inner items
        if inner_items:
            # Get bounding rectangle of all inner items
            min_x = min(item.pos().x() + item.boundingRect().left() for item in inner_items)
            max_x = max(item.pos().x() + item.boundingRect().right() for item in inner_items)
            min_y = min(item.pos().y() + item.boundingRect().top() for item in inner_items)
            max_y = max(item.pos().y() + item.boundingRect().bottom() for item in inner_items)
            
            # Add padding
            cut_x = min_x - self.cut_padding
            cut_y = min_y - self.cut_padding
            cut_width = (max_x - min_x) + 2 * self.cut_padding
            cut_height = (max_y - min_y) + 2 * self.cut_padding
        else:
            # Default cut size
            cut_x = position.x() - 60
            cut_y = position.y() - 40
            cut_width = 120
            cut_height = 80
        
        cut_item = EnhancedCutItem(cut_id, cut_x, cut_y, cut_width, cut_height, self.editor)
        self.scene.addItem(cut_item)
        self.graphics_items[cut_id] = cut_item
        
        return cut_item
        
    def _render_existential(self, expr_result, position):
        """Render existential quantification (implicit in EG)."""
        # Just render the body - existential quantification is implicit in EG
        return self._render_expression_tree(expr_result['body'], position)
        
    def _render_equality(self, expr_result, position):
        """Render equality - handled through ligature connections."""
        # Equality is represented by ligature connections, not visual items
        return None
        
    def _create_ligatures_from_variables(self, variable_map):
        """Create ligature graphics items based on variable connections."""
        # Group predicates by their connected variables
        line_connections = {}  # Maps line IDs to list of (pred_id, hook_index)
        
        # Scan all predicates in the model to find connections
        for obj_id, obj in self.editor.model.objects.items():
            if isinstance(obj, Predicate):
                for hook_index, line_id in obj.hooks.items():
                    if line_id:
                        if line_id not in line_connections:
                            line_connections[line_id] = []
                        line_connections[line_id].append((obj_id, hook_index))
        
        # Create ligatures for lines with multiple connections
        for line_id, connections in line_connections.items():
            if len(connections) > 1:
                # Find corresponding ligatures in the model
                line_obj = self.editor.model.get_object(line_id)
                if line_obj and hasattr(line_obj, 'ligatures'):
                    for ligature_id in line_obj.ligatures:
                        self.ligature_manager.create_ligature(ligature_id, connections)
                        
    def _render_model_objects(self, graph_model):
        """Render objects directly from a graph model."""
        # First pass: render all cuts and predicates
        positions = self._calculate_layout_positions(graph_model)
        
        for obj_id, obj in graph_model.objects.items():
            if isinstance(obj, Cut):
                pos = positions.get(obj_id, QPointF(0, 0))
                # Calculate cut size based on children
                cut_rect = self._calculate_cut_bounds(obj, positions)
                cut_item = EnhancedCutItem(
                    obj_id, cut_rect.x(), cut_rect.y(), 
                    cut_rect.width(), cut_rect.height(), self.editor
                )
                self.scene.addItem(cut_item)
                self.graphics_items[obj_id] = cut_item
                
            elif isinstance(obj, Predicate):
                pos = positions.get(obj_id, QPointF(0, 0))
                arity = len([h for h in obj.hooks.values() if h is not None])
                pred_item = EnhancedPredicateItem(
                    obj_id, obj.label, arity, pos.x(), pos.y(), self.editor
                )
                self.scene.addItem(pred_item)
                self.graphics_items[obj_id] = pred_item
        
        # Second pass: create ligatures
        self._create_ligatures_from_model(graph_model)
        
    def _calculate_layout_positions(self, graph_model):
        """Calculate optimal positions for all objects."""
        positions = {}
        
        # Simple layout algorithm - can be enhanced
        root_children = graph_model.sheet_of_assertion.children
        
        # Arrange root level items
        x_offset = 0
        for child_id in root_children:
            positions[child_id] = QPointF(x_offset, 0)
            x_offset += self.predicate_spacing
            
            # Recursively position children of cuts
            child_obj = graph_model.get_object(child_id)
            if isinstance(child_obj, Cut):
                self._position_cut_children(child_obj, positions, QPointF(x_offset - self.predicate_spacing, 0))
        
        return positions
        
    def _position_cut_children(self, cut_obj, positions, cut_center):
        """Position children within a cut."""
        children = list(cut_obj.children)
        if not children:
            return
            
        # Arrange children in a circle or grid within the cut
        if len(children) == 1:
            positions[children[0]] = cut_center
        else:
            radius = 30
            angle_step = 2 * math.pi / len(children)
            
            for i, child_id in enumerate(children):
                angle = i * angle_step
                x = cut_center.x() + radius * math.cos(angle)
                y = cut_center.y() + radius * math.sin(angle)
                positions[child_id] = QPointF(x, y)
                
                # Recursively position if this child is also a cut
                child_obj = cut_obj.parent().model.get_object(child_id) if hasattr(cut_obj, 'parent') else None
                if child_obj and isinstance(child_obj, Cut):
                    self._position_cut_children(child_obj, positions, QPointF(x, y))
        
    def _calculate_cut_bounds(self, cut_obj, positions):
        """Calculate the bounding rectangle for a cut based on its children."""
        if not cut_obj.children:
            return QRectF(-60, -40, 120, 80)
            
        # Get positions of all children
        child_positions = [positions.get(child_id, QPointF(0, 0)) for child_id in cut_obj.children]
        
        if not child_positions:
            return QRectF(-60, -40, 120, 80)
            
        # Calculate bounding box
        min_x = min(pos.x() for pos in child_positions) - 40
        max_x = max(pos.x() for pos in child_positions) + 40
        min_y = min(pos.y() for pos in child_positions) - 30
        max_y = max(pos.y() for pos in child_positions) + 30
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        
    def _create_ligatures_from_model(self, graph_model):
        """Create ligatures from the graph model."""
        for obj_id, obj in graph_model.objects.items():
            if isinstance(obj, Ligature):
                connections = list(obj.attachments)
                if len(connections) > 1:
                    self.ligature_manager.create_ligature(obj_id, connections)
                    
    def _optimize_layout(self):
        """Optimize the layout to minimize overlaps and improve readability."""
        # Simple optimization - can be enhanced with more sophisticated algorithms
        
        # Separate items by type
        predicates = []
        cuts = []
        
        for item in self.graphics_items.values():
            if hasattr(item, 'predicate_id'):
                predicates.append(item)
            elif hasattr(item, 'cut_id'):
                cuts.append(item)
        
        # Adjust predicate positions to avoid overlaps
        self._resolve_predicate_overlaps(predicates)
        
        # Update ligature paths
        for ligature in self.ligature_manager.ligatures.values():
            ligature.update_path()
            
    def _resolve_predicate_overlaps(self, predicates):
        """Resolve overlapping predicates by adjusting positions."""
        if len(predicates) < 2:
            return
            
        # Simple force-based separation
        for i in range(len(predicates)):
            for j in range(i + 1, len(predicates)):
                item1, item2 = predicates[i], predicates[j]
                
                # Check if items overlap
                rect1 = item1.sceneBoundingRect()
                rect2 = item2.sceneBoundingRect()
                
                if rect1.intersects(rect2):
                    # Calculate separation vector
                    center1 = rect1.center()
                    center2 = rect2.center()
                    
                    dx = center2.x() - center1.x()
                    dy = center2.y() - center1.y()
                    
                    if abs(dx) < 1 and abs(dy) < 1:
                        dx, dy = 50, 0  # Default separation
                    
                    # Normalize and scale
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        dx = (dx / length) * 60
                        dy = (dy / length) * 30
                        
                        # Move items apart
                        item1.setPos(item1.pos() - QPointF(dx/2, dy/2))
                        item2.setPos(item2.pos() + QPointF(dx/2, dy/2))
    
    def set_mode(self, mode):
        """Set interaction mode for all rendered items."""
        for item in self.graphics_items.values():
            if hasattr(item, 'set_mode'):
                item.set_mode(mode)
                
        self.ligature_manager.set_mode(mode)
        
    def get_graphics_item(self, object_id):
        """Get graphics item by object ID."""
        return self.graphics_items.get(object_id)
        
    def get_all_graphics_items(self):
        """Get all graphics items."""
        return self.graphics_items.copy()

# Example usage and testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QGraphicsView
    from eg_editor import EGEditor
    from clif_parser import ClifParser
    import sys
    
    app = QApplication(sys.argv)
    
    # Create test setup
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    editor = EGEditor()
    renderer = EGRenderer(scene, editor)
    
    # Test with a simple CLIF expression
    parser = ClifParser(editor)
    result = parser.parse("(exists (x y) (and (Cat x) (Mat y) (On x y)))")
    
    if result['success']:
        renderer.render_from_parse_result(result)
        print("Rendered successfully")
    else:
        print(f"Parse error: {result['error']}")
    
    view.show()
    view.fitInView(scene.itemsBoundingRect())
    
    print("EG Renderer test - close window to exit")
    app.exec()
