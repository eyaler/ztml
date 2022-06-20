"""crEnc encoding based on yEnc and optimized for inline HTML / JS text compression

If we can set the HTML or JS charset to a single-byte encoding as cp1252 (ascii, latin1),
we can use 254 byte values out of 256 (excluding only CR and an escape character),
and embed in JS template literals quotes ``, after escaping \, ` and ${ with a \
The escape character can be predetermined or optimized per message.
The decoder further takes care of HTML character overrides for NUL and codes in 128 - 159.
A minimalistic JS decoder code is generated.
The overhead is ~1.6% (compared to 33.3% for Base64).
References:
http://www.yenc.org
https://github.com/eshaz/simple-yenc
https://html.spec.whatwg.org/multipage/parsing.html#table-charref-overrides
https://stackoverflow.com/a/10081375/664456
"""


from collections import Counter
import re
from typing import Optional, Tuple, Union

from ztml import default_names


def find_best_escape(data: bytes) -> int:
    chars = [k for k, v in Counter(data).most_common()]
    chars += [c for c in range(256) if c not in chars]
    return sorted([c for c in chars if c not in b'\x0c\r'], key=lambda c: [c != x for x in b'\\`$'])[-1]


def encode(data: bytes, escape: Optional[int] = None) -> Union[bytes, Tuple[bytes, int]]:
    return_escape = False
    if escape is None:
        escape = find_best_escape(data)
        return_escape = True
    out = bytearray()
    for byte in data:
        if byte in [13, escape]:
            out.append(escape)
            byte = (byte + 1) % 256
        out.append(byte)
    out = re.sub(br'\\|`|\${', br'\\\g<0>', out)
    if return_escape:
        out = out, escape
    return out


def get_js_decoder(data: bytes,
                   escape: Optional[int] = None,
                   output_name: str = default_names.bytearray
                   ) -> bytes:
    if escape is None:
        escape = find_best_escape(data)
    last_part = '''`
OUTPUT_NAME=new Uint8Array(s.length)
j=e=0
for(c of s){
i=c.charCodeAt()%65533
i>255&&(i=128+'€ ‚ƒ„…†‡ˆ‰Š‹Œ Ž  ‘’“”•–—˜™š›œ žŸ'.indexOf(c))
if(i==ESCAPE&&!e){
e=1
continue}
e&&(e=0,i--)
OUTPUT_NAME[j++]=i}
OUTPUT_NAME=OUTPUT_NAME.slice(0,j)
'''.replace('OUTPUT_NAME', output_name).replace('ESCAPE', str(escape))
    return b's=`' + encode(data, escape) + last_part.encode('cp1252')
