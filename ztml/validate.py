import os
import re
from time import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ztml import text_utils


chrome_options = Options()
chrome_options.headless = True
service = Service(ChromeDriverManager(log_level=0).install())
default_element_name = 'body'


def render_html(filename: str, element_name: str = default_element_name) -> Optional[str]:
    with webdriver.Chrome(service=service, options=chrome_options) as browser:
        browser.get('file:///' + os.path.abspath(filename))
        try:
            return WebDriverWait(browser, 60).until(lambda x: x.find_element(by=By.TAG_NAME, value=element_name).text)
        except TimeoutException:
            return None


def validate_html(filename: str,
                  text: str,
                  compare_caps: bool = True,
                  eos: str = text_utils.default_eos,
                  ignore_regex: str = '',
                  element_name: str = default_element_name,
                  verbose: bool = True
                  ) -> Optional[bool]:
    render = render_html(filename, element_name)
    if render is None:
        return None
    if not compare_caps:
        render = render.lower()
        text = text.lower()
    text = text.rstrip(eos)
    render = re.sub(ignore_regex, '', render)
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
                   element_name: str = default_element_name,
                   verbose: bool = True
                   ) -> None:
    text_size = None
    base64_size = None
    overhead = ''
    for label, filename in filenames.items():
        ext = os.path.splitext(filename)[-1][1:]
        if not ext.endswith(('txt', 'html')):
            continue
        size = os.path.getsize(filename)
        if text is None:
            assert ext == 'txt', filename
            text_size = size
            with open(filename, 'rb') as f:
                text = text_utils.normalize(f.read().decode(), reduce_whitespace, fix_newline, fix_punct)
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
            print(f'{filename} {size:,} B{stats}', end='' if ext == 'html' else None)
        start_time = time()
        if ext == 'html':
            validate = validate_html(filename, text, compare_caps, eos, ignore_regex, element_name, verbose)
            assert validate is not False, filename
            if verbose:
                if validate:
                    print(f' rendering took {time() - start_time :.1f} s')
                else:
                    print(' - NOT validated due to rendering timeout!')
