#!/usr/bin/env python3

import colorama
colorama.init()

import argparse
from colorama import Fore, Back, Style
from copy import copy
import itertools
from math import sqrt
from statistics import median
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


DEFAULT_NUM_BENCHMARK = 50


def parse_args():
	parser = argparse.ArgumentParser()

	group = parser.add_argument_group('Game')
	group.add_argument('-s', dest='solution', type=str, default=None, help='Specify a solution')
	group.add_argument('-g', metavar='GUESS', dest='guesses', type=str, nargs='+', help='Specify first guesses')
	group.add_argument('--all-words', action='store_true', help='Allow all valid words as solutions, not limited set')
	group.add_argument('--endless', action='store_true', help="Don't end after six guesses if still unsolved")
	group.add_argument('--solve', action='store_true', help="Automatically use solver's guess")

	group = parser.add_argument_group('Solver')
	group.add_argument(
		'-l', dest='limit', type=float, default=4,
		help='Limit solver search space complexity (i.e. higher will do a better job of solving, but run much slower). Specified as a power of 10. Default 4.')
	group.add_argument('--agnostic', action='store_true', help='Make solver unaware of limited set of possible solutions')

	group = parser.add_argument_group('Benchmarking & A/B testing')
	group.add_argument(
		'-b', metavar='RUNS', dest='benchmark', type=int, default=None,
		help='Benchmark performance')
	group.add_argument('--benchmark', dest='benchmark', action='store_const', const=DEFAULT_NUM_BENCHMARK, help='Equivalent to -b %i' % DEFAULT_NUM_BENCHMARK)
	group.add_argument('--ab', dest='a_b_test', action='store_true', help='Benchmark A/B test (currently hard-coded to compare --agnostic against not)')

	group = parser.add_argument_group('Debugging')
	group.add_argument('--cheat', action='store_true', help='Show the solution before starting the game')
	group.add_argument('--debug', action='store_true', help='Enable debug printing')

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


def play_game(solution, solver: Solver, auto_solve: bool, endless=False, silent=False, specified_guesses=None) -> int:
	"""
	:returns: Number of guesses game was solved in
	"""

	def game_print(*args, **kwargs):
		if not silent:
			print(*args, **kwargs)

	if specified_guesses is None:
		specified_guesses = []
	else:
		def _check_guess(guess: str) -> str:
			if len(guess) != 5:
				raise ValueError('Specified guess "%s" does not have length 5!' % guess.upper())
			# TODO: warn if guess isn't in list of allowed guesses
			return guess.lower()
		specified_guesses = [_check_guess(guess) for guess in specified_guesses]

	letter_status = LetterStatus()
	guesses = []

	game_print()

	for guess_num in itertools.count(1):

		if not silent:
			letter_status.print_keyboard()
		game_print()

		specified_guess = specified_guesses[guess_num - 1] if (guess_num - 1) < len(specified_guesses) else None

		solver_guess = None

		if (solver is not None) and (not specified_guess):

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

		if specified_guess:
			game_print('Using specified guess: %s' % specified_guess.upper())
			guess = specified_guess
		elif auto_solve and (solver_guess is not None):
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
		self.squared_sum = 0
		self.count = 0
		self.min = None
		self.max = None
		self.values = []

	def add(self, value):
		self.sum += value
		self.squared_sum += value * value
		self.count += 1
		self.min = value if self.min is None else min(value, self.min)
		self.max = value if self.max is None else max(value, self.max)
		self.values.append(value)

	def mean(self):
		if self.count == 0:
			return 0
		return self.sum / self.count

	def mean_squared(self):
		if self.count == 0:
			return 0
		return self.squared_sum / self.count

	def rms(self):
		return sqrt(self.mean_squared())

	def median(self):
		if self.count == 0:
			return 0
		return median(self.values)

class ABTestInstance:
	def __init__(self, name: Optional[str] = None, solver_args: Optional[dict] = None):
		self.name = name
		self.solver_args = solver_args if solver_args is not None else dict()
		self.num_guesses_stats = RollingStats()
		self.duration_stats = RollingStats()
		self.num_solved = 0

	def add_result(self, num_guesses: int, duration: float):
		solved = (0 < num_guesses <= 6)
		self.num_guesses_stats.add(num_guesses)
		self.duration_stats.add(duration)
		if solved:
			self.num_solved += 1


def benchmark(args, a_b_test: bool, num_benchmark=50):

	results = []

	duration_stats = RollingStats()
	num_guesses_stats = RollingStats()
	num_solved = 0

	default_solver_args = dict(
		valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
		allowed_words=word_list.words,
		complexity_limit=int(round(10.0 ** args.limit)),
		verbosity=SolverVerbosity.silent,
	)

	if a_b_test:
		a_b_tests = [
			ABTestInstance(name='Agnostic', solver_args=dict(valid_solutions=word_list.words)),
			ABTestInstance(name='Knowledgeable', solver_args=dict(valid_solutions=word_list.solutions)),

			#ABTestInstance(name='Complexity 1,000', solver_args=dict(complexity_limit=1000)),
			#ABTestInstance(name='Complexity 100,000', solver_args=dict(complexity_limit=100000)),
		]
	else:
		a_b_tests = [
			ABTestInstance()
		]

	print()
	print('Benchmarking %i runs...' % num_benchmark)
	print()
	if len(a_b_tests) > 1:
		print('        ' + ''.join(['   %-15s' % test.name for test in a_b_tests]))
		print('Solution' + ('   Guesses    Time' * len(a_b_tests)))
	else:
		print('Solution   Guesses    Time')
	print()

	for solution_idx in range(num_benchmark):

		solution = pick_solution(args, deterministic_idx=solution_idx, do_print=False)

		results_per_solver = []

		for a_b_test in a_b_tests:
			this_solver_args = copy(default_solver_args)
			this_solver_args.update(a_b_test.solver_args)

			# TODO: benchmark time per guess (plus solver construction), in addition to total
			# First guess should be fast, last guess may be fast as well; intermediate guess time is a more interesting stat
			start_time = time.time()

			solver = Solver(**this_solver_args)
			num_guesses = play_game(solution=solution, solver=solver, auto_solve=True, endless=True, silent=True, specified_guesses=args.guesses)

			end_time = time.time()
			duration = end_time - start_time

			solved = (0 < num_guesses <= 6)
			if solved:
				num_solved += 1

			a_b_test.add_result(num_guesses=num_guesses, duration=duration)
			results_per_solver.append((num_guesses, duration))

		print_str = '%8s' % solution.upper()

		for num_guesses, duration in results_per_solver:
			print_str += '   %s%7i%s   %.3f' % (
				get_format_for_num_guesses(num_guesses), num_guesses, Style.RESET_ALL,
				duration
			)

		print(print_str)

	# TODO: print which solution had the worst benchmarks
	# TODO: for A/B testing, print scores of one vs the other

	print()
	print('Benchmarked %s runs:' % num_benchmark)

	for a_b_test in a_b_tests:
		if len(a_b_tests) > 1:
			print()
			print('%s:' % a_b_test.name)
		print('  Solved %u/%u (%.1f%%)' % (a_b_test.num_solved, num_benchmark, a_b_test.num_solved / num_benchmark * 100.0))
		print('  Guesses: best %i, median %g, mean %.2f, RMS %.2f, worst %i' % (
			a_b_test.num_guesses_stats.min,
			a_b_test.num_guesses_stats.median(),
			a_b_test.num_guesses_stats.mean(),
			a_b_test.num_guesses_stats.rms(),
			a_b_test.num_guesses_stats.max))
		print('  Time: best %.3f, median %.3f, mean %.3f, RMS %.3f, worst %.3f' % (
			a_b_test.duration_stats.min,
			a_b_test.duration_stats.median(),
			a_b_test.duration_stats.mean(),
			a_b_test.duration_stats.rms(),
			a_b_test.duration_stats.max))


def main():
	args = parse_args()
	print('Wordle solver')

	if args.benchmark or args.a_b_test:
		benchmark(args, a_b_test=args.a_b_test, num_benchmark=(args.benchmark if args.benchmark else DEFAULT_NUM_BENCHMARK))
		return

	solution = pick_solution(args)

	solver = Solver(
		valid_solutions=(word_list.words if (args.all_words or args.agnostic) else word_list.solutions),
		allowed_words=word_list.words,
		complexity_limit=int(round(10.0 ** args.limit)),
		verbosity=(SolverVerbosity.debug if args.debug else SolverVerbosity.regular),
	)

	play_game(solution=solution, solver=solver, auto_solve=args.solve, endless=args.endless, specified_guesses=args.guesses)


if __name__ == "__main__":
	main()
