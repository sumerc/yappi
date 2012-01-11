#!/usr/bin/env python

from distutils.core import setup, Extension

f = open('README')
long_description = f.read()

HOMEPAGE = "http://yappi.googlecode.com/"
NAME = "yappi"
VERSION = "0.54"

setup(name=NAME, 
    version=VERSION,    
    author="Sumer Cip",
    author_email="sumerc@gmail.com",
    ext_modules = [Extension
        ("_yappi",
            sources = ["_yappi.c", "_ycallstack.c", 
                "_yhashtab.c", "_ymem.c", "_yfreelist.c", 
                "_ytiming.c"],
            depends = ["_ycallstack.h"],
            #define_macros=[('DEBUG_MEM', '1'), ('DEBUG_CALL', '1'), ('YDEBUG', '1')],
            #define_macros=[('YDEBUG', '1')],
            #define_macros=[('DEBUG_CALL', '1')],
            #define_macros=[('DEBUG_MEM', '1')],		
            #extra_link_args = ["-lrt"]
            #extra_compile_args = ["TEST"]
            #extra_compile_args = ["-E"]
        )
    ],
    py_modules =  ["yappi"],
    description="Yet Another Python Profiler",
    long_description = long_description,
    keywords = "python multithread profile",
    license = "MIT",
    url = HOMEPAGE,
    download_url = "%s/files/%s-%s.tar.gz" % (HOMEPAGE, NAME, VERSION),
)
