import json
import os
import sys

import ast_nodes as ast

from Tokenizer import scan_file

DATA_TYPES = ("integer", "double", "float", "char")
RELATIONAL_OPERATORS = (">", ">=", "<", "<=", "=")
STATEMENT_KEYWORDS = ("display", "set", "input", "if", "while", "return")


class ParseError(Exception):
    """Raised for the first syntax or semantic error; parsing stops there."""
    pass


class Node:
    """One node of the parse tree: a grammar rule (<name>) or a token."""

    def __init__(self, label):
        self.label = label
        self.children = []

    def add(self, child):
        self.children.append(child)
        return child

    def render(self, prefix="", is_last=True, is_root=True):
        """Return the tree as a list of text lines (plain ASCII drawing)."""
        if is_root:
            lines = [self.label]
            child_prefix = ""
        else:
            lines = [prefix + ("`-- " if is_last else "|-- ") + self.label]
            child_prefix = prefix + ("    " if is_last else "|   ")
        for number, child in enumerate(self.children):
            lines.extend(child.render(child_prefix, number == len(self.children) - 1, False))
        return lines


class Parser:
    def __init__(self, source, output_path=None, trace=False):
        """source is an .scl file (scanned here) or a JSON token file."""
        self._source = source
        self._output_path = output_path
        self._trace = trace
        self._tokens = self._load_tokens(source)
        self._position = -1          # index of the current token in the list
        self._current = None         # the token the parser is looking at
        self._symbols = {}           # declared variables: name -> data type
        self._statement_count = 0
        self._output = []            # every line printed, also saved to a file
        self.ast_program = None      # build ast program node for Executer


    # Public functions

    def getNextToken(self):
        """Move to the next token and return it. Comment tokens are skipped,
        so the grammar never sees them (the scanner already drops comments;
        the check is kept in case a token file contains them). End-of-statement
        markers are skipped too, but their line numbers are kept for errors."""
        while True:
            self._position += 1
            if self._position >= len(self._tokens):
                last_line = self._tokens[-1].get("line") if self._tokens else None
                self._current = {"Type": "EOF", "id": -1, "value": "end of file", "line": last_line}
                break
            token = self._tokens[self._position]
            if token["Type"] in ("Comment", "EndOfStatement"):
                continue
            self._current = token
            break

        if self._trace:
            self._emit("Next token is: %s (%s)   Next lexeme is %s" %
                       (self._current["Type"], self._current["id"], self._current["value"]))
        if self._current["Type"] == "UNKNOWN":
            raise ParseError("Lexical error on line %s: unrecognized token '%s'" %
                             (self._line(), self._current["value"]))
        return self._current

    def identifierExists(self, identifier):
        """True if the variable has already been declared."""
        return identifier in self._symbols

    def begin(self):
        """Parse the whole program. Returns True if correct."""
        success = False
        self.ast_program = None
        try:
            self.getNextToken()
            tree, self.ast_program = self._start()
            tree = self._start()
            self._emit("")
            self._emit("Parsing completed successfully: %d statements recognized, %d variables declared." %
                       (self._statement_count, len(self._symbols)))
            self._emit("")
            self._emit("Parse tree:")
            for line in tree.render():
                self._emit(line)
            success = True
        except ParseError as error:
            self.ast_program
            self._emit("")
            self._emit("ERROR: %s" % error)
            self._emit("Parsing stopped at the first error.")

        if self._output_path:
            with open(self._output_path, "w") as out:
                out.write("\n".join(self._output) + "\n")
            print("")
            print("Output saved in %s" % self._output_path)
        return success


    # Helpers

    def _load_tokens(self, source):
        """Get the token list: from a JSON file, or by running the scanner."""
        if source.lower().endswith(".json"):
            with open(source) as file:
                data = json.load(file)
            if isinstance(data, dict):
                keys = sorted(data.keys(), key=lambda k: int(k.split("_")[-1]))
                return [data[k] for k in keys]
            return data
        return [token.toDict() for token in scan_file(source)]

    def _emit(self, text):
        print(text)
        self._output.append(text)

    def _line(self):
        line = self._current.get("line")
        return line if line is not None else "?"

    def _found(self):
        if self._current["Type"] == "EOF":
            return "the end of the file"
        return "'%s'" % self._current["value"]

    def _error(self, expected):
        raise ParseError("Syntax error on line %s: expected %s but found %s" %
                         (self._line(), expected, self._found()))

    def _is_keyword(self, word):
        return self._current["Type"] == "Keyword" and self._current["value"] == word

    def _is_operator(self, symbol):
        return self._current["Type"] == "Operator" and self._current["value"] == symbol

    def _is_comma(self):
        return self._current["Type"] == "SpecialSymbol" and self._current["value"] == ","

    def _consume(self, node):
        """Add the current token to the tree node and read the next token."""
        label = "%s: %s" % (self._current["Type"], self._current["value"])
        if self._current["Type"] == "StringLiteral":
            label = '%s: "%s"' % (self._current["Type"], self._current["value"])
        node.add(Node(label))
        self.getNextToken()

    def _expect_keyword(self, word, node, expected=None):
        if not self._is_keyword(word):
            self._error(expected or "'%s'" % word)
        self._consume(node)

    def _expect_operator(self, symbol, node):
        if not self._is_operator(symbol):
            self._error("'%s'" % symbol)
        self._consume(node)

    def _variable(self, node):
        """An identifier that must already be declared."""
        if self._current["Type"] != "Identifier":
            self._error("a variable name")
        name = self._current["value"]
        if not self.identifierExists(name):
            raise ParseError("Semantic error on line %s: variable '%s' is used but has not been declared" %
                             (self._line(), name))
        self._consume(node)
        return name

    def _recognized(self, what, line):
        self._emit("Line %s: %s recognized" % (line, what))


    # Grammar rules - one function per non-terminal
    # each rule returns (cst_node, ast_node). cst_node is parse tree node, ast_node is abstract syntax tree node

    def _start(self):
        # <program> ::= { <import_statement> } "implementations" <function>
        node = Node("<program>")
        imports = []
        while self._is_keyword("import"):
            imp_node, imp_val = self._import_statement()
            node.add(imp_node)
            imports.append(imp_val)
        self._expect_keyword("implementations", node, "'import' or 'implementations'")
        func_node, func_ast = self._function()
        node.add(func_node)
        if self._current["Type"] != "EOF":
            self._error("the end of the file after 'endfun main'")
        return node, ast.Program(imports=imports, function=func_ast)

    def _import_statement(self):
        # <import_statement> ::= "import" STRING
        node = Node("<import_statement>")
        line = self._line()
        self._expect_keyword("import", node)
        if self._current["Type"] != "StringLiteral":
            self._error("a file name in quotes")
        imp_val = self._current["value"]
        self._consume(node)
        self._recognized("<import_statement>", line)
        return node, imp_val

    def _function(self):
        # <function> ::= "function" "main" "is" "variables" <declarations>
        #                "begin" <statements> "endfun" "main"
        node = Node("<function>")
        self._expect_keyword("function", node)
        self._expect_keyword("main", node)
        self._expect_keyword("is", node)
        self._expect_keyword("variables", node)
        decls_node, decls_ast = self._declarations()
        node.add(decls_node)
        self._expect_keyword("begin", node, "'define' or 'begin'")
        stmts_node, stmts_ast = self._statements()
        node.add(stmts_node)
        self._expect_keyword("endfun", node, "a statement or 'endfun'")
        self._expect_keyword("main", node)
        return node, ast.Function(name="main", declarations=decls_ast, statements=stmts_ast)

    def _declarations(self):
        # <declarations> ::= { <declaration> }
        node = Node("<declarations>")
        decls_ast = []
        while self._is_keyword("define"):
            decl_node, decl_ast = self._declaration()
            node.add(decl_node)
            decls_ast.append(decl_ast)
        return node, decls_ast

    def _declaration(self):
        # <declaration> ::= "define" IDENTIFIER [ "pointer" ] "of" "type" <type>
        node = Node("<declaration>")
        line = self._line()
        self._expect_keyword("define", node)
        if self._current["Type"] != "Identifier":
            self._error("a variable name")
        name = self._current["value"]
        if self.identifierExists(name):
            raise ParseError("Semantic error on line %s: variable '%s' has already been declared" %
                             (self._line(), name))
        self._consume(node)
        is_pointer = False
        if self._is_keyword("pointer"):
            is_pointer = True
            self._consume(node)
        self._expect_keyword("of", node)
        self._expect_keyword("type", node)
        type_node = node.add(Node("<type>"))
        if self._current["Type"] != "Keyword" or self._current["value"] not in DATA_TYPES:
            self._error("a data type (integer, double, float or char)")
        data_type = self._current["value"]
        self._consume(type_node)
        self._symbols[name] = data_type
        self._recognized("<declaration> (variable '%s' of type %s)" % (name, data_type), line)
        decl_ast = ast.VariableDeclaration(ast.Identifier(name), data_type, is_pointer=is_pointer)
        return node, decl_ast

    def _statements(self):
        # <statements> ::= { <statement> }
        node = Node("<statements>")
        stmts_ast = []
        while self._current["Type"] == "Keyword" and self._current["value"] in STATEMENT_KEYWORDS:
            stmt_node, stmt_ast = self._statement()
            node.add(stmt_node)
            stmts_ast.append(stmt_ast)
        return node, stmts_ast

    def _statement(self):
        # <statement> ::= <display_statement> | <set_statement> | <input_statement>
        #               | <if_statement> | <while_statement> | <return_statement>
        node = Node("<statement>")
        word = self._current["value"]
        self._statement_count += 1
        if word == "display":
            stmt_node, stmt_ast = self._display_statement()
        elif word == "set":
            stmt_node, stmt_ast = self._set_statement()
        elif word == "input":
            stmt_node, stmt_ast = self._input_statement()
        elif word == "if":
            stmt_node, stmt_ast = self._if_statement()
        elif word == "while":
            stmt_node, stmt_ast = self._while_statement()
        else:
            stmt_node, stmt_ast = self._return_statement()
        node.add(stmt_node)
        return node, stmt_ast

    def _display_statement(self):
        # <display_statement> ::= "display" <item> { "," <item> }
        node = Node("<display_statement>")
        line = self._line()
        self._expect_keyword("display", node)
        items_ast = []
        item_node, item_ast = self._item()
        node.add(item_node)
        items_ast.append(item_ast)
        while self._is_comma():
            self._consume(node)
            item_node, item_ast = self._item()
            node.add(item_node)
            items_ast.append(item_ast)
        self._recognized("<display_statement>", line)
        return node, ast.Display(items_ast)

    def _item(self):
        # <item> ::= STRING | <expression>
        node = Node("<item>")
        if self._current["Type"] == "StringLiteral":
            value = self._current["value"]
            self._consume(node)
            return node, ast.StringLiteral(value)
        expr_node, expr_ast = self._expression()
        node.add(expr_node)
        return node, expr_ast

    def _set_statement(self):
        # <set_statement> ::= "set" IDENTIFIER "=" <expression>
        node = Node("<set_statement>")
        line = self._line()
        self._expect_keyword("set", node)
        var_name = self._variable(node)
        self._expect_operator("=", node)
        expr_node, expr_ast = self._expression()
        node.add(expr_node)
        self._recognized("<set_statement>", line)
        return node, ast.Set(ast.Identifier(var_name), expr_ast)

    def _input_statement(self):
        # <input_statement> ::= "input" STRING "," IDENTIFIER
        node = Node("<input_statement>")
        line = self._line()
        self._expect_keyword("input", node)
        if self._current["Type"] != "StringLiteral":
            self._error("a prompt string in quotes")
        prompt_val = self._current["value"]
        self._consume(node)
        if not self._is_comma():
            self._error("','")
        self._consume(node)
        var_name = self._variable(node)
        self._recognized("<input_statement>", line)
        return node, ast.Input(prompt_val, ast.Identifier(var_name))

    def _if_statement(self):
        # <if_statement> ::= "if" <condition> "then" <statements>
        #                    [ "else" <statements> ] "endif"
        node = Node("<if_statement>")
        line = self._line()
        self._expect_keyword("if", node)
        cond_node, cond_ast = self._condition()
        node.add(cond_node)
        self._expect_keyword("then", node)
        if_node, if_ast = self._statements()
        node.add(if_node)
        else_ast = []
        if self._is_keyword("else"):
            self._consume(node)
            else_node, else_ast = self._statements()
            node.add(else_node)
        self._expect_keyword("endif", node, "a statement, 'else' or 'endif'")
        self._recognized("<if_statement>", line)
        return node, ast.If(cond_ast, if_ast, else_ast)

    def _while_statement(self):
        # <while_statement> ::= "while" <condition> "do" <statements> "endwhile"
        node = Node("<while_statement>")
        line = self._line()
        self._expect_keyword("while", node)
        cond_node, cond_ast = self._condition()
        node.add(cond_node)
        self._expect_keyword("do", node)
        body_node, body_ast = self._statements()
        node.add(body_node)
        self._expect_keyword("endwhile", node, "a statement or 'endwhile'")
        self._recognized("<while_statement>", line)
        return node, ast.While(cond_ast, body_ast)

    def _return_statement(self):
        # <return_statement> ::= "return" <expression>
        node = Node("<return_statement>")
        line = self._line()
        self._expect_keyword("return", node)
        expr_node, expr_ast = self._expression()
        node.add(expr_node)
        self._recognized("<return_statement>", line)
        return node, ast.Return(expr_ast)

    def _condition(self):
        # <condition> ::= [ "not" ] <expression> <relop> <expression>
        node = Node("<condition>")
        if self._is_keyword("not"):
            negated = True
            self._consume(node)
        left_node, left_ast = self._expression()
        node.add(left_node)
        op_node, op_ast = self.relop()
        node.add(op_node)
        right_node, right_ast = self._expression()
        node.add(right_node)
        return node, ast.Condition(left_ast, op_ast, right_ast, negated=negated)

    def _relop(self):
        # <relop> ::= ">" | ">=" | "<" | "<=" | "="
        #           | "greater" [ "or" "equal" ] | "equal"
        node = Node("<relop>")
        if self._current["Type"] == "Operator" and self._current["value"] in RELATIONAL_OPERATORS:
            op_str = self._current["value"]
            self._consume(node)
            return node, ast.Operator(op_str)
        elif self._is_keyword("greater"):
            self._consume(node)
            if self._is_keyword("or"):
                self._consume(node)
                self._expect_keyword("equal", node)
                return node, ast.Operator("greater or equal")
            return node, ast.Operator("greater")
        elif self._is_keyword("equal"):
            self._consume(node)
            return node, ast.Operator("equal")
        else:
            self._error("a comparison operator (>, >=, <, <=, =, greater, equal)")
            return node, None

    def _expression(self):
        # <expression> ::= <term> { ( "+" | "-" ) <term> }
        node = Node("<expression>")
        left_node, left_ast = self._term()
        node.add(left_node)
        while self._is_operator("+") or self._is_operator("-"):
            op_str = self._current["value"]
            self._consume(node)
            right_node, right_ast = self._term()
            node.add(right_node)
            left_ast = ast.BinaryOperation(left_ast, op_str, right_ast)
        return node, left_ast

    def _term(self):
        # <term> ::= <factor> { ( "*" | "/" ) <factor> }
        node = Node("<term>")
        left_node, left_ast = self._factor()
        node.add(left_node)
        while self._is_operator("*") or self._is_operator("/"):
            op_str = self._current["value"]
            self._consume(node)
            right_node, right_ast = self._factor()
            node.add(right_node)
            left_ast = ast.BinaryOperation(left_ast, op_str, right_ast)
        return node, left_ast

    def _factor(self):
        # <factor> ::= IDENTIFIER | NUMBER | "(" <expression> ")" | "-" <factor>
        node = Node("<factor>")
        if self._current["Type"] == "Identifier":
            var_name = self._variable(node)
            return node, ast.Identifier(var_name)
        elif self._current["Type"] == "NumericLiteral":
            num_val = self._current["value"]
            self._consume(node)
            return node, ast.NumericLiteral(num_val)
        elif self._is_operator("("):
            self._consume(node)
            expr_node, expr_ast = self._expression()
            node.add(expr_node)
            self._expect_operator(")", node)
            return node, expr_ast
        elif self._is_operator("-"):
            self._consume(node)
            fac_node, fac_ast = self._factor()
            node.add(fac_node)
            return node, ast.BinaryOperation(ast.NumericLiteral(0), "-", fac_ast)
        else:
            self._error("a variable, a number or '('")
            return node, None


def main(arguments):
    trace = "--trace" in arguments
    names = [a for a in arguments if not a.startswith("--")]

    if names:
        file_name = names[0]
    else:
        file_name = input("Enter the name of the SCL source file (or a scanner token .json file): ").strip().strip('"')

    if file_name == "":
        print("No file name was entered.")
        return 2
    if not os.path.isfile(file_name):
        print("no such file or directory: ", file_name)
        return 2

    stem = os.path.splitext(os.path.basename(file_name))[0]
    parser = Parser(file_name, stem + "_parse_output.txt", trace)
    return 0 if parser.begin() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))