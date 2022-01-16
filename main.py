#!/usr/bin/env python3

import colorama
colorama.init()

import argparse
from colorama import Fore, Back, Style
from typing import List, Iterable
import random

from game_types import *
from solver import Solver
import word_list
import user_input


FORMAT_UNKOWN = Back.BLACK + Fore.WHITE
FORMAT_CORRECT = Back.GREEN + Fore.WHITE
FORMAT_WRONG_POSITION = Back.YELLOW + Fore.WHITE
FORMAT_NOT_IN_SOLUTION = Back.WHITE + Fore.BLACK


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', '--solution', type=str, default=None, help='Set the specific solution')
	parser.add_argument('--all-words', action='store_true', help='Allow all valid words as solutions, not just limited set')
	parser.add_argument('--agnostic', action='store_true', help='Make solver unaware of limited set of possible solutions')
	parser.add_argument('--cheat', action='store_true', help='Show the solution')
	return parser.parse_args()


def get_format(char_status: CharStatus) -> str:
	return {
		CharStatus.unknown:         FORMAT_UNKOWN,
		CharStatus.not_in_solution: FORMAT_NOT_IN_SOLUTION,
		CharStatus.wrong_position:  FORMAT_WRONG_POSITION,
		CharStatus.correct:         FORMAT_CORRECT,
	}[char_status]


def format_guess(guess: str, statuses: Iterable[CharStatus]) -> str:
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

	def add_guess(self, guess, statuses):
		for character, status in zip(guess.lower(), statuses):
			if self.char_status[character].value < status.value:
				self.char_status[character] = status


def pick_solution(args):

	print('%u total allowed words, %u possible solutions' % (len(word_list.words), len(word_list.solutions)))

	if args.solution is not None:

		solution = args.solution.strip().lower()

		if len(solution) != 5:
			print('ERROR: "%s" is not a valid solution, must have length 5' % solution.upper())
			exit(1)
		elif solution not in word_list.words:
			print('WARNING: "%s" is not a valid word; proceeding with game anyway' % solution.upper())
			print()
		elif (solution not in word_list.solutions) and not args.all_words:
			print('WARNING: "%s" is an accepted word, but not in solutions list; proceeding with game anyway' % solution.upper())
			print()

		print('Solution given: %s' % solution.upper())

	else:
		if args.all_words:
			solution = random.choice(list(word_list.words))
		else:
			solution = random.choice(list(word_list.solutions))

		if args.cheat:
			print()
			print('CHEAT MODE: solution is %s' % solution.upper())

	return solution


def play_game(solution, solver: Solver):

	letter_status = LetterStatus()
	guesses = []

	do_solver = True

	print()

	for guess_num in range(1,7):
		letter_status.print_keyboard()
		print()

		if solver is not None:

			num_possible_solutions = solver.get_num_possible_solutions()

			if num_possible_solutions > 100:
				# 101+
				print('%i possible solutions' % num_possible_solutions)

			elif num_possible_solutions > 10:
				# 11-100
				print('%i possible solutions:' % num_possible_solutions)
				solutions = sorted(list(solver.get_possible_solitions()))
				for tens in range(len(solutions) // 10 + 1):
					idx_start = tens * 10
					idx_end = min(idx_start + 10, len(solutions))
					print('  ' + ', '.join([solution.upper() for solution in solutions[idx_start:idx_end]]))

			elif num_possible_solutions > 1:
				# 2-10
				solutions = sorted([solution.upper() for solution in solver.get_possible_solitions()])
				print('%i possible solutions: %s' % (num_possible_solutions, ', '.join(solutions)))

			else:
				# 1
				print('Only 1 possible solution: %s' % tuple(solver.get_possible_solitions())[0].upper())

			if num_possible_solutions > 1:
				most_common_unsolved_letters = solver.get_most_common_unsolved_letters()
				print(
					'Most common unsolved letters: ' +
					''.join([letter.upper() for letter, frequency in most_common_unsolved_letters]))

			print()
			solver.get_best_guess()

		guess = user_input.ask_word(guess_num)

		guesses.append(guess)
		statuses = get_character_statuses(guess=guess, solution=solution)

		letter_status.add_guess(guess, statuses)
		solver.add_guess(guess, statuses)

		print()
		for n, this_guess in enumerate(guesses):
			statuses = get_character_statuses(guess=this_guess, solution=solution)
			print('%i: %s' % (n + 1, format_guess(this_guess, statuses)))
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

	solver = Solver(
		valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
		allowed_words=word_list.words,
	)

	play_game(solution=solution, solver=solver)


if __name__ == "__main__":
	main()
