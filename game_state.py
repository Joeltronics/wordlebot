#!/usr/bin/env python3

import collections
from copy import copy

from game_types import *
import matching


class LetterStatuses:

	def __init__(self):
		self.char_status = {
			chr(ch): LetterResult.unknown for ch in range(ord('A'), ord('Z') + 1)
		}

	def _format_char(self, ch: str):
		return self.char_status[ch.upper()].get_format() + ch.upper()

	def print_keyboard(self):
		rows = [
			'QWERTYUIOP',
			'ASDFGHJKL',
			'ZXCVBNM',
		]
		for row in rows:
			print(''.join([self._format_char(ch) for ch in row]) + Style.RESET_ALL + ' ')

	def add_guess(self, guess: Guess):
		for character, status in guess:
			assert character == character.upper()
			if self.char_status[character].value < status.value:
				self.char_status[character] = status



class GameState:
	def __init__(
			self,
			allowed_words: set[Word],
			possible_solutions: set[Word],
			):
		self.allowed_words = allowed_words
		self.possible_solutions = possible_solutions
		self.guesses = []
		self.letter_statuses = LetterStatuses()
		self.solved_letters = [None] * 5

	def add_guess(self, guess: Guess):

		possible_solutions = {word for word in self.possible_solutions if matching.is_valid_for_guess(word, guess)}
		if len(possible_solutions) == 0:
			raise ValueError('This guess result does not leave any possible solutions!')

		self.guesses.append(guess)
		self.possible_solutions = possible_solutions
		self.letter_statuses.add_guess(guess)

		# TODO: in theory, could use process of elimination to sometimes guarantee position from yellow letters
		# A simple way to do this would be to look at remaining possible solutions instead of past letter results
		# However, I suspect this is unlikely to actually make much of a difference in practice
		for idx in range(5):
			if guess.result[idx] == LetterResult.correct:
				self.solved_letters[idx] = guess.word[idx]

	def print_keyboard(self):
		self.letter_statuses.print_keyboard()

	def get_num_possible_solutions(self) -> int:
		return len(self.possible_solutions)

	def get_possible_solutions(self) -> set[str]:
		return self.possible_solutions

	def get_unsolved_letters_counter(self, possible_solutions: Optional[list[str]] = None, per_position=False):

		def _remove_solved_letters(word):
			return ''.join([
				letter if (solved_letter is None or letter != solved_letter) else ''
				for letter, solved_letter in zip(word, self.solved_letters)
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
				word[position_idx] for word in possible_solutions
			])

		return counter, position_counters

	def get_most_common_unsolved_letters(self):
		return self.get_unsolved_letters_counter().most_common()
