from distutils.core import setup, Extension

setup(name="_yappi", 
	  version="0.5 beta",
	  description="Yet Another Python Profiler",
      author="Sumer Cip",
      author_email="sumerc@gmail.com",
	  ext_modules = [Extension
					 ("_yappi",
					  sources = ["_yappi.c", "_ycallstack.c", 
					  "_yhashtab.c", "_ymem.c", "_yfreelist.c", 
					  "_ytiming.c"],
					  #define_macros=[('DEBUG_MEM', '1'), ('DEBUG_CALL', '1'), ('YDEBUG', '1')],
					  #define_macros=[('YDEBUG', '1')],
					  #define_macros=[('DEBUG_CALL', '1')],
					  #define_macros=[('DEBUG_MEM', '1')],		
					  #extra_link_args = ["-lrt"]
					  #extra_compile_args = ["TEST"]
				     )
				    ],
	  py_modules =  ["yappi"]
)
