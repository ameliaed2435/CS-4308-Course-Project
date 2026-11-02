import json
import os
import sys

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
        try:
            self.getNextToken()
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

    def _recognized(self, what, line):
        self._emit("Line %s: %s recognized" % (line, what))


    # Grammar rules - one function per non-terminal

    def _start(self):
        # <program> ::= { <import_statement> } "implementations" <function>
        node = Node("<program>")
        while self._is_keyword("import"):
            node.add(self._import_statement())
        self._expect_keyword("implementations", node, "'import' or 'implementations'")
        node.add(self._function())
        if self._current["Type"] != "EOF":
            self._error("the end of the file after 'endfun main'")
        return node

    def _import_statement(self):
        # <import_statement> ::= "import" STRING
        node = Node("<import_statement>")
        line = self._line()
        self._expect_keyword("import", node)
        if self._current["Type"] != "StringLiteral":
            self._error("a file name in quotes")
        self._consume(node)
        self._recognized("<import_statement>", line)
        return node

    def _function(self):
        # <function> ::= "function" "main" "is" "variables" <declarations>
        #                "begin" <statements> "endfun" "main"
        node = Node("<function>")
        self._expect_keyword("function", node)
        self._expect_keyword("main", node)
        self._expect_keyword("is", node)
        self._expect_keyword("variables", node)
        node.add(self._declarations())
        self._expect_keyword("begin", node, "'define' or 'begin'")
        node.add(self._statements())
        self._expect_keyword("endfun", node, "a statement or 'endfun'")
        self._expect_keyword("main", node)
        return node

    def _declarations(self):
        # <declarations> ::= { <declaration> }
        node = Node("<declarations>")
        while self._is_keyword("define"):
            node.add(self._declaration())
        return node

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
        if self._is_keyword("pointer"):
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
        return node

    def _statements(self):
        # <statements> ::= { <statement> }
        node = Node("<statements>")
        while self._current["Type"] == "Keyword" and self._current["value"] in STATEMENT_KEYWORDS:
            node.add(self._statement())
        return node

    def _statement(self):
        # <statement> ::= <display_statement> | <set_statement> | <input_statement>
        #               | <if_statement> | <while_statement> | <return_statement>
        node = Node("<statement>")
        word = self._current["value"]
        self._statement_count += 1
        if word == "display":
            node.add(self._display_statement())
        elif word == "set":
            node.add(self._set_statement())
        elif word == "input":
            node.add(self._input_statement())
        elif word == "if":
            node.add(self._if_statement())
        elif word == "while":
            node.add(self._while_statement())
        else:
            node.add(self._return_statement())
        return node

    def _display_statement(self):
        # <display_statement> ::= "display" <item> { "," <item> }
        node = Node("<display_statement>")
        line = self._line()
        self._expect_keyword("display", node)
        node.add(self._item())
        while self._is_comma():
            self._consume(node)
            node.add(self._item())
        self._recognized("<display_statement>", line)
        return node

    def _item(self):
        # <item> ::= STRING | <expression>
        node = Node("<item>")
        if self._current["Type"] == "StringLiteral":
            self._consume(node)
        else:
            node.add(self._expression())
        return node

    def _set_statement(self):
        # <set_statement> ::= "set" IDENTIFIER "=" <expression>
        node = Node("<set_statement>")
        line = self._line()
        self._expect_keyword("set", node)
        self._variable(node)
        self._expect_operator("=", node)
        node.add(self._expression())
        self._recognized("<set_statement>", line)
        return node

    def _input_statement(self):
        # <input_statement> ::= "input" STRING "," IDENTIFIER
        node = Node("<input_statement>")
        line = self._line()
        self._expect_keyword("input", node)
        if self._current["Type"] != "StringLiteral":
            self._error("a prompt string in quotes")
        self._consume(node)
        if not self._is_comma():
            self._error("','")
        self._consume(node)
        self._variable(node)
        self._recognized("<input_statement>", line)
        return node

    def _if_statement(self):
        # <if_statement> ::= "if" <condition> "then" <statements>
        #                    [ "else" <statements> ] "endif"
        node = Node("<if_statement>")
        line = self._line()
        self._expect_keyword("if", node)
        node.add(self._condition())
        self._expect_keyword("then", node)
        node.add(self._statements())
        if self._is_keyword("else"):
            self._consume(node)
            node.add(self._statements())
        self._expect_keyword("endif", node, "a statement, 'else' or 'endif'")
        self._recognized("<if_statement>", line)
        return node

    def _while_statement(self):
        # <while_statement> ::= "while" <condition> "do" <statements> "endwhile"
        node = Node("<while_statement>")
        line = self._line()
        self._expect_keyword("while", node)
        node.add(self._condition())
        self._expect_keyword("do", node)
        node.add(self._statements())
        self._expect_keyword("endwhile", node, "a statement or 'endwhile'")
        self._recognized("<while_statement>", line)
        return node

    def _return_statement(self):
        # <return_statement> ::= "return" <expression>
        node = Node("<return_statement>")
        line = self._line()
        self._expect_keyword("return", node)
        node.add(self._expression())
        self._recognized("<return_statement>", line)
        return node

    def _condition(self):
        # <condition> ::= [ "not" ] <expression> <relop> <expression>
        node = Node("<condition>")
        if self._is_keyword("not"):
            self._consume(node)
        node.add(self._expression())
        node.add(self._relop())
        node.add(self._expression())
        return node

    def _relop(self):
        # <relop> ::= ">" | ">=" | "<" | "<=" | "="
        #           | "greater" [ "or" "equal" ] | "equal"
        node = Node("<relop>")
        if self._current["Type"] == "Operator" and self._current["value"] in RELATIONAL_OPERATORS:
            self._consume(node)
        elif self._is_keyword("greater"):
            self._consume(node)
            if self._is_keyword("or"):
                self._consume(node)
                self._expect_keyword("equal", node)
        elif self._is_keyword("equal"):
            self._consume(node)
        else:
            self._error("a comparison operator (>, >=, <, <=, =, greater, equal)")
        return node

    def _expression(self):
        # <expression> ::= <term> { ( "+" | "-" ) <term> }
        node = Node("<expression>")
        node.add(self._term())
        while self._is_operator("+") or self._is_operator("-"):
            self._consume(node)
            node.add(self._term())
        return node

    def _term(self):
        # <term> ::= <factor> { ( "*" | "/" ) <factor> }
        node = Node("<term>")
        node.add(self._factor())
        while self._is_operator("*") or self._is_operator("/"):
            self._consume(node)
            node.add(self._factor())
        return node

    def _factor(self):
        # <factor> ::= IDENTIFIER | NUMBER | "(" <expression> ")" | "-" <factor>
        node = Node("<factor>")
        if self._current["Type"] == "Identifier":
            self._variable(node)
        elif self._current["Type"] == "NumericLiteral":
            self._consume(node)
        elif self._is_operator("("):
            self._consume(node)
            node.add(self._expression())
            self._expect_operator(")", node)
        elif self._is_operator("-"):
            self._consume(node)
            node.add(self._factor())
        else:
            self._error("a variable, a number or '('")
        return node


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