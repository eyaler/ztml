"""Burrows–Wheeler and Move-to-front transforms

Implementation follows pydivsufsort tests, to unnecessitate adding an EOF token.
Benchmarked and rejected the following variations of [Balkenhol & Shtarkov 1999]: vowel-sorted bwt, mtf-1, mtf-2.

References:
https://www.hpl.hp.com/techreports/Compaq-DEC/SRC-RR-124.pdf
https://github.com/louisabraham/pydivsufsort/blob/master/tests/reference.py
[Balkenhol & Shtarkov 1999] https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.43.1175&rep=rep1&type=pdf
"""


from typing import Iterable, Optional, Tuple, Union

import numpy as np
from pydivsufsort import divsufsort

if not __package__:
    import default_vars
else:
    from . import default_vars


DataType = Union[str, Iterable[int]]


def encode(data: DataType, mtf: bool = True, validate: bool = True) -> Tuple[DataType, int]:
    is_str = isinstance(data, str)
    lst = [ord(c) for c in data] if is_str else data
    sa = divsufsort(np.array(lst)) if lst else []
    trans = lst[-1:] + [lst[i - 1] for i in sa if i]
    index = list(sa).index(0) if lst else 0
    if mtf:
        ranks = list(range(max(lst, default=-1) + 1))
        mtf_trans = []
        for i in trans:
            rank = ranks.index(i)  # Time-consuming op.
            mtf_trans.append(rank)
            ranks.pop(rank)
            ranks.insert(0, i)
        trans = mtf_trans
    if is_str:
        trans = ''.join(chr(i) for i in trans)
    if validate:
        decoded = decode(trans, index, mtf)
        assert decoded == data, (len(decoded), len(data), decoded[:30], data[:30])
    return trans, index


def decode(trans: DataType, index: int, mtf: bool = True) -> DataType:
    is_str = isinstance(trans, str)
    if mtf:
        if is_str:
            trans = [ord(c) for c in trans]
        else:
            trans = trans[:]
        ranks = list(range(max(trans, default=-1) + 1))
        for i, rank in enumerate(trans):
            trans[i] = ranks.pop(rank)
            ranks.insert(0, trans[i])
        if is_str:
            trans = ''.join([chr(i) for i in trans])
    ordered = [(c, i - (i <= index)) for i, c in enumerate(trans)]
    ordered.sort()
    out: DataType = [0] * len(trans)
    for i in range(len(trans)):
        out[i], index = ordered[index]
    if is_str:
        out = ''.join(out)
    return out


def get_js_decoder(index: int,
                   is_str: bool = False,
                   mtf: bool = True,
                   add_bwt_func: bool = True,
                   bwt_func_var: str = default_vars.bwt_func,
                   data_var: Optional[str] = None
                   ) -> str:
    if data_var is None:
        data_var = default_vars.text if is_str else default_vars.bitarray
    js_decoder = ''
    if mtf and data_var != default_vars.bitarray:
        if is_str:
            js_decoder += f'{data_var}=[...{data_var}].map(c=>c.codePointAt())\n'
        js_decoder += f'''d=[...Array({data_var}.reduce((a,b)=>Math.max(a,b+1),0)).keys()]
j=0
for(k of {data_var}){data_var}[j++]=d[k],d.unshift(d.splice(k,1)[0])
'''
        if is_str:
            js_decoder += f'{data_var}={data_var}.map(i=>String.fromCodePoint(i))\n'
    if add_bwt_func:
        js_decoder += f'{bwt_func_var}=(d,k)=>{{s=d.map((c,i)=>[c,i-(i<=k)]).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]);for(j=0;j<s.length;)[d[j++],k]=s[k]}}\n'
    expand = f'=[...{data_var}]' if is_str else ''
    js_decoder += f'{bwt_func_var}({data_var}{expand},{index})\n'
    if is_str:
        js_decoder += f"{data_var}={data_var}.join('')\n"
    return js_decoder


def encode_and_get_js_decoder(data: DataType,
                              mtf: bool = True,
                              add_bwt_func: bool = True,
                              bwt_func_var: str = default_vars.bwt_func,
                              data_var: Optional[str] = None,
                              validate: bool = True
                              ) -> Tuple[DataType, str]:
    trans, index = encode(data, mtf, validate)
    return trans, get_js_decoder(index, isinstance(data, str), mtf, add_bwt_func, bwt_func_var, data_var)


def test() -> None:
    symbols = ['', 'a', 'b', 'א', 'ב']
    for x in symbols:
        for y in symbols:
            for z in symbols:
                encode(f'{x}{y}{z}', mtf=False, validate=True)
                encode(f'{x}{y}{z}', mtf=True, validate=True)
    symbols = ['', '0', '1', '255']
    for x in symbols:
        for y in symbols:
            for z in symbols:
                encode([int(c) for c in f'{x}{y}{z}'], mtf=False, validate=True)
                encode([int(c) for c in f'{x}{y}{z}'], mtf=True, validate=True)


if __name__ == '__main__':
    test()
