import ast_nodes as ast

class Executer:

    def _init_(self, program, memory):
        self.program = program
        self.memory = memory

    def execute(self):
        for statement in self.program.statements:
            self.execute_statement(statement)

    def execute_statement(self, statement):
        if isinstance(statement, ast.Display):
            value = self.evaluate_expression(statement.expression)
            print(value)
            # self.log(value) # I do not think this is necessary
        elif isinstance(statement, ast.Set):
            value = self.evaluate_expression(statement.expression)
            self.memory[statement.identifier.name] = value
        elif isinstance(statement, ast.Input):
            value = input(statement.prompt)
            self.memory[statement.identifier.name] = value
        elif isinstance(statement, ast.Exit):
            exit()
        elif isinstance(statement, ast.Return):
            return self.evaluate_expression(statement.expression)
        elif isinstance(statement, ast.If):
            condition_value = self.evaluate_condition(statement.condition)
            if condition_value:
                self.execute_statement(statement.if_block)
            else:
                self.execute_statement(statement.else_block)
        elif isinstance(statement, ast.While):
            while self.evaluate_condition(statement.condition):
                self.execute_statement(statement.body)

    def evaluate_expression(self, expression):
        if isinstance(expression, ast.BinaryOperation):
            left = self.evaluate_expression(expression.left)
            right = self.evaluate_expression(expression.right)
            return expression.operator.apply(left, right)
        elif isinstance(expression, ast.Identifier):
            return self.memory[expression.name]
        elif isinstance(expression, ast.StringLiteral):
            return expression.value
        elif isinstance(expression, ast.NumericLiteral):
            return expression.value

    def evaluate_condition(self, condition):
        if isinstance(condition, ast.BinaryOperation):
            left = self.evaluate_expression(condition.left)
            right = self.evaluate_expression(condition.right)
            return condition.operator.apply(left, right)
        elif isinstance(condition, ast.Condition):
            left = self.evaluate_expression(condition.left)
            right = self.evaluate_expression(condition.right)
            out = condition.operator.apply(left, right)
            if condition.negated:
                out = not out
            return out
        elif isinstance(condition, ast.Identifier):
            return bool(self.memory[condition.name])