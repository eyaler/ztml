"""Base125 encoding based on Base122 and optimized for inline HTML / JS text compression

If we must use utf8 encoding for HTML or JS, crEnc will not work.
Instead, we can use this unnecessarily optimized version of the variable length Base122.
The original byte stream is split into 7 bit chunks,
which are encoded as a single byte: 0xxxxxxx, to comply with utf8 code point scheme.
We only use 125 byte values out of 128 (excluding CR, \ and `)
and encode the remaining three in a double byte scheme: 110ssxxx 10xxxxxx,
where ss is 01, 10 or 11, and 9 bits are left for next data.
alternatively, if these are the final 7 bits, we instead encode as: 1100010x 10xxxxxx.
We then embed in JS template literals quotes ``, after escaping ${ with a \
The decoder further takes care of HTML character override for NUL.
A minimalistic JS decoder code is generated.
The overhead is ~15% (compared to 33.3% for Base64).
References:
https://blog.kevinalbs.com/base122
https://github.com/kevinAlbs/Base122
"""


from typing import Optional

from ztml import default_names


illegal = ['', 13, 92, 96]


def encode(data: bytes, validate: bool = True) -> bytes:
    curIndex = 0
    curBit = 0  # Points to current bit needed
    out = bytearray()

    # Get 7 or 9 bits of input data. Returns false if there is no input left.
    def get_bits(length : int) -> Optional[int]:
        nonlocal curIndex, curBit
        if curIndex >= len(data):
            return None

        # Shift, mask, unshift to get first part. Align it to a 7 or 9 bit chunk.
        firstPart = (255>>curBit & data[curIndex]) << curBit
        diff = 8 - length
        if diff > 0:
            firstPart >>= diff
        else:
            firstPart <<= -diff
        # Check if we need to go to the next byte for more bits.
        curBit += length
        if curBit < 8:
            return firstPart  # Do not need next byte.
        curBit -= 8
        curIndex += 1
        # Now we want bits [0..curBit] of the next byte if it exists.
        if curIndex >= len(data):
            return firstPart
        # Align it.
        secondPart = (0xFF00>>curBit & data[curIndex]) >> 8-curBit
        return firstPart | secondPart

    while True:
        # Grab 7 bits.
        bits = get_bits(7)
        if bits is None:
            break
        try:
            illegalIndex = illegal.index(bits)
            # Since this will be a two-byte character, get the next chunk of 9 bits.
            nextBits = get_bits(9)
            if nextBits is None:
                b1 = 4
                nextBits = bits
            else:
                b1 = illegalIndex << 3
            # Push first 3 bits onto first byte, remaining 6 onto second.
            out.extend([192 | b1 | nextBits >> 6, 128 | nextBits & 63])

        except ValueError:
            out.append(bits)

    if validate:
        assert data == decode(out), len(data)
    return out.replace(b'${', b'\\${')


def decode(data: bytes) -> bytes:
    out = bytearray()
    next_byte = 0
    k = 0

    def push_bits(bits: int, length: int = 7) -> None:
        nonlocal next_byte, k
        next_byte |= bits << (length < 8) >> k >> (length > 8)
        k += length
        if k > 7:
            out.append(next_byte & 255)
            k -= 8
            next_byte = bits << 8-k

    for byte in data.decode():
        b = ord(byte)
        if b > 127:
            ss = b >> 9
            if ss:
                push_bits(illegal[ss])
            push_bits(b << 2*(not ss) & 511, 9)
        else:
            push_bits(b)
    return out


def get_js_decoder(data: bytes, output_name: str = default_names.bytearray) -> bytes:
    illegal_str = ','.join(str(i) for i in illegal)
    last_part = '''`
OUTPUT_NAME=new Uint8Array(s.length*2)
j=k=n=0
p=(b,l=7)=>{n|=b<<(l<8)>>k>>(l>8);k+=l;k>7&&(OUTPUT_NAME[j++]=n,k-=8,n=b<<8-k)}
for(c of s){
i=c.charCodeAt()%65533
if(i>127){
e=i>>9
e&&p([ILLEGAL_STR][e]) 
p(i<<2*!e&511,9)}
else p(i)}
OUTPUT_NAME=OUTPUT_NAME.slice(0,j)
'''.replace('OUTPUT_NAME', output_name).replace('ILLEGAL_STR', illegal_str)
    return b's=`' + encode(data) + last_part.encode()


def test() -> None:
    for i in range(100):
        for j in range(100):
            encode(b'\0'*i + b'\r'*j)
            encode(b'\0'*i + b'\\'*j)
            encode(b'\0'*i + b'`'*j)


if __name__ == '__main__':
    test()
