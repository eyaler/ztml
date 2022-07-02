from base64 import b64encode
import os
from time import time

from ztml import base125, crenc, deflate, huffman, webify, text_utils, validate


filenames = dict(text='example.txt',
                 base64_html='example64.html',
                 base125_html='example125.html',
                 crenc_html='example_cr.html')
output_folder = 'output'


start_time = time()

os.makedirs(output_folder, exist_ok=True)
filenames = {k: os.path.join(output_folder, v) for k, v in filenames.items()}

# If missing, download an example text file from the web
if not os.path.exists(filenames['text']):
    from gutenberg.acquire.text import load_etext
    with open(filenames['text'], 'wb') as f:
        f.write(load_etext(2600).encode())

with open(filenames['text'], 'rb') as f:
    text = f.read().decode()

text = text_utils.normalize(text)  # reduce whitespace
condensed, string_decoder = text_utils.encode_and_get_js_decoder(text)  # lower case and shorten common strings
bits, huffman_decoder = huffman.encode_and_get_js_decoder(condensed)  # huffman encode
zop_data = deflate.to_png(bits)  # PNG encode
render = huffman_decoder + string_decoder + "document.body.style.whiteSpace='pre';document.body.textContent=t"

# create minified html using base64 encoding
base64_image = b"i=new Image;i.src='data:image/png;base64," + b64encode(zop_data) + b"'\n"
base64_js = base64_image + deflate.get_js_image_data(render).encode()
with open(filenames['base64_html'], 'wb') as f:
    f.write(webify.html_wrap(base64_js))

image_decoder = deflate.get_js_image_decoder(render).encode()

# create minified html using base125 encoding
base125_js = base125.get_js_decoder(zop_data) + image_decoder
with open(filenames['base125_html'], 'wb') as f:
    f.write(webify.html_wrap(base125_js))

# create minified html using crEnc encoding
crenc_js = crenc.get_js_decoder(zop_data) + image_decoder
with open(filenames['crenc_html'], 'wb') as f:
    f.write(webify.html_wrap(crenc_js, encoding='cp1252'))

# compare file sizes and validate text is recovered
validate.validate_files(filenames, compare_caps=False)

print(f'took {(time()-start_time) / 60 :.1f} min.')
