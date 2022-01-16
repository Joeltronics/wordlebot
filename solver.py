#!/usr/bin/env python3

import random
from typing import Tuple, Iterable, Optional

from game_types import *
import word_list


class Solver:
	def __init__(self):
		self.guesses = []
		self.possible_solutions = word_list.words

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

	def _num_words_remaining(self, guess: str, possible_solution: str) -> int:
		"""
		If we guess this word, and see this result, figure out how many possible words could be remaining
		"""
		# TODO: this is a bottleneck, see if it can be optimized
		character_status = get_character_statuses(guess, possible_solution)
		new_possible_solutions = [word for word in self.possible_solutions if self._is_valid_for_guess(word, (guess, character_status))]
		return len(new_possible_solutions)


	def _brute_force_guess_for_fewest_remaining_words(self) -> str:

		guesses_possible_solutions = set(self.possible_solutions)
		guesses_not_solutions = list(word_list.words - guesses_possible_solutions)

		guesses_possible_solutions = list(guesses_possible_solutions)
		random.shuffle(guesses_possible_solutions)
		random.shuffle(guesses_not_solutions)

		print('Brute forcing based on fewest remaining words; %u * %u = %u total combos to check' % (
			len(guesses_possible_solutions) + len(guesses_not_solutions),
			len(self.possible_solutions),
			(len(guesses_possible_solutions) + len(guesses_not_solutions)) * len(self.possible_solutions),
		))
		print()
		print('Checking possible solutions; %u * %u = %u combos to check...' % (
			len(guesses_possible_solutions), len(self.possible_solutions), len(guesses_possible_solutions) * len(self.possible_solutions)))
		psosible_solution_best_guess, possible_solution_best_score = self._brute_force_guess_for_fewest_remaining_words_list(guesses_possible_solutions)
		print()

		print('Checking non-solutions; %u * %u = %u combos to check...' % (
			len(guesses_not_solutions), len(self.possible_solutions), len(guesses_not_solutions) * len(self.possible_solutions)))
		not_solution_best_guess, not_solution_best_score = self._brute_force_guess_for_fewest_remaining_words_list(guesses_not_solutions)
		print()

		if possible_solution_best_score < not_solution_best_score:
			print('Best guess: %s' % psosible_solution_best_guess.upper())
		else:
			print("Best possible solution guess: %s, score %.2f" % (psosible_solution_best_guess.upper(), possible_solution_best_score))
			print('Best other guess:             %s, score %.2f' % (not_solution_best_guess.upper(), not_solution_best_score))
		print()


	def _brute_force_guess_for_fewest_remaining_words_list(self, guesses) -> Tuple[str, float]:

		# Take every possible valid guess, and run it against every possible remaining valid word, figure
		lowest_average = None
		lowest_max = None
		best_guess = None
		lowest_score = None
		for guess_idx, guess in enumerate(guesses):

			if (guess_idx + 1) % 100 == 0:
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

		assert num_possible_solutions > 0

		if num_possible_solutions == 1:
			return tuple(self.possible_solutions)[0]

		elif num_possible_solutions == 2:
			return None

		elif num_possible_solutions <= 50:
			# TODO: technically the metric of "fewest remaining words" is still a heuristic - a good one, but still
			# The actual metric we want to optimize is "fewest number of guesses to solve"
			return self._brute_force_guess_for_fewest_remaining_words()

		elif num_possible_solutions <= 1000:
			pass  # TODO: not sure - heuristics?
			return None

		else:
			pass  # TODO: use "opening book"?
			return None
