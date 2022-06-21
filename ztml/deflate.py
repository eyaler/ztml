"""PNG / DEFLATE encoding optimized for arbitrary data compression

Encoding data as a PNG image gives efficient DEFLATE compression,
while allowing use of the browser's native decompression capability,
thus avoiding the need of external decompression library dependencies.
The data is then read from the HTML canvas element.
The image aspect ratio is optimized to minimize the necessary padding to a rectangle.
We use Google's optimized Zopfli compression which is compatible with DEFLATE decompression.
A minimalistic JS decoder code is generated.
References:
https://web.archive.org/web/20090220141811/http://blog.nihilogic.dk/2008/05/compression-using-canvas-and-png.html
https://github.com/google/zopfli
https://github.com/hattya/zopflipy
https://github.com/jhildenbiddle/canvas-size#test-results
"""


from io import BytesIO
import math
from typing import List, Iterable

import png
import zopfli

from . import default_names


max_dim = 32767
max_len = 11180 ** 2
default_padding_bit = 0


def to_png(bits: Iterable[int],
           padding_sep_code: str = '',
           padding_bit: int = default_padding_bit,
           filename: str = '',
           verbose: bool = False) -> bytes:
    bits = list(bits)
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
        while height > 1 and length % height and length // (height-1) <= max_dim:
            height -= 1
        width = length // height
        assert width <= max_dim, width
    bits = [bits[i : i + width] for i in range(0, length, width)]
    png_data = BytesIO()
    png.Writer(width, height, greyscale=True, bitdepth=1, compression=9).write(png_data, bits)
    png_data.seek(0)
    png_data = png_data.read()
    zop_data = zopfli.ZopfliPNG(filter_strategies='01234mepb', iterations=15, iterations_large=5).optimize(png_data)
    if verbose:
        print(f'width={width} height={height} pad_len={pad_len} bits={length} bytes={length+7 >> 3} png={len(png_data)} zop={len(zop_data)}')
    if filename:
        with open(filename, 'wb') as f:
            f.write(zop_data)
    return zop_data


def load_png(filename: str) -> List[int]:
    return png.Reader(filename=filename).read_flat()[2].tolist()


def get_js_create_image(bytearray_name: str = default_names.bytearray,
                        image_name: str = default_names.image
                        ) -> str:
    return '''IMAGE_NAME=new Image
IMAGE_NAME.src=URL.createObjectURL(new Blob([BYTEARRAY_NAME],{type:'image/png'}))
'''.replace('IMAGE_NAME', image_name).replace('BYTEARRAY_NAME', bytearray_name)


def get_js_image_data(after_script: str = '',
                      bitarray_name: str = default_names.bitarray,
                      image_name: str = default_names.image
                      ) -> str:
    return '''IMAGE_NAME.decode().then(()=>{
c=document.createElement('canvas')
x=c.getContext('2d')
c=[c.width,c.height]=[IMAGE_NAME.width,IMAGE_NAME.height]
x.imageSmoothingEnabled=0
x.drawImage(IMAGE_NAME,0,0)
BITARRAY_NAME=x.getImageData(0,0,...c).data
AFTER_SCRIPT})'''.replace('AFTER_SCRIPT', after_script.strip()).replace('IMAGE_NAME', image_name).replace('BITARRAY_NAME', bitarray_name)


def get_js_image_decoder(after_script: str = '',
                         bytearray_name: str = default_names.bytearray,
                         bitarray_name: str = default_names.bitarray,
                         image_name: str = default_names.image
                         ) -> str:
    return get_js_create_image(bytearray_name, image_name) + get_js_image_data(after_script, bitarray_name, image_name)
