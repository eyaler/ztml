# This is just for testing that ZTML can work on its own HTML outputs in raw mode


import os
import sys
from time import time

start_time = time()

sys.path.append('..')
from ztml import validation, ztml


raw_files = ['30123_64.html',
             '30123_125.html',
             '30123_cr.html',
             'test_pattern.jpg_64.html',
             'test_pattern.jpg_125.html',
             'test_pattern.jpg_cr.html'
             ]
output_folder = '../output'


error = False
for url in raw_files:
    item_start_time = time()
    item = url.replace(os.sep, '/').rsplit('/', 1)[-1]
    filenames = dict(raw=item,
                     # base64_js=f'{item}_64.js',
                     base64_html=f'{item}_64.html',
                     # base125_js=f'{item}_125.js',
                     base125_html=f'{item}_125.html',
                     # crenc_js=f'{item}_cr.js',
                     crenc_html=f'{item}_cr.html')
    os.makedirs(output_folder, exist_ok=True)
    filenames = {k: os.path.join(output_folder, v) for k, v in filenames.items()}

    with open(filenames['raw'], 'rb') as f:
        data = f.read()
    if os.path.splitext(item)[0].endswith('_cr'):
        data = data.decode('cp1252', 'backslashreplace')

    cnt = 0
    for label, filename in filenames.items():
        if label == 'raw':
            continue
        file = ztml.ztml(data, filename, bin2txt=label.rsplit('_', 1)[0], raw=True, text_var='z')
        cnt += 1

    print(f'{cnt} encodings of {item} took {(time()-item_start_time) / 60 :.1f} min.')

    # Compare file sizes and validate data is recovered
    error |= validation.validate_files(filenames, data, raw=True, content_var='z')
    print()

if error:
    print('Error: some renderings timed out')
else:
    print(f'Total of {len(raw_files)} raw files took {(time()-start_time) / 60 :.1f} min.')
sys.exit(int(error))
