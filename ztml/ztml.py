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


bin2txt_encodings = 'base64', 'base125', 'crenc'
default_bin2txt = 'crenc'


@overload
def ztml(text, filename=..., reduce_whitespace=..., unix_newline=..., fix_punct=...,
         caps=..., mtf=..., bin2txt=..., raw=..., js=..., uglify=..., replace_quoted=...,
         lang=..., mobile=..., validate: Literal[True] = ..., ignore_regex=...,
         browser=..., timeout=..., verbose=...) -> bytes:
    ...


@overload
def ztml(text, filename=..., reduce_whitespace=..., unix_newline=..., fix_punct=...,
         caps=..., mtf=..., bin2txt=..., raw=..., js=..., uglify=..., replace_quoted=...,
         lang=..., mobile=..., validate: Literal[False] = ..., ignore_regex=...,
         browser=..., timeout=..., verbose=...) -> Tuple[bytes, int]:
    ...


def ztml(text: AnyStr,
         filename: str = '',
         reduce_whitespace: bool = False,
         unix_newline: bool = True,
         fix_punct: bool = False,
         caps: str = text_prep.default_caps,
         mtf: Optional[int] = bwt_mtf.default_mtf,
         bin2txt: str = default_bin2txt,
         raw: bool = False,
         js: bool = False,
         uglify: bool = True,
         replace_quoted: bool = True,
         lang: str = webify.default_lang,
         mobile: bool = False,
         validate: bool = False,
         ignore_regex: str = '',
         browser: validation.BrowserType = validation.default_browser,
         timeout: int = validation.default_timeout,
         verbose: bool = False
         ):
    start_time = time()
    encoding = 'cp1252' if bin2txt == 'crenc' else 'utf8'
    if isinstance(text, bytes):
        text = text.decode()
    text = text_prep.normalize(text, reduce_whitespace, unix_newline, fix_punct)  # Reduce whitespace
    condensed, string_decoder = text_prep.encode_and_get_js_decoder(text, caps)  # Lower case and shorten common strings
    bwt_mtf_text, bwt_mtf_text_decoder = bwt_mtf.encode_and_get_js_decoder(condensed, mtf=mtf, add_bwt_func=False)  # Burrows-Wheeler + Move-to-front transforms on text. MTF is a time-consuming op.
    bits, huffman_decoder = huffman.encode_and_get_js_decoder(bwt_mtf_text)  # Huffman encode
    bwt_bits, bwt_bits_decoder = bwt_mtf.encode_and_get_js_decoder(bits)  # Burrows-Wheeler transform on bits
    zop_data = deflate.to_png(bwt_bits)  # PNG encode. Time-consuming op.
    if raw:
        render = f'document.write({default_vars.text})'
    else:
        render = f"document.body.style.whiteSpace='pre';document.body.textContent={default_vars.text}"
    decoder = f'{bwt_bits_decoder}{huffman_decoder}{bwt_mtf_text_decoder}{string_decoder}{render}'
    if bin2txt == 'base64':  # Note: this is just for benchmarking and is not recommended
        image_var = default_vars.image
        image = f"{image_var}=new Image;{image_var}.src='data:image/png;base64,".encode() + b64encode(zop_data) + b"'\n"
        out = image + deflate.get_js_image_data(len(bwt_bits), decoder).encode()
    elif bin2txt == 'base125':
        out = base125.get_js_decoder(zop_data)  # Time-consuming op. when offset==None
    elif bin2txt == 'crenc':
        out = crenc.get_js_decoder(zop_data)  # Time-consuming op. when offset==None
    else:
        raise NotImplementedError(bin2txt)
    if bin2txt != 'base64':
        image = deflate.get_js_image_decoder(len(bwt_bits), decoder)
        out += webify.safe_encode(image, encoding)
    if os.path.splitext(filename)[-1] == '.js':
        js = True
    if js and uglify:
        out = webify.uglify(out, replace_quoted=replace_quoted, encoding=encoding)
    elif not js:
        out = webify.html_wrap(out, aliases=webify.default_aliases if uglify else '',
                               replace_quoted=replace_quoted, lang=lang,
                               encoding=encoding, mobile=mobile)
    if filename:
        with open(filename, 'wb') as f:
            f.write(out)
    if verbose:
        print(f'Encoding took {time() - start_time :,.1f} sec.', file=sys.stderr)
    if validate:
        file = webify.html_wrap(out, aliases='', encoding=encoding) if js else filename or out
        valid = validation.validate_html(file, text, caps, ignore_regex=ignore_regex, browser=browser, timeout=timeout, raw=raw, verbose=True)
        out = out, not valid
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_filename')
    parser.add_argument('output_filename', nargs='?', default='')
    parser.add_argument('--input_encoding')
    parser.add_argument('--reduce_whitespace', action='store_true')
    parser.add_argument('--skip_unix_newline', action='store_true')
    parser.add_argument('--fix_punct', action='store_true')
    parser.add_argument('--caps', type=str.lower, choices=text_prep.caps_modes, default=text_prep.default_caps)
    parser.add_argument('--mtf', type=lambda x: None if x.lower() == 'none' else int(x), choices=bwt_mtf.mtf_variants,
                        default=bwt_mtf.default_mtf)
    parser.add_argument('--bin2txt', type=str.lower, choices=bin2txt_encodings, default=default_bin2txt)
    parser.add_argument('--raw', action='store_true', help='use document.write() to overwrite the document with the raw text')
    parser.add_argument('--js', action='store_true', help='can also be inferred from output_filename extension')
    parser.add_argument('--skip_uglify', action='store_true')
    parser.add_argument('--skip_replace_quoted', action='store_true')
    parser.add_argument('--lang', default=webify.default_lang)
    parser.add_argument('--mobile', action='store_true')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--ignore_regex', default='')
    parser.add_argument('--browser', type=str.lower, choices=list(validation.drivers), default=validation.default_browser)
    parser.add_argument('--timeout', type=int, default=validation.default_timeout, help='seconds')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    with open(args.input_filename, 'rb') as f:
        text = f.read()
        if args.input_encoding:
            text = text.decode(args.input_encoding)
        else:
            encoding = chardet.detect(text)['encoding'] or 'utf8'
            try:
                text = text.decode(encoding)
            except UnicodeDecodeError:
                if encoding.replace('-', '') == 'utf8':
                    raise
    out = ztml(text, args.output_filename, args.reduce_whitespace,
               not args.skip_unix_newline, args.fix_punct, args.caps, args.mtf,
               args.bin2txt, args.raw, args.js, not args.skip_uglify,
               not args.skip_replace_quoted, args.lang, args.mobile, args.validate,
               args.ignore_regex, args.browser, args.timeout, args.verbose)
    result = False
    if args.validate:
        out, result = out
    if not args.output_filename:
        sys.stdout.buffer.write(out)
    sys.exit(int(result))
