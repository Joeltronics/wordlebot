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
class LetterResult(Enum):
	unknown = 0
	not_in_solution = 1
	wrong_position = 2
	correct = 3

	def get_format(self) -> str:
		return {
			LetterResult.unknown:         FORMAT_UNKOWN,
			LetterResult.not_in_solution: FORMAT_NOT_IN_SOLUTION,
			LetterResult.wrong_position:  FORMAT_WRONG_POSITION,
			LetterResult.correct:         FORMAT_CORRECT,
		}[self]


assert all([0 <= result.value < 4 for result in LetterResult])


@dataclass(frozen=True)
class GuessResult:
	_char_results: tuple[LetterResult, LetterResult, LetterResult, LetterResult, LetterResult]

	def as_int(self) -> int:
		return \
			(self._char_results[0].value << 8) | \
			(self._char_results[1].value << 6) | \
			(self._char_results[2].value << 4) | \
			(self._char_results[3].value << 2) | \
			(self._char_results[4].value << 0)

	@classmethod
	def from_int(cls, as_int: int):
		return GuessResult((
			LetterResult((as_int & 0x300) >> 8),
			LetterResult((as_int & 0x0C0) >> 6),
			LetterResult((as_int & 0x030) >> 4),
			LetterResult((as_int & 0x00C) >> 2),
			LetterResult(as_int & 0x003),
		))

	def __getitem__(self, idx: int):
		return self._char_results[idx]

	def __iter__(self):
		return self._char_results.__iter__()
	
	def __next__(self):
		return self._char_results.__next__()


# Test integer conversions
_test_result = GuessResult((
	LetterResult.correct,
	LetterResult.not_in_solution,
	LetterResult.correct,
	LetterResult.wrong_position,
	LetterResult.wrong_position))
assert GuessResult.from_int(GuessResult.as_int(_test_result)) == _test_result


@dataclass(frozen=True)
class Word:
	word: str
	index: int

	def __post_init__(self):
		if len(self.word) != 5:
			raise ValueError(f'Word does not have 5 letters: "{self.word}"')

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


@dataclass(frozen=True)
class GuessWithResult:
	guess: Word
	result: GuessResult

	def __str__(self):
		return ''.join([
			char_char_results.get_format() + character for character, char_char_results in zip(self.guess, self.result)
		]) + Style.RESET_ALL


def format_guess(guess: Word, result: GuessResult) -> str:
	return str(GuessWithResult(guess=guess, result=result))
