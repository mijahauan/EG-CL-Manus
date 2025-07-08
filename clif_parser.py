"""
CLIF Parser for Existential Graphs
Addresses all remaining issues with constant handling and ligature connections.
"""

import re
import uuid
from typing import List, Dict, Any, Set, Tuple
from eg_editor import EGEditor

class ClifParser:
    """
    CLIF parser that properly handles:
    1. Constants as separate predicate nodes with proper connections
    2. Correct ligature connections to specific hooks
    3. Proper variable-to-hook mapping
    4. Lines of identity for all variables
    """
    
    def __init__(self, editor: EGEditor):
        self.editor = editor
        self.variable_map = {}  # Maps variables to line IDs
        self.constant_predicates = {}  # Maps constants to their predicate IDs
        self.hook_connections = {}  # Maps (predicate_id, hook_index) to line_id
        self.reset()
    
    def reset(self):
        """Reset parser state for new expression."""
        self.variable_map.clear()
        self.constant_predicates.clear()
        self.hook_connections.clear()
    
    def parse(self, clif_string: str) -> Dict[str, Any]:
        """Parse a CLIF expression and return result with success status."""
        try:
            self.reset()
            
            # Tokenize
            tokens = self._tokenize(clif_string)
            
            # Parse expression
            result = self._parse_expression(tokens, 'SA')
            
            return {
                'success': True,
                'result': result,
                'variable_map': self.variable_map.copy(),
                'constant_predicates': self.constant_predicates.copy(),
                'hook_connections': self.hook_connections.copy()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'variable_map': {},
                'constant_predicates': {},
                'hook_connections': {}
            }
    
    def _tokenize(self, clif_string: str) -> List[str]:
        """Tokenize a CLIF string into a list of tokens."""
        # Remove comments and normalize whitespace
        clif_string = re.sub(r';.*$', '', clif_string, flags=re.MULTILINE)
        clif_string = re.sub(r'\s+', ' ', clif_string).strip()
        
        if not clif_string:
            raise Exception("Empty expression")
        
        # Tokenize using regex
        token_pattern = r'\(|\)|[^\s()]+'
        tokens = re.findall(token_pattern, clif_string)
        
        if not tokens:
            raise Exception("No valid tokens found")
            
        # Validate parentheses balance
        paren_count = 0
        for token in tokens:
            if token == '(':
                paren_count += 1
            elif token == ')':
                paren_count -= 1
                if paren_count < 0:
                    raise Exception("Unmatched closing parenthesis")
        
        if paren_count != 0:
            raise Exception("Unmatched opening parenthesis")
            
        return tokens
    
    def _parse_expression(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse a single CLIF expression."""
        if not tokens:
            raise Exception("Empty expression")
        
        # Single token - constant
        if len(tokens) == 1:
            return self._parse_single_constant(tokens[0], parent_context)
        
        # Parenthesized expression
        if tokens[0] == '(' and tokens[-1] == ')':
            inner_tokens = tokens[1:-1]
            
            if not inner_tokens:
                raise Exception("Empty parentheses")
            
            operator = inner_tokens[0]
            
            if operator == 'exists':
                return self._parse_exists(tokens, parent_context)
            elif operator == 'and':
                return self._parse_and(tokens, parent_context)
            elif operator == 'not':
                return self._parse_not(tokens, parent_context)
            elif operator == '=':
                return self._parse_equality(tokens, parent_context)
            else:
                # Predicate with arguments
                return self._parse_predicate(tokens, parent_context)
        
        raise Exception(f"Invalid expression: {' '.join(tokens)}")
    
    def _parse_single_constant(self, token: str, parent_context: str) -> Dict[str, Any]:
        """Parse a single constant token."""
        # Create predicate for constant (arity 0)
        pred_id = self.editor.add_predicate(token.capitalize(), 0, parent_context)
        self.constant_predicates[token] = pred_id
        
        return {
            'type': 'constant',
            'name': token,
            'predicate_id': pred_id
        }
    
    def _parse_predicate(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse a predicate with arguments like '(Cat x)' or '(On x y)'."""
        inner_tokens = tokens[1:-1]
        predicate_name = inner_tokens[0]
        arguments = inner_tokens[1:]
        
        # Create main predicate
        arity = len(arguments)
        pred_id = self.editor.add_predicate(predicate_name, arity, parent_context)
        
        # Process each argument and create proper connections
        argument_info = []
        
        for i, arg in enumerate(arguments):
            hook_index = i + 1
            
            if self._is_constant(arg):
                # Create constant predicate
                const_pred_id = self._create_constant_predicate(arg, parent_context)
                
                # Create line of identity for the connection
                line_id = self._create_line_of_identity()
                
                # Connect constant predicate to line (constants have hook 1)
                self.hook_connections[(const_pred_id, 1)] = line_id
                
                # Connect main predicate's hook to the same line
                self.hook_connections[(pred_id, hook_index)] = line_id
                
                argument_info.append({
                    'type': 'constant',
                    'name': arg,
                    'predicate_id': const_pred_id,
                    'line_id': line_id,
                    'hook_index': hook_index
                })
            else:
                # Variable - get or create line of identity
                line_id = self._get_or_create_line_for_variable(arg)
                
                # Connect main predicate's hook to the line
                self.hook_connections[(pred_id, hook_index)] = line_id
                
                argument_info.append({
                    'type': 'variable',
                    'name': arg,
                    'line_id': line_id,
                    'hook_index': hook_index
                })
        
        return {
            'type': 'predicate',
            'predicate_id': pred_id,
            'name': predicate_name,
            'arguments': argument_info,
            'arity': arity
        }
    
    def _create_constant_predicate(self, constant: str, parent_context: str) -> str:
        """Create a predicate for a constant."""
        if constant in self.constant_predicates:
            return self.constant_predicates[constant]
        
        # Create new predicate for this constant (arity 1 for connection)
        pred_id = self.editor.add_predicate(constant.capitalize(), 1, parent_context)
        self.constant_predicates[constant] = pred_id
        return pred_id
    
    def _is_constant(self, token: str) -> bool:
        """Determine if a token represents a constant."""
        # Simple heuristic: constants are lowercase or start with lowercase
        if len(token) == 1 and token.isupper():
            return False  # Single uppercase letter is likely a variable
        if token.islower() or (token[0].islower() and len(token) > 1):
            return True
        return False
    
    def _parse_equality(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse equality with corrected merged line representation."""
        if len(tokens) != 5:  # (= x y)
            raise Exception("Equality requires exactly two arguments")
        
        var1 = tokens[2]
        var2 = tokens[3]
        
        # Create or get line for first variable
        line_id = self._get_or_create_line_for_variable(var1)
        
        # Map second variable to the SAME line of identity
        self.variable_map[var2] = line_id
        
        return {
            'type': 'equality',
            'variable1': var1,
            'variable2': var2,
            'shared_line_id': line_id,
            'representation': 'merged_lines'
        }
    
    def _parse_exists(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse existential quantification."""
        if len(tokens) < 5:
            raise Exception("Malformed 'exists' expression")
        
        # Extract variable list
        var_end = self._find_matching_paren_from_start(tokens, 2)
        variables = tokens[3:var_end]
        
        # Extract body
        body_tokens = tokens[var_end + 1:-1]
        
        # Create lines of identity for all quantified variables
        for var in variables:
            self._get_or_create_line_for_variable(var)
        
        # Parse body
        result = self._parse_expression(body_tokens, parent_context)
        
        return {
            'type': 'exists',
            'variables': variables,
            'body': result
        }
    
    def _parse_not(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse negation - creates a cut."""
        if len(tokens) < 4:
            raise Exception("Malformed 'not' expression")
        
        # Create cut for negation
        cut_id = self.editor.add_cut(parent_context)
        
        # Parse body within the cut
        body_tokens = tokens[2:-1]
        result = self._parse_expression(body_tokens, cut_id)
        
        return {
            'type': 'not',
            'cut_id': cut_id,
            'negated': result
        }
    
    def _parse_and(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse conjunction."""
        if len(tokens) < 4:
            raise Exception("Malformed 'and' expression")
            
        conjuncts = []
        inner_tokens = tokens[2:-1]
        
        i = 0
        while i < len(inner_tokens):
            if inner_tokens[i] == '(':
                end = self._find_matching_paren(inner_tokens, i)
                if end == -1:
                    raise Exception("Unclosed parenthesis in 'and'")
                expr_tokens = inner_tokens[i:end + 1]
                i = end + 1
            else:
                expr_tokens = [inner_tokens[i]]
                i += 1
            
            if expr_tokens:
                conjunct_result = self._parse_expression(expr_tokens, parent_context)
                conjuncts.append(conjunct_result)
        
        if not conjuncts:
            raise Exception("No valid conjuncts found in 'and' expression")
        
        return {
            'type': 'and',
            'conjuncts': conjuncts
        }
    
    def _get_or_create_line_for_variable(self, variable: str) -> str:
        """Get or create a line of identity for a variable."""
        if variable not in self.variable_map:
            line_id = self._create_line_of_identity()
            self.variable_map[variable] = line_id
        return self.variable_map[variable]
    
    def _create_line_of_identity(self) -> str:
        """Create a new line of identity."""
        ligature_id = self.editor.add_ligature()
        ligature = self.editor.model.get_object(ligature_id)
        return ligature.line_of_identity_id
    
    def _find_matching_paren(self, tokens: List[str], start: int) -> int:
        """Find the index of the matching closing parenthesis."""
        if start >= len(tokens) or tokens[start] != '(':
            return -1
        
        count = 1
        for i in range(start + 1, len(tokens)):
            if tokens[i] == '(':
                count += 1
            elif tokens[i] == ')':
                count -= 1
                if count == 0:
                    return i
        
        return -1
    
    def _find_matching_paren_from_start(self, tokens: List[str], start: int) -> int:
        """Find the index of the matching closing parenthesis starting from given position."""
        return self._find_matching_paren(tokens, start)

# Test the CLIF parser
if __name__ == "__main__":
    from eg_editor import EGEditor
    
    print("Testing CLIF Parser")
    print("=" * 40)
    
    test_cases = [
        "(On cat mat)",
        "(Cat x)",
        "(exists (x y) (and (Cat x) (Mat y) (On x y)))",
        "(= x y)",
        "(and (Cat x) (Dog y))"
    ]
    
    for expr in test_cases:
        print(f"\nTesting: {expr}")
        
        editor = EGEditor()
        parser = ClifParser(editor)
        result = parser.parse(expr)
        
        if result['success']:
            print(f"✓ Success: {result['result']['type']}")
            
            if result['variable_map']:
                print(f"  Variables: {list(result['variable_map'].keys())}")
            
            if result['constant_predicates']:
                print(f"  Constants: {list(result['constant_predicates'].keys())}")
                
            if result['hook_connections']:
                print(f"  Hook connections: {len(result['hook_connections'])}")
                
        else:
            print(f"✗ Error: {result['error']}")
