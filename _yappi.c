/*

 yappi
 Yet Another Python Profiler

 Sumer Cip 2010

*/

#include "Python.h"
#include "frameobject.h"
#include "_ycallstack.h"
#include "_yhashtab.h"
#include "_ydebug.h"
#include "_ytiming.h"
#include "_yfreelist.h"
#include "_ystatic.h"
#include "_ymem.h"

PyDoc_STRVAR(_yappi__doc__, "Yet Another Python Profiler");

// module macros
#define YSTRMOVEND(s) (*s += strlen(*s))

// module definitions
typedef struct {
    PyObject *co; // CodeObject or MethodDef descriptive string.
    unsigned long callcount;
    long long tsubtotal;
    long long ttotal;
    int builtin;
    int cpc;
} _pit; // profile_item

typedef struct {
    _cstack *cs;
    long id;
    _pit *last_pit;
    unsigned long sched_cnt;
    long long ttotal;
    char *class_name;
} _ctx; // context

typedef struct {
    int builtins;
    int timing_sample;
} _flag; // flags passed from yappi.start()


// stat related definitions
typedef struct {
    unsigned long callcount;
    double ttot;
    double tsub;
    double tavg;
    char result[LINE_LEN+1];
    char fname[FUNC_NAME_LEN+1];
} _statitem; //statitem created while getting stats


struct _stat_node_t {
    _statitem *it;
    struct _stat_node_t *next;
};
typedef struct _stat_node_t _statnode; // linked list used for appending stats


// profiler global vars
static PyObject *YappiProfileError;
static _statnode *statshead;
static _htab *contexts;
static _htab *pits;
static _flag flags;
static _freelist *flpit;
static _freelist *flctx;
static int yappinitialized;
static int yapphavestats;	// start() called at least once or stats cleared?
static int yapprunning;
static time_t yappstarttime;
static long long yappstarttick;
static long long yappstoptick;
static _ctx *prev_ctx;
static _ctx *current_ctx;

// forward
static _ctx * _profile_thread(PyThreadState *ts);

// module functions
static _pit *
_create_pit(void)
{
    _pit *pit;

    pit = flget(flpit);
    if (!pit)
        return NULL;
    pit->callcount = 0;
    pit->ttotal = 0;
    pit->tsubtotal = 0;
    pit->co = NULL;
    pit->builtin = 0;

    // we do not profile the fist time as if the first timing measures
    // can give incorrect calculations because of the caching behavior
    // of Python. This is because we multiply the flags.timing_sample
    // with the timing values of the function for the cold start. So just
    // do not measure time the first time unless timing sample is "1" of
    // course.
    pit->cpc = 0;

    return pit;
}

static _ctx *
_create_ctx(void)
{
    _ctx *ctx;

    ctx = flget(flctx);
    if (!ctx)
        return NULL;
    ctx->cs = screate(100);
    if (!ctx->cs)
        return NULL;
    ctx->last_pit = NULL;
    ctx->sched_cnt = 0;
    ctx->ttotal = 0;
    ctx->id = 0;
    ctx->class_name = NULL;
    return ctx;
}


// extracts the function name from a given pit. Note that pit->co may be
// either a PyCodeObject or a descriptive string.
static char *
_item2fname(_pit *pt)
{
    char *buf;
    PyObject *fname;

    if (!pt)
        return NULL;

    if (PyCode_Check(pt->co)) {
#ifdef IS_PY3K
    fname =  PyUnicode_FromFormat( "%s.%s:%d",
    		PyUnicode_AsUTF8String(((PyCodeObject *)pt->co)->co_filename),
    		PyUnicode_AsUTF8String(((PyCodeObject *)pt->co)->co_name),
            ((PyCodeObject *)pt->co)->co_firstlineno );
#else
    fname =  PyString_FromFormat( "%s.%s:%d",
                                  PyString_AS_STRING(((PyCodeObject *)pt->co)->co_filename),
                                  PyString_AS_STRING(((PyCodeObject *)pt->co)->co_name),
                                  ((PyCodeObject *)pt->co)->co_firstlineno );
#endif
    } else {
        fname = pt->co;
    }
    
// TODO:memleak on buf?
#ifdef IS_PY3K    
    buf = PyUnicode_AsUTF8String(fname);
#else
    buf = PyString_AS_STRING(fname); 
#endif    
    if (PyCode_Check(pt->co)) {
        Py_DECREF(fname);
    }
    return buf;
}

char *
_get_current_thread_class_name(void)
{
    PyObject *mthr, *cthr, *tattr1, *tattr2;

    mthr = cthr = tattr1 = tattr2 = NULL;

    mthr = PyImport_ImportModule("threading");
    if (!mthr)
        goto err;
    cthr = PyObject_CallMethod(mthr, "currentThread", "");
    if (!cthr)
        goto err;
    tattr1 = PyObject_GetAttrString(cthr, "__class__");
    if (!tattr1)
        goto err;
    tattr2 = PyObject_GetAttrString(tattr1, "__name__");
    if (!tattr2)
        goto err;
        
#ifdef IS_PY3K
    return PyUnicode_AsUTF8String(tattr2);
#else
    return PyString_AS_STRING(tattr2);
#endif

err:
    Py_XDECREF(mthr);
    Py_XDECREF(cthr);
    Py_XDECREF(tattr1);
    Py_XDECREF(tattr2);
    return NULL; //continue enumeration on err.
}

static _ctx *
_thread2ctx(PyThreadState *ts)
{
    _hitem *it;

    it = hfind(contexts, (uintptr_t)ts);
    if (!it) {        
        // callback functions in some circumtances, can be called before the context entry is not
        // created. (See issue 21). To prevent this problem we need to ensure the context entry for
        // the thread is always available here. 
        return _profile_thread(ts);        
    }
    return (_ctx *)it->val;
}

// the pit will be cleared by the relevant freelist. we do not free it here.
// we only DECREF the CodeObject or the MethodDescriptive string.
static void
_del_pit(_pit *pit)
{
    // if it is a regular C string all DECREF will do is to decrement the first
    // character's value.
    Py_DECREF(pit->co);
}

static _pit *
_ccode2pit(void *cco)
{
    PyCFunctionObject *cfn;
    _hitem *it;

    cfn = cco;
    // Issue #15:
    // Hashing cfn to the pits table causes different object methods
    // to be hashed into the same slot. Use cfn->m_ml for hashing the
    // Python C functions.
    it = hfind(pits, (uintptr_t)cfn->m_ml);
    if (!it) {
        _pit *pit = _create_pit();
        if (!pit)
            return NULL;
        if (!hadd(pits, (uintptr_t)cfn->m_ml, (uintptr_t)pit))
            return NULL;

        pit->builtin = 1; // set the bultin here

        // built-in function?
        if (cfn->m_self == NULL) {

            PyObject *mod = cfn->m_module;
            const char *modname;


#ifdef IS_PY3K
            if (mod && PyUnicode_Check(mod)) {
                modname = PyUnicode_AsUTF8String(mod);
#else
            if (mod && PyString_Check(mod)) {
                modname = PyString_AS_STRING(mod);
#endif
            } else if (mod && PyModule_Check(mod)) {
                modname = PyModule_GetName(mod);
                if (modname == NULL) {
                    PyErr_Clear();
                    modname = "__builtin__";
                }
            } else {
                modname = "__builtin__";
            }
            if (strcmp(modname, "__builtin__") != 0) {
#ifdef IS_PY3K
                pit->co = PyUnicode_FromFormat("<%s.%s>",
                                               modname,
                                               cfn->m_ml->ml_name);
#else
                pit->co = PyString_FromFormat("<%s.%s>",
                                              modname,
                                              cfn->m_ml->ml_name);
#endif                                              
            } else {
#ifdef IS_PY3K
                pit->co = PyUnicode_FromFormat("<%s>",
                                               cfn->m_ml->ml_name);
#else
                pit->co = PyString_FromFormat("<%s>",
                                              cfn->m_ml->ml_name);
#endif
            }

        } else { // built-in method?
            PyObject *self = cfn->m_self;
#ifdef IS_PY3K
            PyObject *name = PyUnicode_FromString(cfn->m_ml->ml_name);
#else
            PyObject *name = PyString_FromString(cfn->m_ml->ml_name);
#endif
            if (name != NULL) {
                PyObject *mo = _PyType_Lookup((PyTypeObject *)PyObject_Type(self), name);
                Py_XINCREF(mo);
                Py_DECREF(name);
                if (mo != NULL) {
                    PyObject *res = PyObject_Repr(mo);
                    Py_DECREF(mo);
                    if (res != NULL) {
                        pit->co = res;
                        return pit;
                    }
                }
            }
            PyErr_Clear();
#ifdef IS_PY3K
            pit->co = PyUnicode_FromFormat("<built-in method %s>",
                                           cfn->m_ml->ml_name);
#else
            pit->co = PyString_FromFormat("<built-in method %s>",
                                          cfn->m_ml->ml_name);
#endif
        }
        return pit;
    }
    return ((_pit *)it->val);
}

// maps the PyCodeObject to our internal pit item via hash table.
static _pit *
_code2pit(void *co)
{
    _hitem *it;

    it = hfind(pits, (uintptr_t)co);
    if (!it) {
        _pit *pit = _create_pit();
        if (!pit)
            return NULL;
        if (!hadd(pits, (uintptr_t)co, (uintptr_t)pit))
            return NULL;
        Py_INCREF((PyObject *)co);
        pit->co = co; //dummy
        return pit;
    }
    return ((_pit *)it->val);
}

static void
_call_enter(PyObject *self, PyFrameObject *frame, PyObject *arg, int ccall)
{
    _pit *cp;
    PyObject *last_type, *last_value, *last_tb;
    _cstackitem *hci;

    PyErr_Fetch(&last_type, &last_value, &last_tb);

    if (ccall) {
        cp = _ccode2pit((PyCFunctionObject *)arg);
    } else {
        cp = _code2pit(frame->f_code);
    }

    // something went wrong. No mem, or another error. we cannot find
    // a corresponding pit. just run away:)
    if (!cp) {
        yerr("pit not found");
        goto err;
    }

    hci = spush(current_ctx->cs, cp);
    if (!hci) { // runaway!
        yerr("spush failed.");
        goto err;
    }

    // do not do timing measures until timing_sample is reached.
    if (++cp->cpc >= flags.timing_sample) {
        hci->t0 = tickcount();
    }

    cp->callcount++;

    // do not show builtin pits if specified even in last_pit of the context.
    if  ((!flags.builtins) && (cp->builtin))
        ;
    else {
        current_ctx->last_pit = cp;
    }

    PyErr_Restore(last_type, last_value, last_tb);

err:

    PyErr_Restore(last_type, last_value, last_tb);

}


static void
_call_leave(PyObject *self, PyFrameObject *frame, PyObject *arg)
{
    _pit *cp, *pp;
    _cstackitem *ci,*pi;
    long long elapsed;

    ci = spop(current_ctx->cs);
    if (!ci) {
        return; // leaving a frame while callstack is empty
    }
    cp = ci->ckey;

    // timing sample reached?
    if (cp->cpc < flags.timing_sample) {
        return;
    }

    elapsed = tickcount() - ci->t0;
    cp->cpc = 0;

    // get the parent function in the callstack
    pi = shead(current_ctx->cs);
    if (!pi) { // no head this is the first function in the callstack?
        cp->ttotal += elapsed;
        return;
    }
    pp = pi->ckey;

    // are we leaving a recursive function that is already in the callstack?
    // then extract the elapsed from subtotal of the the current pit(profile item).
    if (scount(current_ctx->cs, cp) > 0) {
        cp->tsubtotal -= elapsed;
        current_ctx->ttotal -= elapsed;
    } else {
        cp->ttotal += elapsed;
    }

    // update parent's sub total if recursive above code will extract the subtotal and
    // below code will have no effect.
    pp->tsubtotal += elapsed;

    current_ctx->ttotal += elapsed;
}

// context will be cleared by the free list. we do not free it here.
// we only free the context call stack.
static void
_del_ctx(_ctx * ctx)
{
    sdestroy(ctx->cs);
}

static int
_yapp_callback(PyObject *self, PyFrameObject *frame, int what,
               PyObject *arg)
{
    // get current ctx
    current_ctx = _thread2ctx(frame->f_tstate);
    if (!current_ctx) {
        yerr("no context found or can be created.");
        return 0;
    }
    
    switch (what) {
    case PyTrace_CALL:
        _call_enter(self, frame, arg, 0);
        break;
    case PyTrace_RETURN: // either normally or with an exception
        _call_leave(self, frame, arg);
        break;

#ifdef PyTrace_C_CALL	// not defined in Python <= 2.3 
    case PyTrace_C_CALL:
        if (PyCFunction_Check(arg))
            _call_enter(self, frame, arg, 1); // set ccall to true
        break;

    case PyTrace_C_RETURN:
    case PyTrace_C_EXCEPTION:
        if (PyCFunction_Check(arg))
            _call_leave(self, frame, arg);
        break;
#endif
    default:
        break;
    }

    // update ctx statistics
    if (prev_ctx != current_ctx) {
        current_ctx->sched_cnt++;
    }
    if (!current_ctx->class_name) {
        current_ctx->class_name = _get_current_thread_class_name();
    }
    prev_ctx = current_ctx;
    return 0;
}


static _ctx *
_profile_thread(PyThreadState *ts)
{
    _ctx *ctx;

    ctx = _create_ctx();
    if (!ctx) {
        return NULL;
    }
    
    // If a ThreadState object is destroyed, currently yappi does not
    // delete the associated resources. Instead, we rely on the fact that
    // the ThreadState objects are actually recycled. We are using pointer
    // to map to the internal contexts table, and Python VM will try to use
    // the destructed thread's pointer when a new thread is created. They are
    // pooled inside the VM. So this means we wii use the same pointer for our
    // hash table like lazy deletion. This is a hecky solution, but there is no
    // efficient and easy way to somehow know that a Python Thread is about
    // to be destructed.
    if (!hadd(contexts, (uintptr_t)ts, (uintptr_t)ctx)) {
        _del_ctx(ctx);
        if (!flput(flctx, ctx)) {
            yerr("Context cannot be recycled. Possible memory leak.");
        }
        dprintf("Context add failed. Already added?(%p, %ld)", ts,
                PyThreadState_GET()->thread_id);
        return NULL;
    }

    ts->use_tracing = 1;
    ts->c_profilefunc = _yapp_callback;
    ctx->id = ts->thread_id;
    return ctx;
}

static _ctx*
_unprofile_thread(PyThreadState *ts)
{
    ts->use_tracing = 0;
    ts->c_profilefunc = NULL;
    return NULL; //dummy return for enum_threads() func. prototype
}

static void
_ensure_thread_profiled(PyThreadState *ts)
{
    PyThreadState *p = NULL;

    for (p=ts->interp->tstate_head ; p != NULL; p = p->next) {
        if (ts->c_profilefunc != _yapp_callback) {
            _profile_thread(ts);
        }
    }
}

static void
_enum_threads(_ctx* (*f) (PyThreadState *))
{
    PyThreadState *p = NULL;

    for (p=PyThreadState_GET()->interp->tstate_head ; p != NULL; p = p->next) {
        f(p);
    }
}

static int
_init_profiler(void)
{
    // already initialized? only after clear_stats() and first time, this flag
    // will be unset.
    if (!yappinitialized) {
        contexts = htcreate(HT_CTX_SIZE);
        if (!contexts)
            return 0;
        pits = htcreate(HT_PIT_SIZE);
        if (!pits)
            return 0;
        flpit = flcreate(sizeof(_pit), FL_PIT_SIZE);
        if (!flpit)
            return 0;
        flctx = flcreate(sizeof(_ctx), FL_CTX_SIZE);
        if (!flctx)
            return 0;
        yappinitialized = 1;
        statshead = NULL;
        current_ctx = NULL;
        prev_ctx = NULL;
    }
    return 1;
}

static PyObject*
profile_event(PyObject *self, PyObject *args)
{
    char *ev;
    PyObject *arg;
    PyObject *event;
    PyFrameObject * frame;

    if (!PyArg_ParseTuple(args, "OOO", &frame, &event, &arg)) {
        return NULL;
    }

    _ensure_thread_profiled(PyThreadState_GET());
    
#ifdef IS_PY3K
    ev = PyUnicode_AsUTF8String(event);
#else
    ev = PyString_AS_STRING(event);
#endif

    if (strcmp("call", ev)==0)
        _yapp_callback(self, frame, PyTrace_CALL, arg);
    else if (strcmp("return", ev)==0)
        _yapp_callback(self, frame, PyTrace_RETURN, arg);
    else if (strcmp("c_call", ev)==0)
        _yapp_callback(self, frame, PyTrace_C_CALL, arg);
    else if (strcmp("c_return", ev)==0)
        _yapp_callback(self, frame, PyTrace_C_RETURN, arg);
    else if (strcmp("c_exception", ev)==0)
        _yapp_callback(self, frame, PyTrace_C_EXCEPTION, arg);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
start(PyObject *self, PyObject *args)
{
    if (yapprunning) {
        PyErr_SetString(YappiProfileError, "profiler is already started. yappi is a per-interpreter resource.");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "ii", &flags.builtins, &flags.timing_sample))
        return NULL;

    if (flags.timing_sample < 1) {
        PyErr_SetString(YappiProfileError, "profiler timing sample value cannot be less than 1.");
        return NULL;
    }

    if (!_init_profiler()) {
        PyErr_SetString(YappiProfileError, "profiler cannot be initialized.");
        return NULL;
    }

    _enum_threads(&_profile_thread);

    yapprunning = 1;
    yapphavestats = 1;
    time (&yappstarttime);
    yappstarttick = tickcount();

    Py_INCREF(Py_None);
    return Py_None;
}


static long long
_calc_cumdiff(long long a, long long b)
{
    long long r;

    r = a - b;
    if (r < 0)
        return 0;
    return r;
}

static int
_pitenumstat(_hitem *item, void * arg)
{
    long long cumdiff;
    PyObject *efn;
    char *fname;
    _pit *pt;

    pt = (_pit *)item->val;
    cumdiff = _calc_cumdiff(pt->ttotal, pt->tsubtotal);
    efn = (PyObject *)arg;

    fname = _item2fname(pt);
    if (!fname)
        fname = "N/A";

    // do not show builtin pits if specified
    if  ((!flags.builtins) && (pt->builtin))
        return 0;

    // We may have MT issues here!!! declaring a preenum func in yappi.py
    // does not help as we need a per-profiler sync. object for this. This means
    // additional complexity and additional overhead. Any idea on this?
    // Do we really have an mt issue here? The parameters that are sent to the
    // function does not directly use the same ones, they will copied over to the VM.
    PyObject_CallFunction(efn, "((skff))", fname,
                          pt->callcount, pt->ttotal * tickfactor() * flags.timing_sample,
                          cumdiff * tickfactor() * flags.timing_sample);

    return 0;
}

// adds spaces to extend to the size, or shrinks the string
// from wrapfrom d�rection with adding dots.
void
_yzipstr(char *s, int size, int wrapfrom)
{
    int i,len;

    len = strlen(s);

    for(i=len; i<size; i++)
        s[i]  = ' ';
    s[size] = '\0';

    // no wrapping needed?
    if (len+ZIP_MARGIN_LEN < size)
        return;

    // extend the string with spaces
    for(i=0; i<ZIP_MARGIN_LEN; i++)
        s[size-i-1] = ' ';

    // wrap the string according to the direction
    if (wrapfrom == M_LEFT) {
        for(i=0; i<ZIP_DOT_COUNT; i++)
            s[i] = '.';
    } else {
        for(i=0; i<ZIP_DOT_COUNT; i++)
            s[size-i-ZIP_MARGIN_LEN-1] = '.';
    }
}

// From Python 2.6.5 Doc:
// PyOS_snprintf() and PyOS_vsnprintf() wrap the Standard C library functions snprintf() and vsnprintf(). Their
// purpose is to guarantee consistent behavior in corner cases, which the Standard C functions do not.
// The wrappers ensure that str*[*size-1] is always '\0' upon return. They never write more than size bytes
// (including the trailing '\0' into str. Both functions require that str != NULL, size > 0 and format != NULL.
// If the platform doesn't have vsnprintf() and the buffer size needed to avoid truncation exceeds size by more
// than 512 bytes, Python aborts with a Py_FatalError.The return value (rv) for these functions should be
// interpreted as follows: When 0 <= rv < size, the output conversion was successful and rv characters were
// written to str (excluding the trailing '\0' byte at str*[*rv]).When rv >= size, the output conversion was
// truncated and a buffer with rv + 1 bytes would have been needed to succeed. str*[*size-1] is '\0' in this
// case.When rv < 0, something bad happened. str*[*size-1] is '\0' in this case too, but the rest of str is
// undefined. The exact cause of the error depends on the underlying platform. The following functions provide
// locale-independent string to number conversions. Copies the size bytes of the string 'a' to the end of the
// result string 's' and zipstr the result string.
void
_yformat_string(char *a, char *s, int size)
{
    int slen;

    YSTRMOVEND(&s);
    slen = strlen(a);
    if (slen > size) {
        PyOS_snprintf(s, size, "%s", &a[slen-size]);
    } else {
        PyOS_snprintf(s, size, "%s", a);
    }
    _yzipstr(s, size, M_LEFT);
}

void
_yformat_double(double a, char *s)
{
    YSTRMOVEND(&s);
    PyOS_snprintf(s, DOUBLE_COLUMN_LEN, "%0.6f", a);
    _yzipstr(s, DOUBLE_COLUMN_LEN, M_RIGHT);
}

void
_yformat_ulong(unsigned long a, char *s)
{
    YSTRMOVEND(&s);
    PyOS_snprintf(s, INT_COLUMN_LEN, "%lu", a);
    _yzipstr(s, INT_COLUMN_LEN, M_RIGHT);
}

void
_yformat_long(long a, char *s)
{
    YSTRMOVEND(&s);
    PyOS_snprintf(s, LONG_COLUMN_LEN, "%ld", a);
    _yzipstr(s, LONG_COLUMN_LEN, M_RIGHT);
}

void
_yformat_int(int a, char *s)
{
    YSTRMOVEND(&s);
    PyOS_snprintf(s, INT_COLUMN_LEN, "%d", a);
    _yzipstr(s, INT_COLUMN_LEN, M_RIGHT);
}

_statitem *
_create_statitem(char *fname, unsigned long callcount, double ttot, double tsub, double tavg)
{
    _statitem *si;

    si = (_statitem *)ymalloc(sizeof(_statitem));
    if (!si)
        return NULL;

    // init the stat item fields.
    memset(si->fname, 0, FUNC_NAME_LEN);
    memset(si->result, 0, LINE_LEN);

    _yformat_string(fname, si->fname, FUNC_NAME_LEN);
    si->callcount = callcount;
    si->ttot = ttot;
    si->tsub = tsub;
    si->tavg = tavg;

    // generate the result string field.
    _yformat_string(fname, si->result, FUNC_NAME_LEN);
    _yformat_ulong(callcount, si->result);
    _yformat_double(tsub, si->result);
    _yformat_double(ttot, si->result);
    _yformat_double(tavg, si->result);


    return si;
}

// inserts items to statshead pointed linked list for later usage according to the
// sorttype param. Note that sorting is descending by default. Read reverse from list
// to have a ascending order.
void
_insert_stats_internal(_statnode *sn, uintptr_t sorttype)
{
    _statnode *p, *prev;

    prev = NULL;
    p = statshead;
    while(p) {
        //dprintf("sn:%p, sn->it:%p : p:%p, p->it:%p.\n", sn, sn->it, p, p->it);
        if (sorttype == STAT_SORT_TIME_TOTAL) {
            if (sn->it->ttot > p->it->ttot)
                break;
        } else if (sorttype == STAT_SORT_CALL_COUNT) {
            if (sn->it->callcount > p->it->callcount)
                break;
        } else if (sorttype == STAT_SORT_TIME_SUB) {
            if (sn->it->tsub > p->it->tsub)
                break;
        } else if (sorttype == STAT_SORT_TIME_AVG) {
            if (sn->it->tavg > p->it->tavg)
                break;
        } else if (sorttype == STAT_SORT_FUNC_NAME) {
            if (strcmp(sn->it->fname, p->it->fname) > 0)
                break;
        }
        prev = p;
        p = p->next;
    }

    // insert at head
    if (!prev) {
        sn->next = statshead;
        statshead = sn;
    } else {
        sn->next = prev->next;
        prev->next = sn;
    }
}

// reverses the statshead list according to a given order.
void
_order_stats_internal(int order)
{
    _statnode *p,*tmp,*pr;

    if (order == STAT_SORT_DESCENDING) {
        ; // nothing to do as internal order is by default descending
    } else if (order == STAT_SORT_ASCENDING) {
        // reverse stat linked list
        pr = tmp = NULL;
        p = statshead;
        while (p != NULL) {
            tmp  = p->next;
            p->next = pr;
            pr = p;
            p = tmp;
        }
        statshead = pr;
    }
}

void
_clear_stats_internal(void)
{
    _statnode *p,*next;

    p = statshead;
    while(p) {
        next = p->next;
        yfree(p->it);
        yfree(p);
        p = next;
    }
    statshead = NULL;
}

static int
_pitenumstat2(_hitem *item, void * arg)
{
    _pit *pt;
    char *fname;
    _statitem *si;
    long long cumdiff;
    _statnode *sni;

    pt = (_pit *)item->val;
    cumdiff = _calc_cumdiff(pt->ttotal, pt->tsubtotal);
    fname = _item2fname(pt);
    if (!fname)
        fname = "N/A";

    // do not show builtins if specified in yappi.start(..)
    if  ((!flags.builtins) && (pt->builtin))
        return 0;

    si = _create_statitem(fname, pt->callcount, pt->ttotal * tickfactor() * flags.timing_sample,
                          cumdiff * tickfactor() * flags.timing_sample,
                          (pt->ttotal * tickfactor() * flags.timing_sample) / pt->callcount);

    if (!si)
        return 1; // abort enumeration
    sni = (_statnode *)ymalloc(sizeof(_statnode));
    if (!sni)
        return 1; // abort enumeration
    sni->it = si;

    _insert_stats_internal(sni, (uintptr_t)arg);

    return 0;
}

static int
_pitenumdel(_hitem *item, void *arg)
{
    _del_pit((_pit *)item->val);
    return 0;
}

static int
_ctxenumdel(_hitem *item, void *arg)
{
    _del_ctx(((_ctx *)item->val) );
    return 0;
}

static int
_ctxenumstat(_hitem *item, void *arg)
{
    char *fname, *tcname;
    _ctx * ctx;
    char temp[LINE_LEN];
    PyObject *buf;

    ctx = (_ctx *)item->val;

    fname = _item2fname(ctx->last_pit);
    if (!fname)
        fname = "N/A";

    memset(temp, 0, LINE_LEN);

    tcname = ctx->class_name;
    if (tcname == NULL)
        tcname = "N/A";

    _yformat_string(tcname, temp, THREAD_NAME_LEN);
    _yformat_long(ctx->id, temp);
    _yformat_string(fname, temp, FUNC_NAME_LEN);
    _yformat_ulong(ctx->sched_cnt, temp);
    _yformat_double(ctx->ttotal * tickfactor(), temp);

#ifdef IS_PY3K  
    buf = PyUnicode_FromString(temp);    
#else
    buf = PyString_FromString(temp);
#endif
    if (!buf)
        return 0; // just continue.

    if (PyList_Append((PyObject *)arg, buf) < 0)
        return 0; // just continue.

    return 0;
}

static PyObject*
stop(PyObject *self, PyObject *args)
{
    if (!yapprunning) {
        PyErr_SetString(YappiProfileError, "profiler is not started yet.");
        return NULL;
    }

    _enum_threads(&_unprofile_thread);

    yapprunning = 0;
    yappstoptick = tickcount();

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
clear_stats(PyObject *self, PyObject *args)
{
    if (yapprunning) {
        PyErr_SetString(YappiProfileError,
                        "profiler is running. Stop profiler before clearing stats.");
        return NULL;
    }

    henum(pits, _pitenumdel, NULL);
    htdestroy(pits);
    henum(contexts, _ctxenumdel, NULL);
    htdestroy(contexts);

    fldestroy(flpit);
    fldestroy(flctx);
    yappinitialized = 0;
    yapphavestats = 0;

// check for mem leaks if DEBUG_MEM is specified
#ifdef DEBUG_MEM
    YMEMLEAKCHECK();
#endif

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject*
get_stats(PyObject *self, PyObject *args)
{

    char *prof_state,*timestr;
    _statnode *p;
    PyObject *buf,*li;
    int order, limit, fcnt;
    uintptr_t type;
    char temp[LINE_LEN];
    long long appttotal;

    li = buf = NULL;

    if (!yapphavestats) {
        PyErr_SetString(YappiProfileError, "profiler do not have any statistics. not started?");
        goto err;
    }

    if (!PyArg_ParseTuple(args, "iii", &type, &order, &limit)) {
        PyErr_SetString(YappiProfileError, "invalid param to get_stats");
        goto err;
    }
    // sorttype/order/limit is in valid bounds?
    if ((type < 0) || (type > STAT_SORT_TYPE_MAX)) {
        PyErr_SetString(YappiProfileError, "sorttype param for get_stats is out of bounds");
        goto err;
    }
    if ((order < 0) || (order > STAT_SORT_ORDER_MAX)) {
        PyErr_SetString(YappiProfileError, "sortorder param for get_stats is out of bounds");
        goto err;
    }
    if (limit < STAT_SHOW_ALL) {
        PyErr_SetString(YappiProfileError, "limit param for get_stats is out of bounds");
        goto err;
    }



    // enum and present stats in a linked list.(statshead)
    henum(pits, _pitenumstat2, (void *)type);
    _order_stats_internal(order);

    li = PyList_New(0);
    if (!li)
        goto err;

#ifdef IS_PY3K
    if (PyList_Append(li, PyUnicode_FromString(STAT_HEADER_STR)) < 0) {
#else
    if (PyList_Append(li, PyString_FromString(STAT_HEADER_STR)) < 0) {
#endif
        goto err;
    }

    fcnt = 0;
    p = statshead;
    while(p) {
        // limit reached?
        if (limit != STAT_SHOW_ALL) {
            if (fcnt == limit)
                break;
        }
#ifdef IS_PY3K
        buf = PyUnicode_FromString(p->it->result);
#else
        buf = PyString_FromString(p->it->result);
#endif
        if (!buf)
            goto err;
        if (PyList_Append(li, buf) < 0)
            goto err;

        Py_DECREF(buf);
        fcnt++;
        p = p->next;
    }
#ifdef IS_PY3K
    if (PyList_Append(li, PyUnicode_FromString(STAT_FOOTER_STR)) < 0) {
#else
    if (PyList_Append(li, PyString_FromString(STAT_FOOTER_STR)) < 0) {
#endif
        goto err;
    }
    
    henum(contexts, _ctxenumstat, (void *)li);
    
#ifdef IS_PY3K
    if (PyList_Append(li, PyUnicode_FromString(STAT_FOOTER_STR2)) < 0) {
#else
    if (PyList_Append(li, PyString_FromString(STAT_FOOTER_STR2)) < 0) {        
#endif
        goto err;
    }
    
    if (yapprunning) {
        appttotal = tickcount()-yappstarttick;
        prof_state = "running";
    } else {
        appttotal = yappstoptick - yappstarttick;
        prof_state = "stopped";
    }

    memset(temp, 0, LINE_LEN);
    _yformat_string(prof_state, temp, DOUBLE_COLUMN_LEN);

    // FIX: Issue #13.
    // ctime() string is a static allocated block of char and it is followed by a '\n'
    // char let's exclude it. See:
    // http://www.cplusplus.com/reference/clibrary/ctime/ctime/
    timestr = ctime(&yappstarttime);
    timestr[strlen(timestr)-1] = '\0';

    _yformat_string(timestr, temp, TIMESTR_COLUMN_LEN);
    _yformat_int(hcount(pits), temp);
    _yformat_int(hcount(contexts), temp);
    _yformat_ulong(ymemusage(), temp);

#ifdef IS_PY3K
    if (PyList_Append(li, PyUnicode_FromString(temp)) < 0) {
#else
    if (PyList_Append(li, PyString_FromString(temp)) < 0) {
#endif
        goto err;
    }

    // clear the internal pit stat items that are generated temporarily.
    _clear_stats_internal();

    return li;
err:
    _clear_stats_internal();
    Py_XDECREF(li);
    Py_XDECREF(buf);
    return NULL;
}

static PyObject*
enum_stats(PyObject *self, PyObject *args)
{
    PyObject *enumfn;

    if (!yapphavestats) {
        PyErr_SetString(YappiProfileError, "profiler do not have any statistics. not started?");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "O", &enumfn)) {
        PyErr_SetString(YappiProfileError, "invalid param to enum_stats");
        return NULL;
    }

    if (!PyCallable_Check(enumfn)) {
        PyErr_SetString(YappiProfileError, "enum function must be callable");
        return NULL;
    }

    henum(pits, _pitenumstat, enumfn);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef yappi_methods[] = {
    {"start", start, METH_VARARGS, NULL},
    {"stop", stop, METH_VARARGS, NULL},
    {"get_stats", get_stats, METH_VARARGS, NULL},
    {"enum_stats", enum_stats, METH_VARARGS, NULL},
    {"clear_stats", clear_stats, METH_VARARGS, NULL},
    {"profile_event", profile_event, METH_VARARGS, NULL}, // for internal usage. do not call this.
    {NULL, NULL}      /* sentinel */
};

#ifdef IS_PY3K
static struct PyModuleDef _yappi_module = {
        PyModuleDef_HEAD_INIT,
        "_yappi",
        _yappi__doc__,
        -1,
        yappi_methods,
        NULL,
        NULL,
        NULL,
        NULL
};
#endif

PyMODINIT_FUNC
#ifdef IS_PY3K
PyInit__yappi(void)
#else
init_yappi(void)
#endif
{
    PyObject *m, *d;

#ifdef IS_PY3K
    m = PyModule_Create(&_yappi_module);
    if (m == NULL)
        return NULL;
#else
    m = Py_InitModule("_yappi",  yappi_methods);
    if (m == NULL)
        return;
#endif        

    d = PyModule_GetDict(m);
    YappiProfileError = PyErr_NewException("_yappi.error", NULL, NULL);
    PyDict_SetItemString(d, "error", YappiProfileError);

    // add int constants
    PyModule_AddIntConstant(m, "SORTTYPE_NAME", STAT_SORT_FUNC_NAME);
    PyModule_AddIntConstant(m, "SORTTYPE_NCALL", STAT_SORT_CALL_COUNT);
    PyModule_AddIntConstant(m, "SORTTYPE_TTOTAL", STAT_SORT_TIME_TOTAL);
    PyModule_AddIntConstant(m, "SORTTYPE_TSUB", STAT_SORT_TIME_SUB);
    PyModule_AddIntConstant(m, "SORTTYPE_TAVG", STAT_SORT_TIME_AVG);
    PyModule_AddIntConstant(m, "SORTORDER_ASCENDING", STAT_SORT_ASCENDING);
    PyModule_AddIntConstant(m, "SORTORDER_DESCENDING", STAT_SORT_DESCENDING);
    PyModule_AddIntConstant(m, "SHOW_ALL", STAT_SHOW_ALL);

    // init the profiler memory and internal constants
    yappinitialized = 0;
    yapphavestats = 0;
    yapprunning = 0;

    if (!_init_profiler()) {
        PyErr_SetString(YappiProfileError, "profiler cannot be initialized.");
#ifdef IS_PY3K
        return NULL;
#else
        return;
#endif
    }
    
#ifdef IS_PY3K
    return m;
#endif
}
