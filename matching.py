#!/usr/bin/env python3


from game_types import *
import word_list

import numpy as np
import sys
import os
from typing import Iterable


GUESS_MAJOR = True

LUT_CACHE_FILE_GUESS_MAJOR = 'cached_lut_guess_major.npy'
LUT_CACHE_FILE_NON_GUESS_MAJOR = 'cached_lut_solution_major.npy'
LUT_CACHE_FILE = LUT_CACHE_FILE_GUESS_MAJOR if GUESS_MAJOR else LUT_CACHE_FILE_NON_GUESS_MAJOR


class MatchingLookupTable:
	def __init__(self) -> None:
		self.lut = None
		self.num_guesses = 0
		self.num_solutions = 0

	def save(self, filename: os.PathLike):
		np.save(filename, self.lut)

	def load(self, filename: os.PathLike) -> bool:
		"""
		:returns: True on success
		"""
		if not os.path.isfile(filename):
			raise FileNotFoundError(filename)

		with open(filename, 'rb') as f:
			new_lut = np.load(f)

		expected_shape = (len(word_list.words), len(word_list.solutions)) if GUESS_MAJOR else (len(word_list.solutions), len(word_list.words))

		# TODO: check guess major, and cache version

		if new_lut.shape != expected_shape:
			print(f'Saved LUT does not have expected shape - expected {expected_shape}, actual {new_lut.shape}. Regenerating...')
			return False

		self.lut = new_lut
		return True

	def is_init(self) -> bool:
		return self.lut is not None

	def init(self) -> None:

		# TODO: allow these to be different
		# (need to account for mismatch when loading - i.e. need to know word list)
		possible_guesses = word_list.words
		possible_solutions = word_list.solutions

		print('0%%...', end='')

		if GUESS_MAJOR:
			self.lut = np.empty((len(possible_guesses), len(possible_solutions)), dtype=np.uint16)

			for guess_idx, guess in enumerate(possible_guesses):
				guess = word_list.get_word_by_idx(guess_idx)
				assert guess.index == guess_idx

				for solution_idx, solution in enumerate(possible_solutions):
					solution = word_list.get_word_by_idx(solution_idx)
					assert solution.index == solution_idx
					result = _calculate_word_result(guess=guess, solution=solution)
					result_as_int = result.as_int()
					assert 0 <= result_as_int < (2**16 - 1)
					self.lut[guess_idx, solution_idx] = result_as_int

				if guess_idx % 100 == 0:
					print('\r%i%%...' % int(round(guess_idx / len(possible_guesses) * 100.0)), end='')

		else:
			self.lut = np.empty((len(possible_solutions), len(possible_guesses)), dtype=np.uint16)

			for solution_idx, solution in enumerate(possible_solutions):
				solution = word_list.get_word_by_idx(solution_idx)
				assert solution.index == solution_idx

				for guess_idx, guess in enumerate(possible_guesses):
					assert guess.index == guess_idx
					guess = word_list.get_word_by_idx(guess_idx)
					result = _calculate_word_result(guess=guess, solution=solution)
					result_as_int = result.as_int()
					assert 0 <= result_as_int < (2**16 - 1)
					self.lut[solution_idx, guess_idx] = result_as_int

				if solution_idx % 100 == 0:
					print('\r%i%%...' % int(round(solution_idx / len(possible_solutions) * 100.0)), end='')

		self.num_guesses = len(possible_guesses)
		self.num_solutions = len(possible_solutions)

		print()

	def lookup_as_int(self, guess: Word, solution: Word) -> int:
		if GUESS_MAJOR:
			return int(self.lut[guess.index, solution.index])
		else:
			return int(self.lut[solution.index, guess.index])

	def lookup(self, guess: Word, solution: Word) -> WordResult:
		return WordResult.from_int(self.lookup_as_int(guess=guess, solution=solution))

	def get_word_result(self, guess: Word, solution: Word) -> WordResult:
		return self.lookup(guess=guess, solution=solution)

	def get_word_result_as_int(self, guess: Word, solution: Word) -> int:
		return self.lookup_as_int(guess=guess, solution=solution)

	def get_word_result_and_solutions_remaining(self, guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> tuple[WordResult, list[Word]]:
		"""
		If we guess this word, and see this result, figure out which words remain
		"""
		result_int = self.lookup_as_int(guess=guess, solution=possible_solution)
		new_possible_solutions = [
			word for word in solutions
			if self.lookup_as_int(guess=guess, solution=word) == result_int
		]

		return WordResult.from_int(result_int), new_possible_solutions

	def solutions_remaining(self, guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> list[Word]:
		"""
		If we guess this word, and see this result, figure out which words remain
		"""
		result_int = self.lookup_as_int(guess=guess, solution=possible_solution)
		new_possible_solutions = [
			word for word in solutions
			if self.lookup_as_int(guess=guess, solution=word) == result_int
		]

		return new_possible_solutions

	def num_solutions_remaining(self, guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> int:
		"""
		If we guess this word, and see this result, figure out how many possible words could be remaining
		"""
		result_int = self.lookup_as_int(guess=guess, solution=possible_solution)
		return sum(
			self.lookup_as_int(guess=guess, solution=word) == result_int
			for word in solutions
		)


_lut = MatchingLookupTable()


def _calculate_word_result(guess: Word, solution: Word) -> WordResult:

	results = [None for _ in range(5)]

	unsolved_chars = list(solution)

	# 1st pass: green or definite grey (yellow is more complicated, since there could be multiple of the same letter)
	for n, character in enumerate(guess):

		if character == solution[n]:
			results[n] = LetterResult.correct
			unsolved_chars[n] = ' '

		elif character not in solution:
			results[n] = LetterResult.not_in_solution

	# 2nd pass: letters that are in word but in wrong place (not necessarily yellow when multiple of same letter in word)
	for n, character in enumerate(guess):
		if results[n] is None:
			assert character in solution
			if character in unsolved_chars:
				results[n] = LetterResult.wrong_position
				unsolved_char_idx = unsolved_chars.index(character)
				unsolved_chars[unsolved_char_idx] = ' '
			else:
				results[n] = LetterResult.not_in_solution

	assert not any([result is None for result in results])
	return WordResult(tuple(results))


def init_lut():
	if os.path.isfile(LUT_CACHE_FILE):
		try:
			print('Loading cached lookup table')
			load_success = _lut.load(LUT_CACHE_FILE)

			if load_success:
				assert _lut.is_init()
				print('Loaded cached lookup table')
				return
			else:
				print('Failed to load cached lookup table')

		except Exception as ex:
			print('Failed to load cached lookup table: %s' % ex)

	print('Generating lookup table...')
	_lut.init()
	print(f'Generating lookup table complete; size: {sys.getsizeof(_lut.lut)}')
	assert _lut.is_init()
	print('Saving lookup table...')
	_lut.save(LUT_CACHE_FILE)
	print('Complete')


def get_word_result(guess: Word, solution: Word) -> WordResult:
	if _lut.is_init():
		return _lut.lookup(guess=guess, solution=solution)
	else:
		return _calculate_word_result(guess=guess, solution=solution)


def is_valid_for_guess(word: Word, guess: Guess) -> bool:
	result_if_this_is_solution = get_word_result(guess=guess.word, solution=word)
	return result_if_this_is_solution == guess.result


def get_word_result_and_solutions_remaining(guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> tuple[WordResult, list[Word]]:
	if _lut.is_init():
		return _lut.get_word_result_and_solutions_remaining(
			guess=guess,
			possible_solution=possible_solution,
			solutions=solutions,
		)
	else:
		result = _calculate_word_result(guess, possible_solution)
		new_possible_solutions = [
			word for word in solutions
			if _calculate_word_result(guess=guess, solution=word) == result
		]

		return result, new_possible_solutions


def solutions_remaining(guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> list[Word]:
	"""
	If we guess this word, and see this result, figure out which words remain
	"""

	if _lut.is_init():
		return _lut.solutions_remaining(
			guess=guess,
			possible_solution=possible_solution,
			solutions=solutions,
		)

	else:
		result = _calculate_word_result(guess, possible_solution)
		new_possible_solutions = [
			word for word in solutions
			if _calculate_word_result(guess=guess, solution=word) == result
		]

		return new_possible_solutions


def num_solutions_remaining(guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> int:
	"""
	If we guess this word, and see this result, figure out how many possible words could be remaining
	"""

	if _lut.is_init():
		return _lut.num_solutions_remaining(
			guess=guess,
			possible_solution=possible_solution,
			solutions=solutions,
		)

	else:
		result = _calculate_word_result(guess, possible_solution)
		return sum(
			_calculate_word_result(guess=guess, solution=word) == result
			for word in solutions
		)


# Inline unit tests

# Basic
assert _calculate_word_result(solution=Word('ABCDE', 1), guess=Word('FGHIJ', 2)) == WordResult((
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution))
assert _calculate_word_result(solution=Word('ABCDE', 1), guess=Word('ACXYZ', 2)) == WordResult((
	LetterResult.correct,
	LetterResult.wrong_position,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution))

# "multiple of same letter" logic
assert _calculate_word_result(solution=Word('MOUNT', 1), guess=Word('BOOKS', 2)) == WordResult((
	LetterResult.not_in_solution,
	LetterResult.correct,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution))
assert _calculate_word_result(solution=Word('MOUNT', 1), guess=Word('BROOK', 2)) == WordResult((
	LetterResult.not_in_solution,
	LetterResult.not_in_solution,
	LetterResult.wrong_position,
	LetterResult.not_in_solution,
	LetterResult.not_in_solution))
assert _calculate_word_result(solution=Word('BOOKS', 1), guess=Word('BROOK', 2)) == WordResult((
	LetterResult.correct,
	LetterResult.not_in_solution,
	LetterResult.correct,
	LetterResult.wrong_position,
	LetterResult.wrong_position))
