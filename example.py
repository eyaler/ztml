import os
import sys
from time import time

start_time = time()

from ztml import validation, ztml


books = [30123, 2600]
book_mtf = [0, 80]
book_ect = [False, True]
output_folder = 'output'
skip_download_exists = True
element_id = ''


assert len(books) == len(book_mtf) == len(book_ect)
error = False
for item, mtf, ect in zip(books, book_mtf, book_ect):
    item_start_time = time()
    filenames = dict(raw=f'{item}.txt',
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
        from gutenberg.acquire.text import load_etext
        with open(filenames['raw'], 'wb') as f:
            f.write(load_etext(item).encode())

    with open(filenames['raw'], 'rb') as f:
        data = f.read()

    cnt = 0
    for label, filename in filenames.items():
        if label == 'raw':
            continue
        file = ztml.ztml(data, filename, mtf=mtf, ect=ect, bin2txt=label.rsplit('_', 1)[0], element_id=element_id)
        cnt += 1

    print(f'{cnt} encodings of {item} took {(time()-item_start_time) / 60 :.1f} min.')

    # Compare file sizes and validate data is recovered
    error |= validation.validate_files(filenames, by='id' * bool(element_id), element=element_id)
    print()

if error:
    print('Error: some renderings timed out')
else:
    print(f'Total of {len(books)} books took {(time()-start_time) / 60 :.1f} min.')
sys.exit(int(error))
