#!/usr/bin/env python3

import itertools
from typing import Optional

from game_types import *
import matching
from solver import Solver
import user_input
from word_list import get_word_from_str


class LetterStatus:

	def __init__(self):
		self.char_status = {
			chr(ch): LetterResult.unknown for ch in range(ord('A'), ord('Z') + 1)
		}

	def _format_char(self, ch: str):
		return self.char_status[ch.upper()].get_format() + ch.upper()

	def print_keyboard(self):
		rows = [
			'QWERTYUIOP',
			'ASDFGHJKL',
			'ZXCVBNM',
		]
		for row in rows:
			print(''.join([self._format_char(ch) for ch in row]) + Style.RESET_ALL + ' ')

	def add_guess(self, guess: GuessWithResult):
		for character, status in zip(guess.guess, guess.result):
			assert character == character.upper()
			if self.char_status[character].value < status.value:
				self.char_status[character] = status


def print_possible_solutions(solver, max_num_to_print=100):
	
	num_possible_solutions = solver.get_num_possible_solutions()

	if (max_num_to_print is not None) and (num_possible_solutions > max_num_to_print):
		# 101+
		print('%i possible solutions' % num_possible_solutions)

	elif num_possible_solutions > 10:
		# 11-100
		print('%i possible solutions:' % num_possible_solutions)
		solutions = sorted(list(solver.get_possible_solitions()))
		for tens in range(len(solutions) // 10 + 1):
			idx_start = tens * 10
			idx_end = min(idx_start + 10, len(solutions))
			print('  ' + ', '.join([str(solution) for solution in solutions[idx_start:idx_end]]))

	elif num_possible_solutions > 1:
		# 2-10
		solutions = sorted([solution for solution in solver.get_possible_solitions()])
		print('%i possible solutions: %s' % (num_possible_solutions, ', '.join([str(s) for s in solutions])))

	else:
		# 1
		print('Only 1 possible solution: %s' % tuple(solver.get_possible_solitions())[0])


def print_most_common_unsolved_letters(solver):
	num_possible_solutions = solver.get_num_possible_solutions()

	if num_possible_solutions > 2:

		unsolved_letters_overall_counter, unsolved_letter_positional_counters = \
			solver.get_unsolved_letters_counter(per_position=True)

		print(
			'Order of most common unsolved letters: ' +
			''.join([letter.upper() for letter, frequency in unsolved_letters_overall_counter.most_common()]))

		for position_idx, position_counter in enumerate(unsolved_letter_positional_counters):
			if position_counter is None:
				continue
			print(
				f'Order of most common position {position_idx + 1} letters: ' +
				''.join([letter.upper() for letter, frequency in position_counter.most_common()]))


class Game:
	def __init__(
			self,
			solution: Word,
			solver: Optional[Solver],
			silent = False,
			specified_guesses: Optional[list[Word]] = None):

		self.solution = solution
		self.solver = solver
		self.silent = silent
		self.guess_results = []

		if specified_guesses is None:
			self.specified_guesses = []
		else:
			def _check_guess(guess: str) -> str:
				if len(guess) != 5:
					raise ValueError('Specified guess "%s" does not have length 5!' % guess.upper())
				# TODO: validate guesses
				return guess.lower()
			self.specified_guesses = [_check_guess(guess) for guess in specified_guesses]

		self.letter_status = None if silent else LetterStatus()

	def print(self, *args, **kwargs):
		if not self.silent:
			print(*args, **kwargs)

	def _show_solution(self):
		print('Solution is %s' % self.solution)

	def _get_guess(self, turn_num: int, auto_solve: bool) -> Word:
		if not self.silent:
			self.letter_status.print_keyboard()
		self.print()

		specified_guess = self.specified_guesses[turn_num - 1] if (turn_num - 1) < len(self.specified_guesses) else None

		if specified_guess:
			self.print('Using specified guess: %s' % specified_guess)
			return get_word_from_str(specified_guess)

		if auto_solve:
			if self.solver is None:
				raise AssertionError('Cannot auto-solve if solver is not given!')
	
			if not self.silent:
				print_possible_solutions(solver=self.solver)
				print_most_common_unsolved_letters(solver=self.solver)

			self.print()
			guess = self.solver.get_best_guess()
			self.print('Using guess from solver: %s' % guess)
			return guess

		extra_commands = {
			'cheat': (lambda: self._show_solution(), 'Show solution')
		}

		if self.solver is not None:
			extra_commands['num'] = (
				lambda: self.print('%i possible solutions' % self.solver.get_num_possible_solutions()),
				'Show number of possible solutions'
			)
			extra_commands['list'] = (
				lambda: print_possible_solutions(solver=self.solver, max_num_to_print=None),
				'List possible solutions'
			)
			extra_commands['stats'] = (
				lambda: print_most_common_unsolved_letters(solver=self.solver),
				'List most common unsolved letters'
			)
			extra_commands['solve'] = (
				lambda: self.print("Solver's best guess is %s" % self.solver.get_best_guess()),
				'Get guess from solver'
			)

		guess = user_input.ask_word(turn_num, extra_commands=extra_commands)
		guess = get_word_from_str(guess)
		
		return guess

	def _handle_guess(self, guess: Word):

		result = matching.get_guess_result(guess=guess, solution=self.solution)
		guess_with_result = GuessWithResult(guess=guess, result=result)

		self.guess_results.append(guess_with_result)

		if self.letter_status is not None:
			self.letter_status.add_guess(guess_with_result)

		if self.solver is not None:
			self.solver.add_guess(guess_with_result)

		self.print()
		for n, guess_to_print in enumerate(self.guess_results):
			self.print('%i: %s' % (n + 1, guess_to_print))
		self.print()

	def play(self, auto_solve: bool, endless=False) -> int:
		"""
		:returns: Number of guesses game was solved in
		"""

		self.print()

		for turn_num in itertools.count(1):

			guess = self._get_guess(turn_num=turn_num, auto_solve=auto_solve)
			self._handle_guess(guess)

			if guess == self.solution:
				self.print('Success!')
				return turn_num

			elif turn_num == 6 and endless:
				self.print('Playing in endless mode - continuing after 6 guesses')
				self.print()

			elif turn_num >= 6 and not endless:
				self.print('Failed, the solution was %s' % self.solution)
				return 0
