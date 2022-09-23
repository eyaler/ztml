""" Minification by way of aliasing AKA uglification

Warnings:
1. The two-parameter aliases would miss substitutions involving tag function syntax, i.e.
   func`str`, even if you specify such forms explicitly. However, see following examples.
2. While alias substitution does support some level of composition, e.g.:
      a.appendChild(b=document.createElement`p`).innerHTML='hi'           # => C(a,b=E`p`).C='hi'
   More complex compositions would miss later substitutions, e.g.:
      a.appendChild(b=document.createElement`p`).appendChild(c)           # => C(a,b=E`p`).appendChild(c)
      a.appendChild(b=document.createElement`p`).setAttribute('style',c)  # => C(a,b=E`p`).setAttribute('style',c)
3. Non-static method aliases support only specific parameter signatures as appear in
   default_aliases. Attempting to specify different signatures will break your code.
4. You may need to set replace_quoted=False if you do not want e.g. all 'length', "Length"
   to be replaced by: L
5. Aliases to be used in other aliases e.g. document, should be specified before the latter.
"""


import re
import sys
from typing import AnyStr

if not __package__:
    import default_vars
else:
    from . import default_vars


default_lang = 'en'

default_aliases = '''
D = document
A = (e, d) => e.setAttribute('style', d)
B = document.body
C = (e, c) => e.appendChild(c)
E = (e='div') => document.createElement(e)
F = String
G = 'target'
H = 'innerHTML'
I = setInterval
J = clearInterval
K = e => e.codePointAt()
L = 'length'
M = Math
N = speechSynthesis
O = setTimeout
'''


def get_literals_regex(payload_var: str = default_vars.payload) -> str:
    return rf'(\b{payload_var}=`(?:\\.|[^`\\])*`)'


def safe_encode(s: str, encoding: str) -> bytes:
    return re.sub(rb'\\U000?([\dA-Fa-f]{5,6})', rb'\\u{\1}',
                  s.encode(encoding, 'strict' if encoding.lower().replace('-', '') == 'utf8' else 'backslashreplace'))


def get_len(script: str, encoding: str) -> int:
    return len(safe_encode(script, encoding) if isinstance(script, str) else script)


def uglify(script: AnyStr,
           aliases: str = default_aliases,
           replace_quoted: bool = True,
           min_cnt: int = 2,
           prevent_grow: bool = True,
           add_used_aliases: bool = True,
           encoding: str = 'utf8',
           payload_var: str = default_vars.payload
           ) -> AnyStr:
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
        comma = ''
        if re.search('(\\b\\w+\\b)[^>]*=>[^.]*\\b\\1\\.', long):
            prefix = '(\\w[\\w.[\\]]*)\\.'
            if re.search('[^,]+,[^>]+=>', long):
                comma = ','
        long = re.sub('[^>]*(?P<prefix>\\b\\w+\\b)[^>]*=>[^.]*\\b(?P=prefix)\\.|[^>]+=>|\\([^,)]*\\)|,.*', '', long)
        if prefix:
            short += '(\\1'
            if '(' not in long:
                long += '('
                short += comma
            long = prefix + re.sub('[\'"]', '[\'"]', re.escape(long))
        elif long[0] == long[-1] in '\'"':
            short = lambda x, short=short, long=long: f"{'[' * (len(x[0]) < len(long))}{short}{']' * (len(x[0]) < len(long))}"
            long = f'\\.{long[1:-1]}' + re.sub('[\'"]', '[\'"]', f'|{long}') * replace_quoted
        if re.match('\\w', long[0]):
            long = f'\\b{long}'
        if re.match('\\w', long[-1]):
            long += '\\b'
        literals_regex = get_literals_regex(payload_var)
        if isinstance(script, bytes):
            long = safe_encode(long, encoding)
            if isinstance(short, str):
                short = safe_encode(short, encoding)
            else:
                short = lambda x, short=short: safe_encode(short(x), encoding)
            literals_regex = literals_regex.encode()
        sub = script[:0]
        cnt = 0
        parts = re.split(literals_regex, script)
        literals_parts = [part for i, part in enumerate(parts) if i % 2]
        payload_index = max(range(len(literals_parts)), key=lambda i: get_len(literals_parts[i], encoding), default=None)
        for i, part in enumerate(parts):
            if (i-1) / 2 != payload_index or not payload_var:
                part, c = re.subn(long, short, part)
                cnt += c
            sub += part
        if cnt >= min_cnt:
            if add_used_aliases:
                alias += '\n'
                if isinstance(sub, bytes):
                    alias = safe_encode(alias, encoding)
                if alias not in sub:
                    sub = alias + sub.lstrip()
            if not prevent_grow or get_len(sub, encoding) < get_len(script, encoding):
                script = sub
    new_len = get_len(script, encoding)
    if new_len > orig_len:
        print(f'Warning: uglified size increased: {new_len} B > {orig_len} B', file=sys.stderr)
    return script


def html_wrap(script: AnyStr,
              aliases: str = default_aliases,
              replace_quoted: bool = True,
              min_cnt: int = 2,
              prevent_grow: bool = True,
              lang: str = default_lang,
              encoding: str = 'utf8',
              mobile: bool = False,
              payload_var: str = default_vars.payload
              ) -> AnyStr:
    mobile_meta = '<meta name=viewport content="width=device-width,initial-scale=1">' * mobile
    html_header = f'<!DOCTYPEhtml><html lang={lang}><meta charset={encoding}>{mobile_meta}<body><script>'
    html_footer = '</script>'
    sep = ''
    if isinstance(script, bytes):
        html_header = html_header.encode()
        html_footer = html_footer.encode()
        sep = sep.encode()
    if aliases:
        script = uglify(script, aliases, replace_quoted, min_cnt, prevent_grow, encoding=encoding, payload_var=payload_var)
    return sep.join([html_header, script.strip(), html_footer])
