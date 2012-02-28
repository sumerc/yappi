#include "_ytiming.h"

#if defined(_WINDOWS)

long long
tickcount(void)
{
    LARGE_INTEGER li;
    FILETIME ftCreate, ftExit, ftKernel, ftUser;
    
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

#elif defined(_MACH)

long long
tickcount(void)
{
	long long rc;
	kern_return_t kr;
    thread_basic_info_t tinfo_basic;
	thread_info_data_t tinfo_data;
	mach_msg_type_number_t tinfo_count;
	
	tinfo_count = THREAD_INFO_MAX;
	kr = thread_info(mach_thread_self(), THREAD_BASIC_INFO,
		(thread_info_t)tinfo_data, &tinfo_count);
	tinfo_basic = (thread_basic_info_t)tinfo_data;
    
    rc = 0;
    if (!(tinfo_basic->flags & TH_FLAGS_IDLE))
    {
        rc = (tinfo_basic->user_time.seconds + tinfo_basic->system_time.seconds);
        rc = (rc * 1000000) + (tinfo_basic->user_time.microseconds + tinfo_basic->system_time.microseconds);
    }
    return rc;
}

double
tickfactor(void)
{
     return 0.000001;
}

#elif defined(_UNIX)

long long
tickcount(void)
{
    long long rc;
#if defined(USE_CLOCK_TYPE_CLOCKGETTIME)
    struct timespec tp;
    
    clock_gettime(CLOCK_THREAD_CPUTIME_ID, &tp);
    rc = tp.tv_sec;
    rc = rc * 1000000000 + (tp.tv_nsec);
#elif (defined(USE_CLOCK_TYPE_RUSAGE) && defined(RUSAGE_WHO))
    struct timeval tv;
    struct rusage usage;
    
    getrusage(RUSAGE_WHO, &usage);
    rc = (usage.ru_utime.tv_sec + usage.ru_stime.tv_sec);
    rc = (rc * 1000000) + (usage.ru_utime.tv_usec + usage.ru_stime.tv_usec);
#endif
    return rc;    
}

double
tickfactor(void)
{
#if defined(USE_CLOCK_TYPE_CLOCKGETTIME)
    return 0.000000001;
#elif defined(USE_CLOCK_TYPE_RUSAGE)
    return 0.000001;
#endif
}

#endif /* *nix */
