#!/usr/bin/env python

import io
import os
import sys
from setuptools import setup
from distutils.core import Extension
from distutils.ccompiler import new_compiler

with io.open('README.md', encoding='UTF-8') as f:
    long_description = f.read()

HOMEPAGE = "https://github.com/sumerc/yappi"
NAME = "yappi"
VERSION = "1.0"
_DEBUG = False    # compile/link code for debugging
_PROFILE = False    # profile yappi itself

user_macros = []
user_libraries = []
compile_args = []
link_args = []

if os.name == 'posix' and sys.platform != 'darwin':
    compiler = new_compiler()
    if compiler.has_function('timer_create', libraries=('rt', )):
        user_macros.append(('LIB_RT_AVAILABLE', '1'))
        user_libraries.append('rt')
if _DEBUG:
    if os.name == 'posix':
        compile_args.append('-g')
    elif os.name == 'nt':
        compile_args.append('/Zi')
        link_args.append('/DEBUG')

if _PROFILE:
    # Link with cpu profiler to allow profiling yappi itself
    # http://google-perftools.googlecode.com/svn/trunk/doc/cpuprofile.html
    user_libraries.append('profiler')

#user_macros.append(('DEBUG_MEM', '1')),
#user_macros.append(('DEBUG_CALL', '1'))
#user_macros.append(('YDEBUG', '1')),

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: Implementation :: CPython',
    'Operating System :: OS Independent',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

setup(
    name=NAME,
    version=VERSION,
    author="Sumer Cip",
    author_email="sumerc@gmail.com",
    ext_modules=[
        Extension(
            "_yappi",
            sources=[
                "_yappi.c", "callstack.c", "hashtab.c", "mem.c", "freelist.c",
                "timing.c"
            ],
            define_macros=user_macros,
            libraries=user_libraries,
            extra_compile_args=compile_args,
            extra_link_args=link_args,
        )
    ],
    py_modules=["yappi"],
    entry_points={
        'console_scripts': [
            'yappi = yappi:main',
        ],
    },
    description="Yet Another Python Profiler",
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords="python thread multithread profiler",
    classifiers=CLASSIFIERS,
    license="MIT",
    url=HOMEPAGE,
    # download_url = "http://bitbucket.org/sumerc/yappi/downloads/%s-%s.tar.gz" % (NAME, VERSION),
    test_suite='nose.collector')
