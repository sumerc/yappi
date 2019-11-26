#ifndef YCONFIG_H
#define YCONFIG_H

#include "Python.h"

#if defined(MS_WINDOWS)
#define _WINDOWS
#elif (defined(__MACH__) && defined(__APPLE__))
#define _MACH
#else /* *nix */
#define _UNIX
#endif

#ifndef _MSC_VER /* non-windows compiler */
#include "stdint.h"
#endif

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

// static pool sizes
#define FL_PIT_SIZE 1
#define FL_CTX_SIZE 1
#define HT_PIT_SIZE 1
#define HT_TAGGED_PIT_SIZE 1
#define HT_CTX_SIZE 1
#define HT_RLEVEL_SIZE 1
#define DEFAULT_TEST_ELAPSED_TIME 3

#endif
