#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2020, Håkan Rönngren <hakan.ronngren@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = r'''
---
module: textfile
version_added: "2.10"
short_description: Transform text files
description:
- Convert line breaks, transform between encodings and deal with other file portability issues

options:
  path:
    description:
    - Path to the file being managed.
    type: path
    required: yes
    aliases: [ name ]

  eol:
    description:
    - If C(LF), the file will have Unix-style line endings
    - If C(CRLF), the file will have Windows-style line endings, also commonly used in Internet protocols
    - If C(CR), the file will have legacy Mac-style line endings
    type: str
    required: yes
    choices: [ CR, LF, CRLF ]

  end_eol:
    description:
    - If C(absent), the last line will not end with a line ending
    - If C(present), the last line will end with a line ending
    - If C(as-is), no line ending will be appended to the last line, but if there is one already, it will have the required format
    type: str
    default: as-is
    choices: [ absent, present, as-is ]

  bom:
    description:
    - Controls how to deal with a leading byte order mark, common in files created using Microsoft software
    type: str
    default: as-is
    choices: [ absent, as-is ]

  encoding:
    description:
    - Generally not needed if the file is created using an editor that is intended for programming, and there are only English letters.
    - "The file will be transformed into the specified encoding, see https://docs.python.org/2.4/lib/standard-encodings.html."
    - If not specified, this module will essentially treat the text before each line break as binary data and not alter it in any way.
    type: str
    default: as-is

  original_encoding:
    description:
    - This option is relevant when encoding is specified
    - If you specify the original encoding, the transformation is going to be much more reliable. The same rules apply as for encoding.
    - If you can't tell, the module will try to help you out, but your text may become distorted.
    type: str
    default: guess

  encoding_errors:
    description:
    - This option is relevant when encoding is specified
    - If C(strict), encoding will fail if the file text cannot be written using the selected encoding, e.g. when using ascii for a non-English text.
    - If C(replace), all letters that cannot be encoded will be replaced with a question mark.
    - If C(ignore), all letters that cannot be encoded will be deleted.
    type: str
    default: strict
    choices: [ strict, replace, ignore ]

seealso:
- module: file

author:
- Håkan Rönngren (@hakan-ronngren)
'''

EXAMPLES = r'''
- name: Ensure that a file has LF on every line and no BOM
  text_file:
    path: /etc/cron.d/myapp.cron
    eol: LF
    end_eol: present
    bom: absent

- name: Ensure that every existing line ending in a file is CRLF
  text_file:
    path: /tmp/file-to-send.txt
    eol: CRLF

'''
RETURN = r'''

'''

# Some ideas for improvement on Python 3:
# https://six.readthedocs.io/
# https://pythonconquerstheuniverse.wordpress.com/2011/05/08/newline-conversion-in-python-3/
# https://medium.com/better-programming/strings-unicode-and-bytes-in-python-3-everything-you-always-wanted-to-know-27dc02ff2686

import os
import shutil
import sys
import tempfile

from ansible.module_utils import six
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native


def guess_encoding(b_text):
    """Find a text codec that would decode a given file.

    This function should not be expected to find the correct
    encoding, only one that would not obviously break."""

    b_zero = '\x00' if six.PY2 else b'\x00'
    zero_ix = b_text.find(b_zero)
    if zero_ix >= 0:
        # The presence of a zero byte indicates that we have UTF-16.
        # (It could be UTF-32 as well but we do not handle that.)
        if zero_ix % 2 == 0:
            # Even position => big endian
            return 'utf_16_be'
        else:
            # Odd position => big endian
            return 'utf_16_le'
    else:
        # Iterate over encodings that can fail, in order of decreasing
        # probability of failure. As ascii will reject any byte over
        # 0xf7, it goes first. Last in the list should be an encoding
        # that accepts any byte sequence.
        for encoding in ('ascii', 'utf_8', 'cp1252', 'latin_1'):
            try:
                b_text.decode(encoding)
                return encoding
            except UnicodeDecodeError as e:
                continue

    # If we reach this point using some Python version, it means that
    # the list of encodings to try does not meet the requirements.
    raise Exception("bug: fallback failed for guess_encoding")


def is_utf_name(name):
    return name in ['utf_8', 'utf_16_be', 'utf_16_le']


def process_file(module):
    params = module.params
    temp_path = tempfile.mkstemp()[-1]
    changed = False

    b_crlf = '\r\n' if six.PY2 else b'\r\n'
    b_cr = '\r' if six.PY2 else b'\r'
    b_lf = '\n' if six.PY2 else b'\n'
    b_bom8 = '\xef\xbb\xbf' if six.PY2 else b'\xef\xbb\xbf'
    b_bom16le = '\xff\xfe' if six.PY2 else b'\xff\xfe'
    b_bom16be = '\xfe\xff' if six.PY2 else b'\xfe\xff'
    b_empty = '' if six.PY2 else b''

    # Set desired eol byte sequence
    if params['eol'] == 'CRLF':
        eol = '\r\n'
    elif params['eol'] == 'CR':
        eol = '\r'
    elif params['eol'] == 'LF':
        eol = '\n'
    else:
        raise Exception('missing support for eol=%s' % params['eol'])

    with open(params['path'], 'rb') as f_in:
        b_in = f_in.read()

    # Set input encoding
    if params['original_encoding'] == 'guess':
        from_enc = guess_encoding(b_in)
    else:
        from_enc = params['original_encoding']

    # Set output encoding
    if params['encoding'] == 'as-is':
        to_enc = from_enc
    else:
        to_enc = params['encoding']

    # Delete byte order mark but remember if we had one
    if b_in.startswith(b_bom8):
        b_out = b_in[len(b_bom8):]
        have_bom = True
    elif (b_in.startswith(b_bom16le)
            or b_in.startswith(b_bom16be)):
        b_out = b_in[len(b_bom16le):]
        have_bom = True
    else:
        have_bom = False
        b_out = b_in

    # Decode so that we can treat the data as pure text when converting
    s_out = b_out.decode(from_enc)

    # Ensure the required eol type, using LF as intermediate
    s_out = s_out.replace('\r\n', '\n')
    s_out = s_out.replace('\r', '\n')
    s_out = s_out.replace('\n', eol)

    # Obey end eol requirement
    if (params['end_eol'] == 'present'
            and not s_out.endswith(eol)):
        s_out += eol
    elif (params['end_eol'] == 'absent'
            and s_out.endswith(eol)):
        s_out = s_out[:-len(eol)]

    # Encode with the required encoding
    errors = params['encoding_errors']
    if sys.version_info >= (2, 7):
        b_out = s_out.encode(to_enc, errors=errors)
    else:
        b_out = s_out.encode(to_enc, errors)

    # Add bom if required
    if is_utf_name(to_enc) and have_bom and params['bom'] == 'as-is':
        if to_enc == 'utf_8':
            b_out = b_bom8 + b_out
        elif to_enc == 'utf_16_le':
            b_out = b_bom16le + b_out
        elif to_enc == 'utf_16_be':
            b_out = b_bom16be + b_out

    if (b_out != b_in):
        changed = True

    with open(temp_path, 'wb') as f_out:
        f_out.write(b_out)

    shutil.move(temp_path, params['path'])
    return dict(changed=changed)


def main():
    result = dict()
    module = None
    try:
        module = AnsibleModule(argument_spec=dict(
            path=dict(type='path', required=True, aliases=['name']),
            eol=dict(type='str', required=True, choices=['CR', 'LF', 'CRLF']),
            end_eol=dict(type='str',
                         default='as-is',
                         choices=['as-is', 'present', 'absent']),
            bom=dict(type='str', default='as-is', choices=['as-is', 'absent']),
            encoding=dict(
                type='str',
                default='as-is',
            ),
            original_encoding=dict(
                type='str',
                default='guess',
            ),
            encoding_errors=dict(type='str',
                                 default='strict',
                                 choices=['strict', 'replace', 'ignore']),
        ))
        result = process_file(module)
        module.exit_json(**result)
    except Exception as e:
        if module:
            module.fail_json(msg='Could not convert %s: "%s"' %
                             (module.params['path'], to_native(e)),
                             meta=result)


if __name__ == '__main__':
    main()
