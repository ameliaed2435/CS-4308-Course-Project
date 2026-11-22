import operator as py_op

# Program node
class Program:
    def __init__(self, imports=None, function=None):
        self.imports = imports if imports is not None else []
        self.function = function # function node

    def __repr__(self):
        return f"Program(imports={self.imports}, function={self.function})"


class Function:
    def __init__(self, name="main", declarations=None, statements=None):
        self.name = name
        self.declarations = declarations if declarations is not None else []
        self.statements = statements if statements is not None else []

    def __repr__(self):
        return f"Function({self.name}, declarations={self.declarations}, statements={self.statements})"

class VariableDeclaration:
    def __init__(self, identifier, data_type, is_pointer=False):
        self.identifier = identifier #identifier node
        self.data_type = data_type
        self.is_pointer = is_pointer

    def __repr__(self):
        ptr = " pointer" if self.is_pointer else ""
        return f"VariableDeclaration({self.identifier}{ptr} of type {self.data_type})"

# Statement nodes
class Statement: # class for scl statements
    pass

class Display(Statement):
    def __init__(self, items):
        self.items = items

    def __repr__(self):
        return f"Display({self.items})"

class Set(Statement):
    def __init__(self, identifier, expression):
        self.identifier = identifier #identifier node
        self.expression = expression #expression node

    def __repr__(self):
        return f"Set({self.identifier} = {self.expression})"

class Input(Statement):
    def __init__(self, prompt, identifier):
        self.prompt = prompt
        self.identifier = identifier

    def __repr__(self):
        return f"Input(prompt={self.prompt!r}, target={self.identifier})"

class If(Statement):
    # conditional branching statements
    def __init__(self, condition, if_block, else_block=None):
        self.condition = condition #condition node
        self.if_block = if_block #list of statements
        self.else_block = else_block if else_block else [] #list of statement nodes

    def __repr__(self):
        return f"If({self.condition}, then={self.if_block}, else={self.else_block})"

class While(Statement):
    # while loop statements
    def __init__(self, condition, body):
        self.condition = condition #condition node
        self.body = body #list of statement nodes

    def __repr__(self):
        return f"While({self.condition}, do={self.body})"

class Return(Statement):
    # return statements
    def __init__(self, expression):
        self.expression = expression #expression node

    def __repr__(self):
        return f"Return({self.expression})"



# Operators, conditions, expressions
class Operator:
    # handles arithmetic and scl relational operators
    OPERATORS = {
        "+": py_op.add,
        "-": py_op.sub,
        "*": py_op.mul,
        "/": py_op.truediv,
        ">": py_op.gt,
        "greater": py_op.gt,
        ">=": py_op.ge,
        "greater or equal": py_op.ge,
        "<": py_op.lt,
        "<=": py_op.le,
        "=": py_op.eq,
        "equal": py_op.eq,
    }

    def __init__(self, symbol):
        self.symbol = " ".join(symbol.split()).lower() if isinstance(symbol, str) else symbol

    def apply(self, left, right):
        func = self.OPERATORS.get(self.symbol)
        if func is None:
            raise ValueError(f"Unsupported operator: {self.symbol}")
        return func(left, right)

    def __repr__(self):
        return f"Operator({self.symbol!r})"


class Expression: # base class for scl expressions
    pass

class Exit(Expression): # exit class
    pass

class Condition(Expression):
    # represents condition
    def __init__(self, left, operator, right, negated=False):
        self.left = left
        # accepts an operator instance or raw operator
        self.operator = operator if isinstance(operator, Operator) else Operator(operator)
        self.right = right
        self.negated = negated # True if following a "not" operator

    def __repr__(self):
        prefix = "not " if self.negated else ""
        return f"Condition({prefix}{self.left} {self.operator.symbol} {self.right})"


class BinaryOperation(Expression):
    # represents binary arithmetic operation
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator if isinstance(operator, Operator) else Operator(operator)
        self.right = right

    def __repr__(self):
        return f"BinaryOperation({self.left} {self.operator.symbol} {self.right})"

""" SCL has no Unary Operations
class UnaryOperation(Expression):
    # represents unary arithmetic operation
    def __init__(self, operator, operand):
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return f"UnaryOperation({self.operator}{self.operand})"
"""

class Identifier(Expression):
    # IDENTIFIER token reference
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


class NumericLiteral(Expression):
    # NUMBER token
    # stores int or float
    def __init__(self, value):
        if isinstance(value, (int, float)):
            self.value = value
        else:
            text = str(value)
            self.value = float(text) if '.' in text else int(text)

    def __repr__(self):
        return f"NumericLiteral({self.value})"


class StringLiteral(Expression):
    # STRING token
    def __init__(self, value):
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            text = text[1:-1]
        self.value = text

    def __repr__(self):
        return f"StringLiteral({self.value!r})"