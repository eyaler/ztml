"""PNG / DEFLATE encoding optimized for arbitrary data compression

Encoding data as a PNG image allows efficient DEFLATE compression (similar to ZIP),
while allowing use of the browser's native decompression capability for free,
thus saving the need of an additional decoder, AKA PNG bootstarpping.
The data is then read from the HTML canvas element.
The image aspect ratio is optimized to be squarish (for higher browser compatibility) with minimal padding.
We do not use the alpha channel due to the browser's alpha pre-multiplication in Canvas 2D causing inaccuracies.
In Safari, even without an alpha channel, similar inaccuracies prevent using 8-bit and 24-bit depths for PNGs.
By default, we use Google's optimized Zopfli compression which is compatible with DEFLATE decompression.
Alternatively, you can use ECT which can be beneficial for large texts (but may slightly hurt smaller ones)
(e.g. ECT 0.9.4 gave 1.4% overall improvement over Zopfli on 2600.txt and minibook)
A minimalistic JS decoder code is generated.

Other experiments:
8-bit and 24-bit (RGB) give similar overall results to 1-bit (but does not work on Safari)
WEBP gave worse overall results (libwebp/cwebp from 8-bit and 24-bit PNG, but does seem to work on Safari).

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
https://github.com/fhanau/Efficient-Compression-Tool (ECT)
https://encode.su/threads/2274-ECT-an-file-optimizer-with-fast-zopfli-like-deflate-compression
https://stackoverflow.com/questions/60074569/html-canvas-returns-off-by-some-bytes-from-getimagedata
https://stackoverflow.com/questions/23497925/how-can-i-stop-the-alpha-premultiplication-with-canvas-imagedata/#60564905
https://github.com/jhildenbiddle/canvas-size#test-results
https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit
https://bugs.webkit.org/show_bug.cgi?id=230855
"""


from io import BytesIO
import math
import os
import platform
import sys
from tempfile import NamedTemporaryFile
from typing import List, Iterable, Optional

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
allowed_bitdepths = [1, 8, 24]  # Warning: 8-bit and 24-bit do not work on Safari
default_bitdepth = 1


def to_png(bits: Iterable[int],
           bitdepth: int = default_bitdepth,  # 1, 8, 24
           compression: Optional[int] = 9,
           ect: bool = False,  # This will override zop settings
           ect_compression: int = 20009,
           ect_filters: str = 'allfilters',  # 'allfilters', 'allfilters-b' (brute), 'allfilters-c' (cheap) or ''
           zop_filters: str = '',  # Any subset of 01234mepb or '' for auto
           zop_iterations: int = 15,
           zop_iterations_large: int = 5,
           omit_iend: bool = True,
           filename: str = '',
           verbose: bool = False) -> bytes:
    data = list(bits)
    bit_len = len(data)
    assert bit_len
    assert bitdepth in allowed_bitdepths, f'Error: bitdepth={bitdepth} not in {allowed_bitdepths}'
    assert compression is None or -1 <= compression <= 9
    pad_bits = (bitdepth - bit_len) % bitdepth
    if bitdepth > 1:
        data += [data[-1]] * pad_bits
        data = [int(''.join(str(b) for b in data[i : i + bitdepth]), 2) for i in range(0, len(data), bitdepth)]
    width = height = pad_pixels = 0
    length = None
    while width * height != length:
        if length is not None:
            data.append(data[-1])
            pad_pixels += 1
        length = len(data)
        assert length <= max_len, f'Error: length={length:,} > max_len={max_len:,}'
        height = int(math.sqrt(length))
        while length % height and height > 1 and length // (height-1) <= max_dim:
            height -= 1
        width = length // height
        assert width <= max_dim, f'Error: width={width:,} > max_dim={max_dim:,}'
    width_with_channels = width
    length_with_channels = length
    if bitdepth > 8:
        data = [b for i in data for b in i.to_bytes(bitdepth // 8, 'big')]
        width_with_channels *= bitdepth // 8
        length_with_channels *= bitdepth // 8
    data = [data[i : i + width_with_channels] for i in range(0, length_with_channels, width_with_channels)]
    png_data = BytesIO()
    png.Writer(width, height, greyscale=bitdepth <= 8,
               bitdepth=1 if bitdepth == 1 else 8,
               compression=compression).write(png_data, data)
    png_data.seek(0)
    png_data = png_data.read()
    out = png_data

    if ect:
        with NamedTemporaryFile(suffix='.png', delete=False) as f:  # See https://github.com/python/cpython/issues/88221
            f.write(out)
            filename = f.name
        ect_filters_arg = f'--{ect_filters}' * bool(ect_filters)
        ect_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'ect', 'ect')) + '-ubuntu' * (platform.system() == 'Linux')
        error = os.system(f'{ect_path} -{ect_compression} -strip -quiet --strict {ect_filters_arg} --mt-deflate {filename}')  # Time-consuming op.
        assert not error, f'Error: could not run {ect_path} - Please install from https://github.com/fhanau/Efficient-Compression-Tool or use ect=False'
        with open(filename, 'rb') as f:
            out = f.read()
        try:
            os.remove(filename)
        except PermissionError:
            pass
    elif zop_iterations > 0 and zop_iterations_large > 0:
        out = zopfli.ZopfliPNG(filter_strategies=zop_filters,
                               iterations=zop_iterations,
                               iterations_large=zop_iterations_large
                               ).optimize(png_data)  # Time-consuming op.
    if omit_iend:  # Warning: do this only for PNG files
        out = out[:-12]  # IEND length (4 bytes) + IEND tag (4 bytes) + IEND CRC-32 (4 bytes). Note: do not omit the IDAT zlib Adler-32 or the IDAT CRC-32 as this will break Safari
    if verbose:
        print(f'input_bits={bit_len} pad_bits={pad_bits} width={width} height={height} pad_pixels={pad_pixels} total_pad_bits={length*bitdepth - bit_len} bits={length * bitdepth} bytes={length*bitdepth+7 >> 3} png={len(png_data)} final={len(out)}', file=sys.stderr)
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


def get_js_image_data(bit_len: int,
                      decoder_script: str = '',
                      bitdepth: int = default_bitdepth,
                      image_var: str = default_vars.image,
                      bitarray_var: str = default_vars.bitarray
                      ) -> str:
    assert bitdepth in allowed_bitdepths, f'Error: bitdepth={bitdepth} not in {allowed_bitdepths}'
    js_image_data = f'''{image_var}.decode().then(c=>{{
c=document.createElement`canvas`
x=c.getContext`2d`
c=[c.width={image_var}.width,c.height={image_var}.height]
x.drawImage({image_var},0,0)
s=x.getImageData({bitarray_var}=[],0,...c).data{'.filter((v,i)=>(i+1)%4)' * (bitdepth == 24)}
'''
    if bitdepth == 1:
        js_image_data += f'for(j={bit_len};j--;){bitarray_var}[j]=s[j*4]>>7&1\n'  # Applying >>7 to deal with Safari PNG rendering inaccuracy
    else:  # Will break Safari
        js_image_data += f'''for(j={(bit_len+(bitdepth-bit_len)%bitdepth) // 8};j--;)for(k=8;k--;){bitarray_var}[j*8+k]=s[j{'*4' * (bitdepth <= 8)}]>>7-k&1
{bitarray_var}={bitarray_var}.slice(0,{bit_len})
'''
    js_image_data += f'{decoder_script.strip()}}})'
    return js_image_data


def get_js_image_decoder(bit_len: int,
                         decoder_script: str = '',
                         bitdepth: int = default_bitdepth,
                         image_var: str = default_vars.image,
                         bytearray_var: str = default_vars.bytearray,
                         bitarray_var: str = default_vars.bitarray
                         ) -> str:
    return get_js_create_image(image_var, bytearray_var) + get_js_image_data(
        bit_len, decoder_script, bitdepth, image_var, bitarray_var)
