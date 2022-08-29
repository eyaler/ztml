import os
from time import time

start_time = time()

from ztml import validation, ztml


books = 30123, 2600
mtf_variants = 0, 80
output_folder = 'output'


for book, mtf in zip(books, mtf_variants):
    book_start_time = time()
    filenames = dict(text=f'{book}.txt',
                     base64_js=f'{book}_64.js',
                     base64_html=f'{book}_64.html',
                     base125_js=f'{book}_125.js',
                     base125_html=f'{book}_125.html',
                     crenc_js=f'{book}_cr.js',
                     crenc_html=f'{book}_cr.html')
    os.makedirs(output_folder, exist_ok=True)
    filenames = {k: os.path.join(output_folder, v) for k, v in filenames.items()}

    # If missing, download an example text file from the web
    if not os.path.exists(filenames['text']):
        from gutenberg.acquire.text import load_etext
        with open(filenames['text'], 'wb') as f:
            f.write(load_etext(book).encode())

    with open(filenames['text'], 'rb') as f:
        text = f.read().decode()

    for label, filename in filenames.items():
        ext = os.path.splitext(filename)[-1][1:]
        if ext not in ['js', 'html']:
            continue
        file = ztml.ztml(text, filename, mtf=mtf, bin2txt=label.split('_', 1)[0])

    print(f'All encodings of {book} took {(time()-book_start_time) / 60 :.1f} min.')

    # Compare file sizes and validate text is recovered
    validation.validate_files(filenames, compare_caps=False)
    print()

print(f'Total took {(time()-start_time) / 60 :.1f} min.')
