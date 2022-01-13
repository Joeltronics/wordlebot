#!/usr/bin/env python3

from colorama import Fore, Back, Style
import colorama
colorama.init()

import argparse
from enum import Enum, unique
from typing import List
import random

import word_list
import user_input


FORMAT_UNKOWN = Back.BLACK + Fore.WHITE
FORMAT_CORRECT = Back.GREEN + Fore.WHITE
FORMAT_WRONG_POSITION = Back.YELLOW + Fore.WHITE
FORMAT_NOT_IN_SOLUTION = Back.WHITE + Fore.BLACK


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', '--solution', type=str, default=None, help='Set the specific solution')
	parser.add_argument('--cheat', action='store_true', help='Show the solution')
	return parser.parse_args()


@unique
class CharStatus(Enum):
	unknown = 0
	not_in_solution = 1
	wrong_position = 2
	correct = 3


def get_format(char_status: CharStatus) -> str:
	return {
		CharStatus.unknown:         FORMAT_UNKOWN,
		CharStatus.not_in_solution: FORMAT_NOT_IN_SOLUTION,
		CharStatus.wrong_position:  FORMAT_WRONG_POSITION,
		CharStatus.correct:         FORMAT_CORRECT,
	}[char_status]


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


def format_guess(guess: str, solution: str) -> str:
	statuses = get_character_statuses(guess=guess, solution=solution)
	return ''.join([
		get_format(status) + character.upper() for character, status in zip(guess, statuses)
	]) + Style.RESET_ALL


class LetterStatus:

	def __init__(self):
		self.char_status = {
			chr(ch): CharStatus.unknown for ch in range(ord('a'), ord('z') + 1)
		}

	def _format_char(self, ch: str):
		return get_format(self.char_status[ch.lower()]) + ch.upper()

	def print_keyboard(self):
		rows = [
			'QWERTYUIOP',
			'ASDFGHJKL',
			'ZXCVBNM',
		]
		for row in rows:
			print(''.join([self._format_char(ch) for ch in row]) + Style.RESET_ALL)

	def add_guess(self, guess, solution):

		assert len(guess) == len(solution)
		guess = guess.lower()
		solution = solution.lower()

		statuses = get_character_statuses(guess=guess, solution=solution)

		for character, status in zip(guess, statuses):
			if self.char_status[character].value < status.value:
				self.char_status[character] = status


def pick_solution(args):

	print('%u total allowed words' % (len(word_list.words)))


	if args.solution is not None:

		solution = args.solution.strip().lower()

		if len(solution) != 5:
			print('ERROR: "%s" is not a valid solution, must have length 5' % solution.upper())
			exit(1)

		if solution not in word_list.words:
			print('WARNING: "%s" is not a valid word; proceeding with game anyway' % solution.upper())
			print()

		print('Solution given: %s' % solution.upper())

	else:
		solution = random.choice(list(word_list.words))
		if args.cheat:
			print()
			print('CHEAT MODE: solution is %s' % solution.upper())

	return solution


def play_game(solution):

	letter_status = LetterStatus()
	guesses = []

	print()

	for guess_num in range(1,7):
		letter_status.print_keyboard()
		print()
		guess = user_input.ask_word(guess_num)
		
		guesses.append(guess)
		letter_status.add_guess(guess, solution)
		
		print()
		for n, word in enumerate(guesses):
			print('%i: %s' % (n + 1, format_guess(word, solution)))
		print()
		
		if guess == solution:
			print('Success!')
			return

	else:
		print('Failed, the solution was %s' % solution.upper())


def main():
	args = parse_args()
	print('Wordle solver')
	solution = pick_solution(args)
	play_game(solution)


if __name__ == "__main__":
	main()
