import os
import sys
from time import time

start_time = time()

if not __package__:
    import validation, ztml
else:
    from . import validation, ztml


min_char_code = 0
max_char_code = 10000
browsers = ['chrome']
input_encodings = ['utf8', 'cp1255']
temp_folder = 'tmp'
cleanup = True


max_unicode = 1114111
text = ''.join(chr(i) for i in range(min_char_code, min(max_char_code or max_unicode, max_unicode) + 1) if (i < 55296 or i > 57343))
os.makedirs(temp_folder, exist_ok=True)
i = 0
for browser in browsers:
    with validation.get_browser(browser) as b:
        for enc in input_encodings:
            enc = enc.lower().replace('-', '')
            for bin2txt in ztml.bin2txt_encodings:
                i += 1
                print(f'{i}/{len(browsers) * len(input_encodings) * len(ztml.bin2txt_encodings)} browser={browser} input_enc={enc} bin2txt={bin2txt}')
                input_filename = os.path.join(temp_folder, f'ztml_test_file_{enc}_{bin2txt}.txt')
                output_filename = os.path.join(temp_folder, f'ztml_test_file_{enc}_{bin2txt}.html')
                output_stream = os.path.join(temp_folder, f'ztml_test_stream_{enc}_{bin2txt}.html')
                with open(input_filename, 'wb') as f:
                    f.write((text if enc.startswith('utf') else 'אבגדהוזחטיךכלםמןנסעףפץצקרשת').encode(enc))
                if enc == 'utf8':
                    out1, result1 = ztml.generate(text, bin2txt=bin2txt, validate=True, compare_caps=False, browser=b, verbose=True)
                    out2, result2 = ztml.generate(text, output_filename, bin2txt=bin2txt, validate=True, compare_caps=False, browser=b, verbose=True)
                    with open(output_filename, 'rb') as f:
                        assert not result1 and not result2 and out1 == out2 == f.read(), (result1, result2, output_filename)
                result1 = os.system(f'python ztml.py "{input_filename}" "{output_filename}" --bin2txt {bin2txt} --validate --skip_compare_caps --browser {browser} --verbose')
                result2 = os.system(f'python ztml.py "{input_filename}" --bin2txt {bin2txt} --validate --skip_compare_caps --browser {browser} --verbose > {output_stream}')
                with open(output_filename, 'rb') as f1, open(output_stream, 'rb') as f2:
                    assert not result1 and not result2 and f1.read() == f2.read(), (result1, result2, output_filename)
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
    except PermissionError:
        pass
print(f'Total took {(time()-start_time) / 60 :.1f} min.', file=sys.stderr)
