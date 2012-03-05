#!/usr/bin/env python
import os
import sys
from distutils.core import setup, Extension
from distutils.ccompiler import new_compiler

f = open('README')
long_description = f.read()

HOMEPAGE = "http://yappi.googlecode.com/"
NAME = "yappi"
VERSION = "0.62"

user_macros = []
user_libraries = []

if os.name == 'posix' and sys.platform != 'darwin': 
    compiler = new_compiler()
    if compiler.has_function('timer_create', libraries=('rt',)):
        user_macros.append(('LIB_RT_AVAILABLE','1'))
        user_libraries.append('rt')
    
#user_macros.append(('DEBUG_MEM', '1')),
#user_macros.append(('DEBUG_CALL', '1'))
#user_macros.append(('YDEBUG', '1')),
setup(name=NAME, 
    version=VERSION,    
    author="Sumer Cip",
    author_email="sumerc@gmail.com",
    ext_modules = [Extension(
        "_yappi",
        sources = ["_yappi.c", "callstack.c", "hashtab.c", "mem.c", "freelist.c", "timing.c"],
        define_macros = user_macros,
        libraries = user_libraries,
        )],
    py_modules =  ["yappi"],
    description="Yet Another Python Profiler",
    long_description = long_description,
    keywords = "python multithread profile",
    license = "MIT",
    url = HOMEPAGE,
    download_url = "%s/files/%s-%s.tar.gz" % (HOMEPAGE, NAME, VERSION),
)
