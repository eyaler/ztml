# Todo

### Usability
- Support encoding video/audio/fonts/PDF/...
- Support encoding multiple media elements
- Provide an easy way to view and edit output HTML in Colab
- Make into a PIP library and start doing versioning
- JS library?
- Expose more parameters and allow skipping steps in ztml() / CLI / Colab, possibly via config file
- Stand-alone online web GUI
- Stand-alone executable (+ script to build it)

### Compression
- Ablation benchmarks
- Launch a challenge for smaller decoders

- #### Entropy coding:
- Auto-caps should use modifiers for next letter/word/sentence/paragraph or block-level, over simple mode instead of falling back to raw. See e.g. [Grabowski](https://www.researchgate.net/profile/Szymon-Grabowski-2/publication/258239689_Text_Preprocessing_for_Burrows-Wheeler_Block_Sorting_Compression/links/0046352789a298f289000000), [Batista&Alexandre](https://www.di.ubi.pt/~lfbaa/pubs/dcc2008.pdf)
- Dictionary compression for large texts + add references
- [Fast Huffman one-shift decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes), and follow-up works: [Gagie et al.](https://arxiv.org/pdf/1410.3438.pdf), [Grabowski&Koppl](https://arxiv.org/pdf/2108.05495.pdf)
- Consider [Roadroller](https://lifthrasiir.github.io/roadroller) entropy coder

  #### MTF:
- Improve JS MTF decoding times for large files
- Automatic optimizing over MTF variants
- Benchmark alternatives to MTF + add references

  #### Deflate:
- Investigate effect of PNG aspect ratio on compression / optimize over it
- Investigate Safari canvas size limits
- Use 8/24-bit to overcome canvas size limits when necessary (will not work on Safari, unless we go WebGL)
- Compress metadata into PNG 
- [Use WOFF2 as a Brotli container](https://github.com/lifthrasiir/roadroller/issues/9#issuecomment-905580540)

  #### Webification and minification:
- [Base139](https://github.com/kevinAlbs/Base122/issues/3#issuecomment-263787763)
- Compress the JS itself and use [eval](http://perfectionkills.com/global-eval-what-are-the-options), considering also JS packing e.g. [JSCrush](http://iteral.com/jscrush), [JS Crusher](https://jmperezperez.com/js-crusher), [RegPack](https://siorki.github.io/regPack), [Roadroller](https://lifthrasiir.github.io/roadroller)
- Strip whitespace from code lines not part of multi-line content strings (see e.g. above JS packers and [closure-compiler](https://github.com/google/closure-compiler), [jsmin](https://crockford.com/jsmin), [miniMinifier](https://github.com/xem/miniMinifier), [Terser](https://terser.org), [UglifyJS](https://github.com/mishoo/UglifyJS))

### Validation and testing
- Linux installation instructions / Enable validation in Colab
- Validation testing for Safari
- Fix slow rendering with Selenium in validation
- Tests for text_prep.py: normalize, caps, the
- Automatic testing on GitHub
