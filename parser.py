# Parser program for the scanner

from lexier import Lexier
from lexier import Token

#Main Parser Class
class Parser:
    lexier = Lexier()
    token = Token()
    nextToken = None

    #Constructor
    def fileTime(self, filePath):
        file = open(filePath)
        for line in file:
            parser.compile(line)

    #Compile function
    def compile(self, input):
        self.lexier.analyzer(input)
        self.getNextToken()
        self.keywords()

    def keywords(self):
        print("Started parsing Keywords")
        self.identifier()
        while(self.nextToken.TYPE == self.lexier.ADD_OP or self.nextToken.TYPE == self.lexier.SUB_OP):
            self.getNextToken()
            self.identifier()
        print("End parsing Keywords")

    def identifier(self):
        print("Started parsing Terms")
        self.operators()
        while(self.nextToken.TYPE == self.lexier.MULT_OP or self.nextToken.TYPE == self.lexier.DIV_OP):
            self.getNextToken()
            self.operators()
        print("End parsing Terms")

    def operators(self):
        print("Started parsing operators")
        if(self.nextToken.TYPE == self.lexier.IDENT or self.nextToken.TYPE == self.lexier.INT_LIT):
            self.getNextToken()
        else:
            if(self.nextToken.TYPE == self.lexier.LEFT_PAREN):
                self.getNextToken()
                self.keywords()
                if(self.nextToken.TYPE == self.lexier.RIGHT_PAREN):
                    self.getNextToken()
                else:
                    self.error()
        print("End parsing operators")

        # Get next token
    def getNextToken(self):
        self.nextToken = self.lexier.getNext()


    # Function to print error
    def error(self):
        print("Syntax error")



parser = Parser()

txtFile = input("What is the file name? (Please do NOT enclose in quotation marks)\n")

if txtFile == "":
    print("File found, but is empty")
else:
    parser.fileTime(txtFile)
