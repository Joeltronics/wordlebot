#!/usr/bin/env python3

from typing import Optional, Callable
from game_types import WordResult, LetterResult, Word

import word_list


_falsy_words = ['n', 'no', '0', 'false']
_truthy_words = ['y', 'yes', '1', 'true']
_exit_words = ['q', 'x', 'quit', 'exit']


def ask_word(guess_num: int, extra_commands: Optional[dict[str, tuple[Callable, str]]]=None) -> Word:

	while True:
		if guess_num <= 6:
			input_str = 'Enter guess %i/6 (or "!help" for a list of extra commands): '
		else:
			input_str = 'Enter guess %i (or "!help" for a list of extra commands): '

		user_input = input(input_str % guess_num).strip()

		if not user_input:
			continue

		user_input = user_input.lower()

		if user_input in _exit_words:
			raise SystemExit()

		elif user_input == '!help':

			print('')
			print('Extra commands:')
			print('  %-10s show this help message' % '!help')
			print('  %-10s quit' % _exit_words[0])
			if extra_commands:
				for key, command in sorted(extra_commands.items()):
					print('  !%-9s %s' % (key, command[1]))
			continue

		elif user_input.startswith('!'):
			command = user_input[1:]
			if extra_commands and command in extra_commands.keys():
				extra_commands[command][0]()
			else:
				print('Unknown command: "!%s". Enter "!help" for a list of commands' % command)
			continue

		guess = user_input.upper()

		# Debug feature: start with '!' to force allowing a guess
		allow_invalid = False
		if guess.endswith('!'):
			allow_invalid = True
			guess = guess[:-1]

		if len(guess) != 5:
			print('Guess must be length 5')
			continue
		
		if guess not in word_list.words:
			if allow_invalid:
				print('Allowing invalid word "%s" because you yelled it' % guess.upper())
				return Word(word=guess, index=None)
			else:
				print('Invalid word: %s' % guess.upper())
				continue

		return word_list.get_word_from_str(guess)


def ask_result() -> WordResult:
	while True:

		user_input = input('Enter result - 0=grey, 1=yellow, 2=green: ').strip()

		if not user_input:
			continue

		if user_input.lower() in _exit_words:
			raise SystemExit()

		if (len(user_input) != 5) or (not all(val in ('0', '1', '2') for val in user_input)):
			print('Invalid! Must be 5-digit number of 0, 1, and 2')
			continue

		def digit_to_status(digit: str) -> LetterResult:
			return {
				'0': LetterResult.not_in_solution,
				'1': LetterResult.wrong_position,
				'2': LetterResult.correct,
			}[digit]

		status = tuple(digit_to_status(digit) for digit in user_input)

		return WordResult(status)


def ask_yes_no(query_str: str, default: Optional[bool] = None) -> bool:

	if default is None:
		query_str = f'{query_str} [y/n] '
	elif default:
		query_str = f'{query_str} [Y/n] '
	else:
		query_str = f'{query_str} [y/N] '

	while True:
		choice = input(query_str).strip().lower()

		if not choice:
			if default is not None:
				return default
			else:
				continue

		if choice in _falsy_words:
			return False

		if choice in _truthy_words:
			return True


def ask_choice(query_str: str, choices: list) -> int:

	while True:
		print(query_str)

		for idx, choice in enumerate(choices):
			print('  %i: %s' % (idx + 1, choice))

		print('  %s: quit' % _exit_words[0])

		choice = input('Select: ').strip()
		if choice in _exit_words:
			raise SystemExit()
		
		try:
			choice_idx = int(choice)
		except ValueError:
			continue

		choice_idx -= 1

		if not (0 <= choice_idx < len(choices)):
			continue

		return choice_idx
