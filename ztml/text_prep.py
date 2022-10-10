import sys
from typing import Optional, Tuple

import regex

if not __package__:
    import default_vars
else:
    from . import default_vars


newline = '\\n\\v\\f\\r\\x85\\u2028'
single_quote = '[\u2018-\u201b\u05f3\uff07]'
double_quote = '[\u201c-\u201f\u05f4\uff02]'
apos = "['’]"  # \\uff07
eos = '[!.?]'  # \\uff01\\uff0e\\uff1f\\ufe52\\ufe56\\ufe57
nonword = '\\p{L}\\p{M}\\p{N}'
caps_modes = ['auto', 'lower', 'raw', 'simple', 'upper']
default_caps = 'auto'


def normalize(text: str,
              reduce_whitespace: bool = False,
              unix_newline: bool = True,
              fix_punct: bool = False
              ) -> str:
    if reduce_whitespace:
        text = regex.sub(f'\\s*[{newline}]\\s*[{newline}]\\s*', '\n\n', text.replace('\u2029', '\n\n'))
        text = regex.sub(f'[^\\S{newline}]*[{newline}][^\\S{newline}]*', '\n', text)
        text = regex.sub(f'[^\\S{newline}]+', ' ', text)
        text = text.strip()
    elif unix_newline:
        text = regex.sub('\r\n?', '\n', text)
    if fix_punct:
        text = regex.sub('\\p{Pd}', '-', text)
        text = regex.sub(single_quote, "'", text)
        text = regex.sub(double_quote, '"', text)
        text = regex.sub('\u2026', '...', text)
    return text.lstrip('\ufeff')  # Remove BOM


caps_regex = f'(((?=(\\r\\n|[{newline}]))\\3){{2,}}|\\u2029|^|{eos})\\P{{L}}*.|(^|[^{nonword}])i(?![{nonword}])'  # Avoid lookbehind to support Safari


def decode_caps_simple(text: str) -> str:
    return regex.sub(caps_regex, lambda m: m[0].upper(), text)


def encode_caps(text: str, caps: str = default_caps) -> str:
    assert caps in caps_modes, f"Error: caps='{caps}' not in {caps_modes}"
    return text if caps == 'raw' else text.upper() if caps == 'upper' else text.lower()


def remove_the(text: str) -> str:
    the_str = 'THE' if text == text.upper() else 'the'
    return regex.sub(f'(^| ){the_str} ', '\\1 ', text, flags=regex.MULTILINE)


def get_qu_regex(next_letter_case: str, u_caps: Optional[bool] = None) -> str:
    u = 'U' if u_caps or u_caps is None and next_letter_case == 'u' else 'u'
    return f'(?={apos}?[^{u}\\P{{L{next_letter_case}}}])'


def encode_quq(text: str) -> str:
    return regex.sub(f"QU{get_qu_regex('')}", 'Q', regex.sub(f"([Qq])u{get_qu_regex('l')}", '\\1', text))


def decode_quq(text: str, caps: str) -> str:
    if caps == 'raw':
        text = regex.sub(f"Q{get_qu_regex('u')}", 'QU', regex.sub(f"[Qq]{get_qu_regex('l')}", '\\g<0>u', text))
    elif caps == 'upper':
        text = regex.sub(f"Q{get_qu_regex('', u_caps=True)}", 'QU', text)
    else:
        text = regex.sub(f"q{get_qu_regex('')}", 'qu', text)
    return text


def get_quq_js_decoder(caps: str) -> str:
    if caps == 'raw':
        js_decoder = f".replace(/[Qq]{get_qu_regex('l')}/gu,'$&u').replace(/Q{get_qu_regex('u')}/gu,'QU')"
    elif caps == 'upper':
        js_decoder = f".replace(/Q{get_qu_regex('', u_caps=True)}/gu,'QU')"
    else:
        js_decoder = f".replace(/q{get_qu_regex('')}/gu,'qu')"
    return js_decoder


def count_bad_quq(text: str, caps: str, verbose: bool = False) -> int:
    text = encode_caps(text, caps)
    recon = decode_quq(encode_quq(text), caps)
    text = regex.split('[Qq]', text)
    recon = regex.split('[Qq]', recon)
    cnt = sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))
    if verbose and cnt:
        print(f'Warning: found {cnt} cases of q followed by a non u, or terminal qu', file=sys.stderr)
    return cnt


def encode_with_fallbacks(text: str,
                          caps: str = default_caps,
                          the: bool = True,
                          quq: bool = True,
                          caps_fallback: bool = True,
                          the_fallback: bool = True,
                          quq_fallback: bool = True,
                          verbose: bool = False
                          ) -> Tuple[str, str, bool, bool]:
    if caps_fallback:
        if caps == 'auto' and text != decode_caps_simple(encode_caps(text, caps)):
            caps = 'raw'
            if verbose:
                print(f"Falling back to caps='{caps}'", file=sys.stderr)
        if caps == 'raw':
            if text == text.lower():
                caps = 'lower'
            elif text == text.upper():
                caps = 'upper'
    text = encode_caps(text, caps)

    if the:
        theless = remove_the(text)
        if the_fallback:
            if theless == text:
                the = False
            if the and regex.search('(^| ) ', text, regex.MULTILINE):
                the = False
                if verbose:
                    print(f'Falling back to the={the}', file=sys.stderr)
        if the:
            text = theless

    if quq:
        quless = encode_quq(text)
        if quq_fallback:
            if len(text) - len(quless) < len(get_quq_js_decoder(caps)):
                quq = False
            if quq and count_bad_quq(text, caps, verbose):
                quq = False
                if verbose:
                    print(f'Falling back to quq={quq}', file=sys.stderr)
        if quq:
            text = quless

    return text, caps, the, quq


def get_js_decoder(text: Optional[str] = None,
                   caps: str = default_caps,
                   the: bool = True,
                   quq: bool = True,
                   text_var: str = default_vars.text
                   ) -> str:
    assert caps in caps_modes, f"Error: caps='{caps}' not in {caps_modes}"
    if text is not None:
        text, caps, the, quq = encode_with_fallbacks(text, caps, the, quq)
    js_decoder = ''
    if quq:
        js_decoder += get_quq_js_decoder(caps)
    if the:
        the_str = 'THE' if caps == 'upper' else 'the'
        js_decoder += f".replace(/(^| ) /gm,'$1{the_str} ')"
    if caps in ['auto', 'simple']:
        js_decoder += f'.replace(/{caps_regex}/gu,m=>m.toUpperCase())'
    if js_decoder:
        js_decoder = f'{text_var}={text_var}{js_decoder}\n'
    return js_decoder


def encode_and_get_js_decoder(text: str,
                              caps: str = default_caps,
                              the: bool = True,
                              quq: bool = True,
                              caps_fallback: bool = True,
                              the_fallback: bool = True,
                              quq_fallback: bool = True,
                              verbose: bool = False,
                              text_var: str = default_vars.text
                              ) -> Tuple[str, str]:
    text, caps, the, quq = encode_with_fallbacks(text, caps, the, quq, caps_fallback, the_fallback, quq_fallback, verbose)
    return text, get_js_decoder(caps=caps, the=the, quq=quq, text_var=text_var)


def test_quq() -> None:
    bad = 0
    for caps in caps_modes:
        for q in 'Qq':
            for u in ['U', 'u', ' ', "' "]:
                for a in "AaUu'’ ":
                    for b in 'Bb ':
                        orig = f'{q}{u}{a}{b}'
                        text, new_caps, _, _ = encode_with_fallbacks(orig, caps, the=False, quq=False)
                        enc = encode_quq(text)
                        dec = decode_quq(text, new_caps)
                        if text != dec:
                            print(f'caps={caps:>6}->{new_caps:>5}: orig={orig} -> text={text} -> enc={enc} -> dec={dec}', file=sys.stderr)
                            bad += 1
    print(f'Found {bad} bad qu cases', file=sys.stderr)


if __name__ == '__main__':
    test_quq()
