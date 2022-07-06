import logging
import os
import regex
from time import time
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, Edge, Firefox, chrome, edge, firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from . import text_utils


default_timeout = 60
default_element_name = 'body'


logging.getLogger('WDM').setLevel(logging.NOTSET)
drivers = dict(chrome=[Chrome, chrome, ChromeDriverManager().install()],
               edge=[Edge, edge, EdgeChromiumDriverManager().install()],
               firefox=[Firefox, firefox, GeckoDriverManager().install()]
               )


def render_html(filename: str, browser: str = list(drivers)[0], timeout: int = default_timeout, element_name: str = default_element_name) -> Optional[str]:
    options = drivers[browser][1].options.Options()
    options.headless = True
    with drivers[browser][0](service=drivers[browser][1].service.Service(drivers[browser][2], log_path=os.devnull), options=options) as b:
        b.get('file:///' + os.path.abspath(filename))
        try:
            return WebDriverWait(b, timeout).until(lambda x: x.find_element(by=By.TAG_NAME, value=element_name).text)
        except TimeoutException:
            return None


def validate_html(filename: str,
                  text: str,
                  compare_caps: bool = True,
                  eos: str = text_utils.default_eos,
                  ignore_regex: str = '',
                  unicode_A: int = 0,
                  browser: str = list(drivers)[0],
                  timeout: int = default_timeout,
                  element_name: str = default_element_name,
                  verbose: bool = True
                  ) -> Optional[bool]:
    render = render_html(filename, browser, timeout, element_name)
    if render is None:
        return None
    if not compare_caps:
        render = render.lower()
        text = text.lower()
    text = text.rstrip(eos)
    render = regex.sub(ignore_regex, '', render)
    if unicode_A:
        render = regex.sub('[^\\p{Z}\\p{C}]', lambda m: chr(ord(m[0]) - unicode_A + 65 + (6 if ord(m[0]) - unicode_A + 65 > 90 else 0)), render)
    if render == text:
        return True
    if verbose:
        i = -1
        for i, (r, t) in enumerate(zip(render, text)):
            if r != t:
                break
        else:
            i += 1
        print('\nFirst difference found at', i)
        sl = slice(max(i - 30, 0), i + 50)
        print('Original:', repr(text[sl]))
        print('Rendered:', repr(render[sl]))
    return False


def validate_files(filenames: dict[str, str],
                   text: Optional[str] = None,
                   reduce_whitespace: bool = True,
                   fix_newline: bool = True,
                   fix_punct: bool = True,
                   compare_caps: bool = True,
                   eos: str = text_utils.default_eos,
                   ignore_regex: str = '',
                   unicode_A: int = 0,
                   element_name: str = default_element_name,
                   browsers: Optional[list[str]] = None,
                   timeout: int = default_timeout,
                   validate: bool = True,
                   verbose: bool = True
                   ) -> None:
    if browsers is None:
        browsers = list(drivers)
    text_size = None
    base64_size = None
    for label, filename in filenames.items():
        ext = os.path.splitext(filename)[-1][1:]
        if not ext.endswith(('txt', 'html')):
            continue
        size = os.path.getsize(filename)
        if text is None:
            assert ext == 'txt', filename
            with open(filename, 'rb') as f:
                text = text_utils.normalize(f.read().decode(), reduce_whitespace, fix_newline, fix_punct)
        if text_size is None:
            text_size = size if ext == 'txt' else len(text.encode())
        if label == 'base64_html':
            base64_size = size * 3 / 4
        if verbose:
            stats = []
            if text_size:
                stats.append(f'compression={round(size / text_size * 100, 1)}%')
            if base64_size:
                stats.append(f'overhead={round((size/base64_size-1) * 100, 1)}%')
            stats = ' '.join(stats)
            if stats:
                stats = f' ({stats})'
            if (mb := size / 1024**2) >= 0.1:
                stats = f' = {round(mb, 1):,} MB' + stats
            if (kb := size / 1024) >= 0.1:
                stats = f' = {round(kb, 1):,} kB' + stats
            print(f'{filename} {size:,} B{stats}', end='' if validate and ext == 'html' else None)
        if validate and ext == 'html':
            times = ''
            for browser in browsers:
                start_time = time()
                valid = validate_html(filename, text, compare_caps, eos, ignore_regex, unicode_A, browser, timeout, element_name, verbose)
                assert valid is not False, filename
                times += f' {browser}=' + (f'{time() - start_time :.1f}' if valid else f'{timeout}(timeout)')
            if verbose:
                print(f' rendering secs:{times}')
