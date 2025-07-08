"""
CLIF Parser for Existential Graphs
Implements "inside-out" parsing methodology to convert CLIF expressions to EG structures.
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from eg_editor import EGEditor

class ClifParserError(Exception):
    """Exception raised for CLIF parsing errors."""
    pass

class ClifParser:
    """
    Parses CLIF (Common Logic Interchange Format) expressions and converts them
    to Existential Graph structures using the EGEditor API.
    """
    
    def __init__(self, editor: EGEditor):
        self.editor = editor
        self.variable_counter = 0
        self.variable_map = {}  # Maps variable names to line IDs
        
    def parse(self, clif_string: str, parent_context: str = 'SA') -> Dict[str, Any]:
        """
        Parse a CLIF string and create corresponding EG structures.
        
        Args:
            clif_string: The CLIF expression to parse
            parent_context: The parent context ID to add structures to
            
        Returns:
            Dictionary with parsing results and created object IDs
        """
        try:
            # Clean and tokenize the input
            tokens = self._tokenize(clif_string.strip())
            
            # Parse the token stream
            result = self._parse_expression(tokens, parent_context)
            
            return {
                'success': True,
                'result': result,
                'variable_map': self.variable_map.copy()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'variable_map': {}
            }
    
    def _tokenize(self, clif_string: str) -> List[str]:
        """Tokenize a CLIF string into a list of tokens."""
        # Remove comments and normalize whitespace
        clif_string = re.sub(r';.*$', '', clif_string, flags=re.MULTILINE)
        clif_string = re.sub(r'\s+', ' ', clif_string).strip()
        
        if not clif_string:
            raise ClifParserError("Empty expression")
        
        # Tokenize using regex
        token_pattern = r'\(|\)|[^\s()]+'
        tokens = re.findall(token_pattern, clif_string)
        
        if not tokens:
            raise ClifParserError("No valid tokens found")
            
        # Validate parentheses balance
        paren_count = 0
        for token in tokens:
            if token == '(':
                paren_count += 1
            elif token == ')':
                paren_count -= 1
                if paren_count < 0:
                    raise ClifParserError("Unmatched closing parenthesis")
        
        if paren_count != 0:
            raise ClifParserError("Unmatched opening parenthesis")
            
        return tokens
    
    def _parse_expression(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse a single CLIF expression."""
        if not tokens:
            raise ClifParserError("Empty token list")
            
        if tokens[0] != '(':
            # Simple predicate or constant
            return self._parse_simple_predicate(tokens, parent_context)
        
        # Complex expression starting with '('
        if len(tokens) < 3:
            raise ClifParserError("Malformed expression")
            
        operator = tokens[1].lower()
        
        if operator == 'exists':
            return self._parse_exists(tokens, parent_context)
        elif operator == 'and':
            return self._parse_and(tokens, parent_context)
        elif operator == 'or':
            return self._parse_or(tokens, parent_context)
        elif operator == 'not':
            return self._parse_not(tokens, parent_context)
        elif operator == '=':
            return self._parse_equality(tokens, parent_context)
        else:
            # Regular predicate with arguments
            return self._parse_predicate(tokens, parent_context)
    
    def _parse_simple_predicate(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse a simple predicate like 'Cat' or 'cat'."""
        if len(tokens) != 1:
            raise ClifParserError(f"Expected single token, got {len(tokens)}")
            
        predicate_name = tokens[0]
        
        # Create a unary predicate (constant)
        pred_id = self.editor.add_predicate(predicate_name, 1, parent_context, p_type='constant')
        
        # Connect it to a line of identity
        ligature_id = self.editor.connect([(pred_id, 1)])
        
        return {
            'type': 'constant',
            'predicate_id': pred_id,
            'ligature_id': ligature_id,
            'name': predicate_name
        }
    
    def _parse_predicate(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse a predicate with arguments like '(Cat x)' or '(On x y)'."""
        if tokens[0] != '(' or tokens[-1] != ')':
            raise ClifParserError("Predicate must be enclosed in parentheses")
            
        inner_tokens = tokens[1:-1]
        if len(inner_tokens) < 1:
            raise ClifParserError("Empty predicate")
            
        predicate_name = inner_tokens[0]
        arguments = inner_tokens[1:]
        
        # Create predicate with appropriate arity
        arity = len(arguments)
        pred_id = self.editor.add_predicate(predicate_name, arity, parent_context)
        
        # Connect arguments to lines of identity
        connections = []
        for i, arg in enumerate(arguments):
            hook_index = i + 1
            line_id = self._get_or_create_line_for_variable(arg)
            connections.append((pred_id, hook_index))
            
            # Update predicate's hook to point to the line
            predicate = self.editor.model.get_object(pred_id)
            predicate.hooks[hook_index] = line_id
        
        # Create ligature if there are connections
        ligature_id = None
        if connections:
            ligature_id = self.editor.connect(connections)
        
        return {
            'type': 'predicate',
            'predicate_id': pred_id,
            'ligature_id': ligature_id,
            'name': predicate_name,
            'arguments': arguments,
            'arity': arity
        }
    
    def _parse_exists(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse existential quantification like '(exists (x y) (and (Cat x) (On x y)))'."""
        if len(tokens) < 6:  # (exists (vars) expr)
            raise ClifParserError("Malformed 'exists' expression")
            
        # Find the variable list
        if tokens[2] != '(':
            raise ClifParserError("Expected variable list after 'exists'")
            
        # Find matching closing paren for variable list
        var_end = self._find_matching_paren(tokens, 2)
        if var_end == -1:
            raise ClifParserError("Unclosed variable list in 'exists'")
            
        variables = tokens[3:var_end]
        
        # Parse the body expression
        body_tokens = tokens[var_end + 1:-1]  # Remove outer parens
        
        # In EG, existential quantification is implicit - just parse the body
        result = self._parse_expression(body_tokens, parent_context)
        
        return {
            'type': 'exists',
            'variables': variables,
            'body': result
        }
    
    def _parse_and(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse conjunction like '(and (Cat x) (Mat y) (On x y))'."""
        if len(tokens) < 4:  # (and expr1 expr2)
            raise ClifParserError("Malformed 'and' expression - need at least 2 conjuncts")
            
        # Parse each conjunct
        conjuncts = []
        inner_tokens = tokens[2:-1]  # Remove (and ... )
        
        if not inner_tokens:
            raise ClifParserError("Empty 'and' expression")
        
        i = 0
        while i < len(inner_tokens):
            if inner_tokens[i] == '(':
                # Find matching closing paren
                end = self._find_matching_paren(inner_tokens, i)
                if end == -1:
                    raise ClifParserError("Unclosed parenthesis in 'and'")
                expr_tokens = inner_tokens[i:end + 1]
                i = end + 1
            else:
                # Simple token
                expr_tokens = [inner_tokens[i]]
                i += 1
            
            if expr_tokens:  # Only parse non-empty token lists
                conjunct_result = self._parse_expression(expr_tokens, parent_context)
                conjuncts.append(conjunct_result)
        
        if not conjuncts:
            raise ClifParserError("No valid conjuncts found in 'and' expression")
        
        return {
            'type': 'and',
            'conjuncts': conjuncts
        }
    
    def _parse_or(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse disjunction - requires cuts in EG."""
        # OR in EG requires more complex cut structures
        # For now, implement basic version
        raise ClifParserError("Disjunction (or) not yet implemented")
    
    def _parse_not(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse negation like '(not (Cat x))' - creates a cut."""
        if len(tokens) < 4:  # (not expr)
            raise ClifParserError("Malformed 'not' expression")
            
        # Create a cut for negation
        cut_id = self.editor.add_cut(parent_context)
        
        # Parse the negated expression inside the cut
        inner_tokens = tokens[2:-1]  # Remove (not ... )
        negated_result = self._parse_expression(inner_tokens, cut_id)
        
        return {
            'type': 'not',
            'cut_id': cut_id,
            'negated': negated_result
        }
    
    def _parse_equality(self, tokens: List[str], parent_context: str) -> Dict[str, Any]:
        """Parse equality like '(= x y)' - connects variables."""
        if len(tokens) != 5:  # (= x y)
            raise ClifParserError("Malformed '=' expression")
            
        var1, var2 = tokens[2], tokens[3]
        
        # Get or create lines for both variables
        line1_id = self._get_or_create_line_for_variable(var1)
        line2_id = self._get_or_create_line_for_variable(var2)
        
        # If they're different lines, merge them
        if line1_id != line2_id:
            self.editor._merge_lines(line1_id, line2_id)
            # Update variable map
            self.variable_map[var2] = line1_id
        
        return {
            'type': 'equality',
            'variables': [var1, var2],
            'line_id': line1_id
        }
    
    def _get_or_create_line_for_variable(self, variable: str) -> str:
        """Get existing line ID for variable or create a new one."""
        if variable in self.variable_map:
            return self.variable_map[variable]
        
        # Create new line of identity
        from eg_model import LineOfIdentity
        line = LineOfIdentity()
        self.editor.model.add_object(line)
        
        self.variable_map[variable] = line.id
        return line.id
    
    def _find_matching_paren(self, tokens: List[str], start_index: int) -> int:
        """Find the index of the closing parenthesis matching the opening one at start_index."""
        if start_index >= len(tokens) or tokens[start_index] != '(':
            return -1
            
        depth = 1
        for i in range(start_index + 1, len(tokens)):
            if tokens[i] == '(':
                depth += 1
            elif tokens[i] == ')':
                depth -= 1
                if depth == 0:
                    return i
        
        return -1  # No matching paren found

# Example usage and testing
if __name__ == "__main__":
    from eg_editor import EGEditor
    
    editor = EGEditor()
    parser = ClifParser(editor)
    
    # Test simple expressions
    test_expressions = [
        "cat",
        "(Cat x)",
        "(On cat mat)",
        "(exists (x y) (and (Cat x) (Mat y) (On x y)))",
        "(not (Cat x))"
    ]
    
    for expr in test_expressions:
        print(f"\nParsing: {expr}")
        result = parser.parse(expr)
        if result['success']:
            print(f"Success: {result['result']['type']}")
        else:
            print(f"Error: {result['error']}")
