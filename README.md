# Wordle solver

## Status

This script has a few different modes:

* It can play Wordle on its own and solve it
* It can help you play Wordle (either a game that it runs for you, or assisting an external game you're playing on a web browser). In this mode, it will only give you as much help as you ask for - if you want to ask the solver for the best guess to try next, it can give you that. But if all you want to know is how many possible solutions are left, or what the most common remaining letters are, it can give you just that info without revealing any more.
* Benchmarking & A/B testing modes, for testing the solver performance

The solver does a pretty good job, but it's far from perfect - see TODO.md for some of the bigger areas of improvement, plus there are plenty of TODO/FIXME comments in the code.

## How does it work?

For the first guess, score words based on the most common letters in the list of possible solutions - 2 points if the letter is in the same position in a given solution and is the first occurence of this letter in the guess; 1 point if it's in a different position, or the same position but it's not the first occurence in a guess.

For next guesses while there are still relatively many possible solutions left, find which possible guess will best narrow down the remaining solutions.
This has an O(n^3) complexity, so when there are still many possible solutions remaining, we prune the search space.
The main pruning is the list of possible guesses to check, which we prune based on which use the most common letters among remaining solutions.
When the search space is very large, we also prune the list of possible solutions to check these guesses against.

When there are relatively few possible solutions left, search recursively for which guess will take the fewest remaining guesses to solve.

## FAQ

#### Doesn't this take the fun out of Wordle?

I still enjoy playing Wordle the old-fashioned way!
My goal here is to have fun writing a solver, not to write something that will replace playing Wordle. 
The solver's advantages are that it has a perfect vocabulary, and can try millions of combos of remaining words, neither of which I could do.

When playing Wordle, I often find myself tediously typing out every possible combination of known green & yellow letters. This also has an option to do this for you (command "!combos")

#### Is it "cheating" to have the solver know the full Wordle solution list?

I mean, any solver is already "cheating" :wink:

But yeah, I kind of consider this cheating.
My ideal goal is to have this solver have the same information a normal player (who didn't look at the source code) would have.
Originally I was thinking this meant not using the official Wordle list whatsoever, and using a different standard word list such as the English Open Word List - but then I realized this could lead to situations where it might try to guess an invalid word.
So I pretty much had to at least use the list of valid words - though not necessarily knowing the list of possible solutions.

However, there's still a problem with only using the full valid words list: it's slow.
This solver is much faster if it has fewer possible solutions it needs to look for.
So in the end, I made it aware of the solutions list.
But I left an option to run the original solution-list-agnostic idea, using the `--agnostic` argument.
I would like to revisit which is the default behavior again in the future.

#### Why do green letters appear yellow, and yellow letters appear grey?

This seems to be a problem with the default Windows Powershell terminal colors.
If using Windows, using a different terminal such as cmd or WSL should give you the correct colors.
