import os
from time import time

start_time = time()

if not __package__:
    import text_prep, bwt_mtf, validation, webify, ztml
else:
    from . import text_prep, bwt_mtf, validation, webify, ztml


max_unicode = 1114111
min_char_code1 = 0
max_char_code1 = 14000
min_char_code2 = 55000
max_char_code2 = 66000
browsers = list(validation.drivers)[:1]
input_encodings = ['utf8', 'cp1252', 'cp1255']
bin2txt_encodings = ztml.bin2txt_encodings
caps_modes = ['auto']  # text_prep.caps_modes
mtf_variants = [None, 0, 52, 80]  # bwt_mtf.mtf_variants
temp_folder = 'tmp'
cleanup = True


all_chars = ''.join(chr(i) for i in range(min_char_code1, min(max_char_code1 or max_unicode, max_unicode) + 1))
if min_char_code2 is not None and max_char_code2 is not None:
    all_chars += ''.join(chr(i) for i in range(min_char_code2, min(max_char_code2 or max_unicode, max_unicode) + 1) if chr(i) not in all_chars)
os.makedirs(temp_folder, exist_ok=True)
i = 0
for browser in browsers:
    with validation.get_browser(browser) as b:
        for encoding in input_encodings:
            encoding = encoding.lower().replace('-', '')
            for bin2txt in bin2txt_encodings:
                for caps in caps_modes:
                    for mtf in mtf_variants:
                        for raw in [False, True]:
                            test_time = time()
                            i += 1
                            print(f'{i}/{len(browsers) * len(input_encodings) * len(ztml.bin2txt_encodings) * len(caps_modes) * len(mtf_variants) * 2} browser={browser} input_enc={encoding} bin2txt={bin2txt} caps={caps} mtf={mtf} raw={raw}')
                            suffix = f'{browser}_{encoding}_{bin2txt}_{caps}_{mtf}'
                            if raw:
                                suffix += '_raw'
                            input_filename = os.path.join(temp_folder, f'ztml_test_file_{suffix}.txt')
                            output_filename = os.path.join(temp_folder, f'ztml_test_file_{suffix}.html')
                            output_stream = os.path.join(temp_folder, f'ztml_test_stream_{suffix}.html')
                            text = all_chars
                            if encoding == 'utf8':
                                text = ''.join(c for c in text if ord(c) < bwt_mtf.surrogate_lo or ord(c) > bwt_mtf.surrogate_hi)
                            if raw:
                                text = ''.join(c for c in text if c not in ['\0', '\r'])
                            if mtf is not None:
                                text = ''.join(c for c in text if ord(c) < max_unicode - (bwt_mtf.surrogate_hi-bwt_mtf.surrogate_lo))
                            with open(input_filename, 'wb') as f:
                                f.write(webify.safe_encode(text, encoding))
                            if encoding == 'utf8':
                                out1, result1 = ztml.ztml(text, unix_newline=False, caps=caps, mtf=mtf, bin2txt=bin2txt, raw=raw, validate=True, browser=b, verbose=True)
                                out2, result2 = ztml.ztml(text, output_filename, unix_newline=False, caps=caps, mtf=mtf, bin2txt=bin2txt, raw=raw, validate=True, browser=b, verbose=True)
                                with open(output_filename, 'rb') as f:
                                    out = f.read()
                                assert not result1 and not result2 and out1 == out2 == out, (result1, result2, out1 == out2, out1 == out, out2 == out, len(out1), len(out2), validation.full_path(output_filename), len(out))
                            raw_arg = '--raw' if raw else ''
                            result1 = os.system(f'python ztml.py "{input_filename}" "{output_filename}" --skip_unix_newline --caps {caps} --mtf {mtf} --bin2txt {bin2txt} {raw_arg} --validate --browser {browser} --verbose')
                            result2 = os.system(f'python ztml.py "{input_filename}" --skip_unix_newline --caps {caps} --mtf {mtf} --bin2txt {bin2txt} {raw_arg} --validate --browser {browser} --verbose > {output_stream}')
                            with open(output_filename, 'rb') as f1:
                                out1 = f1.read()
                            with open(output_stream, 'rb') as f2:
                                out2 = f2.read()
                            if out2.endswith(b'\x1b[0m'):
                                out2 = out2[:-4]
                            assert not result1 and not result2 and out1 == out2, (result1, result2, out1 == out2, validation.full_path(output_filename), len(out1), validation.full_path(output_stream), len(out2))
                            if cleanup:
                                for filename in [input_filename, output_filename, output_stream]:
                                    try:
                                        os.remove(filename)
                                    except PermissionError:
                                        pass
                            print(f'Test took {time() - test_time :.0f} sec.\n')
if cleanup:
    try:
        os.rmdir(temp_folder)
    except OSError:
        pass
print(f'Total took {(time()-start_time) / 60 :.1f} min.')
