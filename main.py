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
from solver import Solver, SolverVerbosity
import word_list
import user_input


FORMAT_UNKOWN = Back.BLACK + Fore.WHITE
FORMAT_CORRECT = Back.GREEN + Fore.WHITE
FORMAT_WRONG_POSITION = Back.YELLOW + Fore.WHITE
FORMAT_NOT_IN_SOLUTION = Back.WHITE + Fore.BLACK


def parse_args():
	parser = argparse.ArgumentParser()

	parser.add_argument('-s', dest='solution', type=str, default=None, help='Specify a solution')
	parser.add_argument(
		'-l', dest='limit', type=float, default=6,
		help='Limit solver search space complexity (i.e. higher will do a better job of solving, but run much slower). Specified as a power of 10. Default 6.')
	parser.add_argument(
		'-b', metavar='RUNS', dest='benchmark', type=int, default=None,
		help='Benchmark performance')

	parser.add_argument('--benchmark', dest='benchmark', action='store_const', const=50, help='Equivalent to -b 50')
	parser.add_argument('--all-words', action='store_true', help='Allow all valid words as solutions, not just limited set')
	parser.add_argument('--agnostic', action='store_true', help='Make solver unaware of limited set of possible solutions')
	parser.add_argument('--solve', action='store_true', help="Automatically use solver's guess")
	parser.add_argument('--debug', action='store_true', help='Enable debug printing')
	parser.add_argument('--cheat', action='store_true', help='Show the solution')
	parser.add_argument('--endless', action='store_true', help="Don't end after six guesses if still unsolved")

	args = parser.parse_args()

	if args.limit < 0:
		raise ValueError('Minimum -l value is 0')

	return args


def get_format(char_status: CharStatus) -> str:
	return {
		CharStatus.unknown:         FORMAT_UNKOWN,
		CharStatus.not_in_solution: FORMAT_NOT_IN_SOLUTION,
		CharStatus.wrong_position:  FORMAT_WRONG_POSITION,
		CharStatus.correct:         FORMAT_CORRECT,
	}[char_status]


def get_format_for_num_guesses(num_guesses: int) -> str:
	if num_guesses < 1:
		raise ValueError('num_guesses must be >= 1')

	# I know this isn't in hue order, but green=best, yellow=bad, red=worst made the most sense,
	# so this is the only place blue fits
	return [
		Back.RESET + Fore.WHITE,  # 1
		Back.RESET + Fore.GREEN,  # 2
		Back.RESET + Fore.CYAN,   # 3
		Back.RESET + Fore.BLUE,   # 4
		Back.RESET + Fore.YELLOW, # 5
		Back.RESET + Fore.RED,    # 6
		Back.RED + Fore.WHITE,    # >= 7
	][min(num_guesses - 1, 6)]



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


def pick_solution(args, deterministic_idx: Optional[int] = None, do_print=True):

	if do_print:
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


def play_game(solution, solver: Solver, auto_solve: bool, endless=False, silent=False) -> int:
	"""
	:returns: Number of guesses game was solved in
	"""

	def game_print(*args, **kwargs):
		if not silent:
			print(*args, **kwargs)

	letter_status = LetterStatus()
	guesses = []

	game_print()

	for guess_num in itertools.count(1):

		if not silent:
			letter_status.print_keyboard()
		game_print()

		solver_guess = None

		if solver is not None:

			num_possible_solutions = solver.get_num_possible_solutions()

			if num_possible_solutions > 100:
				# 101+
				game_print('%i possible solutions' % num_possible_solutions)

			elif num_possible_solutions > 10:
				# 11-100
				game_print('%i possible solutions:' % num_possible_solutions)
				solutions = sorted(list(solver.get_possible_solitions()))
				for tens in range(len(solutions) // 10 + 1):
					idx_start = tens * 10
					idx_end = min(idx_start + 10, len(solutions))
					game_print('  ' + ', '.join([solution.upper() for solution in solutions[idx_start:idx_end]]))

			elif num_possible_solutions > 1:
				# 2-10
				solutions = sorted([solution.upper() for solution in solver.get_possible_solitions()])
				game_print('%i possible solutions: %s' % (num_possible_solutions, ', '.join(solutions)))

			else:
				# 1
				game_print('Only 1 possible solution: %s' % tuple(solver.get_possible_solitions())[0].upper())

			if num_possible_solutions > 1:
				most_common_unsolved_letters = solver.get_most_common_unsolved_letters()
				game_print(
					'Order of most common unsolved letters: ' +
					''.join([letter.upper() for letter, frequency in most_common_unsolved_letters]))

			game_print()
			solver_guess = solver.get_best_guess()

		if auto_solve and (solver_guess is not None):
			game_print('Using guess from solver: %s' % solver_guess.upper())
			guess = solver_guess
		else:
			game_print('Solver best guess is %s' % solver_guess.upper())
			guess = user_input.ask_word(guess_num)

		guesses.append(guess)
		statuses = get_character_statuses(guess=guess, solution=solution)

		letter_status.add_guess(guess, statuses)
		solver.add_guess(guess, statuses)

		game_print()
		for n, this_guess in enumerate(guesses):
			statuses = get_character_statuses(guess=this_guess, solution=solution)
			game_print('%i: %s' % (n + 1, format_guess(this_guess, statuses)))
		game_print()
		
		if guess == solution:
			game_print('Success!')
			return guess_num

		if guess_num == 6 and endless:
			game_print('Playing in endless mode - continuing after 6 guesses')
			game_print()
		elif guess_num >= 6 and not endless:
			game_print('Failed, the solution was %s' % solution.upper())
			return 0


class RollingStats:
	def __init__(self):
		self.sum = 0
		self.count = 0
		self.min = None
		self.max = None

	def add(self, value):
		self.sum += value
		self.count += 1
		self.min = value if self.min is None else min(value, self.min)
		self.max = value if self.max is None else min(value, self.max)

	def mean(self):
		if self.count == 0:
			return 0
		return self.sum / self.count

def benchmark(args, num_benchmark=50):

	results = []

	print()
	print('Benchmarking %i runs...' % num_benchmark)
	print()
	print('Solution   Guesses   Time')
	print()

	duration_stats = RollingStats()
	num_guesses_stats = RollingStats()
	num_solved = 0

	for idx in range(num_benchmark):

		solution = pick_solution(args, deterministic_idx=idx, do_print=False)

		# TODO: benchmark time per guess (plus solver construction), in addition to total
		# First guess should be fast, last guess may be fast as well; intermediate guess time is a more interesting stat
		start_time = time.time()

		solver = Solver(
			valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
			allowed_words=word_list.words,
			complexity_limit=int(round(10.0 ** args.limit)),
			verbosity = SolverVerbosity.silent,
		)

		num_guesses = play_game(solution=solution, solver=solver, auto_solve=True, endless=True, silent=True)

		end_time = time.time()
		duration = end_time - start_time

		solved = (0 < num_guesses <= 6)
		if solved:
			num_solved += 1

		duration_stats.add(duration)
		num_guesses_stats.add(num_guesses)

		results.append(dict(solution=solution, num_guesses=num_guesses, duration=duration, solved=solved))

		# TODO: Print with color (according to how bad it was)
		print('%8s   %s%7i%s   %.3f' % (solution.upper(), get_format_for_num_guesses(num_guesses), num_guesses, Style.RESET_ALL, duration))

	assert len(results) == num_benchmark

	# TODO: print which solution had the worst benchmarks

	print()
	print('Benchmarked %s runs:' % len(results))
	print('  Solved %u/%u (%.1f%%)' % (num_solved, len(results), num_solved / len(results) * 100.0))
	print('  Guesses: best %i, average %.2f, worst %i' % (num_guesses_stats.min, num_guesses_stats.mean(), num_guesses_stats.max))
	print('  Time: worst %f, average %f, best %f' % (duration_stats.min, duration_stats.mean(), duration_stats.max))


def main():
	args = parse_args()
	print('Wordle solver')

	if args.benchmark:
		benchmark(args, num_benchmark=args.benchmark)
		return

	solution = pick_solution(args)

	solver = Solver(
		valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
		allowed_words=word_list.words,
		complexity_limit=int(round(10.0 ** args.limit)),
		verbosity=(SolverVerbosity.debug if args.debug else SolverVerbosity.regular),
	)

	play_game(solution=solution, solver=solver, auto_solve=args.solve, endless=args.endless)


if __name__ == "__main__":
	main()
