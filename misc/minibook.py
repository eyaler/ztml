# https://xem.github.io/miniBook


import sys
from urllib.request import urlopen

sys.path.append('..')
from ztml import ztml


with urlopen('https://xem.github.io/miniBook/example') as f:
    out, result = ztml.ztml(f.read(), 'index.html', mtf=80, raw=True, validate=True)
    print(f'{len(out):,} B')
    assert not result
