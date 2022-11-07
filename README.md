<a href="https://colab.research.google.com/github/eyaler/ztml/blob/main/ZTML.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# ZTML

### Extreme inline text compression for HTML / JS
### By [Eyal Gruss](https://eyalgruss.com) ([@eyaler](https://twitter.com/eyaler))

#### Partially made at [Stochastic Labs](http://stochasticlabs.org)

On-chain media storage can require efficient compression for text embedded inline in HTML / JS.
ZTML is a custom pipeline that generates stand-alone HTML or JS files which embed competitively compressed self-extracting text, with file sizes of 25% - 40% the original.
These file sizes include the decoder code which is a highly golfed 1 - 1.5 kB (including auxiliary indices and tables).
The approach makes sense and is optimized for small texts (tens of kB), but performs quite well also on large texts.
The pipeline includes low-overhead [binary-to-text alternatives](https://en.wikipedia.org/wiki/Binary-to-text_encoding) to Base64 which are also useful for inline images.
You can find a very high-level overview in these [slides](misc/reversim2022_slides.pdf) from [Reversim Summit 2022](https://summit2022.reversim.com).

### Benchmark
|                                                                                       | File format   | [Micromegas (En)](https://gutenberg.org/files/30123/30123-8.txt) | [War and Peace (En)](https://gutenberg.org/files/2600/2600-0.txt) |
|---------------------------------------------------------------------------------------|---------------|------------------------------------------------------------------|-------------------------------------------------------------------|
| Project Gutenberg plain text utf8                                                     | txt           | 63.7 kB                                                          | 3.2 MB                                                            |
| [paq8px_v206fix1](http://www.mattmahoney.net/dc/text.html#1250) -12RT (excl. decoder) | paq           | 13.3 kB (21%)                                                    | 575 kB (18%)                                                      |
| 7-Zip 22.01 9 Ultra PPMd (excl. decoder)                                              | 7z            | 20.8 kB (32%)                                                    | 746 kB (23%)                                                      |
| 7-Zip 22.01 9 Ultra PPMd (self-extracting)                                            | exe           | 232 kB (364%)                                                    | 958 kB (29%)                                                      |
| Zstandard 1.5.2 -22 --ultra (excl. decoder)                                           | zst           | 23.4 kB (37%)                                                    | 921 kB (28%)                                                      |
| [Roadroller](https://github.com/lifthrasiir/roadroller) 2.1.0 -O2                     | js            | 26.5 kB (42%)                                                    | 1.0 MB (30%)                                                      |
| **ZTML Base125**                                                                      | html (utf8)   | 26.4 kB (41%) `mtf=0`                                            | 902 kB (28%) `mtf=80` `ect=True`                                  |
| **ZTML crEnc**                                                                        | html (cp1252) | 23.5 kB (37%) `mtf=0`                                            | 803 kB (24%) `mtf=80` `ect=True`                                  |

### Installation
```
git clone https://github.com/eyaler/ztml
pip install -r ztml/requirements.txt
```
For running validations, you also need to have Chrome, Edge and Firefox installed.

### Usage
A standard simplified pipeline can be run by calling `ztml()` or running `python ztml.py` from the command line (CLI). See [ztml.py](ztml/ztml.py).
Of course, there is also an accessible [Google Colab](https://colab.research.google.com/github/eyaler/ztml/blob/main/ztml.ipynb) with a simple GUI. Shortcut: [bit.ly/ztml1](https://bit.ly/ztml).

[crEnc](ztml/crenc.py) gives better compression but requires setting the HTML or JS charset to cp1252.
[Base125](ztml/base125.py) is the second-best option if one must stick with utf8. 

See [example.py](example.py) for a complete example reproducing the ZTML results in the above benchmark,
and [example_image.py](example_image.py) for an example of encoding inline images, by using `image=True` or passing a file with a supported image extension to the CLI.
Outputs of these runs can be accessed at [eyalgruss.com/ztml](https://eyalgruss.com/ztml).
On top of the built-in validations for Chrome, Edge and Firefox, these were also manually tested on macOS Monterey 12.5 Safari 15.6 and iOS 16.0 Safari.

A quick and dirty way to compress an existing single-page HTML websites with embedded inline media is to use `raw=True` or pass a '.html' file to the CLI.

### What this is not
1. Not an HTML inliner
2. Not an image optimizer
3. Not a full-fledged JS minifier 

### Caveats
1. Files larger than a few MB might not work on [iOS Safari](https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit) or [macOS Safari 15](https://bugs.webkit.org/show_bug.cgi?id=230855).
2. This solution favors compression rate over compression and decompression times. Use `mtf=None` for faster decompression of large files.
3. For [compressing word lists](http://golf.horse) (sorted lexicographically), solutions as [Roadroller](https://lifthrasiir.github.io/roadroller) do a much better job.

### Pipeline and source code breakdown
|     | Stage                                      | Source                              | Remarks                                                                                                                                                                                                                                               |
|-----|--------------------------------------------|-------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0   | Pipeline and CLI                           | [ztml.py](ztml/ztml.py)             |                                                                                                                                                                                                                                                       |
| 1   | Text normalization (lossy)                 | [text_prep.py](ztml/text_prep.py)   | Reduce whitespace; substitute unicode punctuation                                                                                                                                                                                                     |
| 2   | Text condensation (lossless)               | [text_prep.py](ztml/text_prep.py)   | Lowercase with automatic capitalization; substitute common strings as: the, qu                                                                                                                                                                        |
| 3   | Burrows–Wheeler + Move-to-front transforms | [bwt_mtf.py](ztml/bwt_mtf.py)       | Alphabet pre-sorting; Various MTF variants, including some new ones; Higher MTF settings beneficial for larger texts                                                                                                                                  |
| 4   | Huffman encoding                           | [huffman.py](ztml/huffman.py)       | Canonical encoding with a [codebook-free decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes); Benefical as a pre-DEFLATE stage                                                            |
| 5   | Burrows–Wheeler transform on bits          | [bwt_mtf.py](ztml/bwt_mtf.py)       | Beneficial for large texts                                                                                                                                                                                                                            |
| 6   | PNG / DEFLATE compression                  | [deflate.py](ztml/deflate.py)       | ZIP-like compression with native browser decompression; aspect ratio optimized for maximal compatibility and minimal padding; [Zopfli](https://github.com/google/zopfli) or [ECT](https://github.com/fhanau/Efficient-Compression-Tool) optimizations |
| 7   | Binary-to-text encoding                    |                                     | Embed in template strings; Fix [HTML character overrides](https://html.spec.whatwg.org/multipage/parsing.html#table-charref-overrides); Allow [dynEncode](https://github.com/eshaz/simple-yenc#what-is-dynencode)-like optimal offset                 |
| 7a  | Base125 (utf8)                             | [base125.py](ztml/base125.py)       | A [Base122](https://blog.kevinalbs.com/base122) variant, with 14.7% overhead                                                                                                                                                                          |
| 7b  | crEnc (cp1252)                             | [crenc.py](ztml/crenc.py)           | A [yEnc](http://www.yenc.org) variant with 1.2% overhead; requires single-byte charset                                                                                                                                                                |
| 8   | Uglification                               | [webify.py](ztml/webify.py)         | Substitute recurring JS names with short aliases                                                                                                                                                                                                      |
| 9   | Validation                                 | [validation.py](ztml/validation.py) | Reproduce input content on Chrome, Edge and Firefox                                                                                                                                                                                                   |

Note: image encoding only uses steps 0 and 7 and later.

See source files for explanations, experiments and more references.

### Projects using this
- [fragium](https://fragium.com)
- [miniBook](https://xem.github.io/miniBook) submission by Eyal Gruss ([source code](misc/minibook.py))
- [WEBZOS](https://wbtz.github.io)
