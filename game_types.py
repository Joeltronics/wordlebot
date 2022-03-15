#!/usr/bin/env python3

from colorama import Fore, Back, Style

from enum import Enum, unique
from typing import Iterable, Type


FORMAT_UNKOWN = Back.BLACK + Fore.WHITE
FORMAT_CORRECT = Back.GREEN + Fore.WHITE
FORMAT_WRONG_POSITION = Back.YELLOW + Fore.WHITE
FORMAT_NOT_IN_SOLUTION = Back.WHITE + Fore.BLACK



@unique
class CharStatus(Enum):
	unknown = 0
	not_in_solution = 1
	wrong_position = 2
	correct = 3


class Word:
	def __init__(self, word: str):

		if isinstance(word, Word):
			self.word = word.word
			return

		if len(word) != 5:
			raise ValueError('Words must have 5 letters')

		if not word.isalpha():
			raise ValueError(f'String is not word: "{word}"')

		word = word.upper()

		self.word = word

	def __str__(self):
		return self.word

	def __eq__(self, other):
		if isinstance(other, Word):
			return self.word == other.word
		elif isinstance(other, str):
			return self.word == other.upper()
		else:
			raise TypeError()

	def __lt__(self, other):
		if isinstance(other, Word):
			return self.word < other.word
		elif isinstance(other, str):
			return self.word < other.upper()
		else:
			raise TypeError()

	def __hash__(self) -> int:
		return hash(self.word)


def get_format(char_status: CharStatus) -> str:
	return {
		CharStatus.unknown:         FORMAT_UNKOWN,
		CharStatus.not_in_solution: FORMAT_NOT_IN_SOLUTION,
		CharStatus.wrong_position:  FORMAT_WRONG_POSITION,
		CharStatus.correct:         FORMAT_CORRECT,
	}[char_status]


def format_guess(guess: Word, statuses: Iterable[CharStatus]) -> str:
	return ''.join([
		get_format(status) + character.upper() for character, status in zip(guess.word, statuses)
	]) + Style.RESET_ALL
