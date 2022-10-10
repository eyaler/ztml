"""ZTML - Extreme inline text compression for HTML / JS"""


import argparse
from base64 import b64encode
import chardet
import os
import sys
from time import time
from typing import AnyStr, Optional, overload, Tuple

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if not __package__:
    import base125, bwt_mtf, crenc, default_vars, deflate, huffman, text_prep, validation, webify
else:
    from . import base125, bwt_mtf, crenc, default_vars, deflate, huffman, text_prep, validation, webify


bin2txt_encodings = ['base64', 'base125', 'crenc']
default_bin2txt = 'crenc'


@overload
def ztml(data, filename, reduce_whitespace, unix_newline, fix_punct, caps, mtf, bin2txt,
         element_id, raw, image, js, uglify, replace_quoted, lang, mobile, title,
         validate: Literal[False], ignore_regex, browser, timeout, verbose) -> bytes:
    ...


@overload
def ztml(data, filename, reduce_whitespace, unix_newline, fix_punct, caps, mtf, bin2txt,
         element_id, raw, image, js, uglify, replace_quoted, lang, mobile, title,
         validate: Literal[True], ignore_regex, browser, timeout, verbose
         ) -> Tuple[bytes, int]:
    ...


def ztml(data: AnyStr,
         filename: str = '',
         reduce_whitespace: bool = False,
         unix_newline: bool = True,
         fix_punct: bool = False,
         caps: str = text_prep.default_caps,
         mtf: Optional[int] = bwt_mtf.default_mtf,
         bin2txt: str = default_bin2txt,
         element_id: str = '',
         raw: bool = False,
         image: bool = False,
         js: bool = False,
         uglify: bool = True,
         replace_quoted: bool = True,
         lang: str = webify.default_lang,
         mobile: bool = False,
         title: str = '',
         validate: bool = False,
         ignore_regex: str = '',
         browser: validation.BrowserType = validation.default_browser,
         timeout: int = validation.default_timeout,
         verbose: bool = False
         ):
    start_time = time()
    if image:
        assert isinstance(data, bytes)
        image_data = data
        bit_len = len(data) * 8
        create_blob = f'URL.createObjectURL(new Blob([{default_vars.bytearray}]))'
        if element_id:
            image_property = f"document.body.appendChild(new Image).id='{element_id}';document.getElementById`{element_id}`.src"
            decoder = f'{image_property}={create_blob}'
        else:
            image_property = 'document.body.style.background'
            decoder = f"{image_property}='url('+{create_blob}+')no-repeat'"
    else:
        if isinstance(data, bytes):
            data = data.decode()
        data = text_prep.normalize(data, reduce_whitespace, unix_newline, fix_punct)  # Reduce whitespace
        condensed, string_decoder = text_prep.encode_and_get_js_decoder(data, caps)  # Lower case and shorten common strings
        bwt_mtf_text, bwt_mtf_text_decoder = bwt_mtf.encode_and_get_js_decoder(condensed, mtf=mtf, add_bwt_func=False)  # Burrows-Wheeler + Move-to-front transforms on text. MTF is a time-consuming op.
        huffman_bits, huffman_decoder = huffman.encode_and_get_js_decoder(bwt_mtf_text)  # Huffman encode
        bits, bwt_bits_decoder = bwt_mtf.encode_and_get_js_decoder(huffman_bits)  # Burrows-Wheeler transform on bits
        if raw:
            renderer = f'document.write({default_vars.text})'
        elif element_id:
            renderer = f"document.body.appendChild(document.createElement`pre`).id='{element_id}';document.getElementById`{element_id}`.textContent={default_vars.text}"
        else:
            renderer = f"document.body.style.whiteSpace='pre';document.body.textContent={default_vars.text}"
        decoder = f'{bwt_bits_decoder}{huffman_decoder}{bwt_mtf_text_decoder}{string_decoder}{renderer}'
        image_data = deflate.to_png(bits)  # PNG encode. Time-consuming op.
        bit_len = len(bits)

    if bin2txt == 'base64':  # Note: this is just for benchmarking and is not recommended
        base64_str = b'data:;base64,' + b64encode(image_data)
        if image:
            if element_id:
                out = f"{image_property}='".encode() + base64_str + b"'\n"
            else:
                out = f"{image_property}='url(".encode() + base64_str + b")no-repeat'\n"
        else:
            image_decoder = f"{default_vars.image}=new Image;{default_vars.image}.src='".encode() + base64_str + b"'\n"
            out = image_decoder + deflate.get_js_image_data(bit_len, decoder).encode()
    elif bin2txt == 'base125':
        out = base125.get_js_decoder(image_data)  # Time-consuming op. when offset==None
    elif bin2txt == 'crenc':
        out = crenc.get_js_decoder(image_data)  # Time-consuming op. when offset==None
    else:
        raise NotImplementedError(bin2txt)
    encoding = 'cp1252' if bin2txt == 'crenc' else 'utf8'
    if bin2txt != 'base64':
        image_decoder = deflate.get_js_image_decoder(bit_len, decoder)
        out += webify.safe_encode(image_decoder, encoding)
    if os.path.splitext(filename)[-1] == '.js':
        js = True
    if js and uglify:
        out = webify.uglify(out, replace_quoted=replace_quoted, encoding=encoding)
    elif not js:
        out = webify.html_wrap(out, aliases=webify.default_aliases if uglify else '',
                               replace_quoted=replace_quoted, lang=lang,
                               encoding=encoding, mobile=mobile, title=title)
    if filename:
        with open(filename, 'wb') as f:
            f.write(out)
    if verbose:
        print(f'Encoding took {time() - start_time :,.1f} sec.', file=sys.stderr)
    if validate:
        file = webify.html_wrap(out, aliases='', encoding=encoding) if js else filename or out
        by = element = ''
        if element_id:
            by = 'id'
            element = element_id
        valid = validation.validate_html(file, data, caps, by=by, element=element,
                                         raw=raw, image=image, browser=browser,
                                         timeout=timeout, ignore_regex=ignore_regex,
                                         verbose=True)
        out = out, not valid
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_filename')
    parser.add_argument('output_filename', nargs='?', default='')
    parser.add_argument('--input_encoding', nargs='?', const='', default='')
    parser.add_argument('--reduce_whitespace', action='store_true')
    parser.add_argument('--skip_unix_newline', action='store_true')
    parser.add_argument('--fix_punct', action='store_true')
    parser.add_argument('--caps', type=str.lower, choices=text_prep.caps_modes, default=text_prep.default_caps)
    parser.add_argument('--mtf', type=lambda x: None if x.lower() == 'none' else int(x), choices=bwt_mtf.mtf_variants,
                        default=bwt_mtf.default_mtf)
    parser.add_argument('--bin2txt', type=str.lower, choices=bin2txt_encodings, default=default_bin2txt)
    parser.add_argument('--element_id', nargs='?', const='', default='')
    parser.add_argument('--raw', action='store_true', help='Use document.write() to overwrite the document with the raw text. May also be inferred from input_filename .html')
    parser.add_argument('--image', action='store_true', help='May also be inferred from input_filename extension')
    parser.add_argument('--js', action='store_true', help='May also be inferred from output_filename extension')
    parser.add_argument('--skip_uglify', action='store_true')
    parser.add_argument('--skip_replace_quoted', action='store_true')
    parser.add_argument('--lang', default=webify.default_lang)
    parser.add_argument('--mobile', action='store_true')
    parser.add_argument('--title', nargs='?', const='', default='')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--ignore_regex', nargs='?', const='', default='')
    parser.add_argument('--browser', type=str.lower, choices=list(validation.drivers), default=validation.default_browser)
    parser.add_argument('--timeout', type=int, default=validation.default_timeout, help='seconds')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    ext = os.path.splitext(args.input_filename)[-1][1:].lower()
    if ext == 'html':
        args.raw = True
    if ext in ['bmp', 'gif', 'jpeg', 'jpg', 'png', 'webp']:
        args.image = True
    with open(args.input_filename, 'rb') as f:
        data = f.read()
        if not args.image:
            if args.input_encoding:
                data = data.decode(args.input_encoding)
            else:
                encoding = chardet.detect(data)['encoding'] or 'utf8'
                try:
                    data = data.decode(encoding)
                except UnicodeDecodeError:
                    if encoding.replace('-', '') == 'utf8':
                        raise
    out = ztml(data, args.output_filename, args.reduce_whitespace,
               not args.skip_unix_newline, args.fix_punct, args.caps, args.mtf,
               args.bin2txt, args.element_id, args.raw, args.image, args.js,
               not args.skip_uglify, not args.skip_replace_quoted, args.lang,
               args.mobile, args.title, args.validate, args.ignore_regex,
               args.browser, args.timeout, args.verbose)
    result = False
    if args.validate:
        out, result = out
    if not args.output_filename:
        sys.stdout.buffer.write(out)
    sys.exit(int(result))
