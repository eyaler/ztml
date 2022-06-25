import re
from typing import AnyStr


default_aliases = '''
Q = document
A = (e, c) => e.appendChild(c)
B = document.body
C = 'textContent'
D = 'dataset'
E = e => document.createElement(e)
F = speechSynthesis
G = 'width'
H = 'height'
I = parseInt
J = 'background'
K = 'color'
L = 'length'
M = (e, d) => e.setAttribute('style', d)
N = setInterval
O = setTimeout
P = 'parentElement'
R = 'target'
S = 'style'
'''


def uglify(script: AnyStr,
           aliases: str = default_aliases,
           min_cnt: int = 2,
           add_used_aliases: bool = True
           ) -> AnyStr:
    orig_len = len(script)
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
        if isinstance(script, bytes):
            long = long.encode()
            short = short.encode()
        sub, cnt = re.subn(long, short, script)
        if cnt >= min_cnt:
            script = sub
            if add_used_aliases:
                alias += '\n'
                if isinstance(script, bytes):
                    alias = alias.encode()
                if alias not in script:
                    script = alias + script.lstrip()
    if len(script) > orig_len:
        print(f'Warning size has grown: {len(script)} > {orig_len}')
    return script


def html_wrap(script: AnyStr,
              aliases: str = default_aliases,
              lang: str = 'en',
              encoding: str = 'utf8',
              add_mobile: bool = False
              ) -> AnyStr:
    mobile_meta = '<meta name=viewport content="width=device-width,initial-scale=1">' if add_mobile else ''
    html_header = f'<!DOCTYPE html><html lang={lang}><head><meta charset={encoding}>{mobile_meta}</head><body><script>'
    html_footer = '</script></body></html>'
    newline = '\n'
    if isinstance(script, bytes):
        html_header = html_header.encode()
        html_footer = html_footer.encode()
        newline = newline.encode()
    if aliases:
        script = uglify(script, aliases)
    return newline.join([html_header, script.strip(), html_footer])
