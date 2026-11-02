import sys
from Token import Token
import Tokenizer

# Group members: Amelia Dodson, Michael Constantine, Jarren Shaw, Alex Rickman

class Parser:
    # Constructor that initializes the parser's state and tokenizer (the scanner).
    def __init__(self, filename):
        self.__tokens = []          # Token list
        self.__index = -1
        self.current_token = None
        self.__identifiers = []          # Effectively a (basic) symbol table to allow tracking of declared variables.
        self.__current_statement = []    # Buffers current line text to print when a statement finishes.
        self.output_log = []             # Stores successfully recognized statements

        # Initialize Tokenizer to run the scanner on the input file
        # Creates a list of Token objects to be parsed.
        Tokenizer.ident_counter = 3000
        Tokenizer.identifier_map = {}
        for line_tokens in Tokenizer.filter_file(filename):
            for raw_token in line_tokens:
                category = Tokenizer.categorize_token(raw_token)
                self.__tokens.append(Token(category["Type"], category["id"], category["value"]))
            self.__tokens.append(Token("EndOfStatement", 1000, "EOS"))

    # =========================================================================
    # Required Functions
    # =========================================================================
    def getNextToken(self):
        # Increments internal pointer to grab the next valid token from the list.
        self.__index += 1
        while self.__index < len(self.__tokens):
            token = self.__tokens[self.__index]
            if token.type != "Comment": # Skip over comments
                self.current_token = token
                return self.current_token
            self.__index += 1
        self.current_token = None
        return None

    # ensure variables are declared before usage.
    def identifierExists(self, identifier):
        return identifier in self.__identifiers

    # Entry points for the parser
    # Grabs the first token and then calls __start() (the root grammar rule)
    def begin(self):
        self.getNextToken()
        self.__start()

    # =========================================================================
    # Helper Functions
    # =========================================================================

    # Error handler. If any grammar violations are found, compilation is stopped immediately
    # after printing which token caused the violation for SCL debugging purposes.
    def __error(self, message):
        found = f"'{self.current_token.value}'" if self.current_token else "EOF"
        print(f"Syntax Error near {found}: {message}")
        sys.exit(1)

    # Compares current token against what the grammar expects.
    # If it matches, the token is added to the statement buffer, consumed by calling getNextToken, then returned.
    # If an EndOfStatement is found, a full syntax rule has completed successfully and is then logged.
    def __match(self, expected_value=None, expected_type=None):
        if self.current_token is None:
            self.__error(f"Unexpected EOF; expected {expected_value or expected_type}")
        if expected_value and self.current_token.value != expected_value:
            self.__error(f"Expected '{expected_value}', found '{self.current_token.value}'")
        if expected_type and self.current_token.type != expected_type:
            self.__error(f"Expected {expected_type}, found '{self.current_token.value}'")

        token = self.current_token

        if token.type == "EndOfStatement": # EOS
            msg = f"Statement recognized: {' '.join(self.__current_statement)}"
            print(msg)
            self.output_log.append(msg)
            self.__current_statement = []
        elif token.type == "StringLiteral":
            self.__current_statement.append(f'"{token.value}"')
        else:
            self.__current_statement.append(token.value)

        self.getNextToken()
        return token

    # =========================================================================
    # Grammar Non-Terminal Functions (follows the rules of the bnf grammar)
    # =========================================================================

    # grammar syntax tree's root.
    # SCL files have to start with imports, then implementations, and end without any leftover garbage tokens
    def __start(self):
        self.__imports()
        self.__implementations()
        if self.current_token is not None:
            self.__error("Unexpected tokens after endfun")

    # loops through and consumes any import statements.
    def __imports(self):
        # it's ok to have no imports, so a while loop is used.
        while self.current_token and self.current_token.value == "import":
            self.__match("import")
            self.__match(expected_type="StringLiteral")
            self.__match("EOS")

    # ensures 'implementations', 'function main', 'variables', and 'begin' keywords are in the correct order.
    def __implementations(self):
        self.__match("implementations")
        self.__match("EOS")
        self.__match("function")
        self.__match("main")
        self.__match("is")
        self.__match("EOS")
        self.__variables()
        self.__match("begin")
        self.__match("EOS")
        self.__actions()
        self.__match("endfun")
        self.__match("main")
        self.__match("EOS")

    #check if a 'variables' section exists
    def __variables(self):
        if self.current_token and self.current_token.value == "variables": # if section exists
            self.__match("variables")
            self.__match("EOS")
            while self.current_token and self.current_token.value == "define": # loops through each define statement
                self.__var_declare()                                           # calls __var_declare to handle variable declaration

    # Parses a single variable declaration
    def __var_declare(self):
        self.__match("define")
        identifier = self.__match(expected_type="Identifier")

        if self.identifierExists(identifier.value): # Prevent duplicate declarations
            self.__error(f"Variable '{identifier.value}' has already been declared")
        self.__identifiers.append(identifier.value) # Append new variable's name to the symbol tracker.

        # Handle optional 'pointer' keyword
        if self.current_token and self.current_token.value == "pointer":
            self.__match("pointer")

        self.__match("of")
        self.__match("type")

        # Validate the data type
        if self.current_token and self.current_token.value in ("integer", "double", "float", "char", "num"):
            self.__match(self.current_token.value)
        else:
            self.__error("Expected valid data type")
        self.__match("EOS")

    def __actions(self):
        valid_actions = ("display", "set", "input", "if", "return", "exit")

        # as long as the next token is a valid action, keep calling __action()
        while self.current_token and self.current_token.value in valid_actions:
            self.__action()

    # Effectively a router for all executable statements.
    def __action(self):
        keyword = self.current_token.value

        if keyword == "display":
            self.__match("display")
            self.__expression()

            # Handles comma separated lists of things for displaying
            while self.current_token and self.current_token.value == ",":
                self.__match(",")
                self.__expression()
            self.__match("EOS")

        elif keyword == "set":
            self.__match("set")
            identifier = self.__match(expected_type="Identifier")

            # Make sure a value cannot be assigned to a variable that was never defined
            if not self.identifierExists(identifier.value):
                self.__error(f"Undeclared variable '{identifier.value}'")
            self.__match("=")
            self.__expression()
            self.__match("EOS")

        elif keyword == "input":
            self.__match("input")
            self.__match(expected_type="StringLiteral")
            self.__match(",")
            identifier = self.__match(expected_type="Identifier")
            if not self.identifierExists(identifier.value):
                self.__error(f"Undeclared variable '{identifier.value}'")
            self.__match("EOS")

        elif keyword == "if":
            self.__match("if")
            self.__condition()
            self.__match("then")
            self.__match("EOS")
            self.__actions() # Recursively call __actions() to parse code inside the if block.

            # check for else block
            if self.current_token and self.current_token.value == "else":
                self.__match("else")
                self.__match("EOS")
                self.__actions()
            self.__match("endif")
            self.__match("EOS")

        elif keyword == "return":
            self.__match("return")
            self.__expression()
            self.__match("EOS")

        elif keyword == "exit":
            self.__match("exit")
            self.__match("EOS")

    def __condition(self):
        # Parse boolean logic
        if self.current_token and self.current_token.value == "not":
            self.__match("not")
        self.__expression()

        # Handle symbolic and keyword-based relational operators (>, greater than, etc)
        if self.current_token and self.current_token.value in (">", "<", "="):
            self.__match(self.current_token.value)
            if self.current_token and self.current_token.value == "=":
                self.__match("=")
        elif self.current_token and self.current_token.value == "greater":
            self.__match("greater")
            if self.current_token and self.current_token.value == "or":
                self.__match("or")
                self.__match("equal")
        elif self.current_token and self.current_token.value == "equal":
            self.__match("equal")
        else:
            self.__error("Expected relational operator")

        self.__expression()

    # Parses math
    def __expression(self):
        self.__operand() # Read an operand
        while self.current_token and self.current_token.value in ("+", "-", "*", "/"): # If there are math operators
            self.__match(self.current_token.value)
            self.__operand() # Link to more operands

    # Parse base units of data (variables, raw numbers, raw text strings)
    def __operand(self):
        if self.current_token is None:
            self.__error("Expected operand")
        if self.current_token.type == "Identifier":
            # If operand is a variable, call identifierExists() to verify it is defined
            if not self.identifierExists(self.current_token.value):
                self.__error(f"Undeclared variable '{self.current_token.value}'")
            self.__match(expected_type="Identifier")
        elif self.current_token.type in ("NumericLiteral", "StringLiteral"):
            self.__match(expected_type=self.current_token.type)
        else:
            self.__error(f"Invalid operand '{self.current_token.value}'")


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "welcome.scl"
    parser = Parser(input_file)
    parser.begin()

    with open("ParserOutput.txt", "w") as f:
        f.write("\n".join(parser.output_log) + "\n")