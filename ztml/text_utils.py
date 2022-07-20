import sys
from typing import Optional, Tuple

import regex

if not __package__:
    import default_vars
else:
    from . import default_vars


newline = '\n\v\f\r\x85\u2028\u2029'
single_quote = '\u2018-\u201b'
double_quote = '\u201c-\u201f'
caps_modes = 'auto', 'lower', 'raw', 'upper'
default_caps_mode = 'auto'


def normalize(text: str,
              reduce_whitespace: bool = False,
              fix_newline: bool = False,
              fix_punct: bool = False
              ) -> str:
    if reduce_whitespace:
        text = regex.sub('\\s*[' + newline + ']\\s*[' + newline + ']\\s*', '\n\n', text)
        text = regex.sub('[^\\S' + newline + ']*[' + newline + '][^\\S' + newline + ']*', '\n', text)
        text = regex.sub('[^\\S' + newline + ']+', ' ', text)
        text = text.strip()
    elif fix_newline:
        text = regex.sub('\r\n?', '\n', text)
    if fix_punct:
        text = regex.sub('\\p{Pd}', '-', text)
        text = regex.sub('[' + single_quote + ']', "'", text)
        text = regex.sub('[' + double_quote + ']', '"', text)
        text = regex.sub('\u2026', '...', text)
    return text.lstrip('\ufeff')  # Remove BOM


def encode_caps(text: str, caps: str = default_caps_mode, caps_warn: bool = False) -> str:
    assert caps in caps_modes, f"caps='{caps}' not in {caps_modes}"
    if caps != 'raw':
        if caps == 'auto' and caps_warn:
            count_bad_auto_caps(text, verbose=True)
        text = text.lower()
    return text


def auto_upper(text: str) -> str:
    return regex.sub('(^|[.?!])\\W*.|(?<!\\w)i(?!\\w)', lambda m: m[0].upper(), text, flags=regex.MULTILINE)


def count_bad_auto_caps(text: str, verbose: bool = False) -> int:
    recon = auto_upper(text.lower())
    cnt = sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))
    if verbose and cnt:
        print(f'Warning: found {cnt} chars with auto-capitalization mismatch', file=sys.stderr)
    return cnt


def remove_the(text: str) -> str:
    return regex.sub('(^| )the ', '\\1 ', text, flags=regex.MULTILINE)


def encode_quq(text: str, warn_for_caps: Optional[str] = None) -> str:
    if warn_for_caps:
        count_bad_quq(text, warn_for_caps, verbose=True)
    return regex.sub("([Qq])u(?=['’](?!\\p{Lu})|\\p{Ll})", '\\1', text)


def decode_quq(text: str) -> str:
    return regex.sub("[Qq](?=['’](?!\\p{Lu})|\\p{Ll})", '\\g<0>u', text)


quq_js_decoder = ".replace(/[Qq](?=['\\u2019](?!\\p{Lu})|\\p{Ll})/gu,'$&u')"  # \u2019 is ’


def count_bad_quq(text: str, caps: str, verbose: bool = False) -> int:
    text = encode_caps(text, caps)
    recon = decode_quq(encode_quq(text))
    text = regex.split('[Qq]', text)
    recon = regex.split('[Qq]', recon)
    cnt = sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))
    if verbose and cnt:
        print(f'Warning: found {cnt} cases of q followed by a non u, or terminal qu', file=sys.stderr)
    return cnt


def encode(text: str,
           caps: str = default_caps_mode,
           the: bool = True,
           quq: bool = True,
           caps_warn: bool = False,
           quq_warn: bool = True
           ) -> str:
    text = encode_caps(text, caps, caps_warn)
    if the:
        text = remove_the(text)
    if quq:
        text = encode_quq(text, caps if quq_warn else None)
    return text


def get_js_decoder(caps: str = default_caps_mode,
                   the: bool = True,
                   quq: bool = True,
                   text_var: str = default_vars.text
                   ) -> str:
    js_decoder = ''
    if quq:
        js_decoder += quq_js_decoder
    if the:
        js_decoder += ".replace(/(^| ) /gm,'$1the ')"
    if caps == 'auto':
        js_decoder += '.replace(/(^|[.?!])\\P{L}*.|(^|\\P{L})i(?!\\p{L})/gmu,s=>s.toUpperCase())'  # Avoid lookbehind to support Safari
    elif caps == 'upper':
        js_decoder += '.toUpperCase()'
    if js_decoder:
        js_decoder = f'{text_var}={text_var}' + js_decoder + '\n'
    return js_decoder


def encode_and_get_js_decoder(text: str,
                              caps: str = default_caps_mode,
                              the: bool = True,
                              quq: bool = True,
                              caps_warn: bool = False,
                              quq_warn: bool = True,
                              caps_fallback: bool = False,
                              text_var: str = default_vars.text
                              ) -> Tuple[str, str]:
    if caps_fallback and caps == 'auto' and not count_bad_auto_caps(text, verbose=caps_warn):
        caps = 'raw'
        if caps_warn:
            print(f"Falling back to caps='{caps}'", file=sys.stderr)
    if the and '  ' in text:
        the = False
    if quq and len(encode(text, caps, the, quq=False)) - len(encode(text, caps, the, quq=True, quq_warn=False)) < len(quq_js_decoder):
        quq = False
    if quq and count_bad_quq(text, caps, verbose=quq_warn):
        quq = False
        if quq_warn:
            print(f'Falling back to quq={quq}', file=sys.stderr)
    return encode(text, caps, the, quq, caps_warn, quq_warn), get_js_decoder(caps, the, quq, text_var)


def test_quq() -> None:
    bad = 0
    for caps in caps_modes:
        for q in 'Qq':
            for u in 'Uu':
                for a in "Aa'":
                    orig = f'{q}{u}{a}'
                    text = encode_caps(orig, caps)
                    enc = encode_quq(text, caps)
                    dec = decode_quq(enc)
                    if text != dec:
                        print(f'caps={caps:>5}: orig={orig} -> text={text} -> enc={enc} -> dec={dec}', file=sys.stderr)
                        bad += 1
    print(f'Found {bad} bad cases', file=sys.stderr)


if __name__ == '__main__':
    test_quq()
