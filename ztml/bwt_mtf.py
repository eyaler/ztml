"""Burrows–Wheeler and Move-to-front transforms

Implementation follows pydivsufsort tests, to unnecessitate adding an EOF token.

References:
https://www.hpl.hp.com/techreports/Compaq-DEC/SRC-RR-124.pdf
https://github.com/louisabraham/pydivsufsort/blob/master/tests/reference.py
https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.43.1175&rep=rep1&type=pdf
https://www.juergen-abel.info/files/preprints/preprint_universal_text_preprocessing.pdf
http://groups.di.unipi.it/~gulli/tutorial/burrows_wheeler.pdf (note: has errors afaict)
"""


from typing import Iterable, List, Optional, overload, Tuple, Union

import numpy as np
from pydivsufsort import divsufsort

if not __package__:
    import default_vars
else:
    from . import default_vars


mtf_variants = None, 0, 1, 2, 50, 52, 60, 70, 80, 90
default_mtf_variant = 0
order1 = 'AOUIEVWXYZaouievwxyz'
order2 = 'VWXYZAOUIEvwxyzaouie'


reorder_table = str.maketrans(order1, order2)
reverse_reorder_table = str.maketrans(order2, order1)


def mtf_rank(mtf: int, rank: int, prev: int) -> int:
    if mtf == 0:
        new_rank = 0
    elif mtf == 1:
        new_rank = rank > 1
    elif mtf == 2:
        new_rank = rank > 1 or rank == 1 and not prev
    elif mtf == 50:
        new_rank = rank // 2
    elif mtf == 52:
        new_rank = rank // 2 if rank > 1 else rank == 1 and not prev
    else:
        new_rank = int(round(rank * mtf / 100))
    return new_rank


def mtf_encode(data: Iterable[int],
               mtf: Optional[int] == default_mtf_variant,
               validate=True
               ) -> List[int]:
    ranks = list(range(max(data, default=-1) + 1))
    out = []
    prev = 1
    for i in data:
        rank = ranks.index(i)  # Time-consuming op.
        out.append(rank)
        ranks.pop(rank)
        ranks.insert(mtf_rank(mtf, rank, prev), i)
        prev = rank
    if validate:
        decoded = mtf_decode(out, mtf)
        if not hasattr(data, '__getitem__'):
            data = type(decoded)(data)
        assert decoded == data, (len(decoded), len(data), decoded[:30], data[:30])
    return out


def mtf_decode(data: Iterable[int], mtf: Optional[int] == default_mtf_variant) -> List[int]:
    out = list(data)
    ranks = list(range(max(out, default=-1) + 1))
    prev = 1
    for i, rank in enumerate(out):
        out[i] = ranks.pop(rank)
        ranks.insert(mtf_rank(mtf, rank, prev), out[i])
        prev = rank
    return out


@overload
def encode(data: str, reorder=..., mtf=..., validate=...) -> Tuple[str, int]:
    ...


@overload
def encode(data: Iterable[int], reorder=..., mtf=..., validate=...) -> Tuple[List[int], int]:
    ...


def encode(data,
           reorder: bool = True,
           mtf: Optional[int] = default_mtf_variant,
           validate: bool = True
           ):
    assert mtf in mtf_variants, mtf
    is_str = isinstance(data, str)
    out = list(data)
    if reorder:
        if not is_str:
            out = [chr(i) for i in out]
        out = ''.join(out).translate(reorder_table)
    if is_str or reorder:
        out = [ord(c) for c in out]
    sa = divsufsort(np.array(out)) if out else []
    out = out[-1:] + [out[i - 1] for i in sa if i]
    index = list(sa).index(0) if out else 0
    if mtf is not None:
        out = mtf_encode(out, mtf, validate)  # Time-consuming op.
    if is_str:
        out = ''.join(chr(i) for i in out)
    if validate:
        decoded = decode(out, index, reorder, mtf)
        if not hasattr(data, '__getitem__'):
            data = type(decoded)(data)
        assert decoded == data, (len(decoded), len(data), decoded[:30], data[:30])
    return out, index


@overload
def decode(data: str, index, reorder=..., mtf=...) -> str:
    ...


@overload
def decode(data: Iterable[int], index, reorder=..., mtf=...) -> List[int]:
    ...


def decode(data, index: int, reorder: bool = True, mtf: Optional[int] = default_mtf_variant):
    assert mtf in mtf_variants, mtf
    is_str = isinstance(data, str)
    out = list(data)
    if mtf is not None:
        if is_str:
            out = [ord(c) for c in out]
        out = mtf_decode(out, mtf)
        if is_str:
            out = [chr(i) for i in out]
    ordered = [(c, i - (i <= index)) for i, c in enumerate(out)]
    ordered.sort()
    for i in range(len(out)):
        out[i], index = ordered[index]
    if reorder:
        if not is_str:
            out = [chr(i) for i in out]
        out = ''.join(out).translate(reverse_reorder_table)
        if not is_str:
            out = [ord(c) for c in out]
    elif is_str:
        out = ''.join(out)
    return out


def get_js_decoder(data: Union[str, Iterable[int]],
                   index: int,
                   reorder: bool = True,
                   mtf: Optional[int] = default_mtf_variant,
                   add_bwt_func: bool = True,
                   bwt_func_var: str = default_vars.bwt_func,
                   data_var: Optional[str] = None
                   ) -> str:
    assert mtf in mtf_variants, mtf
    is_str = isinstance(data, str)
    if data_var is None:
        data_var = default_vars.text if is_str else default_vars.bitarray
    js_decoder = ''
    if mtf is not None:
        if mtf == 0:
            mtf_op = f'd.unshift({data_var}[j++]=d.splice(k,1)[0])'
        elif mtf == 1:
            mtf_op = f'd.splice(k>1,0,{data_var}[j++]=d.splice(k,1)[0])'
        elif mtf == 2:
            js_decoder += 'n=1\n'
            mtf_op = f'd.splice(k>!!n,0,{data_var}[j++]=d.splice(k,1)[0]),n=k'
        elif mtf == 50:
            mtf_op = f'd.splice(k/2|0,0,{data_var}[j++]=d.splice(k,1)[0])'
        elif mtf == 52:
            js_decoder += 'n=1\n'
            mtf_op = f'd.splice(k>1?k/2|0:k>n,0,{data_var}[j++]=d.splice(k,1)[0]),n=k'
        else:
            mtf_op = f'd.splice(k*{mtf / 100}+.5|0,0,{data_var}[j++]=d.splice(k,1)[0])'
        if is_str:
            js_decoder += f'{data_var}=[...{data_var}].map(c=>c.codePointAt())\n'
        js_decoder += f'''d=[...Array({data_var}.reduce((a,b)=>a>b?a:b+1,0)).keys()]
j=0
for(k of {data_var}){mtf_op}
'''
        if is_str:
            js_decoder += f'{data_var}={data_var}.map(i=>String.fromCodePoint(i))\n'
    if add_bwt_func:
        js_decoder += f"{bwt_func_var}=(d,k)=>{{s=d.map((c,i)=>[c,i-(i<=k)]).sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);for(j in s)[d[j],k]=s[k]}}\n"  # ?1:0 needed for Safari (see https://stackoverflow.com/questions/73451718/sorting-nested-arrays-in-safari)
    expand = f'=[...{data_var}]' * is_str
    js_decoder += f'{bwt_func_var}({data_var}{expand},{index})\n'
    dyn_orders = None
    if reorder:
        symbols = set(data)
        if not is_str:
            symbols = {chr(i) for i in symbols}
        dyn_orders = list(zip(*[(c1, c2) for c1, c2 in zip(order1, order2) if c1 in symbols]))
        if dyn_orders:
            dyn_order1, dyn_order2 = dyn_orders
            dyn_order1 = ''.join(dyn_order1)
            dyn_order2 = ''.join(dyn_order2)
            if not is_str:
                js_decoder += f'{data_var}={data_var}.map(i=>String.fromCodePoint(i))\n'
            js_decoder += f'''d={{}};[...'{dyn_order2}'].map((c,i)=>d[c]=[...'{dyn_order1}'][i])
{data_var}={data_var}.map(c=>{'d[c]||c).join``' if is_str else '(d[c]||c).codePointAt())'}
'''
    if is_str and not dyn_orders:
        js_decoder += f'{data_var}={data_var}.join``\n'
    return js_decoder


@overload
def encode_and_get_js_decoder(data: str, reorder=..., mtf=..., add_bwt_func=...,
                              bwt_func_var=..., data_var=..., validate=...) -> Tuple[str, str]:
    ...


@overload
def encode_and_get_js_decoder(data: Iterable[int], reorder=..., mtf=..., add_bwt_func=...,
                              bwt_func_var=..., data_var=..., validate=...) -> Tuple[List[int], str]:
    ...


def encode_and_get_js_decoder(data,
                              reorder: bool = True,
                              mtf: Optional[int] = default_mtf_variant,
                              add_bwt_func: bool = True,
                              bwt_func_var: str = default_vars.bwt_func,
                              data_var: Optional[str] = None,
                              validate: bool = True
                              ):
    assert mtf in mtf_variants, mtf
    is_str = isinstance(data, str)
    if data_var is None:
        data_var = default_vars.text if is_str else default_vars.bitarray
    if data_var == default_vars.bitarray:
        reorder = False
        mtf = None
    encoded, index = encode(data, reorder, mtf, validate)
    return encoded, get_js_decoder(data, index, reorder, mtf, add_bwt_func, bwt_func_var, data_var)


def test() -> None:
    mtf_test = [3, 2, 2, 2, 3, 2, 2, 3, 2, 2]
    mtf0 = mtf_encode(mtf_test[:], mtf=0, validate=True)
    assert mtf0 == [3, 3, 0, 0, 1, 1, 0, 1, 1, 0], mtf0
    mtf1 = mtf_encode(mtf_test[:], mtf=1, validate=True)
    assert mtf1 == [3, 3, 1, 0, 2, 0, 0, 1, 1, 0], mtf1
    mtf2 = mtf_encode(mtf_test[:], mtf=2, validate=True)
    assert mtf2 == [3, 3, 1, 0, 2, 0, 0, 1, 0, 0], mtf2

    symbols = '', '\0', '\1', 'a', 'b', 'א', 'ב'
    for x in symbols:
        for y in symbols:
            for z in symbols:
                for mtf in mtf_variants:
                    for reorder in range(2):
                        encode(f'{x}{y}{z}', reorder=bool(reorder), mtf=mtf, validate=True)

    symbols = '', '0', '1', '97', '255'
    for x in symbols:
        for y in symbols:
            for z in symbols:
                for mtf in mtf_variants:
                    for reorder in range(2):
                        encode([int(c) for c in f'{x}{y}{z}'], reorder=bool(reorder), mtf=mtf, validate=True)


if __name__ == '__main__':
    test()
