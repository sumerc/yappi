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

// stat related
#define M_LEFT 1
#define M_RIGHT -1


#define LINE_LEN 80
#define FUNC_NAME_LEN 37
#define TIMESTR_COLUMN_LEN 27
#define LONG_COLUMN_LEN 7
#define THREAD_NAME_LEN 15
#define DOUBLE_COLUMN_LEN 11
#define INT_COLUMN_LEN 9
#define ZIP_MARGIN_LEN 1
#define ZIP_DOT_COUNT 2
#define STAT_SORT_TYPE_MAX 4
#define STAT_SORT_ORDER_MAX 1
#define STAT_SORT_FUNC_NAME 0
#define STAT_SORT_CALL_COUNT 1
#define STAT_SORT_TIME_TOTAL 2
#define STAT_SORT_TIME_SUB 3
#define STAT_SORT_TIME_AVG 4
#define STAT_SORT_ASCENDING 0
#define STAT_SORT_DESCENDING 1
#define STAT_SHOW_ALL -1

#define STAT_HEADER_STR "\n\n\n\nname                                 #n       tsub       ttot       tavg"
#define STAT_FOOTER_STR "\n\nname           tid    fname                                scnt     ttot"
#define STAT_FOOTER_STR2 "\n\nstatus     tstart                     fcnt     tcnt     mem(bytes)"

#endif
