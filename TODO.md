# Todo


### Usability

[ ] **Example for Base125 / crEnc inline image encoding use case**

[ ] Make into a PIP library and start doing versioning

[ ] Expose more parameters and allow skipping steps in CLI / ztml(), via arguments or config file

[ ] Provide pure JS libraries where relevant

[ ] Online GUI

[ ] Validation testing for Safari

[ ] Fix slow rendering with Selenium in validation

### Compression

[ ] **Ablation benchmarks**

[ ] **Auto-caps should use modifiers for next letter/word/sentence/paragraph or block-level, over simple mode instead of falling back to raw**

[ ] Dictionary compression for long texts

[ ] [Fast Huffman one-shift decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes)

[ ] [Base139](https://github.com/kevinAlbs/Base122/issues/3#issuecomment-263787763)

[ ] Compress the JS itself and use eval, considering also js packing e.g. [JSCrush](https://iteral.com/jscrush), [RegPack](https://siorki.github.io/regPack), [Roadroller](https://lifthrasiir.github.io/roadroller) 

[ ] Benchmark [Roadroller](https://lifthrasiir.github.io/roadroller) entropy coder

[ ] Strip whitespace from script lines not part of multi-line content strings

#### MTF

[ ] Improve JS MTF decoding times for large files

[ ] Automatic optimizing over MTF variants

[ ] Benchmark alternatives to MTF 

[ ] Run length encoding after MTF

#### Deflate

[ ] **Investigate effect of PNG aspect ratio on compression / optimize over it**

[ ] Integrate https://github.com/fhanau/Efficient-Compression-Tool (1.4% improvement on 2600.txt)

[ ] Investigate Safari canvas size limits

[ ] Compress metadata into PNG 

[ ] [Use WOFF2 as a Brotli container](https://github.com/lifthrasiir/roadroller/issues/9#issuecomment-905580540)
