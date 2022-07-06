"""Canonical Huffman encoding

Even though we later compress with DEFLATE which does its own Huffman encoding internally,
I found that for text compression, it is significantly beneficial to pre-encode with Huffman.
Canonical encoding alleviates the necessity to save or to reconstruct the codebook.
A minimalistic JS decoder code is generated.
References:
https://wikipedia.org/wiki/Canonical_Huffman_code
https://github.com/ilanschnell/bitarray/blob/master/doc/canonical.rst
https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes
"""


from collections import Counter
import json
import re
from typing import Dict, List, Tuple

from bitarray import bitarray
from bitarray.util import ba2int, canonical_decode, canonical_huffman
import numpy as np

from . import default_names


no_huffman = False  # note: not implemented in decoder


def encode(text: str,
           validate: bool = True,
           verbose: bool = False
           ) -> Tuple[List[int], str, str, str, Dict[str, str]]:
    charset = canonical_table = lengths = ''
    counter = Counter(text)
    if no_huffman:
        code_len = len(bin(ord(max(counter)))) - 2
        codebook = {c: bitarray(bin(ord(c))[2:].zfill(code_len)) for c in counter}
    else:
        if len(counter):
            codebook, counts, symbols = canonical_huffman(counter)
        else:
            codebook = {}
            counts = []
            symbols = []
        charset = json.dumps(''.join(symbols[::-1]))
        max_diff = len(max(re.findall('0*', ''.join(str(int(c > 0)) for c in counts[1:])), key=len)) + 1
        if max_diff >= 36:
            print(f'Warning: the naive huffman decoded implementation cannot be used with max_diff={max_diff}')
        else:
            lengths = json.dumps(''.join(np.base_repr(len(v) - (len(list(codebook.items())[i - 1][1]) if i else 0), 36)[-1] + k for i, (k, v) in enumerate(codebook.items())))
        canonical_table = {len(code): [ba2int(code), len(codebook) - i - 1] for i, (symbol, code) in enumerate(codebook.items())}
        canonical_table = json.dumps(canonical_table).replace(' ', '').replace('"', '')

    bits = bitarray()
    if codebook:
        bits.encode(codebook, text)
    if verbose:
        print(sorted([(k, v.to01()) for k, v in codebook.items()], key=lambda x: -counter[x[0]]))
        if charset:
            print(len(charset), charset)
            print(canonical_table)
    if validate:
        assert not codebook or text == ''.join(bits.decode(codebook))
        assert no_huffman or text == ''.join(canonical_decode(bits, counts, symbols))
    rev_codebook = {v.to01(): k for k, v in codebook.items()}
    return bits.tolist(), charset, canonical_table, lengths, rev_codebook


def get_js_decoder(charset: str,
                   canonical_table: str,
                   bitarray_name: str = default_names.bitarray,
                   text_name: str = default_names.text
                   ) -> str:
    return '''s=CHARSET
d=CANONICAL_TABLE
for(j=0,TEXT_NAME='';j<BITARRAY_NAME.length;TEXT_NAME+=s[d[k][1]+m])for(c='',k=-1;!((m=d[++k]?.[0]-parseInt(c,2))>=0);j+=4)c+=BITARRAY_NAME[j]>>
'''.replace('CHARSET', charset).replace('CANONICAL_TABLE', canonical_table).replace('BITARRAY_NAME', bitarray_name).replace('TEXT_NAME', text_name)  # note using >>7 instead of &1 to deal with safari rendering inaccduracy


def get_legacy_js_decoder(lengths: str,
                          bitarray_name: str = default_names.bitarray,
                          text_name: str = default_names.text
                          ) -> str:
    return '''s=LENGTHS
d={}
for(j=0,c='';j<s.length;j+=2)c+='0'.repeat(parseInt(s[j],36)),d[c]=s[j+1],c=(parseInt(c,2)+1).toString(2).padStart(c.length,0)
for(j=0,c=TEXT_NAME='';j<BITARRAY_NAME.length;j+=4)(c+=BITARRAY_NAME[j]>>7)in d&&(TEXT_NAME+=d[c],c='')
'''.replace('LENGTHS', lengths).replace('BITARRAY_NAME', bitarray_name).replace('TEXT_NAME', text_name)  # note using >>7 instead of &1 to deal with safari rendering inaccduracy


def encode_and_get_js_decoder(text: str,
                              legacy: bool = False,
                              bitarray_name: str = default_names.bitarray,
                              text_name: str = default_names.text,
                              validate: bool = True,
                              verbose: bool = False
                              ) -> Tuple[List[int], str]:
    bits, charset, canonical_table, lengths, _ = encode(text, validate, verbose)
    if legacy:
        return bits, get_legacy_js_decoder(lengths, bitarray_name, text_name)
    return bits, get_js_decoder(charset, canonical_table, bitarray_name, text_name)
