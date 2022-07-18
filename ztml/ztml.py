"""Extreme inline text compression for HTML / JS"""


import argparse
from base64 import b64encode
import chardet
import sys
from time import time
from typing import Tuple, Union

if not __package__:
    import base125, bwt, crenc, default_vars, deflate, huffman, text_utils, validation, webify
else:
    from . import base125, bwt, crenc, default_vars, deflate, huffman, text_utils, validation, webify


bin2txt_encodings = 'base64', 'base125', 'crenc'
default_bin2txt = 'crenc'


def generate(text: str,
             filename: str = '',
             skip_norm: bool = False,
             caps: str = text_utils.default_caps_mode,
             bin2txt: str = default_bin2txt,
             js: bool = False,
             validate: bool = False,
             compare_caps: bool = True,
             browser: validation.BrowserType = validation.default_browser,
             verbose: bool = False
             ) -> Union[bytes, Tuple[bytes, int]]:
    start_time = time()
    encoding = 'cp1252' if bin2txt == 'crenc' else None
    if not skip_norm:
        text = text_utils.normalize(text)  # Reduce whitespace
    condensed, string_decoder = text_utils.encode_and_get_js_decoder(text, caps)  # Lower case and shorten common strings
    bits, huffman_decoder = huffman.encode_and_get_js_decoder(condensed)  # Huffman encode
    trans, bwt_decoder = bwt.encode_and_get_js_decoder(bits)  # Burrows–Wheeler transform
    zop_data = deflate.to_png(trans)  # PNG encode. Time-consuming op
    render = f"{bwt_decoder}{huffman_decoder}{string_decoder}document.body.style.whiteSpace='pre';document.body.textContent={default_vars.text}"
    if bin2txt == 'base64':
        base64_image = b"i=new Image;i.src='data:image/png;base64," + b64encode(zop_data) + b"'\n"
        script = base64_image+deflate.get_js_image_data(len(trans), render).encode()
    elif bin2txt == 'base125':
        script = base125.get_js_decoder(zop_data)  # Time-consuming op when offset==None
    elif bin2txt == 'crenc':
        script = crenc.get_js_decoder(zop_data)  # Time-consuming op when offset==None
    else:
        raise NotImplementedError(bin2txt)
    if bin2txt != 'base64':
        script += deflate.get_js_image_decoder(len(trans), render).encode()
    if js:
        out = webify.uglify(script, encoding=encoding)
    else:
        out = webify.html_wrap(script, encoding=encoding)
    if filename:
        with open(filename, 'wb') as f:
            f.write(out)
    if verbose:
        print(f'Encoding took {(time()-start_time) / 60 :.1f} min.', file=sys.stderr)
    if validate:
        valid = validation.validate_html(webify.html_wrap(out, aliases='', encoding=encoding) if js else filename or out, text, compare_caps, browser=browser, verbose=True)
        out = out, not valid
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_filename')
    parser.add_argument('output_filename', nargs='?', default='')
    parser.add_argument('--skip_norm', action='store_true')
    parser.add_argument('--caps', choices=text_utils.caps_modes, default=text_utils.default_caps_mode)
    parser.add_argument('--bin2txt', choices=bin2txt_encodings, default=default_bin2txt)
    parser.add_argument('--js', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--skip_compare_caps', action='store_true')
    parser.add_argument('--browser', choices=list(validation.drivers), default=validation.default_browser)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    with open(args.input_filename, 'rb') as f:
        text = f.read()
        encoding = chardet.detect(text)['encoding']
        text = text.decode(encoding or 'utf8')
    out = generate(text, args.output_filename, args.skip_norm, args.caps, args.bin2txt, args.js, args.validate, not args.skip_compare_caps, args.browser, args.verbose)
    result = False
    if args.validate:
        out, result = out
    if not args.output_filename:
        sys.stdout.buffer.write(out)
    sys.exit(int(result))
