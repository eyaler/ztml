# Todo


### Usability

[ ] Better support and benchmarks for non-English texts

[ ] Example for image compression use case

[ ] Provide pure JS libs where relevant

[ ] Online GUI


### Encoding / Compression

[ ] Add a respect-caps mode using a next-letter-invert-caps-symbol (either on top of the auto-caps when that is viable or forced, or stand-alone)

[ ] Consider dictionary compression for long texts

[ ] [Fast Huffman one-shift decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes)

[ ] Save Huffman metadata in image? Maybe in image metadata?

[ ] [dynEncode](https://github.com/eshaz/simple-yenc/pull/3)-like offset to minimize CR and template literal escapes (for crEnc, and for Base125 for which we can consider shifts of different kinds)

[ ] [Base139](https://github.com/kevinAlbs/Base122/issues/3#issuecomment-263787763)?

[ ] Compress the JS itself and use eval?


### Minification

[ ] Factor out all minifications to a dedicated post process

[ ] Strip whitespace from lines not part of content strings

[ ] Explicitly skip uglification for template literals
