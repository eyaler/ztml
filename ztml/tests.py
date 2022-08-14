import os
import sys
from time import time

start_time = time()

if not __package__:
    import bwt_mtf, validation, webify, ztml
else:
    from . import bwt_mtf, validation, webify, ztml


min_char_code = 0
max_char_code = 10000
browsers = list(validation.drivers)[:1]
input_encodings = ['utf8', 'cp1252', 'cp1255']
bin2txt_encodings = ztml.bin2txt_encodings
mtf_variants = [None, 0, 52, 80]  # bwt_mtf.mtf_variants
temp_folder = 'tmp'
cleanup = True


max_unicode = 1114111
text = ''.join(chr(i) for i in range(min_char_code, min(max_char_code or max_unicode, max_unicode) + 1) if (i < 55296 or i > 57343))
os.makedirs(temp_folder, exist_ok=True)
i = 0
for browser in browsers:
    with validation.get_browser(browser) as b:
        for encoding in input_encodings:
            encoding = encoding.lower().replace('-', '')
            for bin2txt in bin2txt_encodings:
                for mtf in mtf_variants:
                    i += 1
                    print(f'{i}/{len(browsers) * len(input_encodings) * len(ztml.bin2txt_encodings) * len(mtf_variants)} browser={browser} input_enc={encoding} bin2txt={bin2txt} mtf={mtf}')
                    input_filename = os.path.join(temp_folder, f'ztml_test_file_{encoding}_{bin2txt}_{mtf}.txt')
                    output_filename = os.path.join(temp_folder, f'ztml_test_file_{encoding}_{bin2txt}_{mtf}.html')
                    output_stream = os.path.join(temp_folder, f'ztml_test_stream_{encoding}_{bin2txt}_{mtf}.html')
                    with open(input_filename, 'wb') as f:
                        f.write(webify.safe_encode(text, encoding))
                    if encoding == 'utf8':
                        out1, result1 = ztml.ztml(text, mtf=mtf, bin2txt=bin2txt, validate=True, compare_caps=False, browser=b, verbose=True)
                        out2, result2 = ztml.ztml(text, output_filename, mtf=mtf, bin2txt=bin2txt, validate=True, compare_caps=False, browser=b, verbose=True)
                        with open(output_filename, 'rb') as f:
                            out = f.read()
                        assert not result1 and not result2 and out1 == out2 == out, (result1, result2, len(out1), len(out2), validation.full_path(output_filename), len(out))
                    result1 = os.system(f'python ztml.py "{input_filename}" "{output_filename}" --mtf {mtf} --bin2txt {bin2txt} --validate --skip_compare_caps --browser {browser} --verbose')
                    result2 = os.system(f'python ztml.py "{input_filename}" --mtf {mtf} --bin2txt {bin2txt} --validate --skip_compare_caps --browser {browser} --verbose > {output_stream}')
                    with open(output_filename, 'rb') as f1:
                        out1 = f1.read()
                    with open(output_stream, 'rb') as f2:
                        out2 = f2.read()
                    assert not out2.endswith(b'\x1b[0m'), 'If running from PyCharm: enable Run -> Edit configurations -> tests -> Emulate terminal in output console'
                    assert not result1 and not result2 and out1 == out2, (result1, result2, validation.full_path(output_filename), len(out1), validation.full_path(output_stream), len(out2))
                    if cleanup:
                        for filename in [input_filename, output_filename, output_stream]:
                            try:
                                os.remove(filename)
                            except PermissionError:
                                pass
                    print()
if cleanup:
    try:
        os.rmdir(temp_folder)
    except OSError:
        pass
print(f'Total took {(time()-start_time) / 60 :.1f} min.', file=sys.stderr)
