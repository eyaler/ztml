from collections import Mapping
from contextlib import ExitStack, redirect_stdout
import os
import sys
from tempfile import NamedTemporaryFile
from time import sleep, time
from typing import AnyStr, Iterable, Optional, Union

import regex
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import Chrome, Edge, Firefox, chrome, edge, firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.firefox import GeckoDriverManager

if not __package__:
    import default_vars, text_prep, webify
else:
    from . import default_vars, text_prep, webify


default_browser = 'chrome'
default_timeout = 60
default_element = 'body'
webdriver_paths_filename = 'webdriver_paths.txt'


os.environ['WDM_LOG'] = '0'
drivers = dict(chrome=[Chrome, chrome, ChromeDriverManager],
               edge=[Edge, edge, EdgeChromiumDriverManager],
               firefox=[Firefox, firefox, GeckoDriverManager]
               )
BrowserType = Union[str, WebDriver]


def full_path(filename: str) -> str:
    return f"file:///{os.path.realpath(filename).replace(os.sep, '/')}"


def get_browser(browser: BrowserType, stack: Optional[ExitStack] = None) -> WebDriver:
    if isinstance(browser, WebDriver):
        return browser
    options = drivers[browser][1].options.Options()
    options.headless = True
    try:
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
    except AttributeError:
        pass
    try:
        with redirect_stdout(None):
            service = drivers[browser][2]().install()
        with open(webdriver_paths_filename, 'a', encoding='utf8') as f:
            f.write(f'{browser},{service}\n')
    except Exception:
        with open(webdriver_paths_filename, encoding='utf8') as f:
            for line in reversed(f.read().splitlines()):
                b, service = line.split(',', 1)
                if b == browser:
                    break
    while isinstance(browser, str):
        try:
            browser = drivers[browser][0](service=drivers[browser][1].service.Service(service, log_path=os.devnull), options=options)
        except WebDriverException as e:
            print(e, file=sys.stderr)
            sleep(30)
    if stack:
        browser = stack.enter_context(browser)
    return browser


def render_html(file: AnyStr,
                browser: BrowserType = default_browser,
                timeout: int = default_timeout,
                element: str = default_element
                ) -> Optional[str]:
    with ExitStack() as stack:
        browser = get_browser(browser, stack)
        if isinstance(file, str):
            filename = file
        else:
            with NamedTemporaryFile(suffix='.html', delete=False) as f:
                f.write(file)
                filename = f.name
        browser.get(full_path(filename))
        if isinstance(file, bytes):
            try:
                os.remove(filename)
            except PermissionError:
                pass
        try:
            WebDriverWait(browser, timeout).until(lambda x: x.find_element(By.TAG_NAME, element).text)
            return browser.find_element(By.TAG_NAME, element).get_attribute('innerText')
        except TimeoutException:
            return None


def find_first_diff(render: str, text: str, verbose: bool = True) -> int:
    i = -1
    for i, (r, t) in enumerate(zip(render, text)):
        if r != t:
            break
    else:
        i += 1
    if verbose:
        print(f'\nFirst difference found at {i} / {len(render)}', file=sys.stderr)
        print('Original:', repr(text[max(i - 30, 0) : i]), '->', repr(text[i : i + 50]), file=sys.stderr)
        print('Rendered:', repr(render[max(i - 30, 0) : i]), '->', repr(render[i : i + 50]), '\n', file=sys.stderr)
    return i


def validate_html(file: AnyStr,
                  text: str,
                  compare_caps: bool = True,
                  ignore_regex: str = '',
                  unicode_A: int = 0,
                  browser: BrowserType = default_browser,
                  timeout: int = default_timeout,
                  element: str = default_element,
                  verbose: bool = True
                  ) -> Optional[bool]:
    render = render_html(file, browser, timeout, element)
    if render is None:
        return None
    if not compare_caps:
        render = render.lower()
        text = text.lower()
    render = regex.sub(ignore_regex, '', render)
    if unicode_A:
        render = regex.sub('[^\\p{Z}\\p{C}]', lambda m: chr(ord(m[0]) - unicode_A + 65 + (6 if ord(m[0]) - unicode_A + 65 > 90 else 0)), render)
    if render == text:
        return True
    if verbose:
        find_first_diff(render, text)
    return False


def validate_files(filenames: Mapping[str, str],
                   text: Optional[str] = None,
                   reduce_whitespace: bool = False,
                   fix_newline: bool = True,
                   fix_punct: bool = False,
                   compare_caps: bool = True,
                   ignore_regex: str = '',
                   unicode_A: int = 0,
                   element: str = default_element,
                   browsers: Optional[Union[BrowserType, Iterable[BrowserType]]] = None,
                   timeout: int = default_timeout,
                   payload_var: str = default_vars.payload,
                   validate: bool = True,
                   verbose: bool = True
                   ) -> None:
    if browsers is None:
        browsers = list(drivers)
    elif isinstance(browsers, (str, WebDriver)):
        browsers = [browsers]
    with ExitStack() as stack:
        browsers = [get_browser(browser, stack) for browser in browsers]
        text_size = None
        base64_size = None
        for label, filename in filenames.items():
            ext = os.path.splitext(filename)[-1][1:]
            if ext not in ['txt', 'html']:
                continue
            size = os.path.getsize(filename)
            if text is None:
                assert ext == 'txt', filename
                with open(filename, 'rb') as f:
                    text = text_prep.normalize(f.read().decode(), reduce_whitespace, fix_newline, fix_punct)  # Assumes first text file is utf8. Otherwise, you can pass the text argument
            if text_size is None:
                text_size = size if ext == 'txt' else len(text.encode())
            if label == 'base64_html':
                base64_size = size * 3 / 4
            if verbose:
                stats = []
                if text_size:
                    stats.append(f'ratio={round(size / text_size * 100, 1)}%')
                if base64_size:
                    stats.append(f'overhead={round((size/base64_size-1) * 100, 1)}%')
                if ext == 'html' and label != 'base64_html':
                    with open(filename, 'rb') as f:
                        script = f.read()
                        if label == 'crenc_html':
                            print('hi')
                        script = script.replace(max(regex.finditer(webify.get_literals_regex(payload_var).encode(), script), key=lambda m: len(m[0]), default=b'')[0].split(b'`', 1)[1].rsplit(b'`', 1)[0], b'')
                    stats.append(f'code: {len(script):,} B = {round(len(script) / 1024, 1):,} kB')
                stats = ' '.join(stats)
                if stats:
                    stats = f' ({stats})'
                if (mb := size / 1024**2) >= 0.1:
                    stats = f' = {round(mb, 1):,} MB' + stats
                if (kb := size / 1024) >= 0.1:
                    stats = f' = {round(kb, 1):,} kB' + stats
                print(f"{full_path(filename)} {size:,} B{stats}", end='' if validate and ext == 'html' else None, file=sys.stderr)
            if validate and ext == 'html':
                for i, browser in enumerate(browsers):
                    start_time = time()
                    valid = validate_html(filename, text, compare_caps, ignore_regex, unicode_A, browser, timeout, element, verbose)
                    assert valid is not False, filename
                    if verbose:
                        if not i:
                            print(f' rendering secs:', end='', file=sys.stderr)
                        print(f' {browser.name}=' + (f'{time() - start_time :.1f}' if valid else f'{timeout}(TIMEOUT)'), end='', file=sys.stderr)
                if verbose:
                    print(file=sys.stderr)
        if verbose and validate:
            print('Note: above rendering times from Selenium are much longer than actual browser rendering', file=sys.stderr)
