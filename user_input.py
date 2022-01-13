#!/usr/bin/env python3


import word_list


_exit_words = [
	'q', 'x', 'quit', 'exit'
]


# TODO: more debug commands, like one that shows the answer


def ask_word(guess_num: int) -> str:

	while True:
		guess = input("Enter guess %i/6 (or 'q' to quit): " % guess_num)
		guess = guess.strip().lower()
		
		# Debug feature: start with '!' to force allowing a guess
		allow_invalid = False
		if guess.endswith('!'):
			allow_invalid = True
			guess = guess[:-1]
		
		if guess in _exit_words:
			raise SystemExit()
		
		if len(guess) != 5:
			print('Guess must be length 5')
			continue
		
		if guess not in word_list.words:
			if allow_invalid:
				print('Allowing invalid word "%s" because you yelled it' % guess.upper())
			else:
				print('Invalid word: %s' % guess.upper())
				continue

		return guess
