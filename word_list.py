#!/usr/bin/env python3

import os
from typing import Iterable

from game_types import *

WORD_LISTS_DIR = 'word_lists'

ORIGINAL_SOLUTIONS_FILENAME = 'original_solutions.txt'
ORIGINAL_EXTRA_WORDS_FILENAME = 'original_extra_words.txt'

NYT_SOLUTIONS_FILENAME = 'nyt_solutions.txt'
NYT_EXTRA_WORDS_FILENAME = 'nyt_extra_words.txt'


# Wrap in mutable type
_g_idx = [0]
_g_indexed_words_raw = set()


def _load_raw_words_from_file(file_path: os.PathLike) -> set[str]:
	"""
	:note: Checks that word is alphanumeric and that there are no duplicates in file; does not check length!
	"""
	raw_words = set()
	with open(file_path, 'r') as f:
		for line in f:
			raw_word = line.rstrip()

			if not raw_word.isalpha():
				raise ValueError(f'Word has invalid characters: "{raw_word}"')

			raw_word_upper = raw_word.upper()

			if raw_word_upper in raw_words:
				raise ValueError(f'Found duplicate word in {file_path}: {raw_word}')

			raw_words.add(raw_word_upper)

	return raw_words


def _raw_words_to_words(raw_words: Iterable[str], ignore_already_indexed_words=False, ignore_invalid_words=False) -> list[Word]:
	global _g_idx, _g_indexed_words_raw

	words = []
	for raw_word in sorted(list(raw_words)):

		assert raw_word == raw_word.upper()

		if raw_word in _g_indexed_words_raw:
			if ignore_already_indexed_words:
				continue
			else:
				raise ValueError('Duplicate word: "%s"' % raw_word)

		_g_indexed_words_raw.add(raw_word)

		try:
			word = Word(raw_word, index=_g_idx[0])
		except ValueError:
			if ignore_invalid_words:
				continue
			else:
				raise

		_g_idx[0] = _g_idx[0] + 1
		words.append(word)

	return words


def _load_words_from_file(file_path: os.PathLike) -> list[Word]:
	raw_words = _load_raw_words_from_file(file_path)
	return _raw_words_to_words(raw_words)


def _all_unique(list_to_check: list) -> bool:
	return len(list_to_check) == len(set(list_to_check))


words = None
solutions = None
extra_words = None


def init(use_nyt_lists=False):
	global words, solutions, extra_words

	solutions_filename = NYT_SOLUTIONS_FILENAME if use_nyt_lists else ORIGINAL_SOLUTIONS_FILENAME
	extra_words_filename = NYT_EXTRA_WORDS_FILENAME if use_nyt_lists else ORIGINAL_EXTRA_WORDS_FILENAME

	solutions = _load_words_from_file(os.path.join(WORD_LISTS_DIR, solutions_filename))
	extra_words = _load_words_from_file(os.path.join(WORD_LISTS_DIR, extra_words_filename))

	words = solutions + extra_words

	assert _all_unique([item.word for item in words])
	assert _all_unique([item.index for item in words])


def get_word_from_str(word_str: str, force=False) -> Word:
	word_str = word_str.upper()
	for word in words:
		if word == word_str:
			return word
	else:
		raise KeyError(f'Invalid word: {word_str}')


def get_word_by_idx(word_idx: int) -> Word:
	return words[word_idx]
