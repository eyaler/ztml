# https://xem.github.io/miniBook


from urllib.request import urlopen

from ztml.ztml import ztml


with urlopen('https://xem.github.io/miniBook/example') as f:
    out, result = ztml.ztml(f.read(), f'index.html', mtf=80, raw=True, validate=True)
    print(f'{len(out):,} B')
    assert not result
