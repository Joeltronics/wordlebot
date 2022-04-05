#!/usr/bin/env python3

from copy import copy
import itertools
from typing import Optional

from game_state import GameState
from game_types import *
import matching
from solver import Solver
import user_input
from word_list import get_word_from_str, words


def print_possible_solutions(game_state: GameState, max_num_to_print=100):
	
	num_possible_solutions = game_state.get_num_possible_solutions()

	if (max_num_to_print is not None) and (num_possible_solutions > max_num_to_print):
		# 101+
		print('%i possible solutions' % num_possible_solutions)

	elif num_possible_solutions > 10:
		# 11-100
		print('%i possible solutions:' % num_possible_solutions)
		solutions = sorted(list(game_state.get_possible_solutions()))
		for tens in range(len(solutions) // 10 + 1):
			idx_start = tens * 10
			idx_end = min(idx_start + 10, len(solutions))
			print('  ' + ', '.join([str(solution) for solution in solutions[idx_start:idx_end]]))

	elif num_possible_solutions > 1:
		# 2-10
		solutions = sorted([solution for solution in game_state.get_possible_solutions()])
		print('%i possible solutions: %s' % (num_possible_solutions, ', '.join([str(s) for s in solutions])))

	else:
		# 1
		print('Only 1 possible solution: %s' % tuple(game_state.get_possible_solutions())[0])


def print_most_common_unsolved_letters(game_state: GameState):
	num_possible_solutions = game_state.get_num_possible_solutions()

	if num_possible_solutions > 2:

		unsolved_letters_overall_counter, unsolved_letter_positional_counters = \
			game_state.get_unsolved_letters_counter(per_position=True)

		print(
			'Order of most common unsolved letters: ' +
			''.join([letter.upper() for letter, frequency in unsolved_letters_overall_counter.most_common()]))

		for position_idx, position_counter in enumerate(unsolved_letter_positional_counters):
			if position_counter is None:
				continue
			print(
				f'Order of most common position {position_idx + 1} letters: ' +
				''.join([letter.upper() for letter, frequency in position_counter.most_common()]))

def print_all_letter_combos(game_state):

	debug_print = False

	def combo_to_str(combo: list[Optional[int]]) -> str:
		return ''.join([(letter if letter is not None else '-') for letter in combo])

	green_letters = [None] * 5
	unsolved_positions = set([0, 1, 2, 3, 4])

	for guess in game_state.guesses:
		for idx, (letter, result) in enumerate(guess):
			if result == LetterResult.correct:
				green_letters[idx] = letter
				if idx in unsolved_positions:
					unsolved_positions.remove(idx)

	if debug_print:
		print(f"Fully known letters: {combo_to_str(green_letters)}")

	# Now look at all yellow letters
	# Each time we find a yellow letter:
	# If this yellow letter could be explained by one of the greens we've already found, ignore it
	# Otherwise, add it to the yellow letters list, in position

	yellow_letters = dict()

	for guess in game_state.guesses:

		unique_letters = set(guess.word.word)
		for letter in unique_letters:

			letter_and_status = [
				(idx, status) for idx, (l, status) in enumerate(guess) if l == letter
			]

			assert len(letter_and_status) > 0

			letter_positions_this_guess_yellow = set(
				idx for idx, status in letter_and_status if status == LetterResult.wrong_position
			)

			letter_positions_this_guess_green = set(
				idx for idx, status in letter_and_status if status == LetterResult.correct
			)

			letter_positions_any_guess_green = set(
				idx for idx, l in enumerate(green_letters) if l == letter
			)

			num_unexplained_yellow = len(letter_positions_this_guess_green) + len(letter_positions_this_guess_yellow) - len(letter_positions_any_guess_green)
			if num_unexplained_yellow <= 0:
				continue

			if letter not in yellow_letters.keys():
				yellow_letters[letter] = set()

			yellow_letters[letter] |= letter_positions_this_guess_yellow

	if debug_print:
		print(f'Yellow letters: {repr(yellow_letters)}')

	combos = [
		green_letters
	]

	for letter, positions in yellow_letters.items():

		positions_this_letter_could_be = (set([0, 1, 2, 3, 4]) - positions) & unsolved_positions

		if debug_print:
			print(f'Letter {letter} could be in positions: {repr(positions_this_letter_could_be)}')
		assert len(positions_this_letter_could_be) > 0

		if debug_print:
			print(f'Combos before: {combos}')

		new_combos = []

		for combo in combos:

			empty_positions = set(idx for idx, l in enumerate(combo) if l is None)
			letter_positions_this_combo = empty_positions & positions_this_letter_could_be

			if debug_print:
				print(f'combo {combo_to_str(combo)}, all empty positions {empty_positions}, this letter could be in {letter_positions_this_combo}')

			for letter_idx in letter_positions_this_combo:
				this_new_combo = copy(combo)
				this_new_combo[letter_idx] = letter
				new_combos.append(this_new_combo)

				if debug_print:
					print(f'new combo {this_new_combo}')

		combos = new_combos

		if debug_print:
			print(f'Combos after letter {letter}: {combos}')

	for combo in combos:
		print(combo_to_str(combo))


class Game:
	def __init__(
			self,
			solution: Word,
			solver: Optional[Solver],
			allowed_words: set[Word],
			possible_solutions: set[Word],
			silent = False,
			specified_guesses: Optional[list[Word]] = None):

		self.game_state = GameState(allowed_words=allowed_words, possible_solutions=possible_solutions)

		self.solution = solution
		self.solver = solver
		self.silent = silent

		if specified_guesses is None:
			self.specified_guesses = []
		else:
			def _check_guess(guess: str) -> str:
				if len(guess) != 5:
					raise ValueError('Specified guess "%s" does not have length 5!' % guess.upper())
				# TODO: validate guesses
				return guess.lower()
			self.specified_guesses = [_check_guess(guess) for guess in specified_guesses]

	def print(self, *args, **kwargs):
		if not self.silent:
			print(*args, **kwargs)

	def _show_solution(self):
		print('Solution is %s' % self.solution)

	def _get_guess(self, turn_num: int, auto_solve: bool) -> Word:
		if not self.silent:
			self.game_state.print_keyboard()
		self.print()

		specified_guess = self.specified_guesses[turn_num - 1] if (turn_num - 1) < len(self.specified_guesses) else None

		if specified_guess:
			self.print('Using specified guess: %s' % specified_guess)

			if specified_guess in words:
				return get_word_from_str(specified_guess)
			else:
				print(f'WARNING: "{specified_guess}" is not in valid words list - attempting anyway!')
				return Word(specified_guess, index=None)

		if auto_solve:
			if self.solver is None:
				raise AssertionError('Cannot auto-solve if solver is not given!')
	
			if not self.silent:
				print_possible_solutions(self.game_state)
				print_most_common_unsolved_letters(self.game_state)

			self.print()
			guess = self.solver.get_best_guess()
			self.print('Using guess from solver: %s' % guess)
			return guess

		extra_commands = {
			'cheat': (self._show_solution, 'Show solution'),
			'num': (
				lambda: self.print('%i possible solution(s)' % self.game_state.get_num_possible_solutions()),
				'Show number of possible solutions'
			),
			'list': (
				lambda: print_possible_solutions(self.game_state, max_num_to_print=None),
				'List possible solutions'
			),
			'stats': (
				lambda: print_most_common_unsolved_letters(self.game_state),
				'List most common unsolved letters'
			),
			'combos': (
				lambda: print_all_letter_combos(self.game_state),
				'Print all letter combos'
			)
		}

		if self.solver is not None:
			extra_commands['solve'] = (
				lambda: self.print("Solver's best guess is %s" % self.solver.get_best_guess()),
				'Get guess from solver'
			)

		return user_input.ask_word(turn_num, extra_commands=extra_commands)

	def _handle_guess(self, guess: Guess):

		self.game_state.add_guess(guess)

		if self.solver is not None:
			self.solver.add_guess(guess)

		self.print()
		for n, guess_to_print in enumerate(self.game_state.guesses):
			self.print('%i: %s' % (n + 1, guess_to_print))
		self.print()

	def play(self, auto_solve: bool, endless=False) -> int:
		"""
		:returns: Number of guesses game was solved in
		"""

		self.print()

		for turn_num in itertools.count(1):

			guess_word = self._get_guess(turn_num=turn_num, auto_solve=auto_solve)
			result = matching.get_word_result(guess=guess_word, solution=self.solution)
			guess = Guess(word=guess_word, result=result)
			self._handle_guess(guess)

			if guess_word == self.solution:
				self.print('Success!')
				return turn_num

			elif turn_num == 6 and endless:
				self.print('Playing in endless mode - continuing after 6 guesses')
				self.print()

			elif turn_num >= 6 and not endless:
				self.print('Failed, the solution was %s' % self.solution)
				return 0


class GameAssist:

	silent = False

	def __init__(
			self,
			solver: Solver,
			allowed_words: set[Word],
			possible_solutions: set[Word]):

		self.game_state = GameState(allowed_words=allowed_words, possible_solutions=possible_solutions)
		self.solver = solver

	def print(self, *args, **kwargs):
		if not self.silent:
			print(*args, **kwargs)

	def _get_guess_word(self, turn_num: int) -> Word:
		self.game_state.print_keyboard()
		self.print()

		extra_commands = {
			'num': (
				lambda: self.print('%i possible solution(s)' % self.game_state.get_num_possible_solutions()),
				'Show number of possible solutions'
			),
			'list': (
				lambda: print_possible_solutions(self.game_state, max_num_to_print=None),
				'List possible solutions'
			),
			'stats': (
				lambda: print_most_common_unsolved_letters(self.game_state),
				'List most common unsolved letters'
			),
			'combos': (
				lambda: print_all_letter_combos(self.game_state),
				'Print all letter combos'
			),
			'solve': (
				lambda: self.print("Solver's best guess is %s" % self.solver.get_best_guess()),
				'Get guess from solver'
			),
		}

		return user_input.ask_word(turn_num, extra_commands=extra_commands)

	def _get_guess(self, turn_num: int) -> Guess:
		guess_word = self._get_guess_word(turn_num=turn_num)
		result = user_input.ask_result()
		return Guess(word=guess_word, result=result)

	def _handle_guess(self, guess: Guess) -> bool:
		"""
		:returns: true on success, false if guess was not valid
		"""
		try:
			self.game_state.add_guess(guess)
		except ValueError as ex:
			self.print(f'Invalid word or result: {ex}')
			return False

		self.solver.add_guess(guess)

		self.print()
		for n, guess_to_print in enumerate(self.game_state.guesses):
			self.print('%i: %s' % (n + 1, guess_to_print))
		self.print()
		return True

	def play(self, endless=False):

		self.print()

		for turn_num in itertools.count(1):

			valid_guess = False
			while not valid_guess:
				guess = self._get_guess(turn_num=turn_num)
				valid_guess = self._handle_guess(guess)

			if guess.result == ALL_CORRECT:
				self.print('Success!')
				return


			if turn_num == 6 and endless:
				self.print('Playing in endless mode - continuing after 6 guesses')
				self.print()

			elif turn_num >= 6 and not endless:
				self.print('Failed')
				print_possible_solutions(self.game_state)
				return
