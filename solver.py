#!/usr/bin/env python3

import collections
from dataclasses import dataclass
from enum import Enum, unique
from math import sqrt
from typing import Tuple, Iterable, Optional

from game_types import *


@unique
class SolverVerbosity(Enum):
	silent = 0
	regular = 1
	debug = 2


@dataclass(frozen=True)
class SolverParams:

	# "Best solution" score weights

	score_weight_mean = 1
	score_weight_mean_squared = 0
	score_weight_max = 10
	score_penalty_non_solution = 5

	# Pruning

	# Ratio of possible guesses to target - if under, then prune solutions too
	prune_target_guess_ratio = 0.1

	# Pruning possible solutions to check against
	# Base divisor is number of solutions remaining divided by this
	prune_divide_possible_num_solutions_divisor = 4
	# Always take at least 1/4 of possible
	prune_divide_possible_max = 4

	# Pruning possible solutions to check how many remain
	# Base divisor is number of solutions remaining divided by this
	prune_divide_num_remaining_num_solutions_divisor = 8
	# Always take at least 1/4 of possible
	prune_divide_num_remaining_max = 4


def clip(value, range):
	return min(
		range[1],
		max(
			value,
			range[0]
		)
	)


class Solver:
	def __init__(
			self,
			valid_solutions: Iterable[str],
			allowed_words: Iterable[str],
			complexity_limit: int,
			params=SolverParams(),
			verbosity=SolverVerbosity.regular):

		self.possible_solutions = valid_solutions
		self.allowed_words = allowed_words
		self.complexity_limit = complexity_limit
		self.params = params
		self.verbosity = verbosity

		self.guesses = []
		self.solved_letters = [None] * 5

	def print(self, *args, **kwargs):
		if self.verbosity.value > SolverVerbosity.silent.value:
			print(*args, **kwargs)

	def dprint(self, *args, **kwargs):
		if self.verbosity.value >= SolverVerbosity.debug.value:
			print(*args, **kwargs)

	def get_num_possible_solutions(self) -> int:
		return len(self.possible_solutions)

	def get_possible_solitions(self) -> List[str]:
		return self.possible_solutions

	def _is_valid_for_guess(self, word: str, guess: Tuple[str, Iterable[CharStatus]]) -> bool:
		guess_word, guess_char_statuses = guess
		status_if_this_is_solution = get_character_statuses(guess=guess_word, solution=word)
		return status_if_this_is_solution == guess_char_statuses

	def _is_valid(self, word: str) -> bool:
		return all([
			self._is_valid_for_guess(word, guess) for guess in self.guesses
		])

	def add_guess(self, guess_word: str, character_statuses: Iterable[CharStatus]):

		this_guess = (guess_word, character_statuses)
		self.guesses.append(this_guess)

		self.possible_solutions = {word for word in self.possible_solutions if self._is_valid_for_guess(word, this_guess)}
		assert len(self.possible_solutions) > 0

		for idx in range(5):
			if character_statuses[idx] == CharStatus.correct:
				self.solved_letters[idx] = guess_word[idx]

	def get_unsolved_letters_counter(self):

		def _remove_solved_letters(word):
			return ''.join([
				letter if (solved_letter is None or letter != solved_letter) else ''
				for letter, solved_letter in zip(word, self.solved_letters)
			])

		words_solved_chars_removed = [_remove_solved_letters(word) for word in self.possible_solutions]
		all_chars = ''.join(words_solved_chars_removed)
		counter = collections.Counter(all_chars)

		return counter

	def get_most_common_unsolved_letters(self):
		return self.get_unsolved_letters_counter().most_common()

	def _num_solutions_remaining(self, guess: str, possible_solution: str, solutions: Iterable[str]) -> int:
		"""
		If we guess this word, and see this result, figure out how many possible words could be remaining
		"""
		# TODO: this is a bottleneck, see if it can be optimized
		character_status = get_character_statuses(guess, possible_solution)
		# TODO: we only need the list length; it may be faster just to instead use:
		#new_possible_solutions = sum([self._is_valid_for_guess(word, (guess, character_status)) for word in solutions])
		new_possible_solutions = [word for word in solutions if self._is_valid_for_guess(word, (guess, character_status))]
		return len(new_possible_solutions)

	def _prune_and_sort_guesses(self, guesses: Iterable[str], max_num: Optional[int]) -> List[str]:

		# Prune based on occurrence of most common unsolved letters

		# TODO: this doesn't take letter position (nor yellow letters) into account

		counter = self.get_unsolved_letters_counter()
		
		def _score(word):
			return sum([counter[unique_letter] for unique_letter in set(word)])

		# Start with sorted list
		# Otherwise behavior will be nondeterministic in cases of tied letter score (i.e. 2 words that are anagrams)
		guesses = sorted(list(guesses))
		guesses.sort(key=_score, reverse=True)

		# TODO: could it be an overall improvement to randomly mix in a few with less common letters too?
		# i.e. instead of a hard cutoff at max_num, make it a gradual "taper off" where we start picking fewer and fewer words from later in the list

		if max_num is not None:
			guesses = guesses[:max_num]

		return guesses

	def _determine_prune_counts(self, max_num_matches: Optional[int]) -> Tuple[int, int, int]:
		"""
		Determine how many guesses & solutions to prune

		:return: (number of guesses, divisor for solutions to check possible, divisor for solutions to check remaining)
		"""

		num_allowed_words = len(self.allowed_words)
		num_possible_solutions = len(self.possible_solutions)
		total_num_matches = num_allowed_words * num_possible_solutions * num_possible_solutions

		if max_num_matches is None:
			return num_allowed_words, 1, 1

		# First, figure out how many solutions to prune

		if not self.params.prune_target_guess_ratio:
			divide_solutions_to_check_possible = 1
			divide_solutions_to_check_num_remaining = 1

		else:
			"""
			If there are very few possible solutions left, bias toward trimming guesses instead of solutions
			Especially prioritize this for num_remaining check which is extra sensitive to low numbers
	
			max_divide_possible (default max 4, divisor 4):
			  >= 16 solutions left: worst case, check 1/4 of solutions
			  12-15 solutions left: worst case, check 1/3 of solutions
			  8-11 solutions left: worst case, check 1/2 of solutions
			  <= 7 solutions left: always check all solutions
	
			max_divide_num_remaining (default max 4, divisor 8):
			  >= 32 solutions left: worst case, check 1/4 of solutions
			  24-31 solutions left: worst case, check 1/3 of solutions
			  16-23 solutions left: worst case, check 1/2 of solutions
			  <= 15 solutions left: always check all solutions
			"""
			max_divide_possible = clip(
				num_possible_solutions // self.params.prune_divide_possible_num_solutions_divisor,
				(1, self.params.prune_divide_possible_max)
			)
			max_divide_num_remaining = clip(
				num_possible_solutions // self.params.prune_divide_num_remaining_num_solutions_divisor,
				(1, self.params.prune_divide_num_remaining_max)
			)

			ideal_total_division = self.params.prune_target_guess_ratio * total_num_matches / max_num_matches
			ideal_division = int(round(sqrt(ideal_total_division)))

			# TODO: these two don't have to be equal (even beyond having separate maximums)
			# e.g. if ideal_total_division is 6, could do 3 & 2, rather than the current logic of 2 & 2
			divide_solutions_to_check_possible = max(min(ideal_division, max_divide_possible), 1)
			divide_solutions_to_check_num_remaining = max(min(ideal_division, max_divide_num_remaining), 1)

		# Now figure out how many guesses to try to be below total matches target

		num_solutions_to_check_possible = num_possible_solutions // divide_solutions_to_check_possible
		num_solutions_to_check_num_remaining = num_possible_solutions // divide_solutions_to_check_num_remaining

		num_guesses_to_try = max_num_matches // (
					num_solutions_to_check_possible * num_solutions_to_check_num_remaining) if (
					max_num_matches is not None) else None
		num_guesses_to_try = max(1, num_guesses_to_try)

		return num_guesses_to_try, divide_solutions_to_check_possible, divide_solutions_to_check_num_remaining

	def _log_pruning(self, num_guesses_to_try, divide_solutions_to_check_possible, divide_solutions_to_check_num_remaining) -> None:

		num_possible_guesses = len(self.allowed_words)
		num_possible_solutions = len(self.possible_solutions)

		total_num_matches = len(self.allowed_words) * num_possible_solutions * num_possible_solutions
		num_solutions_to_check_possible = num_possible_solutions // divide_solutions_to_check_possible
		num_solutions_to_check_num_remaining = num_possible_solutions // divide_solutions_to_check_num_remaining

		num_matches_to_check = num_guesses_to_try * num_solutions_to_check_possible * num_solutions_to_check_num_remaining

		if num_guesses_to_try < num_possible_guesses and (
				divide_solutions_to_check_possible > 1 or divide_solutions_to_check_num_remaining > 1
		):
			self.print(
				f'Checking {num_guesses_to_try:,}/{num_possible_guesses:,} guesses' +
				f' ({num_guesses_to_try / len(self.allowed_words) * 100.0:.1f}%)' +
				f' against {num_solutions_to_check_possible:,}/{num_possible_solutions:,} possible' +
				f' and {num_solutions_to_check_num_remaining:,}/{num_possible_solutions:,} remaining' +
				f' ({num_matches_to_check:,}/{total_num_matches:,} =' +
				f' {num_matches_to_check / total_num_matches * 100.0:.3f}% total matches)...'
			)
		elif num_guesses_to_try < num_possible_guesses:
			self.print(
				f'Checking {num_guesses_to_try:,}/{num_possible_guesses:,} guesses' +
				f' ({num_guesses_to_try / len(self.allowed_words) * 100.0:.1f}%)' +
				f' against all {num_possible_solutions:,} solutions' +
				f' ({num_matches_to_check:,}/{total_num_matches:,} total matches)...'
			)
		else:
			self.print(
				f'Checking all {num_possible_guesses:,} words against all {num_possible_solutions:,} solutions' +
				f' ({total_num_matches:,} total matches)...'
			)


	def _brute_force_guess_for_fewest_remaining_words(self, max_num_matches: Optional[int] = None) -> str:
		"""
		"""

		"""
		The overall algorithm is O(n^3):
		  1. in _brute_force_guess_for_fewest_remaining_words_list(), loop over guesses
		  2. in _brute_force_guess_for_fewest_remaining_words_list(), loop over solutions_to_check_possible
		  3. in _num_solutions_remaining(), another loop over solutions_to_check_num_remaining
		"""

		# Figure out how much to prune

		if max_num_matches is None:
			num_guesses_to_try = len(self.possible_solutions)
			divide_solutions_to_check_possible = 1
			divide_solutions_to_check_num_remaining= 1
		else:
			num_guesses_to_try, divide_solutions_to_check_possible, divide_solutions_to_check_num_remaining = \
				self._determine_prune_counts(max_num_matches=max_num_matches)

		# Do the pruning

		guesses_to_try = list(self.allowed_words)
		guesses_to_try = self._prune_and_sort_guesses(
			guesses_to_try,
			num_guesses_to_try if len(guesses_to_try) > num_guesses_to_try else None,
		)

		"""
		For pruning the solutions to check possible/against, ideally we want to prune out solutions that are the most
		similar to other solutions in the list.
		
		Right now we accomplish this by taking every N from the sorted list, which works decently, though obviously it's
		biased toward the start of the word being similar, not the end
		
		TODO: smarter pruning than this
		"""
		solutions_sorted = sorted(list(self.possible_solutions))

		solutions_to_check_possible = solutions_sorted
		if divide_solutions_to_check_possible > 1:
			solutions_to_check_possible = solutions_to_check_possible[0::divide_solutions_to_check_possible]

		solutions_to_check_num_remaining = solutions_sorted
		if divide_solutions_to_check_num_remaining > 1:
			solutions_to_check_num_remaining = solutions_to_check_num_remaining[1::divide_solutions_to_check_num_remaining]

		# Log it

		self.print()
		self._log_pruning(num_guesses_to_try, divide_solutions_to_check_possible, divide_solutions_to_check_num_remaining)

		self.dprint('Initial best candidates: ' + ' '.join([guess.upper() for guess in (
			guesses_to_try[:5] if len(guesses_to_try) > 5 else guesses_to_try
		)]))

		# Process the pruned lists

		ret, score = self._brute_force_guess_for_fewest_remaining_words_from_lists(
			guesses=guesses_to_try,
			solutions_to_check_possible=solutions_to_check_possible,
			solutions_to_check_num_remaining=solutions_to_check_num_remaining)

		return ret


	def _brute_force_guess_for_fewest_remaining_words_from_lists(
			self,
			guesses: Iterable[str],
			solutions_to_check_possible: Iterable[str] = None,
			solutions_to_check_num_remaining: Iterable[str] = None,
			) -> Tuple[str, float]:

		if solutions_to_check_possible is None:
			solutions_to_check_possible = self.possible_solutions

		if solutions_to_check_num_remaining is None:
			solutions_to_check_num_remaining = self.possible_solutions

		solutions_to_check_possible_ratio = len(self.possible_solutions) / len(solutions_to_check_num_remaining)
		assert solutions_to_check_possible_ratio >= 1.0

		# Take every possible valid guess, and run it against every possible remaining valid word, figure
		lowest_average = None
		lowest_max = None
		best_guess = None
		lowest_score = None
		for guess_idx, guess in enumerate(guesses):

			# Slightly prioritize possible solutions
			is_possible_solution = guess in self.possible_solutions

			if (guess_idx + 1) % 200 == 0:
				self.dprint('%i/%i...' % (guess_idx+1, len(guesses)))

			max_words_remaining = None
			sum_words_remaining = 0
			sum_squared = 0
			for possible_solution in solutions_to_check_possible:
				words_remaining = self._num_solutions_remaining(guess, possible_solution, solutions=solutions_to_check_num_remaining)
				sum_words_remaining += words_remaining
				sum_squared += (words_remaining ** 2)
				max_words_remaining = max(words_remaining, max_words_remaining) if (max_words_remaining is not None) else words_remaining

			mean_squared_words_remaining = \
				sum_squared / len(solutions_to_check_possible) * solutions_to_check_possible_ratio

			mean_words_remaining = \
				sum_words_remaining / len(solutions_to_check_possible) * solutions_to_check_possible_ratio

			max_words_remaining = int(round(max_words_remaining * solutions_to_check_possible_ratio))

			# TODO: when solutions_to_check_possible_ratio > 1, max will be inaccurate; weight it lower
			# TODO: try mean-squared average, this may be a better metric
			score = \
				(self.params.score_weight_max * max_words_remaining) + \
				(self.params.score_weight_mean * mean_words_remaining) + \
				(self.params.score_weight_mean_squared * mean_squared_words_remaining) + \
				(0 if is_possible_solution else self.params.score_penalty_non_solution)

			is_lowest_average = lowest_average is None or mean_words_remaining < lowest_average
			is_lowest_max = lowest_max is None or max_words_remaining < lowest_max
			is_lowest_score = lowest_score is None or score < lowest_score

			if is_lowest_average:
				lowest_average = mean_words_remaining

			if is_lowest_max:
				lowest_max = max_words_remaining

			if is_lowest_score:
				best_guess = guess
				lowest_score = score
				self.dprint('Best so far (%u/%u): %s, score %.2f (average %.2f, lowest %.2f / worst case %i, lowest %i)' % (
					guess_idx + 1, len(guesses),
					guess.upper(),
					score,
					mean_words_remaining, lowest_average,
					max_words_remaining, lowest_max,
				))

			if is_lowest_average and not is_lowest_score:
				self.dprint('New lowest average (%u/%u): %s, average %.2f (score %.2f)' % (
					guess_idx + 1, len(guesses),
					guess.upper(), mean_words_remaining, score
				))

			if is_lowest_max and not is_lowest_score:
				self.dprint('New lowest max (%u/%u): %s, max %i (score %.2f)' % (
					guess_idx + 1, len(guesses),
					guess.upper(), max_words_remaining, score
				))

		return best_guess, lowest_score

	def get_best_guess(self) -> Optional[str]:

		num_possible_solutions = len(self.possible_solutions)

		assert 0 < num_possible_solutions <= len(self.allowed_words)

		if len(self.guesses) == 0:
			# First guess
			# Regular algorithm is O(n^2), which is way too slow
			# Instead just use whichever has the most common letters
			return self._prune_and_sort_guesses(self.allowed_words, None)[0]

		elif num_possible_solutions > 10:
			# Brute force search based on what eliminates the most possible solutions
			# This algorithm will prioritize the most common letters, so it's effective even for very large sets
			return self._brute_force_guess_for_fewest_remaining_words(max_num_matches=self.complexity_limit)

		elif num_possible_solutions > 2:
			# TODO: brute force search based on fewest number of guesses needed to solve puzzle
			# This would make search space massive, which is why we'd only do it when few remaining solutions
			return self._brute_force_guess_for_fewest_remaining_words(max_num_matches=self.complexity_limit)

		elif num_possible_solutions == 2:
			# No possible way to pick
			# Choose the first one alphabetically - that way the behavior is deterministic
			return sorted(list(self.possible_solutions))[0]

		elif num_possible_solutions == 1:
			return tuple(self.possible_solutions)[0]
		
		else:
			raise AssertionError
