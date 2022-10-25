import os
from time import time
from urllib.request import urlopen

start_time = time()

from ztml import validation, ztml


image_urls = ['http://wiesmann.codiferes.net/share/bitmaps/test_pattern.bmp',
              'http://wiesmann.codiferes.net/share/bitmaps/test_pattern.gif',
              'http://wiesmann.codiferes.net/share/bitmaps/test_pattern.jpg',
              'http://wiesmann.codiferes.net/share/bitmaps/test_pattern.png',
              'http://wiesmann.codiferes.net/share/bitmaps/test_pattern.webp'
              ]
output_folder = 'output'
skip_download_exists = True
element_id = ''


error = False
for url in image_urls:
    item_start_time = time()
    item = url.rsplit('/', 1)[-1]
    filenames = dict(raw=item,
                     # base64_js=f'{item}_64.js',
                     base64_html=f'{item}_64.html',
                     # base125_js=f'{item}_125.js',
                     base125_html=f'{item}_125.html',
                     # crenc_js=f'{item}_cr.js',
                     crenc_html=f'{item}_cr.html')
    os.makedirs(output_folder, exist_ok=True)
    filenames = {k: os.path.join(output_folder, v) for k, v in filenames.items()}

    # If missing, download an example file from the web
    if not skip_download_exists or not os.path.exists(filenames['raw']):
        with urlopen(url) as fin, open(filenames['raw'], 'wb') as fout:
            fout.write(fin.read())

    with open(filenames['raw'], 'rb') as f:
        data = f.read()

    cnt = 0
    for label, filename in filenames.items():
        if label == 'raw':
            continue
        file = ztml.ztml(data, filename, bin2txt=label.rsplit('_', 1)[0], element_id=element_id, image=True)
        cnt += 1

    print(f'{cnt} encodings of {item} took {(time()-item_start_time) / 60 :.1f} min.')

    # Compare file sizes and validate data is recovered
    error |= validation.validate_files(filenames, by='id' * bool(element_id), element=element_id, image=True)
    print()

if error:
    print('Error: some renderings timed out')
else:
    print(f'Total of {len(image_urls)} images took {(time()-start_time) / 60 :.1f} min.')
