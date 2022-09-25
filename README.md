# ZTML

### Extreme inline text compression for HTML / JS
### By [Eyal Gruss](https://eyalgruss.com)

#### Partially made at [Stochastic Labs](http://stochasticlabs.org)

On-chain media storage can require efficient compression for text embedded inline in HTML / JS.
ZTML is a custom pipeline that generates stand-alone HTML or JS files which embed competitively compressed self-extracting text, with file sizes of 25% - 40% the original.
These file sizes include the decoder code which is ~ 1.5 kB (including auxiliary indices and tables).
The approach makes sense and is optimized for small texts, but performs quite well also on large texts.
The pipeline includes efficient alternatives to Base64 which are also useful for inline images.

|                                                                                            | File format   | [War and Peace (en)](https://gutenberg.org/files/2600/2600-0.txt) | [Micromegas (en)](https://gutenberg.org/files/30123/30123-8.txt) |
|--------------------------------------------------------------------------------------------|---------------|-------------------------------------------------------------------|------------------------------------------------------------------|
| Project Gutenberg plain text utf8                                                          | txt           | 3.2 MB                                                            | 63.7 kB                                                          |
| [paq8px_v206fix1](http://www.mattmahoney.net/dc/text.html#1250) -12LRT (excluding decoder) | paq           | 575 kB (18%)                                                      | 13.3 kB (21%)                                                    |
| 7-Zip 22.01 9 Ultra PPMd (excluding decoder)                                               | 7z            | 746 kB (23%)                                                      | 20.8 kB (32%)                                                    |
| 7-Zip 22.01 9 Ultra PPMd (self extracting)                                                 | exe           | 958 kB (29%)                                                      | 232 kB (364%)                                                    |
| [Roadroller](https://github.com/lifthrasiir/roadroller) 2.1.0 -O2                          | js            | 1.0 MB (30%)                                                      | 26.5 kB (42%)                                                    |
| **ZTML Base125**                                                                           | html (utf8)   | 916 kB (28%) `mtf=80`                                             | 26.5 kB (42%) `mtf=0`                                            |
| **ZTML crEnc**                                                                             | html (cp1252) | 818 kB (25%) `mtf=80`                                             | 23.8 kB (37%) `mtf=0`                                            |

### Usage
A standard simplified pipeline can be run by calling `ztml()` or running `python ztml.py` from the command line. See [ztml.py](ztml/ztml.py).

[crEnc](ztml/crenc.py) gives better compression but requires setting the HTML or JS charset to cp1252. [Base125](ztml/base125.py) is the second-best option if one must stick with utf8. 

See [example.py](example.py) for a complete example reproducing the above benchmark.

### Caveats:
1. Files larger than a few MB might not work on [iOS Safari](https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit) or [macOS Safari 15](https://bugs.webkit.org/show_bug.cgi?id=230855).
2. This solution favors compression rate over compression and decompression times. Use `mtf=None` for faster decompression of large files.
3. For [compressing word lists](http://golf.horse) (sorted lexicographically), solutions as [Roadroller](https://lifthrasiir.github.io/roadroller) do a much better job.

### ZTML pipeline breakdown:
1. [Text normalization](ztml/text_prep.py) (irreversible; reduce whitespace, substitute unicode punctuation)
2. [Text condensation](ztml/text_prep.py) (reversible; lowercase with automatic capitalization, substitute common strings as: the, qu)
3. [Burrows–Wheeler + Move-to-front transforms](ztml/bwt_mtf.py) on text with some optional variants, including some new ones (beneficial for large texts)
4. [Huffman encoding](ztml/huffman.py) (with a [codebook-free decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes), beneficial even as followed by DEFLATE)
5. [Burrows–Wheeler transform](ztml/bwt_mtf.py) on bits (beneficial for large texts)
6. [PNG / DEFLATE compression](ztml/deflate.py) (allowing [native decompression](https://web.archive.org/web/20090220141811/http://blog.nihilogic.dk/2008/05/compression-using-canvas-and-png.html
), aspect ratio optimized for minimal padding, [Zopfli optimization](https://github.com/google/zopfli))
7. [Binary to text encoding](https://en.wikipedia.org/wiki/Binary-to-text_encoding) embedded in JS template literals:
     1. [crEnc](ztml/crenc.py) encoding (a [yEnc](http://www.yenc.org) variant with 1.6% overhead, to be used with single-byte charset)
     2. [Base125](ztml/base125.py) encoding (a [Base122](https://blog.kevinalbs.com/base122) variant with 15% overhead, to be used with utf8 charset)
8. [Uglification](ztml/webify.py) of the generated JS (substitute recurring element, attribute and function names with short aliases)

### Projects using this:
- [fragium](https://fragium.com)
- [miniBook](https://xem.github.io/miniBook) submission by Eyal Gruss
