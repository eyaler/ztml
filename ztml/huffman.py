"""Canonical Huffman encoding

Even though we later compress with DEFLATE which does its own Huffman encoding internally,
I found that for text compression, it is significantly beneficial to pre-encode with Huffman.
Canonical encoding obviates saving or reconstructing an explicit codebook.
Instead, we save a string of symbols and a sparse dictionary from codeword lengths to bases and offsets
(see Moffat&Turpin paper, but note it is my custom implementation).
A minimalistic JS decoder code is generated.

References:
https://wikipedia.org/wiki/Canonical_Huffman_code
https://github.com/ilanschnell/bitarray/blob/master/doc/canonical.rst
https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes (Moffat&Turpin)
https://arxiv.org/pdf/1410.3438.pdf
https://arxiv.org/pdf/2108.05495.pdf
"""


from collections import Counter
import sys
from typing import Dict, List, Tuple

from bitarray import bitarray
from bitarray.util import ba2int, canonical_decode, canonical_huffman

if not __package__:
    import default_vars
else:
    # noinspection PyPackages
    from . import default_vars


DEBUG_SKIP_HUFFMAN = False  # This is just for benchmarking and is not implemented in JS decoder


def encode(text: str,
           validate: bool = True,
           verbose: bool = False
           ) -> Tuple[List[int], str, str, Dict[str, str]]:
    charset = canonical_table = ''
    counter = Counter(text)
    if DEBUG_SKIP_HUFFMAN:
        code_len = len(bin(ord(max(counter, default='\0')))) - 2
        codebook = {c: bitarray(bin(ord(c))[2:].zfill(code_len)) for c in counter}
    else:
        if len(counter):
            codebook, counts, symbols = canonical_huffman(counter)
        else:
            codebook = {}
            counts = []
            symbols = []
        charset = ''.join(symbols[::-1])
        canonical_table = {len(code): [2**len(code) - ba2int(code), len(codebook) - i - 1]
                           for i, code in enumerate(codebook.values())}
        canonical_table = str(canonical_table).replace(' ', '').replace("'", '')

    bits = bitarray()
    if codebook:
        bits.encode(codebook, text)
    if verbose:
        print(sorted([(k, v.to01()) for k, v in codebook.items()],
                     key=lambda x: -counter[x[0]]), file=sys.stderr)
        if charset:
            print(len(charset), charset, file=sys.stderr)
            print(canonical_table, file=sys.stderr)
    if validate:
        assert not codebook or ''.join(bits.decode(codebook)) == text
        assert DEBUG_SKIP_HUFFMAN or ''.join(canonical_decode(bits, counts, symbols)) == text
    rev_codebook = {v.to01(): k for k, v in codebook.items()}
    return bits.tolist(), charset, canonical_table, rev_codebook


def get_js_decoder(charset: str,
                   canonical_table: str,
                   bitarray_var: str = default_vars.bitarray,
                   text_var: str = default_vars.text,
                   ) -> str:
    charset = charset.replace('\\', '\\\\').replace('\0', '\\0').replace('\r', '\\r').replace('`', '\\`').replace('${', '\\${')  # Note that charset may include more characters requiring safe encoding as regard to encoding domains as well as HTML character overrides
    return f'''s=[...`{charset}`]
d={canonical_table}
for(j=0,{text_var}='';j<{bitarray_var}.length;{text_var}+=s[d[k][1]+m])for(c='',k=-1;!((m=2**++k-d[k]?.[0]-('0b'+c))>=0);j++)c+={bitarray_var}[j]&1
'''


def encode_and_get_js_decoder(text: str,
                              bitarray_var: str = default_vars.bitarray,
                              text_var: str = default_vars.text,
                              validate: bool = True,
                              verbose: bool = False
                              ) -> Tuple[List[int], str]:
    bits, charset, canonical_table, _ = encode(text, validate, verbose)
    return bits, get_js_decoder(charset, canonical_table, bitarray_var, text_var)
