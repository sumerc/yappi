#ifndef YSTATIC_H
#define YSTATIC_H

#include "Python.h"

#ifndef _MSC_VER
#include "stdint.h"
#endif

#if PY_MAJOR_VERSION >= 3
#define IS_PY3K
#endif

// static pool sizes
#define FL_PIT_SIZE 1000
#define FL_CTX_SIZE 100
#define HT_PIT_SIZE 10
#define HT_CTX_SIZE 5
#define HT_CS_COUNT_SIZE 7

#endif
