#!/usr/bin/env python3

import collections
import random
from typing import Tuple, Iterable, Optional

from game_types import *


class Solver:
	def __init__(self, valid_solutions: Iterable[str], allowed_words: Iterable[str]):
		self.guesses = []
		self.all_valid_solutions = valid_solutions
		self.allowed_words = allowed_words
		self.possible_solutions = self.all_valid_solutions
		self.solved_letters = [None] * 5

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

	def get_most_common_unsolved_letters(self):

		def _remove_solved_letters(word):
			return ''.join([
				letter if (solved_letter is None or letter != solved_letter) else ''
				for letter, solved_letter in zip(word, self.solved_letters)
			])

		words_solved_chars_removed = [_remove_solved_letters(word) for word in self.possible_solutions]
		all_chars = ''.join(words_solved_chars_removed)
		counter = collections.Counter(all_chars)

		return counter.most_common()

	def _num_words_remaining(self, guess: str, possible_solution: str) -> int:
		"""
		If we guess this word, and see this result, figure out how many possible words could be remaining
		"""
		# TODO: this is a bottleneck, see if it can be optimized
		character_status = get_character_statuses(guess, possible_solution)
		new_possible_solutions = [word for word in self.possible_solutions if self._is_valid_for_guess(word, (guess, character_status))]
		return len(new_possible_solutions)

	def _prune_guesses(self, guesses: Iterable[str], max_num: int) -> List[str]:
		# TODO: smarter pruning than just random. Prioritize most common remaining unknown letters
		guesses = list(guesses)
		random.shuffle(guesses)
		guesses = guesses[:max_num]
		return guesses

	def _brute_force_guess_for_fewest_remaining_words(self, max_num_combos: Optional[int] = None) -> str:

		total_num_combos = len(self.allowed_words) * len(self.possible_solutions)

		# The maximum number of guesses that we can try without hitting max_num_combos
		max_num_guesses_to_try = max_num_combos // len(self.possible_solutions) if (max_num_combos is not None) else None

		print('Brute forcing based on fewest remaining words; %u * %u = %u possible combos to check' % (
			len(self.allowed_words), len(self.possible_solutions), total_num_combos,
		))

		if (max_num_guesses_to_try is not None) and len(self.allowed_words) > max_num_guesses_to_try:

			guesses_possible_solutions = set(self.possible_solutions)
			guesses_not_solutions = self.allowed_words - set(self.possible_solutions)

			# TODO: smarter pruning than just random
			# Prioritize words with common letters in remaining solutions

			# If num_combos_possible_solutions is more than 25% of the limit, prune both lists
			# Otherwise, only prune guesses_not_solutions
			if len(guesses_possible_solutions) > max_num_guesses_to_try // 4:

				num_possible_solutions = max_num_guesses_to_try // 4
				num_non_solutions = max_num_guesses_to_try - num_possible_solutions

				print('Pruning both (%u > max %u. Trying %u/%u possible answers and %u/%u possible non-answers (%.1f%% of total solution space)' % (
					total_num_combos,
					max_num_combos,
					num_possible_solutions, len(guesses_possible_solutions),
					num_non_solutions, len(guesses_not_solutions),
					100.0 * max_num_combos / total_num_combos,
				))

				guesses_possible_solutions = self._prune_guesses(guesses_possible_solutions, num_possible_solutions)
				guesses_not_solutions = self._prune_guesses(guesses_not_solutions, num_non_solutions)

			else:
				num_non_solutions = max_num_guesses_to_try - len(guesses_possible_solutions)
				print('Pruning guesses from non-possible solutions. Trying %u possible answers, and %u/%u non-answers (%.1f%% of total solution space)' % (
					len(guesses_possible_solutions),
					num_non_solutions,
					len(guesses_not_solutions),
					100.0 * max_num_combos / total_num_combos
				))

				guesses_not_solutions = self._prune_guesses(guesses_not_solutions, num_non_solutions)

				guesses_possible_solutions = list(guesses_possible_solutions)
				random.shuffle(guesses_possible_solutions)

		else:
			guesses_possible_solutions = set(self.possible_solutions)
			guesses_not_solutions = list(self.allowed_words - guesses_possible_solutions)

			guesses_possible_solutions = list(guesses_possible_solutions)

			print('No pruning; trying all %u words' % (len(guesses_not_solutions) + len(guesses_possible_solutions)))

			random.shuffle(guesses_possible_solutions)
			random.shuffle(guesses_not_solutions)

		print()
		print('Checking %u possible solutions (%u * %u = %u combos to check...)' % (
			len(guesses_possible_solutions), len(guesses_possible_solutions), len(self.possible_solutions), len(guesses_possible_solutions) * len(self.possible_solutions)))
		possible_solution_best_guess, possible_solution_best_score = self._brute_force_guess_for_fewest_remaining_words_list(guesses_possible_solutions)
		print()

		print('Checking %u non-solutions (%u * %u = %u combos to check...)' % (
			len(guesses_not_solutions), len(guesses_not_solutions), len(self.possible_solutions), len(guesses_not_solutions) * len(self.possible_solutions)))
		not_solution_best_guess, not_solution_best_score = self._brute_force_guess_for_fewest_remaining_words_list(guesses_not_solutions)
		print()

		if possible_solution_best_score <= not_solution_best_score:
			print('Best guess: %s' % possible_solution_best_guess.upper())
		else:
			print("Best possible solution guess: %s, score %.2f" % (possible_solution_best_guess.upper(), possible_solution_best_score))
			print('Best other guess:             %s, score %.2f' % (not_solution_best_guess.upper(), not_solution_best_score))
		print()


	def _brute_force_guess_for_fewest_remaining_words_list(self, guesses) -> Tuple[str, float]:

		# Take every possible valid guess, and run it against every possible remaining valid word, figure
		lowest_average = None
		lowest_max = None
		best_guess = None
		lowest_score = None
		for guess_idx, guess in enumerate(guesses):

			if (guess_idx + 1) % 1000 == 0:
				print('%i/%i...' % (guess_idx+1, len(guesses)))

			max_words_remaining = None
			sum_words_remaining = 0
			for possible_solution in self.possible_solutions:
				words_remaining = self._num_words_remaining(guess, possible_solution)
				sum_words_remaining += words_remaining
				max_words_remaining = max(words_remaining, max_words_remaining) if (max_words_remaining is not None) else words_remaining

			average_words_remaining = sum_words_remaining / len(self.possible_solutions)

			#average_words_remaining = sum([
			#		self._num_words_remaining(guess, possible_solution) for possible_solution in self.possible_solutions
			#	]) / len(self.possible_solutions)

			score = (10 * max_words_remaining) + average_words_remaining

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
				print('Best so far: %s, score %.2f (average %.2f, lowest %.2f / worst case %i, lowest %i)' % (
					guess.upper(),
					score,
					average_words_remaining, lowest_average,
					max_words_remaining, lowest_max,
				))

			if is_lowest_average and not is_lowest_score:
				print('New lowest average: %s, average %.2f (score %.2f)' % (
					guess.upper(), average_words_remaining, score
				))

			if is_lowest_max and not is_lowest_score:
				print('New lowest max: %s, max %i (score %.2f)' % (
					guess.upper(), max_words_remaining, score
				))

		return best_guess, lowest_score

	def get_best_guess(self) -> Optional[str]:

		num_possible_solutions = len(self.possible_solutions)

		assert 0 < num_possible_solutions <= len(self.allowed_words)

		if num_possible_solutions == len(self.all_valid_solutions):
			# This is the first guess
			# TODO: use "opening book"
			pass  # TODO

		elif num_possible_solutions > 1000:
			# TODO: pick based on most common letters
			return None

		elif num_possible_solutions > 10:
			# Brute force search based on what eliminates the most possible solutions
			return self._brute_force_guess_for_fewest_remaining_words(max_num_combos=int(1e5))

		elif num_possible_solutions > 2:
			# TODO: brute force search based on fewest number of guesses needed to solve puzzle
			# This would make search space massive, which is why we'd only do it when few remaining solutions
			return self._brute_force_guess_for_fewest_remaining_words(max_num_combos=int(1e5))

		elif num_possible_solutions == 2:
			# No possible way to pick
			return None

		elif num_possible_solutions == 1:
			return tuple(self.possible_solutions)[0]
		
		else:
			raise AssertionError
