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
    # noinspection PyPackages
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

literals_regex = rf'((?:\[\.\.\.)`(?:\\.|[^`\\])*`])'


def safe_encode(s: str, encoding: str, get_back_unused: bool = False) -> bytes:
    encoding = encoding.lower()
    out = s.encode(encoding, 'strict' if encoding.replace('-', '') == 'utf8' else 'backslashreplace')
    out = re.sub(rb'\\U000?([\da-f]{5,6})', rb'\\u{\1}', out)
    if get_back_unused and encoding == 'cp1252':
        out = out.replace(b'\\x81', b'\x81').replace(b'\\x8d', b'\x8d').replace(b'\\x8f', b'\x8f').replace(b'\\x90', b'\x90').replace(b'\\x9d', b'\x9d')  # These actually do not require escaping in HTML
    return out


def get_len(s: AnyStr, encoding: str) -> int:
    return len(safe_encode(s, encoding) if isinstance(s, str) else s)


def uglify(script: AnyStr,
           aliases: str = default_aliases,
           replace_quoted: bool = True,
           min_cnt: int = 2,
           prevent_grow: bool = True,
           add_used_aliases: bool = True,
           encoding: str = 'utf8',
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
        if isinstance(script, bytes):
            long = safe_encode(long, encoding)
            if isinstance(short, str):
                short = safe_encode(short, encoding)
            else:
                short = lambda x, short=short: safe_encode(short(x), encoding)
        sub = script[:0]
        cnt = 0
        parts = re.split(safe_encode(literals_regex, encoding) if isinstance(script, bytes) else literals_regex, script)
        for i, part in enumerate(parts):
            if i % 2 == 0:
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
              title: str = '',
              ) -> AnyStr:
    encoding = encoding.lower()
    if encoding == 'utf-8':
        encoding = 'utf8'
    elif encoding in ['cp1252', 'latin1']:
        encoding = 'l1'  # HTML5 treats these the same
    mobile_meta = '<meta name=viewport content="width=device-width,initial-scale=1">' * mobile
    title_element = f'<title>{title}</title>' * bool(title)
    html_header = f'<!DOCTYPEhtml><html lang={lang}><meta charset={encoding}>{mobile_meta}{title_element}<body><script>'
    html_footer = '</script>'
    sep = ''
    if isinstance(script, bytes):
        html_header = safe_encode(html_header, encoding)
        html_footer = safe_encode(html_footer, encoding)
        sep = safe_encode(sep, encoding)
    if aliases:
        script = uglify(script, aliases, replace_quoted, min_cnt, prevent_grow, encoding=encoding)
    return sep.join([html_header, script.strip(), html_footer])
