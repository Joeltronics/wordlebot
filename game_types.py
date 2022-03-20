#!/usr/bin/env python3

from colorama import Fore, Back, Style
from dataclasses import dataclass

from enum import Enum, unique
from typing import Iterable, Optional, Union


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


@dataclass(frozen=True)
class Word:
	word: str
	index: int

	def __post_init__(self):
		if len(self.word) != 5:
			raise ValueError('Words must have 5 letters')

		if not self.word.isalpha():
			raise ValueError(f'String is not word: "{self.word}"')

		if not self.word == self.word.upper():
			raise ValueError(f'Word must be uppercase: "{self.word}"')

	def __str__(self):
		return self.word

	def __eq__(self, other):
		if isinstance(other, Word):
			return self.index == other.index
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
		return self.index

	def __iter__(self):
		return self.word.__iter__()

	def __next__(self):
		return self.word.__next__()

	def __getitem__(self, idx: int):
		return self.word[idx]


def get_format(char_status: CharStatus) -> str:
	return {
		CharStatus.unknown:         FORMAT_UNKOWN,
		CharStatus.not_in_solution: FORMAT_NOT_IN_SOLUTION,
		CharStatus.wrong_position:  FORMAT_WRONG_POSITION,
		CharStatus.correct:         FORMAT_CORRECT,
	}[char_status]


def format_guess(guess: Word, statuses: Iterable[CharStatus]) -> str:
	return ''.join([
		get_format(status) + character.upper() for character, status in zip(guess, statuses)
	]) + Style.RESET_ALL
