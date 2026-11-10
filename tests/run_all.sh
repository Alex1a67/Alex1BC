#!/bin/sh
python3 -m unittest tests.test_core tests.test_server tests.test_phone_page -v
${BPY_PYTHON:-python} tests/bpy_integration.py
