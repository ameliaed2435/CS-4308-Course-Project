"""
CS4308: SCL Subset Interpreter
Authors: Michael Constantine, Amelia Dodson, Alex Rickman, Jarren Shaw

Main entry point. Interpreter pipeline is as follows:
1. Lexical Analysis through Tokenizer.py
2. Syntax & Semantic Analysis through parser.py
3. Execution through Executer.py
"""

import os
import sys

from Executer import Executer
from parser import Parser
from Tokenizer import scan_file, write_json

def run_interpreter(file_name, trace = False, show_tokens = False):
    """Scans, parses, and executes an SCL file."""

    if not os.path.isfile(file_name):
        print("Error: file '%s' not found." % file_name)
        return 2

    stem = os.path.splitext(os.path.basename(file_name))[0]
    tokens_path = stem + "_tokens.json"
    parser_output_path = stem + "_parse_output.txt"
    executer_output_path = stem + "_execute_output.txt"

    # Scanning
    print("Scanning file '%s'..." % file_name)

    try:
        tokens = scan_file(file_name)
    except OSError as error:
        print("Error reading '%s': %s" % (file_name, error))
        return 2

    write_json(tokens, tokens_path)
    print("Scanned %d tokens. Saved token list to %s" % (len(tokens), tokens_path))
    if show_tokens:
        for token in tokens:
            print("Token: %s (line %s)" % (token.getData(), token.line))



    # Parsing
    print("Parsing...")

    parser = Parser(tokens_path, output_path=parser_output_path, trace=trace)

    if not parser.begin():
        print("Error parsing file.")
        return 1



    # Execution
    print("Executing...")

    executer = Executer(parser.ast_program, memory = {}, output_path= executer_output_path)

    if not executer.execute():
        return 1

    return 0


def main(arguments):
    trace = "--trace" in arguments
    show_tokens = "--show-tokens" in arguments
    file_arguments = [arg for arg in arguments if not arg.startswith("--")]

    if file_arguments:
        file_name = file_arguments[0]
    else:
        file_name = input("Enter path to SCL file: ").strip().strip('"')

    if not file_name:
        print("Usage: python main.py <source_file.scl> [--tokens] [--trace]")
        return 2

    return run_interpreter(file_name, trace = trace, show_tokens = show_tokens)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))