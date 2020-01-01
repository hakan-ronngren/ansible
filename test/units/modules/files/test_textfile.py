#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pytest
import sys
import tempfile

from ansible.modules.files.textfile import process_file
from ansible.modules.files.textfile import guess_encoding


# Conversion tests
#
# These conventions are used in test names:
#  * encoding is ascii unless stated
#  * eof: complete last line
#  * noeof: incomplete last line
#  * unless stated, the last line status applies to both input and output

def test_crlf_eof_to_lf():
    module = FakeModule(eol='lf')
    try:
        result, converted_data = exercise(CRLF_COMPL, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL
    finally:
        cleanup(module)


def test_crlf_noeof_to_lf():
    module = FakeModule(eol='lf')
    try:
        result, converted_data = exercise(CRLF_INCOMPL, module)
        assert result == dict(changed=True)
        assert converted_data == LF_INCOMPL
    finally:
        cleanup(module)


def test_crlf_noeof_to_lf_eof():
    module = FakeModule(eol='lf', end_eol='present')
    try:
        result, converted_data = exercise(CRLF_INCOMPL, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL
    finally:
        cleanup(module)


def test_lf_eof_to_crlf():
    module = FakeModule(eol='crlf')
    try:
        result, converted_data = exercise(LF_COMPL, module)
        assert result == dict(changed=True)
        assert converted_data == CRLF_COMPL
    finally:
        cleanup(module)


def test_lf_eof_to_crlf_noeof():
    module = FakeModule(eol='crlf', end_eol='absent')
    try:
        result, converted_data = exercise(LF_COMPL, module)
        assert result == dict(changed=True)
        assert converted_data == CRLF_INCOMPL
    finally:
        cleanup(module)


def test_lf_noeof_to_lf_eof():
    module = FakeModule(eol='lf', end_eol='present')
    try:
        result, converted_data = exercise(LF_INCOMPL, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL
    finally:
        cleanup(module)


def test_lf_to_cr():
    module = FakeModule(eol='cr')
    try:
        result, converted_data = exercise(LF_COMPL, module)
        assert result == dict(changed=True)
        assert converted_data == CR_COMPL
    finally:
        cleanup(module)


def test_remove_windows_utf8_bom():
    module = FakeModule(eol='lf', end_eol='present', bom='absent')
    try:
        result, converted_data = exercise(CRLF_INCOMPL_UTF8_SWE_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_UTF8_SWE_NO_BOM
    finally:
        cleanup(module)


def test_keep_windows_utf8_bom():
    module = FakeModule(eol='lf', end_eol='present')
    try:
        result, converted_data = exercise(CRLF_INCOMPL_UTF8_SWE_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_UTF8_SWE_BOM
    finally:
        cleanup(module)


def test_lf_remains_lf_and_changed_is_false():
    module = FakeModule(eol='lf')
    try:
        result, converted_data = exercise(LF_COMPL, module)
        assert result == dict(changed=False)
        assert converted_data == LF_COMPL
    finally:
        cleanup(module)


def test_can_convert_eol_in_a_file_with_unrecognizable_encoding():
    module = FakeModule(eol='crlf', encoding='as-is')
    try:
        result, converted_data = exercise(LF_COMPL_STRANGE_ENCODING, module)
        assert result == dict(changed=True)
        assert converted_data == CRLF_COMPL_STRANGE_ENCODING
    finally:
        cleanup(module)


def test_guessed_to_cp1252():
    module = FakeModule(eol='lf', encoding='cp1252')
    try:
        result, converted_data = exercise(LF_COMPL_UTF8_SWE_NO_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_CP1252_SWE
    finally:
        cleanup(module)


def test_utf_8_to_cp1252():
    module = FakeModule(eol='lf',
                        original_encoding='utf_8',
                        encoding='cp1252')
    try:
        result, converted_data = exercise(LF_COMPL_UTF8_SWE_NO_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_CP1252_SWE
    finally:
        cleanup(module)


def test_guessed_utf_16_be_to_cp1252():
    module = FakeModule(eol='lf', encoding='cp1252')
    try:
        result, converted_data = exercise(LF_COMPL_UTF16BE_SWE_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_CP1252_SWE
    finally:
        cleanup(module)


def test_guessed_utf_16_le_to_utf_8_keep_bom_when_as_is():
    module = FakeModule(eol='lf', encoding='utf_8')
    try:
        result, converted_data = exercise(LF_COMPL_UTF16LE_SWE_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_UTF8_SWE_BOM
    finally:
        cleanup(module)


def test_utf_8_to_utf_16_le_keep_bom_when_as_is():
    module = FakeModule(eol='lf', encoding='utf_16_le')
    try:
        result, converted_data = exercise(LF_COMPL_UTF8_SWE_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_UTF16LE_SWE_BOM
    finally:
        cleanup(module)


def test_utf_8_to_ascii_replaced():
    module = FakeModule(eol='lf',
                        original_encoding='utf_8',
                        encoding='ascii',
                        encoding_errors='replace')
    try:
        result, converted_data = exercise(LF_COMPL_UTF8_SWE_NO_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_ASCII_SWE_REPLACED
    finally:
        cleanup(module)


def test_utf_8_to_ascii_invalid_characters_ignored():
    module = FakeModule(eol='lf',
                        original_encoding='utf_8',
                        encoding='ascii',
                        encoding_errors='ignore')
    try:
        result, converted_data = exercise(LF_COMPL_UTF8_SWE_NO_BOM, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_ASCII_SWE_DROPPED
    finally:
        cleanup(module)


def test_cp1252_to_ascii_strict_invalid_character_cause_failure():
    module = FakeModule(eol='lf', encoding='ascii')
    with pytest.raises(UnicodeEncodeError):
        try:
            exercise(LF_COMPL_CP1252_SWE, module)
        finally:
            cleanup(module)


def test_cp1252_to_utf_8():
    module = FakeModule(eol='lf', original_encoding='cp1252', encoding='utf_8')
    try:
        result, converted_data = exercise(LF_COMPL_CP1252_SWE, module)
        assert result == dict(changed=True)
        assert converted_data == LF_COMPL_UTF8_SWE_NO_BOM
    finally:
        cleanup(module)


def test_empty_file_remains_empty_and_changed_is_false_even_when_end_eol_required():
    module = FakeModule(eol='lf', end_eol='present')
    try:
        result, converted_data = exercise(bytearray([]), module)
        assert result == dict(changed=False)
        assert converted_data == bytearray([])
    finally:
        cleanup(module)


def test_file_not_found():
    module = FakeModule()
    cleanup(module)
    with pytest.raises(IOError):
        process_file(module)


# Tests for the ability to guess encoding

def test_guess_ascii():
    result = guess_encoding(LF_COMPL)
    assert result == 'ascii'


def test_guess_utf_8_with_characters_as_only_clue():
    result = guess_encoding(LF_COMPL_UTF8_SWE_NO_BOM)
    assert result == 'utf_8'


def test_guess_utf_8_with_bom_as_only_clue():
    result = guess_encoding(LF_COMPL_UTF8_BOM)
    assert result == 'utf_8'


def test_guess_utf_16_le_with_characters_as_only_clue():
    result = guess_encoding(LF_COMPL_UTF16LE_SWE_NO_BOM)
    assert result == 'utf_16_le'


def test_guess_utf_16_le_with_bom_as_only_clue():
    result = guess_encoding(INCOMPL_UTF16LE_JAP_BOM)
    assert result == 'utf_16_le'


def test_guess_utf_16_le():
    result = guess_encoding(LF_COMPL_UTF16LE_SWE_BOM)
    assert result == 'utf_16_le'


def test_guess_cp_1252():
    result = guess_encoding(LF_COMPL_CP1252_SWE)
    assert result == 'cp1252'


def test_anything_goes_as_latin_1():
    # Actually, the input here is a very wild latin-1 text.
    # The intention is to verify that there is a fallback
    # that always works.
    result = guess_encoding(LF_COMPL_STRANGE_ENCODING)
    assert result == 'latin_1'


# Test data with ascii, various line endings and complete/incomplete last line
# Two lines, containing the strings "Hello" and "World"

CRLF_COMPL = bytearray([
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0d, 0x0a,
    0x57, 0x6f, 0x72, 0x6c, 0x64, 0x0d, 0x0a
])

CRLF_INCOMPL = bytearray([
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0d, 0x0a,
    0x57, 0x6f, 0x72, 0x6c, 0x64
])

LF_COMPL = bytearray([
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0a,
    0x57, 0x6f, 0x72, 0x6c, 0x64, 0x0a,
])

LF_INCOMPL = bytearray([
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0a,
    0x57, 0x6f, 0x72, 0x6c, 0x64,
])

CR_COMPL = bytearray([
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0d,
    0x57, 0x6f, 0x72, 0x6c, 0x64, 0x0d,
])


LF_COMPL_UTF8_BOM = bytearray([
    # Prepending the ascii data with a Windows-style BOM makes it UTF-8
    0xef, 0xbb, 0xbf,
    0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x0a,
    0x57, 0x6f, 0x72, 0x6c, 0x64, 0x0a,
])

# Test data variants with some Swedish characters
# Two lines, containing the strings "Hallå" and "Värld"

CRLF_INCOMPL_UTF8_SWE_BOM = bytearray([
    0xef, 0xbb, 0xbf,
    0x48, 0x61, 0x6c, 0x6c, 0xc3, 0xa5, 0x0d, 0x0a,
    0x56, 0xc3, 0xa4, 0x72, 0x6c, 0x64
])

LF_COMPL_UTF8_SWE_BOM = bytearray([
    0xef, 0xbb, 0xbf,
    0x48, 0x61, 0x6c, 0x6c, 0xc3, 0xa5, 0x0a,
    0x56, 0xc3, 0xa4, 0x72, 0x6c, 0x64, 0x0a
])

LF_COMPL_UTF16BE_SWE_BOM = bytearray([
    0xfe, 0xff,
    0x00, 0x48, 0x00, 0x61, 0x00, 0x6c, 0x00, 0x6c, 0x00, 0xe5, 0x00, 0x0a,
    0x00, 0x56, 0x00, 0xe4, 0x00, 0x72, 0x00, 0x6c, 0x00, 0x64, 0x00, 0x0a
])

LF_COMPL_UTF16LE_SWE_BOM = bytearray([
    0xff, 0xfe,
    0x48, 0x00, 0x61, 0x00, 0x6c, 0x00, 0x6c, 0x00, 0xe5, 0x00, 0x0a, 0x00,
    0x56, 0x00, 0xe4, 0x00, 0x72, 0x00, 0x6c, 0x00, 0x64, 0x00, 0x0a, 0x00
])

LF_COMPL_UTF16LE_SWE_NO_BOM = bytearray([
    0x48, 0x00, 0x61, 0x00, 0x6c, 0x00, 0x6c, 0x00, 0xe5, 0x00, 0x0a, 0x00,
    0x56, 0x00, 0xe4, 0x00, 0x72, 0x00, 0x6c, 0x00, 0x64, 0x00, 0x0a, 0x00
])

LF_COMPL_UTF8_SWE_NO_BOM = bytearray([
    0x48, 0x61, 0x6c, 0x6c, 0xc3, 0xa5, 0x0a,
    0x56, 0xc3, 0xa4, 0x72, 0x6c, 0x64, 0x0a
])

LF_COMPL_CP1252_SWE = bytearray([
    0x48, 0x61, 0x6c, 0x6c, 0xe5, 0x0a,
    0x56, 0xe4, 0x72, 0x6c, 0x64, 0x0a
])

LF_COMPL_ASCII_SWE_REPLACED = bytearray([
    # In this variant, "?" goes in place of non-ascii letters
    0x48, 0x61, 0x6c, 0x6c, 0x3f, 0x0a,
    0x56, 0x3f, 0x72, 0x6c, 0x64, 0x0a
])

LF_COMPL_ASCII_SWE_DROPPED = bytearray([
    # In this variant, non-ascii letters are simply lost
    0x48, 0x61, 0x6c, 0x6c, 0x0a,
    0x56, 0x72, 0x6c, 0x64, 0x0a
])

# Test data with Japanese and no line endings, because with UTF-16 these would
# contain 0x00 bytes that give away the byte order too easily.
# One incomplete line, containing the string "こんにちは" (kon'nichiwa)

INCOMPL_UTF16LE_JAP_BOM = bytearray([
    0xff, 0xfe,
    0x53, 0x30,
    0x93, 0x30,
    0x6b, 0x30,
    0x61, 0x30,
    0x6f, 0x30
])

INCOMPL_UTF8_JAP_BOM = bytearray([
    0xef, 0xbb, 0xbf,
    0xe3, 0x81, 0x93,
    0xe3, 0x82, 0x93,
    0xe3, 0x81, 0xab,
    0xe3, 0x81, 0xa1,
    0xe3, 0x81, 0xaf
])

# Test data to verify the ability to transparently deal with essentially any
# byte values (0x0a and 0x0d reserved for line endings, 0x00 avoided as it
# would suggest UTF-16)

CRLF_COMPL_STRANGE_ENCODING = bytearray([
    0xff, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0d, 0x0a,
    0x08, 0x09, 0xff, 0x0b, 0x0c, 0xff, 0x0e, 0x0f, 0x0d, 0x0a,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x0d, 0x0a,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x0d, 0x0a,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x0d, 0x0a,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x0d, 0x0a,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x0d, 0x0a,
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x0d, 0x0a,
    0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x0d, 0x0a,
    0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x0d, 0x0a,
    0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x0d, 0x0a,
    0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x0d, 0x0a,
    0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x0d, 0x0a,
    0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x0d, 0x0a,
    0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x0d, 0x0a,
    0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x0d, 0x0a,
    0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x0d, 0x0a,
    0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x0d, 0x0a,
    0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x0d, 0x0a,
    0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0x0d, 0x0a,
    0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0x0d, 0x0a,
    0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0x0d, 0x0a,
    0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0x0d, 0x0a,
    0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0x0d, 0x0a,
    0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0x0d, 0x0a,
    0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf, 0x0d, 0x0a,
    0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0x0d, 0x0a,
    0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, 0x0d, 0x0a,
    0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0x0d, 0x0a,
    0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef, 0x0d, 0x0a,
    0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0x0d, 0x0a,
    0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff, 0x0d, 0x0a
])

LF_COMPL_STRANGE_ENCODING = bytearray([
    0xff, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0a,
    0x08, 0x09, 0xff, 0x0b, 0x0c, 0xff, 0x0e, 0x0f, 0x0a,
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x0a,
    0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x0a,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x0a,
    0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x0a,
    0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x0a,
    0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x0a,
    0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x0a,
    0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x0a,
    0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x0a,
    0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x0a,
    0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x0a,
    0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x0a,
    0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x0a,
    0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x0a,
    0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x0a,
    0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x0a,
    0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x0a,
    0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0x0a,
    0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0x0a,
    0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0x0a,
    0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0x0a,
    0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0x0a,
    0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0x0a,
    0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf, 0x0a,
    0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0x0a,
    0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, 0x0a,
    0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0x0a,
    0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef, 0x0a,
    0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0x0a,
    0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff, 0x0a
])


# Helpers

def exercise(indata, module):
    # We put up with the overhead of using real files to get
    # the benefit of knowing that nothing is lost in translation
    # in the Python IO layers.
    if indata:
        with open(module.params['path'], 'wb') as f:
            f.write(indata)
    result = process_file(module)
    with open(module.params['path'], 'rb') as f:
        converted_data = f.read()
    return (result, converted_data)


def cleanup(module):
    path = module.params['path']
    if os.path.exists(path):
        os.remove(path)


class FakeModule():
    fail_json_dict = dict()
    params = dict()

    def __init__(self, **kwargs):
        self.params['path'] = tempfile.mkstemp()[-1]
        self.params['eol'] = 'lf'
        self.params['end_eol'] = 'as-is'
        self.params['bom'] = 'as-is'
        self.params['encoding'] = 'as-is'
        self.params['original_encoding'] = 'guess'
        self.params['encoding_errors'] = 'strict'
        for key in kwargs:
            self.params[key] = kwargs[key]


