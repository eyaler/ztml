"""crEnc encoding based on yEnc and optimized for inline HTML / JS text compression

In the premise of yEnc (why encode?), we only encode symbols where absolutely required,
which in this use case is just the carriage-return (CR).
When the HTML or JS charset can be set to a single-byte encoding as cp1252 (ascii, latin1),
we can use 254 byte values out of 256 (excluding only CR and an escape character),
and embed in JS template literals quotes ``, after escaping \, ` and ${ with a \
The escape character can be predetermined or optimized per message as an infrequent symbol.
An optimal overall offset can be added to minimize escaping as suggested in dynEncode.
The decoder further takes care of HTML character overrides for NUL and codes in 128 - 159.
A minimalistic JS decoder code is generated.
The overhead is ~ 4/256 ~ 1.6% (compared to 33.3% for Base64).

References:
http://www.yenc.org
https://github.com/eshaz/simple-yenc
https://github.com/eshaz/simple-yenc#what-is-dynencode
https://html.spec.whatwg.org/multipage/parsing.html#table-charref-overrides
https://stackoverflow.com/a/10081375/664456
"""


from collections import Counter
import re
from typing import AnyStr, Optional, overload, Tuple, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if not __package__:
    import default_vars
else:
    from . import default_vars


def find_best_escape(data: bytes) -> int:
    chars = [k for k, v in Counter(data).most_common()]
    chars += [c for c in range(256) if c not in chars]
    return sorted([c for c in chars if c not in b'\f\r'], key=lambda c: [c != x for x in b'\\`[_$#'])[-1]


@overload
def encode(data: bytes, escape: Union[int, AnyStr] = ..., offset=...) -> bytes:
    ...


@overload
def encode(data: bytes, escape: Literal[None] = ..., offset=...) -> Tuple[bytes, int]:
    ...


def encode(data: bytes, escape=None, offset: int = 0):
    if offset:
        data = bytes(byte+offset & 255 for byte in data)
    return_escape = False
    if escape is None:
        escape = find_best_escape(data)
        return_escape = True
    elif isinstance(escape, (bytes, str)):
        escape = ord(escape)
    assert escape not in [12, 13], escape
    out = bytearray()
    for byte in data:
        if byte in [13, escape]:
            out.append(escape)
            byte = byte+1 & 255
        assert byte != 13
        out.append(byte)
    out = re.sub(br'\\|`|\${', br'\\\g<0>', out)
    if return_escape:
        out = out, escape
    return out


@overload
def optimize_encode(data, escape: Union[int, AnyStr] = ...) -> Tuple[bytes, int, int]:
    ...


@overload
def optimize_encode(data, escape: Literal[None] = ...) -> Tuple[Tuple[bytes, int], int, int]:
    ...


def optimize_encode(data: bytes, escape=None):
    best_offset = 0
    for offset in range(256):
        out = encode(data, escape, offset)
        length = len(out[0] if escape is None else out)
        if offset == 0:
            best_length = length0 = length
        if length < best_length:
            best_length = length
            best_offset = offset
    out = encode(data, escape, best_offset)
    return out, best_offset, length0 - best_length


def get_js_decoder(data: bytes,
                   escape: Optional[Union[int, AnyStr]] = None,
                   offset: Optional[int] = None,
                   payload_var: str = default_vars.payload,
                   output_var: str = default_vars.bytearray
                   ) -> bytes:
    if offset is None:
        encoded, offset, saved = optimize_encode(data, escape)  # Time-consuming op.
    else:
        encoded = encode(data, escape, offset)
    if escape is None:
        encoded, escape = encoded
    elif isinstance(escape, (bytes, str)):
        escape = ord(escape)
    last_part = f'''`
{output_var}=new Uint8Array({payload_var}.length)
j=e=0
for(c of {payload_var})i=c.charCodeAt()%65533,i>>8&&(i=128+'€ ‚ƒ„…†‡ˆ‰Š‹Œ Ž  ‘’“”•–—˜™š›œ žŸ'.indexOf(c)),i=={escape}&&!e?e=1:(e&&(e=0,i--),{output_var}[j++]=i{-offset if offset else ''})
{output_var}={output_var}.slice(0,j)
'''
    return f'{payload_var}=`'.encode() + encoded + last_part.encode('cp1252')
