#!/usr/bin/env python3

from typing import Tuple, Iterable

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
