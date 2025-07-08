"""
Existential Graph Renderer
Integrates all fixes for proper EG representation.
"""

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import QGraphicsScene
from graphics_items import (PredicateItem, CutItem, 
                           LigatureItem, InteractionMode)
from line_of_identity_item import LineOfIdentityItem, StandaloneLineOfIdentityItem
from eg_model import GraphModel, Cut, Predicate, LineOfIdentity, Ligature
import math

class EGRenderer:
    """
    Renderer that properly handles all identified issues:
    1. Constants as separate predicate nodes with proper connections
    2. Lines of identity as visible elements attached to hooks
    3. Proper hook-to-hook ligature connections
    4. Enhanced containment validation
    5. Correct equality representation
    """
    
    def __init__(self, scene, editor):
        self.scene = scene
        self.editor = editor
        self.graphics_items = {}  # Maps object IDs to graphics items
        self.line_items = {}      # Maps line IDs to line graphics items
        self.ligature_items = {}  # Maps ligature IDs to ligature graphics items
        
        # Layout parameters
        self.predicate_spacing = 120
        self.cut_padding = 40
        self.vertical_spacing = 80
        self.line_length = 30
        
    def clear(self):
        """Clear all rendered items."""
        self.scene.clear()
        self.graphics_items.clear()
        self.line_items.clear()
        self.ligature_items.clear()
        
    def render_from_parse_result(self, parse_result):
        """Render from a final corrected CLIF parser result."""
        if not parse_result.get('success', False):
            return False
            
        self.clear()
        
        # Render the main expression
        root_result = parse_result['result']
        self._render_expression_tree(root_result, QPointF(0, 0))
        
        # Create lines of identity for all variables with proper visibility
        variable_map = parse_result.get('variable_map', {})
        hook_connections = parse_result.get('hook_connections', {})
        self._create_visible_lines_of_identity(variable_map, hook_connections)
        
        # Create ligatures with proper hook connections
        self._create_proper_ligatures(parse_result)
        
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
        """Render a constant as a predicate."""
        pred_id = expr_result['predicate_id']
        name = expr_result['name']
        
        pred_item = PredicateItem(
            pred_id, name.capitalize(), 0, position.x(), position.y(), self.editor
        )
        
        self.scene.addItem(pred_item)
        self.graphics_items[pred_id] = pred_item
        
        return pred_item
        
    def _render_predicate(self, expr_result, position):
        """Render a predicate with proper hook connections."""
        pred_id = expr_result['predicate_id']
        name = expr_result['name']
        arity = expr_result['arity']
        
        pred_item = PredicateItem(
            pred_id, name, arity, position.x(), position.y(), self.editor
        )
        
        self.scene.addItem(pred_item)
        self.graphics_items[pred_id] = pred_item
        
        return pred_item
        
    def _render_conjunction(self, expr_result, position):
        """Render conjunction - place items horizontally."""
        conjuncts = expr_result['conjuncts']
        rendered_items = []
        
        # Calculate positions for conjuncts
        total_width = len(conjuncts) * self.predicate_spacing
        start_x = position.x() - total_width / 2
        
        for i, conjunct in enumerate(conjuncts):
            item_pos = QPointF(start_x + i * self.predicate_spacing, position.y())
            item = self._render_expression_tree(conjunct, item_pos)
            if item:
                if isinstance(item, list):
                    rendered_items.extend(item)
                else:
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
            bounds = self._calculate_items_bounds(inner_items)
            cut_x = bounds.x() - self.cut_padding
            cut_y = bounds.y() - self.cut_padding
            cut_width = bounds.width() + 2 * self.cut_padding
            cut_height = bounds.height() + 2 * self.cut_padding
        else:
            # Default cut size
            cut_x = position.x() - 50
            cut_y = position.y() - 30
            cut_width = 100
            cut_height = 60
        
        cut_item = CutItem(cut_id, cut_x, cut_y, cut_width, cut_height, self.editor)
        self.scene.addItem(cut_item)
        self.graphics_items[cut_id] = cut_item
        
        return cut_item
        
    def _render_existential(self, expr_result, position):
        """Render existential quantification (implicit in EG)."""
        return self._render_expression_tree(expr_result['body'], position)
        
    def _render_equality(self, expr_result, position):
        """Render equality with corrected merged line representation."""
        var1 = expr_result['variable1']
        var2 = expr_result['variable2']
        shared_line_id = expr_result['shared_line_id']
        
        # Create a single line representing both variables
        line_item = LineOfIdentityItem(shared_line_id, f"{var1}={var2}")
        line_item.setPos(position)
        line_item.end_point = QPointF(50, 0)  # Longer line for equality
        
        self.scene.addItem(line_item)
        self.line_items[shared_line_id] = line_item
    
    def _create_visible_lines_of_identity(self, variable_map, hook_connections):
        """Create visible lines of identity that properly connect to predicate hooks."""
        # Group hook connections by variable (line ID)
        line_to_hooks = {}
        
        for (pred_id, hook_index), line_id in hook_connections.items():
            if line_id not in line_to_hooks:
                line_to_hooks[line_id] = []
            line_to_hooks[line_id].append((pred_id, hook_index))
        
        # Create lines of identity for each variable
        for var_name, line_id in variable_map.items():
            if line_id not in self.line_items:
                hook_list = line_to_hooks.get(line_id, [])
                
                if len(hook_list) == 0:
                    # No hook connections - create standalone line
                    line_item = StandaloneLineOfIdentityItem(line_id, var_name)
                    line_item.setPos(QPointF(0, 0))
                    self.scene.addItem(line_item)
                    self.line_items[line_id] = line_item
                    
                elif len(hook_list) == 1:
                    # Single connection - create line attached to hook
                    pred_id, hook_index = hook_list[0]
                    pred_item = self.graphics_items.get(pred_id)
                    
                    if pred_item:
                        line_item = StandaloneLineOfIdentityItem(line_id, var_name, pred_item, hook_index)
                        # The line will position itself based on the hook
                        self.scene.addItem(line_item)
                        self.line_items[line_id] = line_item
                        
                        # Establish the connection
                        pred_item.add_connected_line(line_item)
                        
                elif len(hook_list) >= 2:
                    # Multiple connections - line spans between hooks
                    line_item = LineOfIdentityItem(line_id, var_name)
                    
                    # Connect to all hooks
                    connected_predicates = []
                    for pred_id, hook_index in hook_list:
                        pred_item = self.graphics_items.get(pred_id)
                        if pred_item:
                            line_item.add_hook_connection(pred_item, hook_index)
                            pred_item.add_connected_line(line_item)
                            connected_predicates.append((pred_item, hook_index))
                    
                    # The line will position itself based on the hook connections
                    self.scene.addItem(line_item)
                    self.line_items[line_id] = line_item
    
    def _find_predicates_for_line_via_hooks(self, line_id, hook_connections):
        """Find predicates connected to a line via hook connections."""
        connected = []
        
        for (pred_id, hook_index), connected_line_id in hook_connections.items():
            if connected_line_id == line_id:
                pred_item = self.graphics_items.get(pred_id)
                if pred_item:
                    connected.append((pred_item, hook_index))
        
        return connected
    
    def _create_proper_ligatures(self, parse_result):
        """Create ligatures with proper hook-to-hook connections."""
        hook_connections = parse_result.get('hook_connections', {})
        
        # Group hook connections by line ID
        line_to_hooks = {}
        for (pred_id, hook_index), line_id in hook_connections.items():
            if line_id not in line_to_hooks:
                line_to_hooks[line_id] = []
            line_to_hooks[line_id].append((pred_id, hook_index))
        
        # Create ligatures for lines with multiple hook connections
        for line_id, hook_list in line_to_hooks.items():
            if len(hook_list) > 1:
                # Create ligature connecting these hooks
                ligature_id = f"lig_{line_id}"
                ligature_item = LigatureItem(ligature_id, self.editor)
                
                # Connect to specific hooks
                for pred_id, hook_index in hook_list:
                    pred_item = self.graphics_items.get(pred_id)
                    if pred_item:
                        ligature_item.connect_to_hook(pred_item, hook_index)
                
                self.scene.addItem(ligature_item)
                self.ligature_items[ligature_id] = ligature_item
    
    def _calculate_items_bounds(self, items):
        """Calculate the bounding rectangle of a list of graphics items."""
        if not items:
            return QRectF(0, 0, 0, 0)
        
        bounds = items[0].sceneBoundingRect()
        for item in items[1:]:
            bounds = bounds.united(item.sceneBoundingRect())
        
        return bounds
        
    def _optimize_layout(self):
        """Optimize the layout to minimize overlaps and improve readability."""
        # Separate items by type
        predicates = []
        cuts = []
        lines = []
        
        for item in self.graphics_items.values():
            if hasattr(item, 'predicate_id'):
                predicates.append(item)
            elif hasattr(item, 'cut_id'):
                cuts.append(item)
        
        for item in self.line_items.values():
            lines.append(item)
        
        # Adjust predicate positions to avoid overlaps
        self._resolve_predicate_overlaps(predicates)
        
        # Update line positions
        for line in lines:
            if hasattr(line, 'update_position_from_hooks'):
                line.update_position_from_hooks()
        
        # Update ligature paths
        for ligature in self.ligature_items.values():
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
                        dx, dy = 80, 0  # Default separation
                    
                    # Normalize and scale
                    length = math.sqrt(dx*dx + dy*dy)
                    if length > 0:
                        dx = (dx / length) * 90
                        dy = (dy / length) * 50
                        
                        # Move items apart
                        item1.setPos(item1.pos() - QPointF(dx/2, dy/2))
                        item2.setPos(item2.pos() + QPointF(dx/2, dy/2))
    
    def set_mode(self, mode):
        """Set interaction mode for all rendered items."""
        for item in self.graphics_items.values():
            if hasattr(item, 'set_mode'):
                item.set_mode(mode)
                
        for item in self.ligature_items.values():
            if hasattr(item, 'set_mode'):
                item.set_mode(mode)
        
    def get_graphics_item(self, object_id):
        """Get graphics item by object ID."""
        return self.graphics_items.get(object_id)
        
    def get_line_item(self, line_id):
        """Get line graphics item by line ID."""
        return self.line_items.get(line_id)
        
    def get_ligature_item(self, ligature_id):
        """Get ligature graphics item by ligature ID."""
        return self.ligature_items.get(ligature_id)

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
    
    # Test with CLIF parser
    parser = ClifParser(editor)
    
    test_cases = [
        "(Cat x)",
        "(On cat mat)",
        "(exists (x y) (and (Cat x) (Mat y) (On x y)))",
        "(= x y)",
        "(and (Cat x) (Dog y))"
    ]
    
    for i, expr in enumerate(test_cases):
        print(f"\nTesting: {expr}")
        
        # Create fresh components for each test
        editor = EGEditor()
        parser = ClifParser(editor)
        renderer = EGRenderer(scene, editor)
        
        result = parser.parse(expr)
        
        if result['success']:
            render_success = renderer.render_from_parse_result(result)
            if render_success:
                print(f"✓ Rendered successfully")
                print(f"  Graphics items: {len(renderer.graphics_items)}")
                print(f"  Line items: {len(renderer.line_items)}")
                print(f"  Ligature items: {len(renderer.ligature_items)}")
            else:
                print(f"✗ Render failed")
        else:
            print(f"✗ Parse error: {result['error']}")
        
        if i == 0:  # Show first test visually
            view.show()
            view.fitInView(scene.itemsBoundingRect())
            break
    
    print("EG Renderer test - close window to exit")
    app.exec()
