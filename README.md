# Wordle solver

## Status

So far, there's a basic solver. It does a pretty good job, but it's far from perfect - there are lots of TODO comments in the code where it could be improved.

Right now it will only play its own internal game, there's no way to use this to solve along with a real game of Wordle (at least, not yet)

## How does it work?

For the first guess, choose whichever word uses the most common letters in the list of possible solutions.

For all subsequent guesses, use whichever guess will best narrow down the remaining possible solutions.
"Best" is difficult to quanitify here - there are a few different ways this could be chosen, most obviously worst-case (minimax), lowest average, or lowest mean-squared.
Currently it uses a weighted score of minimax & average, weighted heavily toward minimax.

This has an O(n^3) complexity, so when there are still many possible solutions remaining, we prune the list of possible guesses, based on which use the most common remaining letters.

## How could it be improved?

The actual variable we want to optimize is which will solve with the fewest guesses.
Solving for which guess will best narrow down the remaining possible solutions is a pretty good heuristic, but it's still not perfect.
However, the current algorithm is already slow enough; making the algorithm look ahead to future guesses would significantly increase the complexity.
But it would be worth exploring this when there are few remaining.

This hasn't really been benchmarked - most elements of the algorithm were just chosen based on intuition, not actual data.
It would be good to profile this, and optimize the various tradeoffs for what has the actual best results.

Right now we only prune guesses; I suspect that when we are not yet close to a solution, there could be great performance improvements with little drawback by only comparing against a limited subset of the possible solutions as well.
And since we're only reducing one of the 3 numbers that multiply up to that O(n^3) complexity, the existing pruning doesn't improve performance as much as intended, either (i.e. ideally every guess should take around the same amount of time regardless of total solution space size).

The guess pruning algorithm itself could also stand to be improved - right now it just looks for most common unsolved letters in words, but doesn't account for letter position, yellow letters, or multiple of the same letter in the word.

The code isn't really optimized, and there could be some potential performance gains there.
This is just a quick project from a few evenings of work, so the code quality is definitely not perfect either.

## FAQ

### Doesn't this take the fun out of Wordle?

My goal is to have fun writing a solver, not to write something that will replace playing Wordle for me.
I still enjoy playing Wordle the old fashined way.
No, writing a solver hasn't ruined it for me - the solver's advantages are that it has a perfect vocabulary, and can try every possible combo of remaining words, neither of which a human could do.

### Is it "cheating" to have the solver know the full Wordle solution list?

I mean, any solver is already "cheating" :wink:

But yeah, I kind of consider this cheating.
My ideal goal is to have this solver have the same information a normal player would have (at least, one who didn't look at the source code).
Originally I was thinking this meant not using the official Wordle list whatsoever, and using a different standard word list such as the English Open Word List - but then I realized this could lead to situations where it might try to guess an invalid word.
So I pretty much had to at least use the list of valid words - though not necessarily knowing the list of possible solutions.

However, there's still a problem with only using the full valid words list: it's slow.
This solver is much faster if it has fewer possible solutions it needs to look for.
So in the end, I made it aware of the solutions list.
But I left an option to run the original solution-list-agnostic idea, using the `--agnostic` argument.
I may revisit the default behavior in the future.

### Why do green letters appear yellow, and yellow letters appear grey?

This seems to be a problem with the default Windows Powershell colors.
Using cmd or WSL should give you the correct colors.
