# Todo


### Usability

[ ] Example for image compression use case

[ ] Provide pure JS libs where relevant

[ ] Online GUI


### Encoding / Compression

[ ] Add a respect-caps mode using a next-letter-invert-caps-symbol (either on top of the auto-caps when that is viable or forced, or stand-alone)

[ ] Consider dictionary compression for long texts

[ ] [Fast Huffman one-shift decoder](https://researchgate.net/publication/3159499_On_the_implementation_of_minimum_redundancy_prefix_codes)

[ ] Save Huffman metadata in image? Maybe in image metadata?

[ ] [Base139](https://github.com/kevinAlbs/Base122/issues/3#issuecomment-263787763)?

[ ] Compress the JS itself and use eval?


### Minification

[ ] Factor out all minification to a post process

[ ] Strip whitespace on lines not part of content strings

[ ] Explicitly skip aliasification for string literals
