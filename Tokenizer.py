from Token import Token, tokenList
import json
import sys
import re

# One regular expression, tried left to right at every position of the file.
# The order matters: strings come first so that "//" inside a string is not
# mistaken for a comment, and the keyword/identifier pattern is one generic
# "word" pattern that is looked up in the keyword table afterwards.
TOKEN_REGEX = re.compile(
    r'(?P<string>"[^"\n]*"|\'[^\'\n]*\')'      # "text" or 'text'
    r'|(?P<block_comment>/\*.*?\*/)'           # /* ... */ (may span lines)
    r'|(?P<bad_comment>/\*)'                   # /* with no closing */
    r'|(?P<line_comment>//[^\n]*)'             # // to end of line
    r'|(?P<word>[A-Za-z_]\w*)'                 # keyword or identifier
    r'|(?P<number>\d+(?:\.\d+)?)'              # integer or decimal number
    r'|(?P<symbol>>=|<=|[:.,/=><*()+\-^])'     # operators and special symbols
    r'|(?P<other>\S)',                         # anything else -> UNKNOWN
    re.DOTALL)

ident_counter = 3000
identifier_map = {}

# Function to categorize tokens
def categorize_token(token):
    global ident_counter

    if token in tokenList["keywords"]:
        return {"Type": "Keyword", "id": tokenList["keywords"][str(token)], "value": token}
    elif re.match(r'^[a-zA-Z_]\w*$', token):
        # Each different identifier gets its own id, starting at 3000;
        # the same identifier always gets the same id.
        if token in identifier_map:
            return {"Type": "Identifier", "id": identifier_map[token], "value": token}

        result = {"Type": "Identifier", "id": ident_counter, "value": token}
        identifier_map[token] = ident_counter
        ident_counter += 1
        return result
    elif re.match(r'^[0-9]+(\.[0-9]+)?$', token):
        return {"Type": "NumericLiteral", "id": 4000, "value": token}
    elif token.startswith('"') or token.startswith("'"):
        # Remove the surrounding quotes from string literals
        cleaned_token = token[1:-1].replace('\\"', '"').replace("\\'", "'").replace("\\/", "/")
        return {"Type": "StringLiteral", "id": 5000, "value": cleaned_token}
    elif token in tokenList["operators"]:
        return {"Type": "Operator", "id": tokenList["operators"][str(token)], "value": token}
    elif token == ":":
        return {"Type": "VariableDeclaration", "id": 6002, "value": token}
    elif token in tokenList["specialSymbols"]:
        return {"Type": "SpecialSymbol", "id": tokenList["specialSymbols"][str(token)], "value": token}

    # If none of the above conditions match, treat it as an "UNKNOWN" token
    return {"Type": "UNKNOWN", "id": 1200, "value": token}


def scan_file(file_name):
    """Scan an SCL source file and return a list of Token objects.

    Comments and white space produce no tokens. An EndOfStatement (EOS) token
    is added after the last token of every source line that contains tokens.
    Raises FileNotFoundError if the file cannot be opened."""
    global ident_counter
    ident_counter = 3000          # start fresh for every file that is scanned
    identifier_map.clear()

    with open(file_name, 'r') as source:
        text = source.read()

    tokens = []
    line = 1              # line number of the match being looked at
    counted_up_to = 0     # position in text up to which newlines are counted
    last_token_line = None

    for match in TOKEN_REGEX.finditer(text):
        # keep the line number up to date by counting the newlines we passed
        line += text.count("\n", counted_up_to, match.start())
        counted_up_to = match.start()

        kind = match.lastgroup
        lexeme = match.group(0)

        if kind in ("block_comment", "line_comment"):
            continue                       # comments are ignored

        # a new source line begins: close the previous line with an EOS token
        if last_token_line is not None and line != last_token_line:
            tokens.append(Token('EndOfStatement', 1000, 'EOS', last_token_line))

        if kind in ("other", "bad_comment"):
            info = {"Type": "UNKNOWN", "id": 1200, "value": lexeme}
        else:
            info = categorize_token(lexeme)

        tokens.append(Token(info["Type"], info["id"], info["value"], line))
        last_token_line = line

    if last_token_line is not None:
        tokens.append(Token('EndOfStatement', 1000, 'EOS', last_token_line))

    return tokens


def write_json(tokens, json_name):
    """Write the tokens to a JSON file as Token_0, Token_1, ..."""
    mega_dict = {}
    for number, token in enumerate(tokens):
        mega_dict["Token_" + str(number)] = token.toDict()
    with open(json_name, 'w') as out:
        out.write(json.dumps(mega_dict, indent=4))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("usage: python Tokenizer.py <source file.scl>")
        sys.exit(1)

    try:
        token_list = scan_file(sys.argv[1])
    except FileNotFoundError:
        print("no such file or directory: ", sys.argv[1])
        sys.exit(2)

    for new_token in token_list:
        print("New Token created: ", new_token.getData())

    write_json(token_list, 'OutputTokens.json')