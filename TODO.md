# Wordle solver improvements

This is just something I work on for fun when I feel like it, so I don't expect to ever get to all of these. But things I may want to work on in the future:

## General stuff

* Change the default solver behavior to agnostic
* When agnostic, factor in how common words are, weight more common words higher
* More assist options - e.g. "I want to cover these letters with my next guess, what are the best words that cover the most of these?"
* In play & assist modes, have solve command print more than 1 option, with their scores
* Solver for multi-Wordle games like Dordle/Quardle/Octordle/Sedordle, or Squardle

## Algorithm stuff

#### Combining heuristic and recursive algorithms

The recursive & heuristic algorithms don't need to be mutually exclusive, as they are right now.
For example, we could search 1 or 2 levels recursively, and then use heuristics on the next level after that.
I suspect this would work quite well, and I would like to explore this in the future.

Steps:

1. Determine the average mapping of number of solutions remaining to number of guesses needed to solve
2. Have the heuristic algorithm return this number instead
3. Now the recursive and heuristic algorithms are measuring the same units, so they can be combined

#### Improving heuristic (non-recursive) algorithm

Some of these may be moot after combining algorithms, but some possible improvements anyway:

* Optimize algorithm parameters
  * There are various optimization parameters in the SolverParams dataclass, which can be tweaked to make different tradeoffs
  * So far, these have been chosen based on what seems to make sense, not on actual results
  * There's a benchmarking/A-B testing mode that could be used to fine tune these parameters for best results, but so far I haven't really done this
* Improve exiting loop early
  * We exit the loop early after finding a "perfect" guess (i.e. one that is guaranteed to limit to only 1 guess left), because there's no point in keeping trying other guesses if they can't possibly due any better. However, in order to be perfect, it has to be a possible solution. If we find a non-solution guess that would otherwise be perfect, the only guess that could beat it is a perfect solution. That means, after finding such a guess, we could reduce the search space to only possible solutions.
  * This improvement wouldn't affect the solving ability, but would improve speed in some cases

#### Recursion depth limiting

The recursive algorithm has 2 different ways of calculating score: average, or minimax.
Average is better for optimizing for solving in the fewest guesses, while minimax is better at ensuring a puzzle can be solved within 6 guesses (though averaging is good enough that this isn't really a problem).

Overall, averaging gives very slightly better results.
However, minimax can trivially limit the recursion depth (and thus the processing time), as there's no point ever searching deeper than your current best guess.
Averaging cannot limit recursion depth as easily, so it can be extremely slow in some cases.
There are still ways the depth could be limited with averaging, but these aren't currently implemented.

Currently, the solver uses averaging at the outermost level, and switches to minimax at deeper recursion depths (because minimax can easily limit recursive depth).
However, this has a big flaw - it treats minimax and average numbers as equivalent, and sums them together.
But they're not equivalent.
This isn't as bad as it might sound - it still performs better than just minimax. But it's not great either.

#### Pruning

We prune possible solutions in order to limit the serach space.

* Improve solution pruning
  * For heuristic searching, when we need to prune very heavily, then in addition to pruning guesses to try, we also prune solutions to check against. This pruning is very basic - the goal is to remove solutions that are most similar to existing solutions, which is currently achieved by just sorting the list and taking every N results. This is an _okay_ way of accomplishing this goal, but it could be improved. The catch is it needs to be improved without affecting perfromance too much, because the whole point of this pruning is to improve performance.
* Improve recursive pruning:
  * Be smarter about number of solutions to try
  * Improve mix of solutions vs non-solutions
  * Improve performance here, since this happens on every single recursive iteration

## Performance

#### Lookup table

Apparently a lookup table works well for calculating guess results. There's a basic lookup table implemented, but currently its performance is only slightly better (after generating the lookup table the first time, which is very slow), and it's not well tested, so it's disabled by default.

* Behavior:
  * Make it work with agnostic, or different word lists
  * Make it work with forced words (i.e. invalid words which don't have an ID)
* Vectorize it more with numpy - i.e. anywhere there's a for loop or list comprehension in the MatchingLookupTable class, it could probably be a numpy operation instead
* Use numpy types instead of standard Python int for stuff like Word.id and WordResult.as_int()
* For Word class, only store ID:
  * Option 1: change Solver class to only store ID instead of full Word type, and make matching accept lists of IDs
  * Option 2: make Word type itself only store ID
  * Either way, this would really hurt non-LUT performance, so don't do this until LUT is standard
* Similarly, for WordResult class, only store ID instead of tuple

#### Other performance stuff

* Use multiprocessing
* Various performance optimizations - the code isn't really that optimized, there could probably be some more gains here
