# Wordle solver

## Status

So far, there's a basic solver. It does a pretty good job, but it's far from perfect - there are lots of TODO comments in the code where it could be improved.

Right now it will only play its own internal game; there's no way (yet) to use this to solve along with a real game of Wordle.
Though if you've already played a game of Wordle and want to see what the solver would have picked, you can run it with `-s <solution>` to have it play the same game.

## How does it work?

For the first guess, choose whichever word uses the most common letters in the list of possible solutions.

For next guesses while there are still lots of solutions left, use the heuristic of which guess will best narrow down the remaining possible solutions.
"Best" is difficult to quanitify here - there are a few different ways this could be chosen, such as worst-case (minimax), lowest average, or lowest mean-squared.
Currently it uses a weighted score of minimax & average, weighted heavily toward minimax.

This has an O(n^3) complexity, so when there are still many possible solutions remaining, we prune the search space.
The main pruning is the list of possible guesses, based on which use the most common remaining letters.
When the search space is very large, we also prune the list of possible solutions to check these guesses against.

When there are fewer guesses than a certain limit, search recursively for which guess will take the fewest remaining guesses to solve (using minimax).

## How could it be improved?

#### Recursive algorithm improvements

The recursive algorithm only uses minimax at the moment.
This is because it's very easy to limit the recursion depth - there's no point ever searching deeper than your current best.
However, it would be worth exploring better metrics such as mean or least-squares (there are still ways of limiting depth with these, they're just not as simple). 
Minimax should be better at optimizing for win percentage, but not for trying to solve in the fewest guesses.

Similarly, recursive & heuristic don't need to be mutually exclusive, as they are right now.
For example, we could search 1 or 2 levels recursively, and then use heuristics on the next level after that.
I suspect this would work quite well, and I would like to explore this in the future.

#### Non-recursive algorithm improvements

We exit the loop early after finding a "perfect" guess - no point in keeping searching if it can't be beaten.
However, in order to be perfect, it has to be a possible solution.
If we find a non-solution but otherwise perfect guess, the only guess that could beat it is a perfect solution.
That means, after finding such a guess, we could reduce the search space to only possible solutions.

#### Pruning improvements

The guess pruning algorithm itself could stand to be improved - right now it just looks for most common unsolved letters
in words, but doesn't account for letter position, yellow letters, or multiple of the same letter in the word.
The first guess is chosen using this same algorithm, so it would also benefit from any improvements here.

The pruning of solutions to check against is also very basic - the goal is to remove solutions that are most similar to
existing solutions, which is currently achieved by just sorting the list and taking every N results.
This is an _okay_ way of accomplishing this goal, but it could definitely be improved.

#### Other misc improvements

The code isn't really optimized, and there could be some potential performance gains there.
This is just a quick project from a few evenings of work, so the code quality is definitely not perfect either.

There are various optimization parameters in the SolverParams dataclass, which can be tweaked to make different tradeoffs.
So far, these have been chosen based on what seems make sense, not on actual results.
There's a benchmarking/A-B testing mode that could be used to fine tune these parameters for best results, but so far I haven't done this.
It's still a bit early to optimize these parameters - it doesn't really make sense to fine tune them now if there are more algorithm changes still to come.

## FAQ

#### Doesn't this take the fun out of Wordle?

I still enjoy playing Wordle the old-fashioned way!
My goal here is to have fun writing a solver, not to write something that will replace playing Wordle. 
The solver's advantages are that it has a perfect vocabulary, and can try millions of combos of remaining words, neither of which I could do.

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
I may revisit which is the default behavior again in the future.

Running `--benchmark` under the current default behavior (`-l 6`, which limits the search space to 1,000,000 combos per guess):
* Without `--agnostic`, solves 100% (out of 50 puzzles), with an average of 3.46 guesses, worst case 5, average time 10.8 seconds per puzzle on my laptop
* With `--agnostic`, still solves 100%, but the average goes up to 4.20 guesses, the worst case 6, and the average time 12.9 seconds (mostly due to needing more average guesses)

#### Why do green letters appear yellow, and yellow letters appear grey?

This seems to be a problem with the default Windows Powershell colors.
If using Windows, using cmd or WSL should give you the correct colors.
