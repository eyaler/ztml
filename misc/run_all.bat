#!/bin/bash 2> nul

:; trap "exit" INT TERM
:; set -o errexit
:; function goto() { return $?; }

cd ..

python example.py || goto :error

python example_image.py || goto :error

cd misc

python example_html.py || goto :error

python minibook.py || goto :error

cd ../ztml

python tests.py || goto :error

:; exit 0
exit /b 0

:error
exit /b %errorlevel%
