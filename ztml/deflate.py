"""PNG / DEFLATE encoding optimized for arbitrary data compression

Encoding data as a PNG image allows efficient DEFLATE compression,
while allowing use of the browser's native decompression capability,
thus saving the need of an additional decoder, AKA PNG bootstarpping.
The data is then read from the HTML canvas element.
The image aspect ratio is optimized to be squarish (for higher browser compatibility) with minimal padding.
We use Google's optimized Zopfli compression which is compatible with DEFLATE decompression.
A minimalistic JS decoder code is generated.

Other experiments:
https://github.com/fhanau/Efficient-Compression-Tool gives a 1.4% improvement on 2600.txt
WEBP gave worse overall results (using 8-bit cwebp).

References:
https://web.archive.org/web/20090826082743/http://blog.nihilogic.dk:80/2008/05/compression-using-canvas-and-png.html
https://web.archive.org/web/20130310075429/http://daeken.com/superpacking-js-demos
https://web.archive.org/web/20130219050720/http://alexle.net/archives/306
https://www.iamcal.com/png-store
https://github.com/iamcal/PNGStore
http://bwirl.blogspot.com/2011/11/optimize-web-apps-with-png.html
https://gist.github.com/gasman/2560551 (pnginator)
https://www.pouet.net/prod.php?which=59298 (JsExe)
https://www.pouet.net/topic.php?which=8770
https://github.com/codegolf/zpng
https://github.com/xem/miniBook
https://github.com/google/zopfli
https://github.com/hattya/zopflipy
https://github.com/jhildenbiddle/canvas-size#test-results
https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit
https://bugs.webkit.org/show_bug.cgi?id=230855
"""


from io import BytesIO
import math
import sys
from typing import List, Iterable

import png
# noinspection PyPackageRequirements
import zopfli

if not __package__:
    import default_vars
else:
    # noinspection PyPackages
    from . import default_vars


max_dim = 32767
max_len = 11180 ** 2
default_padding_bit = 0


def to_png(bits: Iterable[int],
           padding_bit: int = default_padding_bit,
           compression: int = 9,
           filter_strategies: str = '',  # Any subset of 01234mepb, '' means auto
           iterations: int = 15,
           iterations_large: int = 5,
           omit_iend: bool = True,
           filename: str = '',
           verbose: bool = False) -> bytes:
    bits = list(bits)
    assert len(bits)
    width = height = pad_len = 0
    length = None
    while width * height != length:
        if length is not None:
            bits.append(padding_bit)
            pad_len += 1
        length = len(bits)
        assert length <= max_len, length
        height = int(math.sqrt(length))
        while length % height and height > 1 and length // (height-1) <= max_dim:
            height -= 1
        width = length // height
        assert width <= max_dim, width
    bits = [bits[i : i + width] for i in range(0, length, width)]
    png_data = BytesIO()
    png.Writer(width, height, greyscale=True, bitdepth=1, compression=compression
               ).write(png_data, bits)
    png_data.seek(0)
    png_data = png_data.read()
    out = png_data
    if iterations > 0 and iterations_large > 0:
        out = zopfli.ZopfliPNG(filter_strategies=filter_strategies,
                               iterations=iterations,
                               iterations_large=iterations_large
                               ).optimize(png_data)  # Time-consuming op.
    if omit_iend:
        out = out[:-12]  # IEND length (4 bytes) + IEND tag (4 bytes) + IEND CRC-32 (4 bytes). Note: do not omit the IDAT zlib Adler-32 or the IDAT CRC-32 as this will break Safari
    if verbose:
        print(f'width={width} height={height} pad_len={pad_len} bits={length} bytes={length+7 >> 3} png={len(png_data)} final={len(out)}', file=sys.stderr)
    if filename:
        with open(filename, 'wb') as f:
            f.write(out)
    return out


encode = to_png


def load_png(filename: str) -> List[int]:
    return png.Reader(filename=filename).read_flat()[2].tolist()


def get_js_create_image(image_var: str = default_vars.image,
                        bytearray_var: str = default_vars.bytearray
                        ) -> str:
    return f'''{image_var}=new Image
{image_var}.src=URL.createObjectURL(new Blob([{bytearray_var}]))
'''


def get_js_image_data(length: int,
                      decoder_script: str = '',
                      image_var: str = default_vars.image,
                      bitarray_var: str = default_vars.bitarray
                      ) -> str:
    return f'''{image_var}.decode().then(_=>{{
c=document.createElement`canvas`
x=c.getContext`2d`
c=[c.width={image_var}.width,c.height={image_var}.height]
x.drawImage({image_var},0,0)
s=x.getImageData({bitarray_var}=[],0,...c).data
for(j={length};j--;){bitarray_var}[j]=s[j*4]>>7
{decoder_script.strip()}}})'''  # Applying >>7 before the Huffman &1 to deal with Safari PNG rendering inaccuracy


def get_js_image_decoder(length: int,
                         decoder_script: str = '',
                         image_var: str = default_vars.image,
                         bytearray_var: str = default_vars.bytearray,
                         bitarray_var: str = default_vars.bitarray
                         ) -> str:
    return get_js_create_image(image_var, bytearray_var) + get_js_image_data(
        length, decoder_script, image_var, bitarray_var)
