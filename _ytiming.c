#include "_ytiming.h"

#if defined(MS_WINDOWS)

#include <windows.h>

long long
tickcount(void)
{
    LARGE_INTEGER li;
    FILETIME ftCreate, ftExit, ftKernel, ftUser;
    
    // resolution = 100ns intervals
    GetThreadTimes(GetCurrentThread(), &ftCreate, &ftExit, &ftKernel, &ftUser);
    
    li.LowPart = ftKernel.dwLowDateTime+ftUser.dwLowDateTime;
    li.HighPart = ftKernel.dwHighDateTime+ftUser.dwHighDateTime;
    
    return li.QuadPart; 
}

double
tickfactor(void)
{
    return 0.0000001;
}

#elif (defined(__MACH__) && defined(__APPLE__))
    // TODO:
#else /* *nix */

#define _GNU_SOURCE

#include <time.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/resource.h>

/* 
    Policy of clock usage on *nix systems is as follows:
    1)  If clock_gettime() is possible, then use it, it has nanosecond 
        resolution. It is available in >Linux 2.6.0.
    2)  If get_rusage() is possible use that. >Linux 2.6.26 and Solaris have that.
    3)  If here, at least use clock_gettime() CLOCK_REALTIME which has nanosecond 
        resolution.
*/
#if (defined(_POSIX_THREAD_CPUTIME) && defined(LIB_RT_AVAILABLE))
#define USE_CLOCK_GETTIME
#elif (defined(RUSAGE_THREAD) || defined(RUSAGE_LWP))
    #define USE_RUSAGE
    #if defined(RUSAGE_LWP)
        #define RUSAGE_WHO RUSAGE_LWP
    #elif defined(RUSAGE_THREAD)
        #define RUSAGE_WHO RUSAGE_THREAD
    #endif
#endif    

long long
tickcount(void)
{
    struct timeval tv;
    struct timespec tp;
    long long rc;
    struct rusage usage;

#if defined(USE_CLOCK_GETTIME)
    printf("Using clock_gettime()...\r\n");
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &tp);
    rc = tp.tv_sec;
    rc = rc * 1000000000 + (tp.tv_nsec);
#elif defined(USE_RUSAGE)
    printf("Using getrusage()...\r\n");    
    getrusage(RUSAGE_WHO, &usage);
    rc = (usage.ru_utime.tv_sec + usage.ru_stime.tv_sec);
    rc = (rc * 1000000) + (usage.ru_utime.tv_usec + usage.ru_stime.tv_usec);
#endif
    return rc;    
}

double
tickfactor(void)
{
    return 0.000001;
}

#endif /* *nix */
