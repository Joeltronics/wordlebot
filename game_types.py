#!/usr/bin/env python3


from enum import Enum, unique
from typing import List


@unique
class CharStatus(Enum):
	unknown = 0
	not_in_solution = 1
	wrong_position = 2
	correct = 3


def get_character_statuses(guess: str, solution: str) -> tuple[CharStatus, CharStatus, CharStatus, CharStatus, CharStatus]:

	assert len(guess) == 5
	assert len(solution) == 5

	guess = guess.lower()
	solution = solution.lower()

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
	return tuple(statuses)


# Inline unit tests

# Basic
assert get_character_statuses(solution='abcde', guess='fghij') == (
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert get_character_statuses(solution='abcde', guess='acxyz') == (
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)

# "multiple of same letter" logic
assert get_character_statuses(solution='mount', guess='books') == (
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert get_character_statuses(solution='mount', guess='brook') == (
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert get_character_statuses(solution='books', guess='brook') == (
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.wrong_position)
