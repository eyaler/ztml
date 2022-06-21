# ZTML

### Extreme inline text compression for HTML / JS
### By Eyal Gruss
#### https://eyalgruss.com

On-chain media storage may require efficient inline text compression for HTML / JS.
Here is a custom pipeline to generate stand-alone HTML or JS files, embedded with self-extracting text, and file sizes of ~50% the original.
The approach makes sense and is optimized for small texts, but performs well also on large texts.


|                                   | War and Peace (en) | Micromegas (en) | 
|-----------------------------------|--------------------|-----------------|
| Project Gutenberg plain text utf8 | 3.2 MB             | 63.7 kB         |
| ZTML (utf8 charset with Base125)  | 1.6 MB (50%)       | 35.0 kB (55%)   |
| ZTML (cp1252 charset with crEnc)  | 1.4 MB (44%)       | 31.3 kB (49%)   |

ZTML pipeline:

1. [Text normalization](ztml/text_utils.py) (irreversible; reduce whitespace, substitute unicode punctuation)
2. [Text condensation](ztml/text_utils.py) (reversible; lowercase with automatic capitalization*, substitute common strings as: the, qu)
3. [Huffman encoding](ztml/huffman.py) (with a [codebook-free decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes
), beneficial even as followed by DEFLATE)
4. [PNG / DEFLATE compression](ztml/deflate.py) (allowing [native decompression](https://web.archive.org/web/20090220141811/http://blog.nihilogic.dk/2008/05/compression-using-canvas-and-png.html
), aspect ratio optimized for minimal padding, [Zopfli optimization](https://github.com/google/zopfli))
5. [Binary to text encoding](https://en.wikipedia.org/wiki/Binary-to-text_encoding) embedded in JS template literals:
     1. [crEnc](ztml/crenc.py) encoding (a [yEnc](http://www.yenc.org) variant with 1.6% overhead, to be used with single-byte charset)
     2. [Base125](ztml/base125.py) encoding (a [Base122](https://blog.kevinalbs.com/base122) variant with 15% overhead, to be used with utf8 charset)
7. [Uglification](ztml/webify.py) of the generated JS (substitute recurring element, attribute and function names with short aliases)

*Automatic capitalization recovery is currently partial.

Note: If the decoding is mangled on Safari, this may be due to serving JS with gzip content encoding.
Upgrade to a modern browser, or try adding in the server's .htaccess:
```    
BrowserMatch Safari gzip-only-text/html
```
