# Wordle solver

## Status

So far, there's a basic solver, but it's far from perfect

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
