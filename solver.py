#!/usr/bin/env python3

import collections
from typing import Tuple, Iterable, Optional

from game_types import *


class Solver:
	def __init__(self, valid_solutions: Iterable[str], allowed_words: Iterable[str], complexity_limit: int, debug_print=False):
		self.guesses = []
		self.allowed_words = allowed_words
		self.possible_solutions = valid_solutions
		self.solved_letters = [None] * 5
		self.complexity_limit = complexity_limit
		self.debug_print = debug_print

	def dprint(self, *args, **kwargs):
		if self.debug_print:
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

		# TODO: this doesn't take letter position into account

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

	def _brute_force_guess_for_fewest_remaining_words(self, max_num_matches: Optional[int] = None) -> str:
		"""
		"""

		"""
		The overall algorithm is O(n^3):
		  1. in _brute_force_guess_for_fewest_remaining_words_list(), loop over guesses
		  2. in _brute_force_guess_for_fewest_remaining_words_list(), loop over solutions_to_check_possible
		  3. in _num_solutions_remaining(), another loop over solutions_to_check_num_remaining
		"""
		num_allowed_words = len(self.allowed_words)
		num_possible_solutions = len(self.possible_solutions)
		total_num_matches = num_allowed_words * num_possible_solutions * num_possible_solutions

		# The maximum number of guesses that we can try without hitting max_num_matches
		max_num_guesses_to_try = max_num_matches // (num_possible_solutions * num_possible_solutions) if (max_num_matches is not None) else None
		max_num_guesses_to_try = max(1, max_num_guesses_to_try)

		print('Brute forcing based on fewest remaining words; %u * %u * %u = %g possible combos to check' % (
			len(self.allowed_words), len(self.possible_solutions), len(self.possible_solutions), total_num_matches,
		))

		guesses_to_try = list(self.allowed_words)

		if (max_num_guesses_to_try is not None) and len(guesses_to_try) > max_num_guesses_to_try:

			print('Pruning guesses from non-possible solutions. Trying %u/%u guesses (%.1f%%)' % (
				max_num_guesses_to_try,
				len(guesses_to_try),
				max_num_guesses_to_try / len(guesses_to_try) * 100.0
			))

			guesses_to_try = self._prune_and_sort_guesses(guesses_to_try, max_num_guesses_to_try)
		else:
			print('No pruning; trying all %u words' % len(guesses_to_try))
			guesses_to_try = self._prune_and_sort_guesses(guesses_to_try, None)

		# TODO: prune these too when we're way over the limit, not just guesses
		solutions_to_check_possible = self.possible_solutions
		solutions_to_check_num_remaining = self.possible_solutions

		print()
		print('Checking %u possible solutions (%u * %u * %u = %u matches to check...)' % (
			len(guesses_to_try),
			len(guesses_to_try),
			len(solutions_to_check_possible),
			len(solutions_to_check_num_remaining),
			len(guesses_to_try) * len(solutions_to_check_possible) * len(solutions_to_check_num_remaining),
		))
		self.dprint('Initial best candidates: ' + ' '.join([guess.upper() for guess in (
			guesses_to_try[:5] if len(guesses_to_try) > 5 else guesses_to_try
		)]))
		ret, score = self._brute_force_guess_for_fewest_remaining_words_list(
			guesses=guesses_to_try,
			solutions_to_check_possible=solutions_to_check_possible,
			solutions_to_check_num_remaining=solutions_to_check_num_remaining)

		return ret


	def _brute_force_guess_for_fewest_remaining_words_list(
			self,
			guesses: Iterable[str],
			solutions_to_check_possible: Iterable[str] = None,
			solutions_to_check_num_remaining: Iterable[str] = None,
			) -> Tuple[str, float]:

		if solutions_to_check_possible is None:
			solutions_to_check_possible = self.possible_solutions

		if solutions_to_check_num_remaining is None:
			solutions_to_check_num_remaining = self.possible_solutions

		# Take every possible valid guess, and run it against every possible remaining valid word, figure
		lowest_average = None
		lowest_max = None
		best_guess = None
		lowest_score = None
		for guess_idx, guess in enumerate(guesses):

			# Slightly prioritize possible solutions
			is_possible_solution = guess in self.possible_solutions

			if (guess_idx + 1) % 1000 == 0:
				self.dprint('%i/%i...' % (guess_idx+1, len(guesses)))

			max_words_remaining = None
			sum_words_remaining = 0
			for possible_solution in solutions_to_check_possible:
				words_remaining = self._num_solutions_remaining(guess, possible_solution, solutions=solutions_to_check_num_remaining)
				sum_words_remaining += words_remaining
				max_words_remaining = max(words_remaining, max_words_remaining) if (max_words_remaining is not None) else words_remaining

			average_words_remaining = sum_words_remaining / len(solutions_to_check_possible)

			score = (10 * max_words_remaining) + average_words_remaining + (0 if is_possible_solution else 5)

			is_lowest_average = lowest_average is None or average_words_remaining < lowest_average
			is_lowest_max = lowest_max is None or max_words_remaining < lowest_max
			is_lowest_score = lowest_score is None or score < lowest_score

			if is_lowest_average:
				lowest_average = average_words_remaining

			if is_lowest_max:
				lowest_max = max_words_remaining

			if is_lowest_score:
				best_guess = guess
				lowest_score = score
				self.dprint('Best so far (%u/%u): %s, score %.2f (average %.2f, lowest %.2f / worst case %i, lowest %i)' % (
					guess_idx + 1, len(guesses),
					guess.upper(),
					score,
					average_words_remaining, lowest_average,
					max_words_remaining, lowest_max,
				))

			if is_lowest_average and not is_lowest_score:
				self.dprint('New lowest average (%u/%u): %s, average %.2f (score %.2f)' % (
					guess_idx + 1, len(guesses),
					guess.upper(), average_words_remaining, score
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
