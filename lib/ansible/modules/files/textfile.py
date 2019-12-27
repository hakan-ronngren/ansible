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


class Reader:
    next_byte = None
    stream = None
    b_crlf = '\r\n' if six.PY2 else b'\r\n'
    b_cr = '\r' if six.PY2 else b'\r'
    b_lf = '\n' if six.PY2 else b'\n'
    b_empty = '' if six.PY2 else b''

    def __init__(self, stream):
        self.stream = stream
        self.next_byte = None

    def read_line_bytes(self):
        """Read bytes from one line.

        Be sure to consume an entire eol sequence if there is one"""

        buf = self.b_empty
        if self.next_byte:
            buf += self.next_byte
            self.next_byte = None
        while True:
            b = self.stream.read(1)
            if b == self.b_lf:
                # Complete LF line ending
                buf += b
                return buf
            elif b == self.b_cr:
                # CR, possibly part of CRLF
                buf += b
                b = self.stream.read(1)
                if b == self.b_lf:
                    # Complete CRLF line ending
                    buf += b
                else:
                    # No, it was just CR, stash the extra byte
                    next_byte = b
                # Complete CR or CRLF line ending
                return buf
            elif b == self.b_empty:
                # Reached EOF
                return buf
            else:
                # Another byte to the line
                buf += b


def guess_encoding(path):
    """Find a text codec that would decode a given file.

    The clues we are looking for may be right at the end, so we read
    the entire file.

    This function should not be expected to find the correct
    encoding, only one that would not obviously break."""

    with open(path, 'rb') as f:
        b_text = f.read()

    # Iterate over encodings that can fail, in order of decreasing
    # probability of failure. As ascii will reject any byte over
    # 0xf7, it goes first.
    for encoding in ('ascii', 'utf-8', 'cp1252', 'latin_1'):
        try:
            b_text.decode(encoding)
            return encoding
        except UnicodeDecodeError as e:
            continue

    # If we reach this point using some Python version, it means
    # that this function is not finished.
    raise Exception("bug: fallback failed for guess_encoding")


def process_file(module):
    params = module.params
    temp_path = tempfile.mkstemp()[-1]
    changed = False
    b_out = None
    b_holdback = None

    with open(params['path'], 'rb') as f_in:
        reader = Reader(f_in)

        # Convenient shortcuts
        b_crlf = reader.b_crlf
        b_cr = reader.b_cr
        b_lf = reader.b_lf
        b_empty = reader.b_empty

        # Get the desired eol byte sequence
        if params['eol'] == 'CRLF':
            b_eol = b_crlf
        elif params['eol'] == 'CR':
            b_eol = b_cr
        elif params['eol'] == 'LF':
            b_eol = b_lf
        else:
            raise Exception('missing support for eol=%s' % params['eol'])

        if params['encoding'] != 'as-is':
            to_enc = params['encoding']
            if params['original_encoding'] == 'guess':
                from_enc = guess_encoding(params['path'])
            else:
                from_enc = params['original_encoding']

        with open(temp_path, 'wb') as f_out:
            while True:
                b_in = reader.read_line_bytes()

                # Done if no input
                if len(b_in) == 0:
                    break

                # If this is the first read and we expect Microsoft's
                # byte order mark to be absent, ensure that.
                if (params['bom'] == 'absent' and not b_out and len(b_in) >= 3
                        and (six.PY2 and b_in.startswith('\xef\xbb\xbf') or
                             (six.PY3 and b_in.startswith(b'\xef\xbb\xbf')))):
                    b_out = b_in[3:]
                else:
                    b_out = b_in

                # Ensure the required eol type, using LF as intermediate
                b_out = b_out.replace(b_crlf, b_lf)
                b_out = b_out.replace(b_cr, b_lf)
                b_out = b_out.replace(b_lf, b_eol)

                # Add eol if required but missing
                if (params['end_eol'] == 'present'
                        and not b_out.endswith(b_eol)):
                    b_out += b_eol

                # If we previously held an eol back to avoid having one
                # on the last line, now print it only if there is also
                # some more to print
                if b_holdback and len(b_out) > 0:
                    f_out.write(b_holdback)
                    b_holdback = None

                # If we do not want an eol on the last line and we have
                # one now, hold it back, because this line may be
                # the last
                if (params['end_eol'] == 'absent' and b_out.endswith(b_eol)):
                    b_holdback = b_eol
                    b_out = b_out[:-len(b_eol)]

                # Transcode if told so
                if params['encoding'] != 'as-is':
                    errors = params['encoding_errors']
                    b_out = b_out.decode(from_enc)
                    if sys.version_info >= (2, 7):
                        b_out = b_out.encode(to_enc, errors=errors)
                    else:
                        b_out = b_out.encode(to_enc, errors)

                f_out.write(b_out)

                if (b_out != b_in):
                    changed = True

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
