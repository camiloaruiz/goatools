#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""Setup for PyPI usage."""

import os.path as op

from glob import glob
from setuptools import setup
from setup_helper import SetupHelper


NAME = "goatools"
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 3',
    'Topic :: Scientific/Engineering :: Bio-Informatics',
    ]

# Use the helper
HLPR = SetupHelper(initfile="goatools/__init__.py", readmefile="README.md")

SETUP_DIR = op.abspath(op.dirname(__file__))
REQUIREMENTS = ['wget'] + \
               [x.strip() for x in open(op.join(SETUP_DIR, 'requirements.txt')).readlines()]

setup(
    NAME=NAME,
    version=HLPR.version,
    author=HLPR.author,
    author_email=HLPR.email,
    license=HLPR.license,
    long_description=HLPR.long_description,
    packages=[
        NAME,
        NAME + ".godag",
        NAME + ".gosubdag",
        NAME + ".gosubdag.plot",
        NAME + ".gosubdag.rpt",
        NAME + ".test_data",
        NAME + ".cli",
        NAME + ".rpt",
        NAME + ".anno",
        NAME + ".anno.extensions",
        NAME + ".grouper",
        NAME + ".parsers"],
    include_package_data=True,
    package_data={"goatools.test_data.nbt_3102": ["*.*"]},
    scripts=glob('scripts/*.py'),
    classifiers=CLASSIFIERS,
    url='http://github.com/tanghaibao/goatools',
    description="Python scripts to find enrichment of GO terms",
    install_requires=REQUIREMENTS
)
