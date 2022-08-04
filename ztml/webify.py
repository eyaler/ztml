""" Minification by way of aliasing AKA uglification

Warnings:
1. The largest literal template chunk is assumed to be the payload (but it will probably work anyway)
2. The two-parameter aliases do not support func`str` syntax (even if you add them explicitly, but it will probably not break your code)
3. Aliases do not support some complex method compositions (which can break your code). E.g.:
    a.appendChild(b=document.createElement`c`)  # works => A(a,b=E`c`)
    a.appendChild(b=document.createElement`c`).setAttribute('style', d)  # will break your code
4. Non-static method aliases support only specific argument forms as appearing in default_aliases (and others will break your code)
"""


import re
import sys
from typing import AnyStr, Optional


default_aliases = '''
Q = document
A = (e, c) => e.appendChild(c)
B = document.body
C = 'textContent'
D = 'dataset'
E = e => document.createElement(e)
F = String.fromCodePoint
G = 'width'
H = 'height'
I = setInterval
J = 'background'
K = 'color'
L = 'length'
M = (e, d) => e.setAttribute('style', d)
N = speechSynthesis
O = setTimeout
P = 'parentElement'
R = 'target'
S = 'style'
'''


def get_encoding_errors(encoding: str):
    if encoding is None:
        encoding = 'utf8'
    errors = 'strict' if encoding.lower().replace('-', '') == 'utf8' else 'backslashreplace'
    return encoding, errors


def get_len(script, encoding):
    return len(script.encode(*get_encoding_errors(encoding)) if isinstance(script, str) else script)


def uglify(script: AnyStr,
           aliases: str = default_aliases,
           min_cnt: int = 2,
           add_used_aliases: bool = True,
           encoding: Optional[str] = None
           ) -> AnyStr:
    encoding, errors = get_encoding_errors(encoding)
    orig_len = get_len(script, encoding)
    shorts = set()
    for alias in reversed(aliases.strip().splitlines()):
        alias = alias.replace(' ', '')
        if not alias:
            continue
        short, long = alias.split('=', 1)
        assert short not in shorts, short
        shorts.add(short)
        prefix = ''
        if ',' in long:
            prefix = '([\\w.]+?)\\.'
        long = re.sub('[^,]+,[^=]+=>[^.]+\\.|[^=]+=>|\\([^,)]+\\)|,.*', '', long)
        if prefix:
            short += '(\\1'
            if '(' not in long:
                long += '('
                short += ','
            long = prefix + re.sub('[\'"]', '[\'"]', re.escape(long))
        elif long[0] == long[-1] in '\'"':
            long = '\\.' + long[1:-1]
            short = '[' + short + ']'
        if re.match('\\w', long[0]):
            long = '\\b' + long
        if re.match('\\w', long[-1]):
            long += '\\b'
        literals = r'(`(?:\\.|[^`\\])*`)'
        if isinstance(script, bytes):
            long = long.encode(encoding, errors)
            short = short.encode(encoding, errors)
            literals = literals.encode(encoding, errors)
        sub = script[:0]
        cnt = 0

        parts = re.split(literals, script)
        literal_parts = [part for i, part in enumerate(parts) if not i % 2]
        payload_index = 2 * max(range(len(literal_parts)), key=lambda i: get_len(literal_parts[i], encoding))
        for i, part in enumerate(parts):
            if i != payload_index:
                part, c = re.subn(long, short, part)
                cnt += c
            sub += part
        if cnt >= min_cnt:
            script = sub
            if add_used_aliases:
                alias += '\n'
                if isinstance(script, bytes):
                    alias = alias.encode(encoding, errors)
                if alias not in script:
                    script = alias + script.lstrip()
    new_len = get_len(script, encoding)
    if new_len > orig_len:
        print(f'Warning size has grown: {new_len} B > {orig_len} B', file=sys.stderr)
    return script


def html_wrap(script: AnyStr,
              aliases: str = default_aliases,
              min_cnt: int = 2,
              lang: Optional[str] = None,
              encoding: Optional[str] = None,
              add_mobile: bool = False
              ) -> AnyStr:
    if lang is None:
        lang = 'en'
    encoding, errors = get_encoding_errors(encoding)
    mobile_meta = '<meta name=viewport content="width=device-width,initial-scale=1">' if add_mobile else ''
    html_header = f'<!DOCTYPE html><html lang={lang}><head><meta charset={encoding}>{mobile_meta}</head><body><script>'
    html_footer = '</script></body></html>'
    newline = '\n'
    if isinstance(script, bytes):
        html_header = html_header.encode(encoding, errors)
        html_footer = html_footer.encode(encoding, errors)
        newline = newline.encode(encoding, errors)
    if aliases:
        script = uglify(script, aliases, min_cnt, encoding=encoding)
    return newline.join([html_header, script.strip(), html_footer])
