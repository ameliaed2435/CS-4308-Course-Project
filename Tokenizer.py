from Token import *
import json
import sys
import re

# Group members (Amelia Dodson, Michael Constantine, Jarren Shaw, Alex Rickman)

def tokenize_line(line):
    tokens = []
    current_token = ""
    in_string = False
    in_hanging_comment = False

    # Combine all the regular expressions
    regex = r'("[^"]*"|\'[^\']*\')|(/\*.*?\*/)|(//.*)|(\b(import|implementations|function|main|is|variables|define|of|begin|display|set|input|if|then|else|endif|not|greater|or|equal|return)\b)|([a-zA-Z_]\w*)|(\d+(\.\d+)?)|(:|\.|:|,|/|=|>|\*|\)|\()'

    matches = re.finditer(regex, line)

    for match in matches:
        token = match.group(0)

        if token.strip() == "":
            continue  # Ignore whitespace tokens

        if '//' in token:
            # If '//' is found, truncate the token to exclude everything after '//'
            token = token.split('//')[0].strip()

        tokens.append(token)

    return tokens

def Convert(a): #This function was removed in the CPL_scanner file, even though it also would not work without is
    it = iter(a)
    res_dct = dict(zip(it, it))
    return res_dct


def filter_file(File_name):
    try:
        file = open(File_name, 'r')
    except:
        print("no such file or directory: ", File_name)
        exit(2)

    lineList = []

    in_hanging_comment = False  # Flag to track if we're inside a hanging comment

    for line in file:
        #if 'description' in line:
        #    in_hanging_comment = True
        # For Scl, the description is in the /* */

        if in_hanging_comment:
            if '*/' in line:
                in_hanging_comment = False
            continue  # Skip lines within hanging comments
        else:
            if line.startswith("/*"):
                in_hanging_comment = True # This line was removed for the CPL_scanner
                continue  # Skip the comment line

            lineTokens = tokenize_line(line)

            # Remove empty tokens or tokens containing only whitespace
            lineTokens = [token for token in lineTokens if token.strip() != '']

            if lineTokens:
                lineList.append(lineTokens)

    return lineList

ident_counter = 3000
identifier_map = {}
# Function to categorize tokens
def categorize_token(token):
    global ident_counter

    if token in tokenList["keywords"]:
        return {"Type": "Keyword", "id": tokenList["keywords"][str(token)], "value": token}
    elif re.match(r'^[a-zA-Z_]\w*$', token):
        #Increment for each ID that is different than one already in the token list
        #Allows for each identifier to have a unique id
        if token in identifier_map:
            return {"Type": "Identifier", "id": identifier_map[token], "value": token}
        
        result = {"Type": "Identifier", "id": ident_counter, "value": token}
        identifier_map[token] = ident_counter
        ident_counter+=1
        return result
    elif re.match(r'^[0-9]+(\.[0-9]+)?$', token):
        return {"Type": "NumericLiteral", "id": 4000, "value": token}
    elif token.startswith('"') or token.startswith("'"):
        # Remove leading and trailing double quotes, "\, and /" from string literals
        cleaned_token = token[1:-1].replace('\\"', '"').replace("\\'", "'").replace("\\/", "/")
        return {"Type": "StringLiteral", "id": 5000, "value": cleaned_token}
    elif token in [",","="]:
        return {"Type": "Operator", "id": 400, "value": token}
    elif token in tokenList["operators"]:
        return {"Type": "Operator", "id": tokenList["operators"][str(token)], "value": token}
    elif token == ":":
        return {"Type": "VariableDeclaration", "id": 6002, "value": token}
    # Add more conditions for other types of tokens

    # If none of the above conditions match, treat it as an "UNKNOWN" token
    return {"Type": "UNKNOWN", "id": 1200, "value": token}

if __name__ == '__main__':
    sysArgv = sys.argv

    ItemList = filter_file(sysArgv[1])
    #ItemList = filter_file("welcome.scl") # For Development Purposes
    finalTokenList = []

    megaDict = {}

    for lineTokens in ItemList:
        for token in lineTokens:
            categorized_token = categorize_token(token)
            newToken = Token(categorized_token["Type"], categorized_token["id"], categorized_token["value"])
            finalTokenList.append(newToken)
            print("New Token created: ", newToken.getData())

        newToken = Token('EndOfStatement', 1000, 'EOS')
        finalTokenList.append(newToken)
        print("New Token created: ", newToken.getData())

    # Converting token objects into a dictionary

    loopCounter = 0
    for Token in finalTokenList:
        tokenStr = "Token_" + str(loopCounter)
    
        # Create a dictionary for the token with relevant information
        tokenData = Token.getData()
        tokenDict = {
            "Type": tokenData[0],
            "id": tokenData[1],
            "value": tokenData[2]
        }
    
        # Add the token dictionary to the megaDict
        megaDict[tokenStr] = tokenDict
    
        loopCounter += 1

    loopCounter = 0
    for Token in finalTokenList:
        tokenData = Token.getData()
        lst = ['Type', tokenData[0], 'id', tokenData[1], 'value', tokenData[2]]
        newList = Convert(lst)
        
        tokenStr = "Token_" + str(loopCounter)

        megaDict[tokenStr].update(newList)
        loopCounter += 1 #This line was also removed from the CPL_scanner file for some reason ㄟ( ▔, ▔ )ㄏ
        
    #Creating JSON object of the mega dictionary and writing to new output JSON file
    json_object = json.dumps(megaDict, indent=4)
    with open('OutputTokens.json', 'w') as f:
        f.write(json_object)
