import ast_nodes as ast

# For catching infinite loops
MAX_LOOP_ITERATIONS = 100000


class RuntimeExecutionError(Exception):
    """Raised when an SCL program has a runtime error"""
    pass

class _ReturnSignal(Exception):
    """Internal signal to get out of nested blocks on return"""

    def __init__(self, value):
        self.value = value

class _ExitSignal(Exception):
    """Internal signal to stop execution on exit"""
    pass

class Executer:

    def __init__(self, program, memory=None, output_path=None):
        self.program = program
        self.memory = memory if memory is not None else {}
        self.types = {}
        self.return_value = None
        self.succeeded = False
        self._output_path = output_path
        self._output = []

    def execute(self):
        self.succeeded = False
        self.return_value = None
        self._output = []

        try:
            if self.program is None or self.program.function is None:
                raise RuntimeExecutionError("No parsed function found to execute")

            for declaration in self.program.function.declarations:
                var_name = declaration.identifier.name
                self.types[var_name] = declaration.data_type
                if var_name not in self.memory:
                    self.memory[var_name] = None

            self.execute_block(self.program.function.statements)
            self.succeeded = True

        except _ReturnSignal as ret:
            self.return_value = ret.value
            self.succeeded = True
            self._emit("Program returned: %s" % ret.value)

        except _ExitSignal:
            self.succeeded = True
            self._emit("Program exited.")

        except RuntimeExecutionError as error:
            self.succeeded = False
            self._emit("Runtime Error: %s" % error)

        finally:
            if self._output_path:
                with open(self._output_path, "w") as out:
                    out.write("\n".join(self._output) + "\n")
                print("")
                print("Execution output saved in %s" % self._output_path)

        return self.succeeded

    def execute_block(self, statements):
        """Execute a list of AST statements in order"""
        for statement in statements:
            self.execute_statement(statement)

    def execute_statement(self, statement):
        """Execute a single AST statement node"""
        if isinstance(statement, ast.Display):
            values = [self.evaluate_expression(item) for item in statement.items]
            line = "".join(str(v) for v in values)
            self._emit(line)

        elif isinstance(statement, ast.Set):
            var_name = statement.identifier.name
            value = self.evaluate_expression(statement.expression)
            self.memory[var_name] = self._cast_value(var_name, value, from_input = False)

        elif isinstance(statement, ast.Input):
            var_name = statement.identifier.name
            raw_value = input(statement.prompt)
            self._log("%s%s" % (statement.prompt, raw_value))
            self.memory[var_name] = self._cast_value(var_name, raw_value, from_input = True)

        elif isinstance(statement, ast.Exit):
            raise _ExitSignal()

        elif isinstance(statement, ast.Return):
            value = self.evaluate_expression(statement.expression)
            raise _ReturnSignal(value)

        elif isinstance(statement, ast.If):
            if self.evaluate_condition(statement.condition):
                self.execute_block(statement.if_block)
            elif statement.else_block:
                self.execute_block(statement.else_block)

        elif isinstance(statement, ast.While):
            iterations = 0
            while self.evaluate_condition(statement.condition):
                iterations += 1
                if iterations > MAX_LOOP_ITERATIONS:
                    raise RuntimeExecutionError("Infinite loop detected")
                self.execute_block(statement.body)

        else:
            raise RuntimeExecutionError("Unknown statement %s" % type(statement).__name__)

    def evaluate_expression(self, expression):
        if isinstance(expression, ast.BinaryOperation):
            left = self.evaluate_expression(expression.left)
            right = self.evaluate_expression(expression.right)

            if expression.operator.symbol == "/" and right == 0:
                raise RuntimeExecutionError("Division by zero.")
            try:
                return expression.operator.apply(left, right)
            except ZeroDivisionError:
                raise RuntimeExecutionError("Division by zero.")
            except (TypeError, ValueError) as error:
                raise RuntimeExecutionError("Invalid operands for operator '%s': %s" % (expression.operator.symbol, error))


        elif isinstance(expression, ast.Identifier):
            name = expression.name
            if name not in self.memory:
                raise RuntimeExecutionError("Undeclared variable '%s'." % name)
            if self.memory[name] is None:
                raise RuntimeExecutionError("Variable '%s' is used before being initialized." % name)
            return self.memory[name]

        elif isinstance(expression, ast.StringLiteral):
            return expression.value

        elif isinstance(expression, ast.NumericLiteral):
            return expression.value

        raise RuntimeExecutionError("Unknown expression type: %s" % type(expression).__name__)

    def evaluate_condition(self, condition):
        """Evaluate a condition AST node and return a boolean"""
        if isinstance(condition, ast.Condition):
            left = self.evaluate_expression(condition.left)
            right = self.evaluate_expression(condition.right)

            try:
                result = condition.operator.apply(left, right)
            except (TypeError, ValueError) as error:
                raise RuntimeExecutionError("Cannot compare values with operator '%s': %s" % (condition.operator.symbol, error))
            return (not result) if condition.negated else bool(result)

        elif isinstance(condition, ast.BinaryOperation):
            left = self.evaluate_expression(condition.left)
            right = self.evaluate_expression(condition.right)

            try:
                return bool(condition.operator.apply(left, right))
            except (TypeError, ValueError) as error:
                raise RuntimeExecutionError("Invalid condition operands for '%s': %s" % (condition.operator.symbol, error))

        elif isinstance(condition, ast.Identifier):
            return bool(self.evaluate_expression(condition))

        raise RuntimeExecutionError("Unknown condition type: %s" % type(condition).__name__)

    # Helpers

    def _cast_value(self, var_name, value, from_input = False):
        """Convert value to match vars declared SCL data type"""
        data_type = self.types.get(var_name)
        if data_type is None:
            raise RuntimeExecutionError("Unknown variable '%s'." % var_name)

        if data_type == "integer":
            if from_input:
                try:
                    return int(str(value).strip())
                except ValueError:
                    raise RuntimeExecutionError("Invalid integer input '%s' for variable '%s'." % (value, var_name))

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RuntimeExecutionError("Cannot assign value %r to integer variable '%s'." % (value, var_name))

            return int(value)

        if data_type in ("double", "float"):
            if from_input:
                try:
                    return float(str(value).strip())
                except ValueError:
                    raise RuntimeExecutionError("Invalid %s input '%s' for variable '%s'." % (data_type, value, var_name))

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise RuntimeExecutionError("Cannot assign value %r to %s variable '%s'." % (value, data_type, var_name))

            return float(value)

        if data_type == "char":
            return str(value)

        return value

    def _log(self, text):
        self._output.append(str(text))

    def _emit(self, text):
        print(text)
        self._log(text)