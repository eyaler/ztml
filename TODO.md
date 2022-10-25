# Todo

### Usability
- Support encoding video/audio/fonts/PDF/...
- Support encoding multiple media elements
- Provide an easy way to view and edit output HTML in Colab
- Make into a PIP library and start doing versioning
- JS library?
- Expose more parameters and allow skipping steps in ztml() / CLI / Colab, possibly via config file
- Online web GUI

### Compression
- Ablation benchmarks
- Auto-caps should use modifiers for next letter/word/sentence/paragraph or block-level, over simple mode instead of falling back to raw
- Dictionary compression for long texts
- [Fast Huffman one-shift decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes)
- [Base139](https://github.com/kevinAlbs/Base122/issues/3#issuecomment-263787763)
- Compress the JS itself and use eval, considering also JS packing e.g. [JSCrush](http://iteral.com/jscrush), [RegPack](https://siorki.github.io/regPack), [Roadroller](https://lifthrasiir.github.io/roadroller)
- Benchmark [Roadroller](https://lifthrasiir.github.io/roadroller) entropy coding
- Strip whitespace from code lines not part of multi-line content strings (see e.g. above JS packers and [jsmin](http://www.crockford.com/jsmin.html), [miniMinifier](https://github.com/xem/miniMinifier), [UglifyJS](https://github.com/mishoo/UglifyJS))

  #### MTF:
- Improve JS MTF decoding times for large files
- Automatic optimizing over MTF variants
- Benchmark alternatives to MTF

  #### Deflate:
- Investigate effect of PNG aspect ratio on compression / optimize over it
- Integrate https://github.com/fhanau/Efficient-Compression-Tool (1.4% improvement on 2600.txt)
- Investigate Safari canvas size limits
- Allow using higher bit-depth to overcome canvas size limits (for larger content and maybe more compressible aspect ratios)
- Compress metadata into PNG 
- [Use WOFF2 as a Brotli container](https://github.com/lifthrasiir/roadroller/issues/9#issuecomment-905580540)

### Validation and testing
- Linux installation instructions / Enable validation in Colab
- Validation testing for Safari
- Fix slow rendering with Selenium in validation
- Tests for text_prep.py: normalize, caps, the; bwt_mtf.py: reorder
- Automatic testing on GitHub
