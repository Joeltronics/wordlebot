#!/usr/bin/env python3

import collections
from copy import copy
from dataclasses import dataclass
from enum import Enum, unique
from math import sqrt
import os
import sys
from typing import Tuple, Iterable, Optional, Union, List

from game_types import *
import matching


RECURSION_HARD_LIMIT = 5
DEBUG_DONT_EXIT_ON_OPTIMAL_GUESS = False


@unique
class SolverVerbosity(Enum):
	silent = 0
	regular = 1
	debug = 2
	verbose_debug = 3


@dataclass(frozen=True)
class SolverParams:

	# Recursion: solve for fewest number of guesses needed, instead of heuristics

	recursion_max_solutions: int = 12
	# Non-solution guesses may be added to pad guess list, up to this many total guesses
	recursion_pad_num_guesses: int = 20
	# At this recursion depth, switch from average to minimax
	recursive_minimax_depth: int = 1

	# "Best solution" score weights

	score_weight_mean: int = 1
	score_weight_mean_squared: int = 0
	score_weight_max: int = 10
	score_penalty_non_solution: int = 5

	# Pruning

	# Ratio of possible guesses to target - if under, then prune solutions too
	prune_target_guess_ratio: float = 0.1

	# Pruning possible solutions to check against
	# Base divisor is number of solutions remaining divided by this
	prune_divide_possible_num_solutions_divisor: int = 4
	# Always take at least 1/4 of possible
	prune_divide_possible_max: int = 4

	# Pruning possible solutions to check how many remain
	# Base divisor is number of solutions remaining divided by this
	prune_divide_num_remaining_num_solutions_divisor: int = 8
	# Always take at least 1/4 of possible
	prune_divide_num_remaining_max: int = 4


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
			valid_solutions: Iterable[Word],
			allowed_words: Iterable[Word],
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

		self.one_line_print = sys.stdout.isatty() and self.verbosity == SolverVerbosity.regular

	def print_progress(self, s):
		if self.one_line_print:
			# TODO: check if this get_terminal_size call is slowing things down
			width = os.get_terminal_size().columns
			print((' ' * (width - 1)) + '\r' + s, end='\r', flush=True)

	def print_progress_complete(self):
		if self.one_line_print:
			print('')

	def print_level(self, level: SolverVerbosity, *args, **kwargs) -> None:
		if self.verbosity.value >= level.value:
			print(*args, **kwargs)

	def print(self, *args, **kwargs) -> None:
		self.print_level(SolverVerbosity.regular, *args, **kwargs)

	def dprint(self, *args, **kwargs) -> None:
		self.print_level(SolverVerbosity.debug, *args, **kwargs)

	def get_num_possible_solutions(self) -> int:
		return len(self.possible_solutions)

	def get_possible_solitions(self) -> List[str]:
		return self.possible_solutions

	def _is_valid(self, word: str) -> bool:
		return all([
			matching.is_valid_for_guess(word, guess) for guess in self.guesses
		])

	def add_guess(self, guess_word: Word, character_statuses: Iterable[CharStatus]):

		this_guess = (guess_word, character_statuses)
		self.guesses.append(this_guess)

		self.possible_solutions = {word for word in self.possible_solutions if matching.is_valid_for_guess(word, this_guess)}
		assert len(self.possible_solutions) > 0

		# TODO: in theory, could use process of elimination to sometimes guarantee position from yellow letters
		# A simple way to do this would be to look at remaining possible solutions instead of past character statuses
		# However, I suspect this is unlikely to actually make much of a difference in practice
		for idx in range(5):
			if character_statuses[idx] == CharStatus.correct:
				self.solved_letters[idx] = guess_word.word[idx]

	def get_unsolved_letters_counter(self, possible_solutions: Optional[list[str]] = None, per_position=False):

		def _remove_solved_letters(word):
			return ''.join([
				letter if (solved_letter is None or letter != solved_letter) else ''
				for letter, solved_letter in zip(word.word, self.solved_letters)
			])

		if possible_solutions is None:
			possible_solutions = self.possible_solutions

		words_solved_chars_removed = [_remove_solved_letters(word) for word in possible_solutions]
		all_chars = ''.join(words_solved_chars_removed)
		counter = collections.Counter(all_chars)

		if not per_position:
			return counter

		position_counters = [None for _ in range(5)]

		for position_idx in range(5):
			if self.solved_letters[position_idx] is not None:
				continue

			position_counters[position_idx] = collections.Counter([
				word.word[position_idx] for word in possible_solutions
			])

		return counter, position_counters

	def get_most_common_unsolved_letters(self):
		return self.get_unsolved_letters_counter().most_common()

	def _preliminary_score_guesses(
			self,
			guesses: Iterable[str],
			positional: bool,
			possible_solutions: Optional[Iterable[str]] = None,
			sort=True,
			debug_log=False) -> List[Tuple[str, int]]:
		"""
		Score guesses based on occurrence of most common unsolved letters
		"""

		if positional:
			counter_overall, counters_per_position = self.get_unsolved_letters_counter(per_position=True, possible_solutions=possible_solutions)
			def _score(word):

				score_unique_letters = sum([
					counter_overall[unique_letter]
					for unique_letter
					in set(word.word)
				])

				score_positional = sum([
					counter[letter]
					for letter, counter
					in zip(word.word, counters_per_position)
					if counter is not None
				])

				return score_unique_letters + score_positional
		else:
			counter = self.get_unsolved_letters_counter(possible_solutions=possible_solutions)
			def _score(word):
				return sum([counter[unique_letter] for unique_letter in set(word)])

		# Pre-sort guesses so that this will be deterministic in case of tied score
		guesses = sorted(list(guesses))

		guesses = [(guess, _score(guess)) for guess in guesses]

		if sort:
			guesses.sort(key=lambda guess_and_score: guess_and_score[1], reverse=True)

		if debug_log:
			num_solutions = len(self.possible_solutions)
			if len(guesses) > 10:
				self.print_level(SolverVerbosity.debug, 'Best guesses:')
				for guess, score in guesses[:5]:
					self.print_level(SolverVerbosity.debug, '  %s %.2f' % (guess, score / num_solutions))
				for guess, score in guesses[5:10]:
					self.print_level(SolverVerbosity.verbose_debug, '  %s %.2f' % (guess, score / num_solutions))

				self.print_level(SolverVerbosity.verbose_debug,'Worst guesses:')
				for guess, score in guesses[-10:]:
					self.print_level(SolverVerbosity.verbose_debug,'  %s %.2f' % (guess, score / num_solutions))

			else:
				self.print_level('All guesses:')
				for guess, score in guesses:
					self.print_level(SolverVerbosity.debug,'  %s %.2f' % (guess, score / num_solutions))

		return guesses

	def _prune_and_sort_guesses(
			self,
			guesses: Iterable[str],
			max_num: Optional[int],
			possible_solutions: Optional[list[str]] = None,
			positional = True,
			return_score = False,
			debug_log = False,
	) -> List[Union[str, Tuple[str, int]]]:
		"""
		Prune guesses based on occurrence of most common unsolved letters
		"""

		# TODO: option to prioritize (or even force) guesses that are solutions

		guesses_scored = self._preliminary_score_guesses(guesses, sort=True, positional=positional, debug_log=debug_log, possible_solutions=possible_solutions)

		# TODO: could it be an overall improvement to randomly mix in a few with less common letters too?
		# i.e. instead of a hard cutoff at max_num, make it a gradual "taper off" where we start picking fewer and fewer words from later in the list
		if max_num is not None:
			guesses_scored = guesses_scored[:max_num]

		if return_score:
			return guesses_scored
		else:
			return [g[0] for g in guesses_scored]

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
				f' ({num_guesses_to_try / num_possible_guesses * 100.0:.1f}%)' +
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

	def _solve_fewest_remaining_words(self, max_num_matches: Optional[int] = None) -> str:
		"""
		Find best guess, based on heuristic of which guess will narrow down to the fewest remaining words
		"""

		"""
		The overall algorithm is O(n^3):
		  1. in _solve_fewest_remaining_words_from_lists(), loop over guesses
		  2. in _solve_fewest_remaining_words_from_lists(), loop over solutions_to_check_possible
		  3. in matching.num_solutions_remaining(), another loop over solutions_to_check_num_remaining
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

		self.dprint('Initial best candidates: ' + ' '.join([str(guess) for guess in (
			guesses_to_try[:5] if len(guesses_to_try) > 5 else guesses_to_try
		)]))

		# Process the pruned lists

		ret, score = self._solve_fewest_remaining_words_from_lists(
			guesses=guesses_to_try,
			solutions_to_check_possible=solutions_to_check_possible,
			solutions_to_check_num_remaining=solutions_to_check_num_remaining)

		return ret

	def _score_guess_fewest_remaining_words(
			self,
			guess: str,
			is_possible_solution: bool,
			solutions_to_check_possible,
			solutions_to_check_num_remaining,
			words_remaining_multiplier=1.0,
	):

		max_words_remaining = None
		sum_words_remaining = 0
		sum_squared = 0
		for possible_solution in solutions_to_check_possible:
			words_remaining = matching.num_solutions_remaining(
				guess, possible_solution, solutions=solutions_to_check_num_remaining)
			sum_words_remaining += words_remaining
			sum_squared += (words_remaining ** 2)
			max_words_remaining = max(words_remaining, max_words_remaining) if (
						max_words_remaining is not None) else words_remaining

		mean_squared_words_remaining = \
			sum_squared / len(solutions_to_check_possible) * words_remaining_multiplier

		mean_words_remaining = \
			sum_words_remaining / len(solutions_to_check_possible) * words_remaining_multiplier

		max_words_remaining = int(round(max_words_remaining * words_remaining_multiplier))

		# TODO: when solutions_to_check_possible_ratio > 1, max will be inaccurate; weight it lower
		score = \
			(self.params.score_weight_max * max_words_remaining) + \
			(self.params.score_weight_mean * mean_words_remaining) + \
			(self.params.score_weight_mean_squared * mean_squared_words_remaining) + \
			(0 if is_possible_solution else self.params.score_penalty_non_solution)

		return score, max_words_remaining, mean_words_remaining, mean_squared_words_remaining

	def _solve_fewest_remaining_words_from_lists(
			self,
			guesses: Iterable[Word],
			solutions_to_check_possible: Iterable[Word] = None,
			solutions_to_check_num_remaining: Iterable[Word] = None,
			) -> Tuple[str, float]:

		if solutions_to_check_possible is None:
			solutions_to_check_possible = self.possible_solutions

		if solutions_to_check_num_remaining is None:
			solutions_to_check_num_remaining = self.possible_solutions

		assert len(solutions_to_check_num_remaining) <= len(self.possible_solutions)
		limited_solutions_to_check_possible = len(self.possible_solutions) != len(solutions_to_check_num_remaining)
		solutions_to_check_possible_ratio = len(self.possible_solutions) / len(solutions_to_check_num_remaining)
		assert solutions_to_check_possible_ratio >= 1.0

		# Take every possible valid guess, and run it against every possible remaining valid word
		lowest_average = None
		lowest_max = None
		best_guess = None
		lowest_score = None
		for guess_idx, guess in enumerate(guesses):

			self.print_progress('%i/%i %s' % (guess_idx + 1, len(guesses), guess))

			if (guess_idx + 1) % 200 == 0:
				self.dprint('%i/%i...' % (guess_idx + 1, len(guesses)))

			is_possible_solution = guess in self.possible_solutions

			score, max_words_remaining, mean_words_remaining, mean_squared_words_remaining = \
				self._score_guess_fewest_remaining_words(
					guess=guess,
					solutions_to_check_possible=solutions_to_check_possible,
					solutions_to_check_num_remaining=solutions_to_check_num_remaining,
					words_remaining_multiplier=solutions_to_check_possible_ratio,
					is_possible_solution=is_possible_solution)

			if (not limited_solutions_to_check_possible) and (max_words_remaining == 1):

				if is_possible_solution:
					# Can't possibly do any better than this, so don't bother processing any further

					if DEBUG_DONT_EXIT_ON_OPTIMAL_GUESS:
						self.print('%i/%i %s: Optimal guess; would stop searching but DEBUG_DONT_EXIT_ON_OPTIMAL_GUESS is set' % (guess_idx + 1, len(guesses), guess))
					else:
						self.print('%i/%i %s: Optimal guess; not searching any further' % (guess_idx + 1, len(guesses), guess))
						return guess, score

				else:
					pass  # TODO: can eliminate all remaining guesses that aren't possible solutions here

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
				self.dprint('%i/%i %s: Best so far, score %.2f (average %.2f, lowest %.2f / worst case %i, lowest %i)' % (
					guess_idx + 1, len(guesses),
					guess,
					score,
					mean_words_remaining, lowest_average,
					max_words_remaining, lowest_max,
				))

			if is_lowest_average and not is_lowest_score:
				self.dprint('%i/%i %s: New lowest average, but not lowest score: %.2f (score %.2f, best %.2f)' % (
					guess_idx + 1, len(guesses),
					guess, mean_words_remaining, score, lowest_score
				))

			if is_lowest_max and not is_lowest_score:
				self.dprint('%i/%i %s: New lowest max, but not lowest score: %i (score %.2f, best %.2f)' % (
					guess_idx + 1, len(guesses),
					guess, max_words_remaining, score, lowest_score
				))

		self.print_progress_complete()

		return best_guess, lowest_score

	def _solve_recursive(self) -> str:

		# TODO: find a way to limit complexity to get consistent time performance out of this

		solutions_sorted = sorted(list(self.possible_solutions))
		num_possible_solutions = len(solutions_sorted)

		# FIXME: this is duplicate logic with _determine_guesses_for_recursive_solving
		num_guesses_to_check = num_possible_solutions + min(
			num_possible_solutions,
			max(self.params.recursion_pad_num_guesses - num_possible_solutions, 0)
		)
		self.print(f'Checking {num_guesses_to_check} guesses against {num_possible_solutions} solutions, recursively...')

		best_guess, best_score = self._solve_recursive_inner(possible_solutions=solutions_sorted, recursive_depth=0)
		self.print_progress_complete()

		if best_guess is None:
			self.dprint()
			self.print('Failed to find a guess!')
			return None

		self.dprint()
		if best_score == 1:
			self.print(f'Best guess {best_guess} (worst case: solve in {best_score:.2f} more guess after this one)')
		else:
			self.print(f'Best guess {best_guess} (worst case: solve in {best_score:.2f} more guesses after this one)')
		return best_guess

	def _determine_guesses_for_recursive_solving(
			self,
			possible_solutions: Iterable[str]):

		# Try all solutions, add in some non-solutions
		# TODO: When lots remaining, should prioritize non-solution guesses (even removing some solution guesses)
		"""
		Current logic, with pad_num_guesses 20:

		>= 20 solutions: try them all
		10-20 solutions: try all the solutions, and pad other guesses to hit 20
		<= 10 solutions: try all the solutions, and an equal number of non-solutions

		e.g.
		12 solutions: try 12 solution + 8 non solution = 20 total
		10 solutions: try 10 solution + 10 non solution = 20 total
		5 solutions: try 5 solution + 5 non solution = 10 total
		3 solutions: try 3 solution + 3 non solution = 6 total
		"""

		total_num_possible_solutions = len(possible_solutions)
		num_guesses_to_try = max(self.params.recursion_pad_num_guesses, total_num_possible_solutions)

		# Never try more non-solutions than solutions
		# i.e. if recursion_pad_num_guesses == 20, but if there are only 3 solutions left,
		# then it's not worth checking 17 non-solutions, so just check 3 solutions + the top 3 non-solutions
		num_non_solutions_to_try = min(num_guesses_to_try - total_num_possible_solutions, total_num_possible_solutions)

		non_solution_guesses_to_try = list(self.allowed_words - set(possible_solutions))
		solution_guesses_to_try = list(possible_solutions)

		solution_guesses_to_try_scored = self._prune_and_sort_guesses(
			solution_guesses_to_try, max_num=None, possible_solutions=possible_solutions)

		non_solution_guesses_to_try_scored = self._prune_and_sort_guesses(
			non_solution_guesses_to_try, max_num=num_non_solutions_to_try, possible_solutions=possible_solutions)

		guesses_to_try = solution_guesses_to_try_scored + non_solution_guesses_to_try_scored

		return guesses_to_try

	def _solve_recursive_inner(
			self,
			possible_solutions: Iterable[str],
			recursive_depth: int,
			recursion_depth_limit: int = RECURSION_HARD_LIMIT,
			recursive_log_str: str = ''
	) -> Tuple[str, float]:

		assert recursive_depth < RECURSION_HARD_LIMIT

		# FIXME: right now we treat minimax and average scores as equivalent and just sum them, this is wrong
		minimax = recursive_depth >= self.params.recursive_minimax_depth

		# TODO: Add another depth limit, which switches to heuristics instead of giving up

		indentation = '    ' * recursive_depth
		if recursive_depth >= 1:
			log = lambda msg: self.print_level(SolverVerbosity.verbose_debug, indentation + msg)
		else:
			log = lambda msg: self.print_level(SolverVerbosity.debug, indentation + msg)

		total_num_possible_solutions = len(possible_solutions)

		guesses_to_try = self._determine_guesses_for_recursive_solving(possible_solutions=possible_solutions)

		best_guess = None
		best_guess_score = None
		for guess_idx, guess in enumerate(guesses_to_try):

			if recursive_depth == 0:
				log('')
				#self.print_progress('%i/%i %s' % (guess_idx + 1, len(guesses_to_try), guess))
				recursive_log_str = '%i/%i %s:' % (guess_idx + 1, len(guesses_to_try), guess)
				self.print_progress(recursive_log_str)

			# Limit depth - if minimax, no point searching any deeper than current minimax

			if minimax and (best_guess_score is not None):
				this_recursion_depth_limit = best_guess_score - 1
			else:
				this_recursion_depth_limit = recursion_depth_limit

			if len(possible_solutions) <= 6:
				log('Guess %i, option %i/%i %s: checking against %i solutions to a max depth of %i: %s' % (
					recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess, len(possible_solutions),
					this_recursion_depth_limit,
					' '.join([str(solution) for solution in possible_solutions])
				))
			else:
				log('Guess %i, option %i/%i %s: checking against %i solutions to a max depth of %i' % (
					recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess, len(possible_solutions),
					this_recursion_depth_limit,
				))

			remaining_possible_solutions = copy(possible_solutions)

			skip_this_guess = False
			worst_solution_score = None
			solution_score_sum = 0

			while len(remaining_possible_solutions) > 0:

				len_at_start_of_loop = len(remaining_possible_solutions)

				possible_solutions_this_guess, character_status = matching.solutions_remaining(
					guess=guess,
					possible_solution=remaining_possible_solutions[0],
					solutions=possible_solutions,
					return_character_status=True,
				)

				if self.one_line_print:
					this_recursive_log_str = recursive_log_str + ' ' + format_guess(guess, character_status)
					self.print_progress(this_recursive_log_str)
				else:
					this_recursive_log_str = ''

				assert len(possible_solutions_this_guess) > 0

				for possible_solution in possible_solutions_this_guess:
					remaining_possible_solutions.remove(possible_solution)

				assert len(remaining_possible_solutions) < len_at_start_of_loop

				if len(possible_solutions_this_guess) == 1:
					log('  Solution possibility %i/%i %s, would have down to 1 solution, guaranteed 1 more guess' % (
						total_num_possible_solutions - len_at_start_of_loop + 1,
						total_num_possible_solutions,
						possible_solutions_this_guess[0],
					))
					this_solution_score = 1

				elif len(possible_solutions_this_guess) == 2:
					log('  Solution possibilities %i-%i/%i %s/%s, would have down to 2 solutions, worst case 2 more guesses' % (
						total_num_possible_solutions - len_at_start_of_loop + 1,
						total_num_possible_solutions - len_at_start_of_loop + len(possible_solutions_this_guess),
						total_num_possible_solutions,
						possible_solutions_this_guess[0],
						possible_solutions_this_guess[1],
					))
					this_solution_score = 2 if minimax else 1.5

				else:
					log('  Solution possibilities %i-%i/%i, would have down to %i solutions' % (
						total_num_possible_solutions - len_at_start_of_loop + 1,
						total_num_possible_solutions - len_at_start_of_loop + len(possible_solutions_this_guess),
						total_num_possible_solutions,
						len(possible_solutions_this_guess),
					))

					next_recursive_depth = recursive_depth + 1

					if next_recursive_depth >= RECURSION_HARD_LIMIT:
						log('  Hit recursion depth hard limit, abandoning this guess')
						skip_this_guess = True
						break

					elif next_recursive_depth > this_recursion_depth_limit:
						log('  Searching deeper would be worse then current best case, abandoning this guess')
						skip_this_guess = True
						break

					else:
						this_level_best_guess, this_level_best_score = self._solve_recursive_inner(
							possible_solutions=possible_solutions_this_guess,
							recursive_depth=next_recursive_depth,
							recursion_depth_limit=this_recursion_depth_limit,
							recursive_log_str=this_recursive_log_str,
						)

						if this_level_best_guess is None:
							log('  Deeper level hit recursion depth limit, abandoning this guess')
							skip_this_guess = True
							break

						this_solution_score = this_level_best_score + 1

				solution_score_sum += this_solution_score * len(possible_solutions_this_guess)

				# For average case, can skip this guess if we know we're guaranteed worse than current best case
				curr_sum_average = solution_score_sum / len(possible_solutions)
				if (best_guess_score is not None) and (not minimax) and (curr_sum_average > best_guess_score):
					log('  Abandoning this guess - current average sum (%.2f) worse than current best (%s %.2f)' % (
						curr_sum_average, best_guess, best_guess_score
					))
					skip_this_guess = True
					break

				if (worst_solution_score is None) or (this_solution_score > worst_solution_score):
					worst_solution_score = this_solution_score

			if skip_this_guess:
				continue

			average_score = solution_score_sum / len(possible_solutions)

			if worst_solution_score is None:
				raise RecursionError('All possible guesses hit recursion limit!')

			score = worst_solution_score if minimax else average_score
			if (best_guess_score is None) or (score < best_guess_score):
				best_guess = guess
				best_guess_score = score

			assert best_guess_score >= 1

			if best_guess_score == 1:
				assert average_score == 1
				log('Guess %i, option %i/%i %s: Guaranteed to solve in 1 more guess' % (
					recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess,
				))
			elif minimax:
				log('Guess %i, option %i/%i %s: Worst case, solve in %i more guesses' % (
					recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess, best_guess_score,
				))
			else:
				log('Guess %i, option %i/%i %s: Average case, solve in %.2f more guesses' % (
					recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess, average_score,
				))

			assert worst_solution_score >= 1

			if worst_solution_score == 1:
				if DEBUG_DONT_EXIT_ON_OPTIMAL_GUESS:
					log('Guess %i, option %i/%i %s: This guess is optimal, would stop searching but DEBUG_DONT_EXIT_ON_OPTIMAL_GUESS is set' % (
						recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess
					))
				else:
					if recursive_depth == 0:
						self.print('%i/%i %s: This guess is optimal (guaranteed to solve in 1 more), not searching any further' % (
							guess_idx + 1, len(guesses_to_try), guess
						))
					else:
						log('Guess %i, option %i/%i %s: This guess is optimal, not searching any further' % (
							recursive_depth + 1, guess_idx + 1, len(guesses_to_try), guess
						))

					return best_guess, best_guess_score

		return best_guess, best_guess_score

	def get_best_guess(self) -> Optional[str]:

		num_possible_solutions = len(self.possible_solutions)

		assert 0 < num_possible_solutions <= len(self.allowed_words)

		if len(self.guesses) == 0:
			# First guess
			# Regular algorithm is O(n^2), which is way too slow
			# Instead just use whichever has the most common letters
			return self._prune_and_sort_guesses(self.allowed_words, None, positional=True, debug_log=True)[0]

		elif num_possible_solutions == 2:
			# No possible way to pick
			# Choose the first one alphabetically - that way the behavior is deterministic
			return sorted(list(self.possible_solutions))[0]

		elif num_possible_solutions == 1:
			return tuple(self.possible_solutions)[0]

		elif num_possible_solutions <= self.params.recursion_max_solutions:
			# Search based on fewest number of guesses needed to solve puzzle
			# This makes the search space massive, which is why we only do it when few remaining solutions
			guess = self._solve_recursive()

			if guess is not None:
				return guess

			self.print('Recursive search failed, falling back to iterative')

		# Brute force search based on what eliminates the most possible solutions
		# This algorithm will prioritize the most common letters, so it's effective even for very large sets
		return self._solve_fewest_remaining_words(max_num_matches=self.complexity_limit)
