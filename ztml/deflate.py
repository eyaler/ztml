"""PNG / DEFLATE encoding optimized for arbitrary data compression

Encoding data as a PNG image gives efficient DEFLATE compression,
while allowing use of the browser's native decompression capability,
thus avoiding the need of external decompression library dependencies.
The data is then read from the HTML canvas element.
The image aspect ratio is optimized to be squarish (for higher browser compatibility) with minimal padding.
We use Google's optimized Zopfli compression which is compatible with DEFLATE decompression.
A minimalistic JS decoder code is generated.

References:
https://web.archive.org/web/20090826082743/http://blog.nihilogic.dk:80/2008/05/compression-using-canvas-and-png.html
https://web.archive.org/web/20130310075429/http://daeken.com/superpacking-js-demos
https://gist.github.com/gasman/2560551
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
import zopfli

if not __package__:
    import default_vars
else:
    from . import default_vars


max_dim = 32767
max_len = 11180 ** 2
default_padding_bit = 0


def to_png(bits: Iterable[int],
           padding_sep_code: str = '',
           padding_bit: int = default_padding_bit,
           filter_strategies: str = '',  # Any subset of 01234mepb, '' means auto
           iterations: int = 15,
           iterations_large: int = 5,
           filename: str = '',
           verbose: bool = False) -> bytes:
    bits = list(bits)
    assert len(bits)
    width = height = pad_len = 0
    length = None
    padding = list(padding_sep_code)
    while width * height != length:
        if length is not None:
            bits += padding
            pad_len += len(padding)
            padding = [padding_bit]
        length = len(bits)
        assert length <= max_len, length
        height = int(math.sqrt(length))
        while length % height and height > 1 and length // (height-1) <= max_dim:
            height -= 1
        width = length // height
        assert width <= max_dim, width
    bits = [bits[i : i + width] for i in range(0, length, width)]
    png_data = BytesIO()
    png.Writer(width, height, greyscale=True, bitdepth=1, compression=9).write(png_data, bits)
    png_data.seek(0)
    png_data = png_data.read()
    zop_data = zopfli.ZopfliPNG(filter_strategies=filter_strategies, iterations=iterations, iterations_large=iterations_large).optimize(png_data)  # Time-consuming op.
    if verbose:
        print(f'width={width} height={height} pad_len={pad_len} bits={length} bytes={length+7 >> 3} png={len(png_data)} zop={len(zop_data)}', file=sys.stderr)
    if filename:
        with open(filename, 'wb') as f:
            f.write(zop_data)
    return zop_data


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
                      render_script: str = '',
                      image_var: str = default_vars.image,
                      bitarray_var: str = default_vars.bitarray
                      ) -> str:
    return f'''{image_var}.decode().then(()=>{{
c=document.createElement`canvas`
x=c.getContext`2d`
c=[c.width,c.height]=[{image_var}.width,{image_var}.height]
x.drawImage({image_var},0,0)
{bitarray_var}=[...x.getImageData(0,0,...c).data].flatMap((i,j)=>j%4||j>{length*4 - 1}?[]:[i>>7])
{render_script.strip()}}})'''  # Using >>7 to deal with safari rendering inaccuracy


def get_js_image_decoder(length: int,
                         render_script: str = '',
                         image_var: str = default_vars.image,
                         bytearray_var: str = default_vars.bytearray,
                         bitarray_var: str = default_vars.bitarray
                         ) -> str:
    return get_js_create_image(image_var, bytearray_var) + get_js_image_data(length, render_script, image_var, bitarray_var)
