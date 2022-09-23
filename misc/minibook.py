# https://xem.github.io/miniBook


from urllib.request import urlopen

from ztml.ztml import ztml


with urlopen('https://xem.github.io/miniBook/example') as f:
    out, result = ztml.ztml(f.read(), f'minibook.html', mtf=80, raw=True, validate=True, ignore_regex='</xmp>')
    print(f'{len(out):,} B')
    assert not result
