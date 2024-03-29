import os
from time import time

start_time = time()

if not __package__:
    import text_prep, bwt_mtf, deflate, validation, webify, ztml
else:
    # noinspection PyPackages
    from . import text_prep, bwt_mtf, deflate, validation, webify, ztml


min_char_code1 = 0
max_char_code1 = 14000
min_char_code2 = 55000
max_char_code2 = 66000
browsers = list(validation.drivers)[:1]
input_encodings = ['utf8', 'cp1252', 'cp1255']
bin2txt_encodings = ztml.bin2txt_encodings
caps_modes = ['auto', 'simple']  # text_prep.caps_modes
mtf_variants = [None, 0, 52, 80]  # bwt_mtf.mtf_variants
bitdepths = deflate.allowed_bitdepths
ect_modes = [False, True]
temp_folder = 'tmp'
cleanup = True


all_chars = ''.join(chr(i) for i in range(min_char_code1, min(max_char_code1 or bwt_mtf.max_unicode, bwt_mtf.max_unicode) + 1))
if min_char_code2 and max_char_code2:
    all_chars += ''.join(chr(i) for i in range(min_char_code2, min(max_char_code2 or bwt_mtf.max_unicode, bwt_mtf.max_unicode) + 1) if chr(i) not in all_chars)
os.makedirs(temp_folder, exist_ok=True)
i = 0
for browser in browsers:
    with validation.get_browser(browser) as b:
        for encoding in input_encodings:
            encoding = encoding.lower()
            for bin2txt in bin2txt_encodings:
                for caps in caps_modes:
                    for bwtsort in [True, False]:
                        for mtf in mtf_variants:
                            for bitdepth in bitdepths:
                                for ect in ect_modes:
                                    for render_mode in range(3):
                                        element_id = ''
                                        raw = False
                                        if render_mode == 1:
                                            element_id = 'myid'
                                        elif render_mode == 2:
                                            raw = True
                                        test_start_time = time()
                                        i += 1
                                        print(f'{i}/{len(browsers) * len(input_encodings) * len(bin2txt_encodings) * len(caps_modes) * 2 * len(mtf_variants) * len(bitdepths) * len(ect_modes) * 3} browser={browser} input_enc={encoding} bin2txt={bin2txt} caps={caps} bwtsort={bwtsort} mtf={mtf} bitdepth={bitdepth} ect={ect} id={bool(element_id)} raw={raw}')
                                        suffix = f"{browser}_{encoding}_{bin2txt}_{caps}{'_bwtsort' * bwtsort}_{mtf}_{bitdepth}{'_ect' * ect}"
                                        if element_id:
                                            suffix += '_id'
                                        if raw:
                                            suffix += '_raw'
                                        input_filename = os.path.join(temp_folder, f'ztml_test_file_{suffix}.txt')
                                        output_filename = os.path.join(temp_folder, f'ztml_test_file_{suffix}.html')
                                        output_stream = os.path.join(temp_folder, f'ztml_test_stream_{suffix}.html')
                                        text = all_chars
                                        if mtf is not None:
                                            text = ''.join(c for c in text if ord(c) <= bwt_mtf.max_ord_for_mtf)
                                        if encoding.replace('-', '') == 'utf8':
                                            text = ''.join(c for c in text if ord(c) < bwt_mtf.surrogate_lo or ord(c) > bwt_mtf.surrogate_hi)
                                            out1, result1 = ztml.ztml(text, unix_newline=False, remove_bom=False, caps=caps, bwtsort=bwtsort, mtf=mtf, bitdepth=bitdepth, ect=ect, bin2txt=bin2txt, element_id=element_id, raw=raw, validate=True, browser=b, verbose=True)
                                            out2, result2 = ztml.ztml(text, output_filename, unix_newline=False, remove_bom=False, caps=caps, bwtsort=bwtsort, mtf=mtf, bitdepth=bitdepth, ect=ect, bin2txt=bin2txt, element_id=element_id, raw=raw, validate=True, browser=b, verbose=True)
                                            with open(output_filename, 'rb') as f:
                                                out = f.read()
                                            assert not result1 and not result2 and out1 == out2 == out, (result1, result2, out1 == out2, out1 == out, out2 == out, len(out1), len(out2), validation.full_path(output_filename), len(out))
                                        with open(input_filename, 'wb') as f:
                                            f.write(webify.safe_encode(text, encoding))
                                        bwtsort_arg = '--skip_bwtsort' * (not bwtsort)
                                        ect_arg = '--ect' * ect
                                        element_id_or_raw_arg = ''
                                        if element_id:
                                            element_id_or_raw_arg = f'--element_id "{element_id}"'
                                        if raw:
                                            element_id_or_raw_arg = '--raw'
                                        result1 = os.system(f'python ztml.py "{input_filename}" "{output_filename}" --skip_unix_newline --skip_remove_bom --caps {caps} {bwtsort_arg} --mtf {mtf} --bitdepth {bitdepth} {ect_arg} --bin2txt {bin2txt} {element_id_or_raw_arg} --validate --browser {browser} --verbose')
                                        result2 = os.system(f'python ztml.py "{input_filename}" --skip_unix_newline --skip_remove_bom --caps {caps} {bwtsort_arg} --mtf {mtf} --bitdepth {bitdepth} {ect_arg} --bin2txt {bin2txt} {element_id_or_raw_arg} --validate --browser {browser} --verbose > {output_stream}')
                                        with open(output_filename, 'rb') as f1:
                                            out1 = f1.read()
                                        with open(output_stream, 'rb') as f2:
                                            out2 = f2.read()
                                        if out2.endswith(b'\x1b[0m'):  # E.g. due to PyCharm terminal
                                            out2 = out2[:-4]
                                        assert not result1 and not result2 and out1 == out2, (result1, result2, out1 == out2, validation.full_path(output_filename), len(out1), validation.full_path(output_stream), len(out2))
                                        if cleanup:
                                            for filename in [input_filename, output_filename, output_stream]:
                                                try:
                                                    os.remove(filename)
                                                except PermissionError:
                                                    pass
                                        print(f'Test took {time() - test_start_time :.0f} sec.\n')
if cleanup:
    try:
        os.rmdir(temp_folder)
    except OSError:
        pass
print(f'Total took {(time()-start_time) / 60 :.1f} min.')
