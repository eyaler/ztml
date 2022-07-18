"""Burrows–Wheeler transform

Implementation follows:
https://github.com/louisabraham/pydivsufsort/blob/master/tests/reference.py
"""


from typing import Iterable, Optional, Tuple, Union

import numpy as np
from pydivsufsort import divsufsort

if not __package__:
    import default_vars
else:
    from . import default_vars


DataType = Union[str, Iterable[int]]


def encode(data: DataType, validate: bool = True) -> Tuple[str, int]:
    lst = [ord(c) for c in data] if isinstance(data, str) else data
    sa = divsufsort(np.array(lst)) if lst else []
    trans = lst[-1:] + [lst[i - 1] for i in sa if i]
    if isinstance(data, str):
        trans = ''.join(chr(i) for i in trans)
    index = list(sa).index(0) if lst else 0
    if validate:
        decoded = decode(trans, index)
        assert decoded == data, (len(decoded), len(data), decoded[:30], data[:30])
    return trans, index


def decode(trans: DataType, index: int) -> DataType:
    ordered = [(c, i - (i <= index)) for i, c in enumerate(trans)]
    ordered.sort()
    out: DataType = [0] * len(trans)
    i = 0
    while i < len(trans):
        out[i], index = ordered[index]
        i += 1
    if isinstance(trans, str):
        out = ''.join(out)
    return out


def get_js_decoder(index: int, is_str: bool = False, data_var: Optional[str] = None) -> str:
    if data_var is None:
        data_var = default_vars.text if is_str else default_vars.bitarray
    expand = join = ''
    if is_str:
        expand = f'{data_var}=[...{data_var}]\n'
        join = f"\n{data_var}={data_var}.join('')"
    return f'''k={index}
{expand}s={data_var}.map((c,i)=>[c,i-(i<=k)]).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0])
for(j=0;j<s.length;)[{data_var}[j++],k]=s[k]{join}
'''


def encode_and_get_js_decoder(data: DataType,
                              data_var: Optional[str] = None,
                              validate: bool = True
                              ) -> Tuple[str, str]:
    trans, index = encode(data, validate)
    return trans, get_js_decoder(index, isinstance(data, str), data_var)


def test() -> None:
    symbols = ['', 'a', 'b', 'א', 'ב']
    for x in symbols:
        for y in symbols:
            for z in symbols:
                encode(f'{x}{y}{z}', validate=True)
    symbols = ['', '0', '1', '255']
    for x in symbols:
        for y in symbols:
            for z in symbols:
                encode([int(c) for c in f'{x}{y}{z}'], validate=True)


if __name__ == '__main__':
    test()
