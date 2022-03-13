#!/usr/bin/env python3


from game_types import *

from typing import Iterable, List


def _calculate_character_statuses(guess: str, solution: str) -> tuple[CharStatus, CharStatus, CharStatus, CharStatus, CharStatus]:

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


def get_character_statuses(guess: str, solution: str) -> tuple[CharStatus, CharStatus, CharStatus, CharStatus, CharStatus]:
	return _calculate_character_statuses(guess=guess, solution=solution)


def is_valid_for_guess(word: str, guess: tuple[str, Iterable[CharStatus]]) -> bool:
	guess_word, guess_char_statuses = guess
	status_if_this_is_solution = get_character_statuses(guess=guess_word, solution=word)
	return status_if_this_is_solution == guess_char_statuses


def solutions_remaining(guess: str, possible_solution: str, solutions: Iterable[str], return_character_status=False) -> List[str]:
	"""
	If we guess this word, and see this result, figure out which words remain
	"""
	# TODO: this is a bottleneck, see if it can be optimized
	character_status = get_character_statuses(guess, possible_solution)
	# TODO: we only need the list length; it may be faster just to instead use:
	#new_possible_solutions = sum([is_valid_for_guess(word, (guess, character_status)) for word in solutions])
	new_possible_solutions = [word for word in solutions if is_valid_for_guess(word, (guess, character_status))]

	if return_character_status:
		return new_possible_solutions, character_status
	else:
		return new_possible_solutions


def num_solutions_remaining(guess: str, possible_solution: str, solutions: Iterable[str]) -> int:
	"""
	If we guess this word, and see this result, figure out how many possible words could be remaining
	"""
	return len(solutions_remaining(guess=guess, possible_solution=possible_solution, solutions=solutions))


# Inline unit tests

# Basic
assert _calculate_character_statuses(solution='abcde', guess='fghij') == (
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert _calculate_character_statuses(solution='abcde', guess='acxyz') == (
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)

# "multiple of same letter" logic
assert _calculate_character_statuses(solution='mount', guess='books') == (
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert _calculate_character_statuses(solution='mount', guess='brook') == (
	CharStatus.not_in_solution,
	CharStatus.not_in_solution,
	CharStatus.wrong_position,
	CharStatus.not_in_solution,
	CharStatus.not_in_solution)
assert _calculate_character_statuses(solution='books', guess='brook') == (
	CharStatus.correct,
	CharStatus.not_in_solution,
	CharStatus.correct,
	CharStatus.wrong_position,
	CharStatus.wrong_position)
