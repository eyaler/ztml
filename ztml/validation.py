from base64 import b64decode
from contextlib import ExitStack, redirect_stdout
import html
import os
import sys
from tempfile import NamedTemporaryFile
from time import sleep, time
from typing import AnyStr, Iterable, Mapping, Optional, Union

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
default_by = By.TAG_NAME
default_element = 'body'
webdriver_paths_filename = 'webdriver_paths.txt'


os.environ['WDM_LOG'] = '0'
drivers = dict(chrome=[Chrome, chrome, ChromeDriverManager],
               edge=[Edge, edge, EdgeChromiumDriverManager],
               firefox=[Firefox, firefox, GeckoDriverManager]
               )
BrowserType = Union[str, WebDriver]
critical_error_strings = ['executable needs to be', 'unable to find binary', 'unexpectedly']


def full_path(filename: str) -> str:
    return f"file:///{os.path.realpath(filename).replace(os.sep, '/')}"


def get_browser(browser: BrowserType, stack: Optional[ExitStack] = None) -> WebDriver:
    if isinstance(browser, WebDriver):
        return browser
    options = drivers[browser][1].options.Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    if hasattr(options, 'add_experimental_option'):
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
    try:
        with redirect_stdout(None):
            service = drivers[browser][2]().install()
        folder = os.path.dirname(webdriver_paths_filename)
        if folder:
            os.makedirs(folder, exist_ok=True)
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
            if any(s in e.msg for s in critical_error_strings):
                raise
            print(e, file=sys.stderr)
            sleep(30)
    if stack:
        browser = stack.enter_context(browser)
    return browser


def render_html(file: AnyStr,
                browser: BrowserType = default_browser,
                timeout: int = default_timeout,
                by: str = default_by,
                element: str = default_element,
                raw: bool = False,
                image: bool = False,
                bytearray_var: str = default_vars.bytearray,
                ) -> Optional[AnyStr]:
    if not by:
        by = default_by
    if not element:
        element = default_element
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
            wait = WebDriverWait(browser, timeout)
            if image:
                if by == By.TAG_NAME and element == 'body':
                    data_url = wait.until(lambda x: regex.sub('^none$', '', x.find_element(by, element).value_of_css_property('background-image')))
                else:
                    data_url = wait.until(lambda x: x.find_element(by, element).get_property('src'))
                if ';base64,' in data_url:
                    return b64decode(data_url.split(';base64,', 1)[1].split('"', 1)[0], validate=True)
                image_data = browser.execute_script(f'return {bytearray_var}')
                if isinstance(image_data, dict):  # For Firefox, see: https://github.com/SeleniumHQ/selenium/issues/11070
                    image_data = [v for k, v in sorted(image_data.items(), key=lambda x: int(x[0]))]
                return bytes(image_data)
            if raw:
                by = By.TAG_NAME
                element = 'body'
                sleep(1)
            wait.until(lambda x: x.find_element(by, element).text)
            text_property = 'innerHTML' if raw else 'innerText'
            out = browser.find_element(by, element).get_property(text_property)
            if raw:
                out = html.unescape(out)
            return out
        except TimeoutException:
            return None
        except Exception:
            print(f'\nError: {browser.name} failed on {full_path(filename)}', file=sys.stderr)
            raise


def find_first_diff(render: AnyStr, data: AnyStr, verbose: bool = True) -> int:
    i = -1
    for i, (r, t) in enumerate(zip(render, data)):
        if r != t:
            break
    else:
        i += 1
    if verbose:
        print(f'\nFirst difference found at {i} / {len(render)}', file=sys.stderr)
        print('Original:', repr(data[max(i - 30, 0) : i]), '->', repr(data[i : i + 50]), file=sys.stderr)
        print('Rendered:', repr(render[max(i - 30, 0) : i]), '->', repr(render[i : i + 50]), '\n', file=sys.stderr)
    return i


def validate_html(file: AnyStr,
                  data: AnyStr,
                  caps: str = text_prep.default_caps,
                  ignore_regex: str = '',
                  unicode_A: int = 0,
                  browser: BrowserType = default_browser,
                  timeout: int = default_timeout,
                  by: str = default_by,
                  element: str = default_element,
                  raw: bool = False,
                  image: bool = False,
                  bytearray_var: str = default_vars.bytearray,
                  verbose: bool = True
                  ) -> Optional[bool]:
    render = render_html(file, browser, timeout, by, element, raw, image, bytearray_var)
    if render is None:
        return None
    if not image:
        if caps == 'lower':
            data = data.lower()
        elif caps == 'upper':
            data = data.upper()
        elif caps == 'simple':
            data = text_prep.decode_caps_simple(data.lower())
        render = regex.sub(ignore_regex, '', render)
        if unicode_A:
            render = regex.sub('[^\\p{Z}\\p{C}]', lambda m: chr(ord(m[0]) - unicode_A + 65 + (6 if ord(m[0]) - unicode_A + 65 > 90 else 0)), render)
    if render == data:
        return True
    if verbose:
        find_first_diff(render, data)
    return False


def validate_files(filenames: Mapping[str, str],
                   data: Optional[AnyStr] = None,
                   reduce_whitespace: bool = False,
                   unix_newline: bool = True,
                   fix_punct: bool = False,
                   caps: str = text_prep.default_caps,
                   ignore_regex: str = '',
                   unicode_A: int = 0,
                   by: str = default_by,
                   element: str = default_element,
                   raw: bool = False,
                   image: bool = False,
                   bytearray_var: str = default_vars.bytearray,
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
        raw_size = None
        base64_size = None
        for label, filename in filenames.items():
            ext = os.path.splitext(filename)[-1][1:]
            if raw_size is not None and ext != 'html' or not os.path.exists(filename):
                continue
            size = os.path.getsize(filename)
            if data is None:
                assert ext != 'html', filename
                if ext.lower() in ['bmp', 'gif', 'jpeg', 'jpg', 'png', 'webp']:
                    image = True
                with open(filename, 'rb') as f:
                    data = f.read()
                    if not image:
                        data = text_prep.normalize(data.decode(), reduce_whitespace, unix_newline, fix_punct)  # Assumes first text file is utf8. Otherwise, you can pass the text argument
            if raw_size is None:
                raw_size = size if ext != 'html' else len(data.encode())
            if label == 'base64_html':
                base64_size = size * 3 / 4
            if verbose:
                stats = []
                if raw_size:
                    stats.append(f'ratio={round(size / raw_size * 100, 1)}%')
                if base64_size:
                    stats.append(f'overhead={round((size/base64_size-1) * 100, 1)}%')
                if ext == 'html' and label != 'base64_html':
                    with open(filename, 'rb') as f:
                        script = f.read()
                        script = script.replace(max(regex.finditer(webify.get_literals_regex(payload_var).encode(), script),
                                                    key=lambda m: len(m[0]), default=b'')[0].split(b'`', 1)[1].rsplit(b'`', 1)[0], b'')
                    stats.append(f'code: {len(script):,} B = {round(len(script) / 1024, 1):,} kB')
                stats = ' '.join(stats)
                if stats:
                    stats = f' ({stats})'
                mb = size / 1024 ** 2
                if mb >= 0.1:
                    stats = f' = {round(mb, 1):,} MB' + stats
                kb = size / 1024
                if kb >= 0.1:
                    stats = f' = {round(kb, 1):,} kB' + stats
                print(f"{full_path(filename)} {size:,} B{stats}", end='' if validate and ext == 'html' else None, file=sys.stderr)
            if validate and ext == 'html':
                for i, browser in enumerate(browsers):
                    start_time = time()
                    valid = validate_html(filename, data, caps, ignore_regex, unicode_A,
                                          browser, timeout, by, element, raw, image,
                                          bytearray_var, verbose)
                    assert valid is not False, filename
                    if verbose:
                        if not i:
                            print(f' rendering secs:', end='', file=sys.stderr)
                        print(f' {browser.name}=' + (f'{time() - start_time :.1f}' if valid else f'{timeout}(TIMEOUT)'), end='', file=sys.stderr)
                if verbose:
                    print(file=sys.stderr)
        if verbose and validate:
            print('Note: above rendering times from Selenium are much longer than actual browser rendering.', file=sys.stderr)
