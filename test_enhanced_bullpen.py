#!/usr/bin/env python3
"""
Comprehensive tests for the Enhanced Bullpen GUI
Tests CLIF parsing, EG rendering, and interactive features.
"""

import unittest
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPointF
from PySide6.QtTest import QTest

# Import the components to test
from enhanced_bullpen_gui import EnhancedBullpenMainWindow, BullpenCanvas
from clif_parser import ClifParser
from eg_renderer import EGRenderer
from enhanced_graphics_items import (EnhancedPredicateItem, EnhancedCutItem, 
                                   FlexibleLigatureItem, InteractionMode)
from eg_editor import EGEditor

class TestEnhancedBullpenGUI(unittest.TestCase):
    """Test suite for the enhanced bullpen GUI."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        self.window = EnhancedBullpenMainWindow()
        self.canvas = self.window.canvas
        self.editor = self.window.editor
        self.parser = self.window.parser
        
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'window'):
            self.window.close()
    
    def test_window_initialization(self):
        """Test that the main window initializes correctly."""
        self.assertIsNotNone(self.window)
        self.assertIsNotNone(self.canvas)
        self.assertIsNotNone(self.editor)
        self.assertIsNotNone(self.parser)
        
        # Check initial state
        self.assertEqual(self.canvas.mode, InteractionMode.CONSTRAINED)
        self.assertEqual(self.window.current_clif, "")
        
    def test_clif_parsing_simple(self):
        """Test parsing simple CLIF expressions."""
        test_cases = [
            "cat",
            "(Cat x)",
            "(On cat mat)",
        ]
        
        for clif_expr in test_cases:
            with self.subTest(clif=clif_expr):
                result = self.parser.parse(clif_expr)
                self.assertTrue(result['success'], f"Failed to parse: {clif_expr}")
                self.assertIn('result', result)
                self.assertIn('type', result['result'])
                
    def test_clif_parsing_complex(self):
        """Test parsing complex CLIF expressions."""
        test_cases = [
            "(exists (x y) (and (Cat x) (Mat y) (On x y)))",
            "(not (Cat x))",
            "(and (Cat x) (Dog y))",
        ]
        
        for clif_expr in test_cases:
            with self.subTest(clif=clif_expr):
                # Create fresh editor and parser for each test
                editor = EGEditor()
                parser = ClifParser(editor)
                result = parser.parse(clif_expr)
                self.assertTrue(result['success'], f"Failed to parse: {clif_expr}. Error: {result.get('error', 'Unknown')}")
                
    def test_rendering_from_clif(self):
        """Test rendering CLIF expressions to graphics."""
        clif_expr = "(exists (x y) (and (Cat x) (Mat y) (On x y)))"
        
        # Parse
        result = self.parser.parse(clif_expr)
        self.assertTrue(result['success'])
        
        # Render
        success = self.canvas.render_clif_result(result)
        self.assertTrue(success)
        
        # Check that items were created
        items = self.canvas.scene.items()
        self.assertGreater(len(items), 0, "No graphics items were created")
        
        # Check for predicate items
        predicate_items = [item for item in items if hasattr(item, 'predicate_id')]
        self.assertGreater(len(predicate_items), 0, "No predicate items found")
        
    def test_mode_switching(self):
        """Test interaction mode switching."""
        # Start in constrained mode
        self.assertEqual(self.canvas.mode, InteractionMode.CONSTRAINED)
        
        # Switch to free mode
        self.window.set_mode(InteractionMode.FREE)
        self.assertEqual(self.canvas.mode, InteractionMode.FREE)
        
        # Switch back to constrained
        self.window.set_mode(InteractionMode.CONSTRAINED)
        self.assertEqual(self.canvas.mode, InteractionMode.CONSTRAINED)
        
    def test_canvas_operations(self):
        """Test basic canvas operations."""
        # Test clearing
        self.canvas.clear_canvas()
        self.assertEqual(len(self.canvas.scene.items()), 0)
        
        # Test rendering
        clif_expr = "(Cat x)"
        result = self.parser.parse(clif_expr)
        success = self.canvas.render_clif_result(result)
        self.assertTrue(success)
        self.assertGreater(len(self.canvas.scene.items()), 0)
        
        # Test clearing again
        self.canvas.clear_canvas()
        self.assertEqual(len(self.canvas.scene.items()), 0)
        
    def test_new_document(self):
        """Test creating a new document."""
        # Add some content first
        clif_expr = "(Cat x)"
        result = self.parser.parse(clif_expr)
        self.canvas.render_clif_result(result)
        self.assertGreater(len(self.canvas.scene.items()), 0)
        
        # Create new document
        self.window.on_new()
        
        # Check that everything is cleared
        self.assertEqual(len(self.canvas.scene.items()), 0)
        self.assertEqual(self.window.current_clif, "")
        self.assertIsNone(self.window.parse_result)

class TestEnhancedGraphicsItems(unittest.TestCase):
    """Test suite for enhanced graphics items."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        self.editor = EGEditor()
        
    def test_enhanced_predicate_item(self):
        """Test enhanced predicate item functionality."""
        pred_item = EnhancedPredicateItem("pred1", "Cat", 2, 0, 0, self.editor)
        
        # Check basic properties
        self.assertEqual(pred_item.predicate_id, "pred1")
        self.assertEqual(len(pred_item.hooks), 2)
        self.assertEqual(pred_item.mode, InteractionMode.CONSTRAINED)
        
        # Test mode switching
        pred_item.set_mode(InteractionMode.FREE)
        self.assertEqual(pred_item.mode, InteractionMode.FREE)
        
    def test_enhanced_cut_item(self):
        """Test enhanced cut item functionality."""
        cut_item = EnhancedCutItem("cut1", 0, 0, 100, 80, self.editor)
        
        # Check basic properties
        self.assertEqual(cut_item.cut_id, "cut1")
        self.assertEqual(cut_item.mode, InteractionMode.CONSTRAINED)
        
        # Test drop highlighting
        cut_item.set_drop_highlighted(True)
        self.assertTrue(cut_item.drop_highlighted)
        
    def test_flexible_ligature_item(self):
        """Test flexible ligature item functionality."""
        ligature = FlexibleLigatureItem("lig1", self.editor)
        
        # Check basic properties
        self.assertEqual(ligature.ligature_id, "lig1")
        self.assertEqual(len(ligature.connected_items), 0)
        
        # Test connection (mock)
        pred1 = EnhancedPredicateItem("pred1", "Cat", 1, 0, 0, self.editor)
        pred2 = EnhancedPredicateItem("pred2", "Animal", 1, 100, 0, self.editor)
        
        ligature.connect_to_item(pred1, 1)
        ligature.connect_to_item(pred2, 1)
        
        self.assertEqual(len(ligature.connected_items), 2)

class TestClifParser(unittest.TestCase):
    """Test suite for CLIF parser."""
    
    def setUp(self):
        """Set up each test."""
        self.editor = EGEditor()
        self.parser = ClifParser(self.editor)
        
    def test_simple_expressions(self):
        """Test parsing simple expressions."""
        test_cases = [
            ("cat", "constant"),
            ("(Cat x)", "predicate"),
            ("(On x y)", "predicate"),
        ]
        
        for expr, expected_type in test_cases:
            with self.subTest(expr=expr):
                result = self.parser.parse(expr)
                self.assertTrue(result['success'])
                self.assertEqual(result['result']['type'], expected_type)
                
    def test_complex_expressions(self):
        """Test parsing complex expressions."""
        test_cases = [
            ("(exists (x) (Cat x))", "exists"),
            ("(not (Cat x))", "not"),
            ("(and (Cat x) (Dog y))", "and"),
        ]
        
        for expr, expected_type in test_cases:
            with self.subTest(expr=expr):
                result = self.parser.parse(expr)
                self.assertTrue(result['success'])
                self.assertEqual(result['result']['type'], expected_type)
                
    def test_error_handling(self):
        """Test error handling for invalid expressions."""
        invalid_expressions = [
            "",
            "(",
            ")",
            "(Cat",
            "Cat)",
            "(and)",
            "(exists)",
        ]
        
        for expr in invalid_expressions:
            with self.subTest(expr=expr):
                result = self.parser.parse(expr)
                self.assertFalse(result['success'])
                self.assertIn('error', result)

class TestEGRenderer(unittest.TestCase):
    """Test suite for EG renderer."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up each test."""
        from PySide6.QtWidgets import QGraphicsScene
        self.scene = QGraphicsScene()
        self.editor = EGEditor()
        self.renderer = EGRenderer(self.scene, self.editor)
        self.parser = ClifParser(self.editor)
        
    def test_render_simple_expression(self):
        """Test rendering a simple expression."""
        clif_expr = "(Cat x)"
        result = self.parser.parse(clif_expr)
        self.assertTrue(result['success'])
        
        success = self.renderer.render_from_parse_result(result)
        self.assertTrue(success)
        
        # Check that items were created
        items = self.scene.items()
        self.assertGreater(len(items), 0)
        
    def test_render_complex_expression(self):
        """Test rendering a complex expression."""
        clif_expr = "(exists (x y) (and (Cat x) (Mat y) (On x y)))"
        result = self.parser.parse(clif_expr)
        self.assertTrue(result['success'])
        
        success = self.renderer.render_from_parse_result(result)
        self.assertTrue(success)
        
        # Check that multiple items were created
        items = self.scene.items()
        self.assertGreater(len(items), 2)  # Should have multiple predicates
        
    def test_clear_renderer(self):
        """Test clearing the renderer."""
        # Render something first
        clif_expr = "(Cat x)"
        result = self.parser.parse(clif_expr)
        self.renderer.render_from_parse_result(result)
        self.assertGreater(len(self.scene.items()), 0)
        
        # Clear
        self.renderer.clear()
        self.assertEqual(len(self.scene.items()), 0)

def run_tests():
    """Run all tests."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestEnhancedBullpenGUI))
    suite.addTest(unittest.makeSuite(TestEnhancedGraphicsItems))
    suite.addTest(unittest.makeSuite(TestClifParser))
    suite.addTest(unittest.makeSuite(TestEGRenderer))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    import os
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    print("Enhanced Bullpen GUI Test Suite")
    print("=" * 50)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
