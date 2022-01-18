#!/usr/bin/env python3

import colorama
colorama.init()

import argparse
from colorama import Fore, Back, Style
import itertools
import time
from typing import Iterable, Optional
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

	parser.add_argument('-s', dest='solution', type=str, default=None, help='Set the specific solution')
	parser.add_argument(
		'-l', dest='limit', type=float, default=6,
		help='Limit solver search space complexity (higher means it will run slower but search more comprehensively); specified as a power of 10; default 6')

	parser.add_argument('--all-words', action='store_true', help='Allow all valid words as solutions, not just limited set')
	parser.add_argument('--agnostic', action='store_true', help='Make solver unaware of limited set of possible solutions')
	parser.add_argument('--solve', action='store_true', help="Automatically use solver's guess")
	parser.add_argument('--debug', action='store_true', help='Enable debug printing')
	parser.add_argument('--cheat', action='store_true', help='Show the solution')
	parser.add_argument('--endless', action='store_true', help="Don't end after six guesses if still unsolved")
	parser.add_argument('--benchmark', action='store_true', help='Benchmark performance')

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


class DeterministicPseudorandom:
	"""
	A pretty bad RNG (using a linear congruential generator)
	"""

	def __init__(self, seed: int):
		self.state = seed
		# Values from C++11 minstd_rand
		self.a = 48271
		self.c = 0
		self.m = 2**31 - 1

	def random(self, range: Optional[int]=None):
		self.state = (self.a * self.state + self.c) % self.m

		if range is not None:
			# Not technically a perfeclty fair way to limit range, but close enough for this use case
			return self.state % range
		else:
			return self.state


def pick_solution(args, deterministic_idx: Optional[int] = None):

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

		words = list(word_list.words if args.all_words else word_list.solutions)

		if deterministic_idx is not None:
			words.sort()
			rng = DeterministicPseudorandom(seed=deterministic_idx)
			solution = words[rng.random(range=len(words))]

		else:
			solution = random.choice(words)

		if args.cheat:
			print()
			print('CHEAT MODE: solution is %s' % solution.upper())

	return solution


def play_game(solution, solver: Solver, auto_solve: bool, endless=False) -> int:
	"""
	:returns: Number of guesses game was solved in
	"""

	letter_status = LetterStatus()
	guesses = []

	print()

	for guess_num in itertools.count(1):

		letter_status.print_keyboard()
		print()

		guess = None

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
					'Order of most common unsolved letters: ' +
					''.join([letter.upper() for letter, frequency in most_common_unsolved_letters]))

			print()
			solver_guess = solver.get_best_guess()

		if auto_solve and (solver_guess is not None):
			print('Using guess from solver: %s' % solver_guess.upper())
			guess = solver_guess
		else:
			print('Solver best guess is %s' % solver_guess.upper())
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
			return guess_num

		if guess_num == 6 and endless:
			print('Playing in endless mode - continuing after 6 guesses')
			print()
		elif guess_num >= 6 and not endless:
			print('Failed, the solution was %s' % solution.upper())
			return 0


def benchmark(args, num_benchmark=50):

	results = []

	print()
	print('Benchmarking %i runs...' % num_benchmark)
	print()

	for idx in range(num_benchmark):

		solution = pick_solution(args, deterministic_idx=idx)

		start_time = time.time()

		# TODO: don't print anything, so this isn't slowed down by I/O

		solver = Solver(
			valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
			allowed_words=word_list.words,
			complexity_limit=int(round(10.0 ** args.limit)),
			debug_print=False
		)

		num_guesses = play_game(solution=solution, solver=solver, auto_solve=True, endless=True)

		end_time = time.time()
		duration = end_time - start_time

		solved = (0 < num_guesses <= 6)

		results.append(dict(solution=solution, num_guesses=num_guesses, duration=duration, solved=solved))

	assert len(results) == num_benchmark

	# TODO: figure out which solution had the worst benchmarks

	avg_duration = sum([result['duration'] for result in results]) / len(results)
	max_duration = max([result['duration'] for result in results])
	min_duration = min([result['duration'] for result in results])

	avg_guesses = sum([result['num_guesses'] for result in results]) / len(results)
	max_guesses = max([result['num_guesses'] for result in results])
	min_guesses = min([result['num_guesses'] for result in results])

	num_solved = sum([result['solved'] for result in results])

	print()
	print('Benchmarked %s runs:' % len(results))
	for result in results:
		print("  %s: %i guesses, %f seconds" % (result['solution'].upper(), result['num_guesses'], result['duration']))
	print()
	print('Solved %u/%u (%.1f%%)' % (num_solved, len(results), num_solved / len(results) * 100.0))
	print('Guesses: min %i, average %.2f, max %i' % (min_guesses, avg_guesses, max_guesses))
	print('Time: min %f, average %f, max %f' % (min_duration, avg_duration, max_duration))


def main():
	args = parse_args()
	print('Wordle solver')

	if args.benchmark:
		benchmark(args)
		return

	solution = pick_solution(args)

	solver = Solver(
		valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
		allowed_words=word_list.words,
		complexity_limit=int(round(10.0 ** args.limit)),
		debug_print=args.debug
	)

	play_game(solution=solution, solver=solver, auto_solve=args.solve, endless=args.endless)


if __name__ == "__main__":
	main()
