from typing import Optional, Tuple

import regex

if __name__ == '__main__':
    import default_names
else:
    from . import default_names


newline = '\n\v\f\r\x85\u2028\u2029'
dash = '\u2010-\u2015'
single_quote = '\u2018-\u201b'
double_quote = '\u201c-\u201f'
default_eos = '\n'
caps_modes = 'auto', 'lower', 'raw', 'upper'


def normalize(text: str,
              reduce_whitespace: bool = True,
              fix_newline: bool = True,
              fix_punct: bool = True
              ) -> str:
    if reduce_whitespace:
        text = regex.sub('\\s*[' + newline + ']\\s*[' + newline + ']\\s*', '\n\n', text)
        text = regex.sub('[^\\S' + newline + ']*[' + newline + '][^\\S' + newline + ']*', '\n', text)
        text = regex.sub('[^\\S' + newline + ']+', ' ', text)
        text = text.strip()
    elif fix_newline:
        text = regex.sub('\r\n?', '\n', text)
    if fix_punct:
        text = regex.sub('[' + dash + ']', '-', text)
        text = regex.sub('[' + single_quote + ']', "'", text)
        text = regex.sub('[' + double_quote + ']', '"', text)
        text = regex.sub('\u2026', '...', text)
    return text.lstrip('\ufeff')  # remove BOM


def auto_upper(text: str) -> str:
    return regex.sub('(^|[.?!])\\W*.|(?<!\\w)i(?!\\w)', lambda m: m[0].upper(), text, flags=regex.MULTILINE)


def check_caps(text: str, verbose: bool = False) -> int:
    recon = auto_upper(text.lower())
    cnt = sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))
    if verbose and cnt:
        print(f'Warning: found {cnt} chars with auto-capitalization mismatch')
    return cnt


def remove_the(text: str) -> str:
    return regex.sub('(^| )the ', '\\1 ', text, flags=regex.MULTILINE)


def encode_quq(text: str, caps: Optional[str] = None) -> str:
    if caps:
        check_quq(text, caps, verbose=True)
    return regex.sub("([Qq])u(?=['’](?!\\p{Lu})|\\p{Ll})", '\\1', text)


def decode_quq(text: str) -> str:
    return regex.sub("[Qq](?=['’](?!\\p{Lu})|\\p{Ll})", '\\g<0>u', text)


def check_quq(text: str, caps: str, verbose: bool = False) -> int:
    assert caps in caps_modes, f"caps='{caps}' not in {caps_modes}"
    if caps != 'raw':
        text = text.lower()
    recon = decode_quq(encode_quq(text))
    text = regex.split('[Qq]', text)
    recon = regex.split('[Qq]', recon)
    cnt = sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))
    if verbose and cnt:
        print(f'Warning: found {cnt} cases of q followed by a non u, or terminal qu')
    return cnt


def encode(text: str,
           caps: str = 'auto',
           the: bool = True,
           quq: bool = True,
           eos: str = default_eos,
           caps_warn: bool = False,
           quq_warn: bool = True
           ) -> str:
    assert caps in caps_modes, f"caps='{caps}' not in {caps_modes}"
    text = text
    if caps != 'raw':
        if caps == 'auto' and caps_warn:
            check_caps(text, verbose=True)
        text = text.lower()
    if the:
        text = remove_the(text)
    if quq:
        text = encode_quq(text, caps if quq_warn else None)
    if not text.endswith(eos):
        text += eos
    return text


def get_js_decoder(caps: str = 'auto',
                   the: bool = True,
                   quq: bool = True,
                   eos: str = default_eos,
                   text_name: str = default_names.text
                   ) -> str:
    assert caps in caps_modes, f"caps='{caps}' not in {caps_modes}"
    js_decoder = ''
    if eos:
        js_decoder += f".replace(/{eos.encode('unicode_escape').decode()}+.*$/,'')"
    if quq:
        js_decoder += ".replace(/[Qq](?=['\\u2019](?!\\p{Lu})|\\p{Ll})/gu,'$&u')"  # \u2019 is ’
    if the:
        js_decoder += ".replace(/(^| ) /gm,'$1the ')"
    if caps == 'auto':
        js_decoder += '.replace(/(^|[.?!])\\P{L}*.|(^|\\P{L})i(?!\\p{L})/gmu,s=>s.toUpperCase())'  # avoid lookbehind to support Safari
    elif caps == 'upper':
        js_decoder += '.toUpperCase()'
    if js_decoder:
        js_decoder = f'{text_name}={text_name}' + js_decoder + '\n'
    return js_decoder


def encode_and_get_js_decoder(text: str,
                              caps: str = 'auto',
                              the: bool = True,
                              quq: bool = True,
                              eos: str = default_eos,
                              caps_warn: bool = False,
                              quq_warn: bool = True,
                              caps_fallback: bool = False,
                              quq_fallback: bool = True,
                              text_name: str = default_names.text
                              ) -> Tuple[str, str]:
    if caps_fallback and caps == 'auto' and not check_caps(text, verbose=caps_warn):
        caps = 'raw'
        if caps_warn:
            print(f"Falling back to caps='{caps}'")
    if quq_fallback and quq and check_quq(text, caps, verbose=quq_warn):
        quq = False
        if quq_warn:
            print('Falling back to quq={quq}')
    return encode(text, caps, the, quq, eos, caps_warn, quq_warn), get_js_decoder(caps, the, quq, eos, text_name)


if __name__ == '__main__':
    bad = 0
    for caps in caps_modes:
        for q in 'Qq':
            for u in 'Uu':
                for a in "Aa'":
                    text = orig = f'{q}{u}{a}'
                    if caps != 'raw':
                        text = text.lower()
                    enc = encode_quq(text, caps)
                    dec = decode_quq(enc)
                    if text != dec:
                        print(f'caps={caps:>5}: orig={orig} -> text={text} -> enc={enc} -> dec={dec}')
                        bad += 1
    print(f'Found {bad} bad cases')
