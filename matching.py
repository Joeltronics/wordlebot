#!/usr/bin/env python3


from game_types import *
import word_list

import numpy as np
import sys
import os
from typing import Iterable, List

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
					status = _calculate_character_statuses(guess=guess, solution=solution)
					status_as_int = status.as_int()
					assert 0 <= status_as_int < (2**16 - 1)
					self.lut[guess_idx, solution_idx] = status_as_int

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
					status = _calculate_character_statuses(guess=guess, solution=solution)
					status_as_int = status.as_int()
					assert 0 <= status_as_int < (2**16 - 1)
					self.lut[solution_idx, guess_idx] = status_as_int

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

	def lookup(self, guess: Word, solution: Word) -> WordCharStatus:
		return WordCharStatus.from_int(self.lookup_as_int(guess=guess, solution=solution))


_lut = MatchingLookupTable()


def _calculate_character_statuses(guess: Word, solution: Word) -> WordCharStatus:

	statuses = [None for _ in range(5)]

	unsolved_chars = list(solution)

	# 1st pass: green or definite grey (yellow is more complicated, since there could be multiple of the same letter)
	for n, character in enumerate(guess):

		if character == solution[n]:
			statuses[n] = CharStatus.correct
			unsolved_chars[n] = ' '

		elif character not in solution:
			statuses[n] = CharStatus.not_in_solution

	# 2nd pass: letters that are in word but in wrong place (not necessarily yellow when multiple of same letter in word)
	for n, character in enumerate(guess):
		if statuses[n] is None:
			assert character in solution
			if character in unsolved_chars:
				statuses[n] = CharStatus.wrong_position
				unsolved_char_idx = unsolved_chars.index(character)
				unsolved_chars[unsolved_char_idx] = ' '
			else:
				statuses[n] = CharStatus.not_in_solution

	assert not any([status is None for status in statuses])
	return WordCharStatus(tuple(statuses))


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


def get_character_statuses(guess: Word, solution: Word) -> WordCharStatus:
	if _lut.is_init():
		return _lut.lookup(guess=guess, solution=solution)
	else:
		return _calculate_character_statuses(guess=guess, solution=solution)


def is_valid_for_guess(word: Word, guess: tuple[Word, WordCharStatus]) -> bool:
	status_if_this_is_solution = get_character_statuses(guess=guess[0], solution=word)
	return status_if_this_is_solution == guess[1]


def solutions_remaining(guess: Word, possible_solution: Word, solutions: Iterable[Word], return_character_status=False) -> List[Word]:
	"""
	If we guess this word, and see this result, figure out which words remain
	"""
	# TODO: this is a bottleneck, see if it can be optimized
	character_status = get_character_statuses(guess, possible_solution)
	new_possible_solutions = [
		word for word in solutions
		if get_character_statuses(guess=guess, solution=word) == character_status
	]

	if return_character_status:
		return new_possible_solutions, character_status
	else:
		return new_possible_solutions


def num_solutions_remaining(guess: Word, possible_solution: Word, solutions: Iterable[Word]) -> int:
	"""
	If we guess this word, and see this result, figure out how many possible words could be remaining
	"""
	character_status = get_character_statuses(guess, possible_solution)
	return sum(
		get_character_statuses(guess=guess, solution=word) == character_status
		for word in solutions
	)


# Inline unit tests

# Basic
assert _calculate_character_statuses(solution=Word('ABCDE', 1), guess=Word('FGHIJ', 2)) == WordCharStatus((
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution))
assert _calculate_character_statuses(solution=Word('ABCDE', 1), guess=Word('ACXYZ', 2)) == WordCharStatus((
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution))

# "multiple of same letter" logic
assert _calculate_character_statuses(solution=Word('MOUNT', 1), guess=Word('BOOKS', 2)) == WordCharStatus((
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution))
assert _calculate_character_statuses(solution=Word('MOUNT', 1), guess=Word('BROOK', 2)) == WordCharStatus((
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution))
assert _calculate_character_statuses(solution=Word('BOOKS', 1), guess=Word('BROOK', 2)) == WordCharStatus((
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.wrong_position))
