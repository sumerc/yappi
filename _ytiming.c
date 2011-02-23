#include "_ytiming.h"

#ifdef MS_WINDOWS

#include <windows.h>

long long
tickcount(void)
{
    LARGE_INTEGER li;
    QueryPerformanceCounter(&li);
    return li.QuadPart;
}

double
tickfactor(void)
{
    LARGE_INTEGER li;
    if (QueryPerformanceFrequency(&li))
        return 1.0 / li.QuadPart;
    else
        return 0.000001;  /* unlikely */
}

#else /* !MS_WINDOWS */

#ifndef HAVE_GETTIMEOFDAY
#error "This module requires gettimeofday() on non-Windows platforms!"
#endif

#if (defined(PYOS_OS2) && defined(PYCC_GCC))
#include <sys/time.h>
#else
#include <sys/resource.h>
#include <sys/times.h>
#endif

long long
tickcount(void)
{
    struct timeval tv;
    long long rc;
#ifdef GETTIMEOFDAY_NO_TZ
    gettimeofday(&tv);
#else
gettimeofday(&tv, (struct timezone *)NULL);
#endif
    rc = tv.tv_sec;
    rc = rc * 1000000 + tv.tv_usec;
    return rc;
}

double
tickfactor(void)
{
    return 0.000001;
}

#endif /* else MS_WINDOWS*/
