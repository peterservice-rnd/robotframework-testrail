# -*- coding: utf-8 -*-
"""Script to generate library documentation using module libdoc."""

from os.path import dirname, join, realpath
from robot.libdoc import libdoc


DOCS_DIR = dirname(__file__)
SRC_DIR = realpath(join(DOCS_DIR, '..', 'src'))
LIBS = {
    'TestRailAPIClient': 'TestRailAPIClient.py::1::2::3::4',
    'TestRailListener': 'TestRailListener.py::1::2::3::4',
    'TestRailPreRunModifier': 'TestRailPreRunModifier.py::1::2::3::4::5::6'
}

if __name__ == '__main__':
    for lib_name, lib_name_with_args in LIBS.items():
        libdoc(join(SRC_DIR, lib_name_with_args), join(DOCS_DIR, lib_name + '.html'), version='1.0.0')
