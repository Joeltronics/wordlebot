#!/usr/bin/env python3


from enum import Enum, unique
from typing import List


@unique
class CharStatus(Enum):
	unknown = 0
	not_in_solution = 1
	wrong_position = 2
	correct = 3


def get_character_statuses(guess: str, solution: str) -> List[CharStatus]:

	assert len(guess) == len(solution)

	guess = guess.lower()
	solution = solution.lower()

	statuses = [CharStatus.unknown for _ in range(5)]

	# 1st pass: green or definite grey
	for n, character in enumerate(guess):

		if character == solution[n]:
			statuses[n] = CharStatus.correct

		elif character not in solution:
			statuses[n] = CharStatus.not_in_solution

	# 2nd pass: letters that are in word but in wrong place - could be yellow or grey depending on green guesses
	for n, character in enumerate(guess):
		if statuses[n] == CharStatus.unknown:
			assert character in solution

			num_this_char_correct = sum([(c == character and s == CharStatus.correct) for c, s in zip(guess, statuses)])
			num_this_char_in_solution = sum([c == character for c in solution])

			assert num_this_char_in_solution >= 1
			assert num_this_char_in_solution >= num_this_char_correct
			num_this_char_in_solution_not_spoken_for = num_this_char_in_solution - num_this_char_correct

			statuses[n] = CharStatus.wrong_position if num_this_char_in_solution_not_spoken_for > 0 else CharStatus.not_in_solution

	assert not any([status == CharStatus.unknown for status in statuses])
	return statuses
