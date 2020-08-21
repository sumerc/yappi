#include "Python.h"
#include "pythread.h"

#ifndef YTLS_H
#define YTLS_H

#if PY_MAJOR_VERSION >= 3 && PY_MINOR_VERSION >= 7
#define PY_NEW_TSS_API
#endif

typedef struct {

#ifdef PY_NEW_TSS_API
    Py_tss_t* _key;
#else
    int _key;
#endif

} tls_key_t;


tls_key_t* create_tls_key(void);
int set_tls_key_value(tls_key_t* key, void* value);
void* get_tls_key_value(tls_key_t* key);
void delete_tls_key(tls_key_t* key);
#endif