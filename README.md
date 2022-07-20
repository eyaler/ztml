# ZTML

### Extreme inline text compression for HTML / JS
### By [Eyal Gruss](https://eyalgruss.com)

On-chain media storage may require efficient inline text compression for HTML / JS.
Here is a custom pipeline to generate stand-alone HTML or JS files, embedding self-extracting text, and having file sizes of 25% - 40% the original.
These file sizes include the decoder code which is less than 1.6 kB.
The approach makes sense and is optimized for small texts, but performs quite well also on large texts.

|                                        | File format | [War and Peace (en)](https://gutenberg.org/files/2600/2600-0.txt) | [Micromegas (en)](https://gutenberg.org/files/30123/30123-8.txt) |
|----------------------------------------|-------------|-------------------------------------------------------------------|------------------------------------------------------------------|
| Project Gutenberg plain text utf8      | txt         | 3.2 MB                                                            | 63.7 kB                                                          |
| 7-Zip 9 Ultra PPMd (excluding decoder) | 7z          | 746 kB (23%)                                                      | 20.8 kB (32%)                                                    |
| 7-Zip 9 Ultra PPMd (self extracting)   | exe         | 958 kB (29%)                                                      | 232 kB (364%)                                                    |
| ZTML Base125 (no normalization)        | html        | 939 kB (29%)                                                      | 26.0 kB (41%)                                                    |
| ZTML crEnc (no normalization)          | html        | 838 kB (26%)                                                      | 23.3 kB (37%)                                                    |

### Usage
The standard simplified pipeline can be run by calling `generate()` or running `python ztml.py` from the command line. See [ztml.py](ztml/ztml.py).

[crEnc](ztml/crenc.py) gives better compression but requires setting the HTML or JS charset to cp1252. [Base125](ztml/base125.py) is the second best option if one must stick with utf8. 

See [example.py](example.py) for a complete example reproducing the above benchmark.

Note: files larger than a few MB might not work on [iOS Safari](https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit) or [macOS Safary 15](https://bugs.webkit.org/show_bug.cgi?id=230855)

### ZTML [pipeline](ztml/ztml.py):
1. [Text normalization](ztml/text_utils.py) (irreversible; reduce whitespace, substitute unicode punctuation)
2. [Text condensation](ztml/text_utils.py) (reversible; lowercase with automatic capitalization*, substitute common strings as: the, qu)
3. [Burrows–Wheeler + Move-to-front transforms](ztml/bwt_mtf.py) on text
4. [Huffman encoding](ztml/huffman.py) (with a [codebook-free decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes), beneficial even as followed by DEFLATE)
5. [Burrows–Wheeler transform](ztml/bwt_mtf.py) on bits (beneficial for large files)
6. [PNG / DEFLATE compression](ztml/deflate.py) (allowing [native decompression](https://web.archive.org/web/20090220141811/http://blog.nihilogic.dk/2008/05/compression-using-canvas-and-png.html
), aspect ratio optimized for minimal padding, [Zopfli optimization](https://github.com/google/zopfli))
7. [Binary to text encoding](https://en.wikipedia.org/wiki/Binary-to-text_encoding) embedded in JS template literals:
     1. [crEnc](ztml/crenc.py) encoding (a [yEnc](http://www.yenc.org) variant with 1.6% overhead, to be used with single-byte charset)
     2. [Base125](ztml/base125.py) encoding (a [Base122](https://blog.kevinalbs.com/base122) variant with 15% overhead, to be used with utf8 charset)
8. [Uglification](ztml/webify.py) of the generated JS (substitute recurring element, attribute and function names with short aliases)

*Automatic capitalization recovery is currently partial.
