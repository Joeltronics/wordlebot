# Wordle solver

## Status

So far, only the game itself, and a count/list of possible remaining guesses is implemented - there's no actual solving yet.

## FAQ

### Why not use the actual list of possible Wordle solutions?

Wordle actually has a separate, smaller list of words that can be selected as solutions.
This checker just uses a single list of all valid words.

This was an intentional choice - using the list of valid solutions felt too much like cheating.
Yes, I realize the irony that this is for a solver. 
But I wanted the solver to have the same information a regular player (who didn't look at the source code) would have.

I didn't want to use the actual Wordle list at all, but that could lead to situations where it might try to guess an ininvalid word, so unfortunately using the official list was necessary.

### Why do yellow letters appear grey?

This seems to be a problem with the default Windows Powershell colors.
Using cmd or WSL should give you the correct colors.
