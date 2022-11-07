"""crEnc encoding based on yEnc and optimized for inline HTML / JS text compression and image encoding

In the spirit of yEnc (why encode?), we only encode symbols where absolutely required.
If the HTML or JS charset can be set to a single-byte encoding as cp1252 (or latin1),
the only symbol requiring special treatment is the carriage-return (CR), hence crEnc,
which can be dealt with by simple backslash escaping.
We embed in JS template literals quotes ``, so we also escape backslash, ` and ${
giving us an effective 253 byte values out of 256,
with an overhead of ~ 3/256 ~ 1.2% (compared to 33.3% for Base64).
JS does the unescaping, so the decoder only needs to take care of HTML character overrides for NUL and codes in 128 - 159.
An optimal global character modular offset can be applied to minimize escaping, similar to dynEncode (enabled by default).
A minimalistic JS decoder code is generated.

References:
https://en.wikipedia.org/wiki/Binary-to-text_encoding
http://www.yenc.org
https://github.com/eshaz/simple-yenc
https://github.com/eshaz/simple-yenc#what-is-dynencode
https://html.spec.whatwg.org/multipage/parsing.html#table-charref-overrides
https://stackoverflow.com/questions/10080605/special-character-u0098-read-as-u02dc-using-charcodeat/#10081375
"""


from typing import Optional, Tuple

if not __package__:
    import default_vars, webify
else:
    # noinspection PyPackages
    from . import default_vars, webify


def encode(data: bytes, offset: int = 0) -> bytes:
    if offset:
        data = bytes(byte+offset & 255 for byte in data)
    return webify.escape(data)


def optimize_encode(data: bytes) -> Tuple[bytes, int, int]:
    best_offset = 0
    for offset in range(256):
        out = encode(data, offset)
        length = len(out)
        if offset == 0:
            best_length = length0 = length
        if length < best_length:
            best_length = length
            best_offset = offset
    out = encode(data, best_offset)
    return out, best_offset, length0 - best_length


def get_js_decoder(data: bytes,
                   offset: Optional[int] = None,
                   output_var: str = default_vars.bytearray
                   ) -> bytes:
    if offset is None:
        encoded, offset, saved = optimize_encode(data)  # Time-consuming op.
    else:
        encoded = encode(data, offset)
    first_part = f'{output_var}=Uint8Array.from(`'
    function = f"(i=c.charCodeAt()%65533)>>8?129+' \x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c \x8e  \x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c \x9e\x9f'.indexOf(c):i"
    if offset:
        function = f'({function})-{offset}'
    last_part = f"`,c=>{function})\n"
    return first_part.encode() + encoded + last_part.encode('l1')  # Encode with l1 as I used explicit bytes above
