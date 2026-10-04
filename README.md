# This is Alex Rickman
She gave us the sample file CPL.scanner.py
This file had three problems:
1. Convert Function was missing
2. MegaDict Loop was broken
3. Commented out "Description:" -> [EOS] instead of "/\*" -> "\*/"

I have corrected these errors and renamed the file Tokenizer.py.
There is a section in the code for names of the people contributing, and I have left that blank for now.
I added the Convert function by viewing it in the Scanner explanation video.

Feel free to clear this after the first deliverable since it would no longer be necessary .

# Amelia Dodson
1. resolved the TODO on Token.py by removing '.' from specialSymbols (see my comment block for justification)
2. if, else, etc to keywords (they were being categorized as identifiers)
3. Removed hardcoded sorting of "," and "=" in categorized_token()
4. Added elif statement in categorize_token() for categorizing specialSymbols