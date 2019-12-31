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
    - If C(lf), the file will have Unix-style line endings
    - If C(crlf), the file will have Windows-style line endings, also commonly used in Internet protocols
    - If C(cr), the file will have legacy Mac-style line endings
    type: str
    required: yes
    choices: [ cr, lf, crlf ]

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
    - Specifies whether or not to have a leading byte order mark when encoding with UTF-8 or UTF-16.
    - if C(as-is), the resulting file will have a byte order mark if and only if it already has one.
    type: str
    default: as-is
    choices: [ absent, as-is ]

  encoding:
    description:
    - Generally not needed if the file is created using an editor that is intended for programming, and there are only English letters.
    - The file will be transformed into the specified encoding
    type: str
    default: as-is
    choices:
    - as-is
    - ascii
    - big5
    - big5hkscs
    - cp037
    - cp424
    - cp437
    - cp500
    - cp737
    - cp775
    - cp850
    - cp852
    - cp855
    - cp856
    - cp857
    - cp860
    - cp861
    - cp862
    - cp863
    - cp864
    - cp865
    - cp866
    - cp869
    - cp874
    - cp875
    - cp932
    - cp949
    - cp950
    - cp1006
    - cp1026
    - cp1140
    - cp1250
    - cp1251
    - cp1252
    - cp1253
    - cp1254
    - cp1255
    - cp1256
    - cp1257
    - cp1258
    - euc_jp
    - euc_jis_2004
    - euc_jisx0213
    - euc_kr
    - gb2312
    - gbk
    - gb18030
    - hz
    - iso2022_jp
    - iso2022_jp_1
    - iso2022_jp_2
    - iso2022_jp_2004
    - iso2022_jp_3
    - iso2022_jp_ext
    - iso2022_kr
    - latin_1
    - iso8859_2
    - iso8859_3
    - iso8859_4
    - iso8859_5
    - iso8859_6
    - iso8859_7
    - iso8859_8
    - iso8859_9
    - iso8859_10
    - iso8859_13
    - iso8859_14
    - iso8859_15
    - johab
    - koi8_r
    - koi8_u
    - mac_cyrillic
    - mac_greek
    - mac_iceland
    - mac_latin2
    - mac_roman
    - mac_turkish
    - ptcp154
    - shift_jis
    - shift_jis_2004
    - shift_jisx0213
    - utf_16_be
    - utf_16_le
    - utf_7
    - utf_8

  original_encoding:
    description:
    - This option is relevant when encoding is specified
    - If you specify the original encoding, the transformation is going to be much more reliable. The same rules apply as for encoding.
    - If you can't tell, the module will try to help you out, but your text may become distorted.
    type: str
    default: guess
    choices:
    - guess
    - ascii
    - big5
    - big5hkscs
    - cp037
    - cp424
    - cp437
    - cp500
    - cp737
    - cp775
    - cp850
    - cp852
    - cp855
    - cp856
    - cp857
    - cp860
    - cp861
    - cp862
    - cp863
    - cp864
    - cp865
    - cp866
    - cp869
    - cp874
    - cp875
    - cp932
    - cp949
    - cp950
    - cp1006
    - cp1026
    - cp1140
    - cp1250
    - cp1251
    - cp1252
    - cp1253
    - cp1254
    - cp1255
    - cp1256
    - cp1257
    - cp1258
    - euc_jp
    - euc_jis_2004
    - euc_jisx0213
    - euc_kr
    - gb2312
    - gbk
    - gb18030
    - hz
    - iso2022_jp
    - iso2022_jp_1
    - iso2022_jp_2
    - iso2022_jp_2004
    - iso2022_jp_3
    - iso2022_jp_ext
    - iso2022_kr
    - latin_1
    - iso8859_2
    - iso8859_3
    - iso8859_4
    - iso8859_5
    - iso8859_6
    - iso8859_7
    - iso8859_8
    - iso8859_9
    - iso8859_10
    - iso8859_13
    - iso8859_14
    - iso8859_15
    - johab
    - koi8_r
    - koi8_u
    - mac_cyrillic
    - mac_greek
    - mac_iceland
    - mac_latin2
    - mac_roman
    - mac_turkish
    - ptcp154
    - shift_jis
    - shift_jis_2004
    - shift_jisx0213
    - utf_16_be
    - utf_16_le
    - utf_7
    - utf_8

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
- name: Ensure that a file has lf on every line and no BOM
  text_file:
    path: /etc/cron.d/myapp.cron
    eol: lf
    end_eol: present
    bom: absent

- name: Ensure that every existing line ending in a file is crlf
  text_file:
    path: /tmp/file-to-send.txt
    eol: crlf

'''
RETURN = r'''

'''

# Documenting a module: https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html
# Python encoding support: https://docs.python.org/2.4/lib/standard-encodings.html
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


def all_encoding_names():
    return [
        'ascii', 'big5', 'big5hkscs', 'cp037', 'cp424', 'cp437', 'cp500',
        'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857',
        'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866',
        'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006',
        'cp1026', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254',
        'cp1255', 'cp1256', 'cp1257', 'cp1258', 'euc_jp', 'euc_jis_2004',
        'euc_jisx0213', 'euc_kr', 'gb2312', 'gbk', 'gb18030', 'hz',
        'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_2004',
        'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1',
        'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6',
        'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_13',
        'iso8859_14', 'iso8859_15', 'johab', 'koi8_r', 'koi8_u',
        'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman',
        'mac_turkish', 'ptcp154', 'shift_jis', 'shift_jis_2004',
        'shift_jisx0213', 'utf_16_be', 'utf_16_le', 'utf_7', 'utf_8'
    ]


def utf_encoding_names():
    return ['utf_8', 'utf_16_be', 'utf_16_le']


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
    if params['eol'] == 'crlf':
        eol = '\r\n'
    elif params['eol'] == 'cr':
        eol = '\r'
    elif params['eol'] == 'lf':
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

    # Ensure the required eol type, using lf as intermediate
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
    if (to_enc in utf_encoding_names()
            and have_bom and params['bom'] == 'as-is'):
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
            eol=dict(type='str', required=True, choices=['cr', 'lf', 'crlf']),
            end_eol=dict(
                type='str',
                default='as-is',
                choices=['as-is', 'present', 'absent']),
            bom=dict(type='str', default='as-is', choices=['as-is', 'absent']),
            encoding=dict(
                type='str',
                default='as-is',
                choices=['as-is'] + all_encoding_names(),
            ),
            original_encoding=dict(
                type='str',
                default='guess',
                choices=['guess'] + all_encoding_names(),
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
                             (module.params['path'], to_native(e)))


if __name__ == '__main__':
    main()
