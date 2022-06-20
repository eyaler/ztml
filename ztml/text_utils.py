import re
from typing import Tuple

from ztml import default_names


newline = '\n\v\f\r\x85\u2028\u2029'
dash = '\u2010-\u2015'
single_quote = '\u2018-\u201b'
double_quote = '\u201c-\u201f'
default_eos = '\n'


def normalize(text: str,
              reduce_whitespace: bool = True,
              fix_newline: bool = True,
              fix_punct: bool = True
              ) -> str:
    if reduce_whitespace:
        text = re.sub('\\s*[' + newline + ']\\s*[' + newline + ']\\s*', '\n\n', text)
        text = re.sub('[^\\S' + newline + ']*[' + newline + '][^\\S' + newline + ']*', '\n', text)
        text = re.sub('[^\\S' + newline + ']+', ' ', text)
        text = text.strip()
    elif fix_newline:
        text = re.sub('\r\n?', '\n', text)
    if fix_punct:
        text = re.sub('[' + dash + ']', '-', text)
        text = re.sub('[' + single_quote + ']', "'", text)
        text = re.sub('[' + double_quote + ']', '"', text)
        text = re.sub('\u2026', '...', text)
    return text.lstrip('\ufeff')  # remove BOM


def smart_upper(text: str) -> str:
    return re.sub('(^|[.?!])\\W*.|(?<!\\w)i(?!\\w)', lambda m: m[0].upper(), text, flags=re.MULTILINE)


def check_caps(text: str) -> int:
    recon = smart_upper(text.lower())
    return sum(a != b for a, b in zip(recon, text)) + abs(len(recon) - len(text))


def remove_the(text: str) -> str:
    return re.sub('(^| )the ', '\\1 ', text, flags=re.MULTILINE)


def check_quq(text: str) -> int:
    return len(re.findall("q([^\\Wu']|u\\b(?!['’]))", text, flags=re.IGNORECASE))


def encode(text: str,
           caps: bool = True,
           the: bool = True,
           quq: bool = True,
           eos: str = default_eos,
           caps_warn: bool = False,
           quq_warn: bool = True
           ) -> str:
    text = text
    if caps:
        if caps_warn:
            cnt = check_caps(text)
            if cnt:
                print(f'Warning: found {cnt} chars with auto-capitalization mismatch')
        text = text.lower()
    if the:
        text = remove_the(text)
    if quq:
        if quq_warn:
            cnt = check_quq(text)
            if cnt:
                print(f'Warning: found {cnt} cases of non-final Q/q not followed by U/u')
        text = re.sub('(q)u', '\\1', text, flags=re.IGNORECASE)
    if not text.endswith(eos):
        text += eos
    return text


def get_js_decoder(caps: bool = True,
                   the: bool = True,
                   quq: bool = True,
                   eos: str = default_eos,
                   text_name: str = default_names.text
                   ) -> str:
    js_decoder = ''
    if eos:
        js_decoder += f".replace(/{eos.encode('unicode_escape').decode()}+.*$/,'')"
    if quq:
        js_decoder += ".replace(/q(?=[\\p{L}'\\u2019])/giu,'$&u')"  # \u2019 is ’
    if the:
        js_decoder += ".replace(/(^| ) /gm,'$1the ')"
    if caps:
        js_decoder += '.replace(/(^|[.?!])\\P{L}*.|(?<!\\p{L})i(?!\\p{L})/gmu,c=>c.toUpperCase())'
    if js_decoder:
        js_decoder = f'{text_name}={text_name}' + js_decoder + '\n'
    return js_decoder


def encode_and_get_js_decoder(text: str,
                              caps: bool = True,
                              the: bool = True,
                              quq: bool = True,
                              eos: str = default_eos,
                              caps_warn: bool = False,
                              quq_warn: bool = True,
                              caps_fallback: bool = False,
                              quq_fallback: bool = True,
                              text_name: str = default_names.text
                              ) -> Tuple[str, str]:
    if caps_fallback and caps and not check_caps(text):
        caps = False
    if quq_fallback and quq and check_quq(text):
        quq = False
    return encode(text, caps, the, quq, eos, caps_warn, quq_warn), get_js_decoder(caps, the, quq, eos, text_name)
