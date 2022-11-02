from base64 import b64decode
from contextlib import ExitStack, redirect_stdout
import os
import sys
from tempfile import NamedTemporaryFile
from time import sleep, time
from typing import AnyStr, Iterable, Mapping, Optional, overload, TypeVar, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

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
    # noinspection PyPackages
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


FilenameOrBytes = TypeVar('FilenameOrBytes', str, bytes)


def full_path(filename: str) -> str:
    return f"file:///{os.path.realpath(filename).replace(os.sep, '/')}"


def get_browser(browser: BrowserType,
                stack: Optional[ExitStack] = None
                ) -> WebDriver:
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


@overload
def render_html(file: FilenameOrBytes, by: str = ..., element: str = ...,
                raw: bool = ..., image: Literal[True] = ...,
                browser: str = ..., timeout: int = ..., content_var: str = ...
                ) -> Optional[bytes]: ...


@overload
def render_html(file: FilenameOrBytes, by: str = ..., element: str = ...,
                raw: bool = ..., image: Literal[False] = ...,
                browser: str = ..., timeout: int = ..., content_var: str = ...
                ) -> Optional[str]: ...


@overload
def render_html(file: FilenameOrBytes, by: str = ..., element: str = ...,
                raw: bool = ..., image: bool = ...,
                browser: str = ..., timeout: int = ..., content_var: str = ...
                ) -> Optional[AnyStr]: ...


def render_html(file,
                by=default_by,
                element=default_element,
                raw=False,
                image=False,
                browser=default_browser,
                timeout=default_timeout,
                content_var=''
                ):
    assert not raw or not image
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
                assert isinstance(data_url, str), type(data_url)
                if ';base64,' in data_url:
                    return b64decode(data_url.split(';base64,', 1)[1].split('"', 1)[0], validate=True)
                image_data = browser.execute_script(f'return {content_var or default_vars.bytearray}')
                if isinstance(image_data, dict):  # Needed for or Firefox, see: https://github.com/SeleniumHQ/selenium/issues/11070
                    image_data = [v for k, v in sorted(image_data.items(), key=lambda x: int(x[0]))]
                return bytes(image_data)
            if raw:
                sleep(0.1)
                get_text = lambda x: x.execute_script(f'return {content_var or default_vars.text}')
            else:
                get_text = lambda x: x.find_element(by, element).get_property('innerText')
            text = wait.until(get_text)
            assert isinstance(text, str), type(text)
            return text
        except TimeoutException:
            return None
        except Exception:
            print(f'\nError: {browser.name} failed on {full_path(filename)}', file=sys.stderr)
            raise


def find_first_diff(rendered: AnyStr, data: AnyStr, verbose: bool = True) -> int:
    i = -1
    for i, (r, t) in enumerate(zip(rendered, data)):
        if r != t:
            break
    else:
        i += 1
    if verbose:
        print(f'\nFirst difference found at {i} / {len(rendered)}', file=sys.stderr)
        print('Original:', repr(data[max(i - 30, 0) : i]), '->', repr(data[i : i + 50]), file=sys.stderr)
        print('Rendered:', repr(rendered[max(i - 30, 0) : i]), '->', repr(rendered[i : i + 50]), '\n', file=sys.stderr)
    return i


def validate_html(file: FilenameOrBytes,  # Don't use AnyStr as it does not have to be the same type as data
                  data: AnyStr,
                  caps: str = text_prep.default_caps,
                  by: str = default_by,
                  element: str = default_element,
                  raw: bool = False,
                  browser: BrowserType = default_browser,
                  timeout: int = default_timeout,
                  unicode_A: int = 0,
                  ignore_regex: str = '',
                  content_var: str = '',
                  verbose: bool = True
                  ) -> Optional[bool]:
    image = isinstance(data, bytes)
    assert data, 'Error: Cannot validate against empty data'
    rendered = render_html(file, by, element, raw, image, browser, timeout, content_var)
    if rendered is None:
        return None
    if not image:
        if caps == 'lower':
            data = data.lower()
        elif caps == 'upper':
            data = data.upper()
        elif caps == 'simple':
            data = text_prep.decode_caps_simple(data.lower())
        if not raw:
            if unicode_A:
                rendered = regex.sub(r'[^\p{Z}\p{C}]', lambda m: chr(ord(m[0]) - unicode_A + 65 + (6 if ord(m[0]) - unicode_A + 65 > 90 else 0)), rendered)
            rendered = regex.sub(ignore_regex, '', rendered)
    if rendered == data:
        return True
    if verbose:
        find_first_diff(rendered, data)
    return False


def validate_files(filenames: Mapping[str, str],
                   data: Optional[AnyStr] = None,
                   reduce_whitespace: bool = False,
                   unix_newline: bool = True,
                   fix_punct: bool = False,
                   remove_bom: bool = True,
                   caps: str = text_prep.default_caps,
                   by: str = default_by,
                   element: str = default_element,
                   raw: bool = False,
                   image: bool = False,
                   browsers: Optional[Union[BrowserType, Iterable[BrowserType]]] = None,
                   timeout: int = default_timeout,
                   unicode_A: int = 0,
                   ignore_regex: str = '',
                   content_var: str = '',
                   validate: bool = True,
                   verbose: bool = True
                   ) -> bool:
    assert not image or (not raw and not isinstance(data, str))
    error = False
    if browsers is None:
        browsers = list(drivers)
    elif isinstance(browsers, (str, WebDriver)):
        browsers = [browsers]
    with ExitStack() as stack:
        if validate:
            browsers = [get_browser(browser, stack) for browser in browsers]
        raw_size = None
        no_overhead_size = None
        for label, filename in sorted(filenames.items(), key=lambda x: (x[0] != 'raw', x[0] != 'base64_html')):
            ext = os.path.splitext(filename)[-1][1:]
            if raw_size is not None and ext != 'html':
                continue
            if (data is None or label == 'raw') and ext.lower() in ['bmp', 'gif', 'jfif', 'jpe', 'jpeg', 'jpg', 'png', 'webp']:
                image = True
            if data is None:
                with open(filename, 'rb') as f:
                    data = f.read()
            if raw_size is None:
                raw_size = len(data.encode() if isinstance(data, str) else data)
            if not image and isinstance(data, bytes):
                data = text_prep.normalize(data.decode(), reduce_whitespace, unix_newline, fix_punct, remove_bom)  # Assumes raw text file is utf8. Otherwise, pass it as a data argument

            if verbose:
                size = os.path.getsize(filename)
                if label == 'base64_html':
                    no_overhead_size = size * 3 / 4
                stats = []
                if raw_size:
                    stats.append(f'ratio={round(size / raw_size * 100, 1)}%')
                if no_overhead_size:
                    stats.append(f'overhead={round((size/no_overhead_size-1) * 100, 1)}%')
                if ext == 'html' and label not in ['raw', 'base64_html']:
                    with open(filename, 'rb') as f:
                        html = f.read()
                        matches = regex.findall(webify.literals_regex.encode(), html)
                        payload = max(matches, key=len, default=b'').split(b'`', 1)[1].rsplit(b'`', 1)[0]
                        html = html.replace(payload, b'')
                    stats.append(f'code: {len(html):,} B = {round(len(html) / 1024, 1):,} kB')
                stats = ' '.join(stats)
                if stats:
                    stats = f' ({stats})'
                mb = size / 1024 ** 2
                if mb >= 0.1:
                    stats = f' = {round(mb, 1):,} MB{stats}'
                kb = size / 1024
                if kb >= 0.1:
                    stats = f' = {round(kb, 1):,} kB{stats}'
                print(f"{full_path(filename)} {size:,} B{stats}", end='' if validate and ext == 'html' and label != 'raw' else None, file=sys.stderr)

            if validate and ext == 'html' and label != 'raw':
                for i, browser in enumerate(browsers):
                    start_time = time()
                    valid = validate_html(filename, data, caps, by, element,
                                          raw, browser, timeout, unicode_A,
                                          ignore_regex, content_var, verbose)
                    assert valid is not False, filename
                    if not valid:
                        error = True
                    if verbose:
                        if i == 0:
                            print(f' rendering secs:', end='', file=sys.stderr)
                        print(f' {browser.name}=' + (f'{time() - start_time :.1f}' if valid else f'{timeout}(TIMEOUT)'), end='', file=sys.stderr)
                if verbose:
                    print(file=sys.stderr)
        if verbose and validate:
            print('Note: above rendering times from Selenium are much longer than actual browser rendering.', file=sys.stderr)
    return error
