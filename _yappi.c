/*

 yappi
 Yet Another Python Profiler

 Sumer Cip 2011

*/

#include "_ystatic.h"

#if !defined(HAVE_LONG_LONG)
#error "Yappi requires long longs!"
#endif
#ifdef IS_PY3K
#include "bytesobject.h"
#endif

#include "frameobject.h"
#include "_ycallstack.h"
#include "_yhashtab.h"
#include "_ydebug.h"
#include "_ytiming.h"
#include "_yfreelist.h"
#include "_ymem.h"

#ifdef IS_PY3K
PyDoc_STRVAR(_yappi__doc__, "Yet Another Python Profiler");
#endif

// module definitions
typedef struct {
    PyObject *co; // CodeObject or MethodDef descriptive string.
    unsigned long callcount;
    long long tsubtotal;
    long long ttotal;
    int builtin;
} _pit; // profile_item

typedef struct {
    _cstack *cs;
    long id;
    _pit *last_pit;
    unsigned long sched_cnt;
    char *class_name;
} _ctx; // context

typedef struct {
    int builtins;
} _flag; // flags passed from yappi.start()

// Issue #25: Python debug build reference count fix.
typedef struct {
    char *c_str;
    PyObject *py_str;
} _mstr;

// profiler global vars
static PyObject *YappiProfileError;
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
    ctx->id = 0;
    ctx->class_name = NULL;
    return ctx;
}

// extracts the function name from a given pit. Note that pit->co may be
// either a PyCodeObject or a descriptive string.
static _mstr
_item2fname(_pit *pt)
{
    _mstr result;

    result.c_str = "N/A";
    result.py_str = NULL;
    
    if (!pt) {
        return result;
    }

    if (PyCode_Check(pt->co)) {
#ifdef IS_PY3K
    result.py_str =  PyUnicode_FromFormat( "%U.%U:%d",
    								(((PyCodeObject *)pt->co)->co_filename),
    								(((PyCodeObject *)pt->co)->co_name),
                                    ((PyCodeObject *)pt->co)->co_firstlineno );
#else
    result.py_str =  PyString_FromFormat( "%s.%s:%d",
                                    PyString_AS_STRING(((PyCodeObject *)pt->co)->co_filename),
                                    PyString_AS_STRING(((PyCodeObject *)pt->co)->co_name),
                                    ((PyCodeObject *)pt->co)->co_firstlineno );
#endif
    } else {
        result.py_str = pt->co;
    }
    
#ifdef IS_PY3K    
    result.c_str = PyBytes_AS_STRING(PyUnicode_AsUTF8String(result.py_str));
#else
    result.c_str = PyString_AS_STRING(result.py_str); 
#endif    
    if (!result.c_str) {
        result.c_str = "N/A";
    }
    return result;
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
    return PyBytes_AS_STRING(PyUnicode_AsUTF8String(tattr2));
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
                modname = PyBytes_AS_STRING(PyUnicode_AsUTF8String(mod));
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

    hci->t0 = tickcount();
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
_call_leave(PyObject *self, PyFrameObject *frame, PyObject *arg, int ccall)
{
    _pit *cp, *pp;
    _cstackitem *ci,*pi;
    long long elapsed;
   
    ci = spop(current_ctx->cs);
    if (!ci) {   
        return; // leaving a frame while callstack is empty
    }
    cp = ci->ckey;

    elapsed = tickcount() - ci->t0;
    
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
    } else {
        cp->ttotal += elapsed;
    }

    // update parent's sub total if recursive above code will extract the subtotal and
    // below code will have no effect.
    pp->tsubtotal += elapsed;
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
        _call_leave(self, frame, arg, 0);
        break;

#ifdef PyTrace_C_CALL	// not defined in Python <= 2.3 
    case PyTrace_C_CALL:
        if (PyCFunction_Check(arg))
            _call_enter(self, frame, arg, 1); // set ccall to true
        break;

    case PyTrace_C_RETURN:
    case PyTrace_C_EXCEPTION:
        if (PyCFunction_Check(arg))
            _call_leave(self, frame, arg, 1);
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
    ev = PyBytes_AS_STRING(PyUnicode_AsUTF8String(event));
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

    if (!PyArg_ParseTuple(args, "i", &flags.builtins))
        return NULL;

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

static int
_ctxenumstat(_hitem *item, void *arg)
{
    PyObject *efn;
    char *tcname;
    _mstr fname_s;
    _ctx * ctx;

    ctx = (_ctx *)item->val;

    fname_s = _item2fname(ctx->last_pit);
    tcname = ctx->class_name;
    if (tcname == NULL)
        tcname = "N/A";
    efn = (PyObject *)arg;
    
    PyObject_CallFunction(efn, "((sksk))", tcname, ctx->id, fname_s.c_str, ctx->sched_cnt);
    
    if (ctx->last_pit) {
        if (PyCode_Check(ctx->last_pit->co)) {
            Py_DECREF(fname_s.py_str);
        }
    }
    
    return 0;
           
}

static PyObject*
enum_thread_stats(PyObject *self, PyObject *args)
{
    PyObject *enumfn;

    if (!yapphavestats) {
        PyErr_SetString(YappiProfileError, "profiler do not have any statistics. not started?");
        return NULL;
    }

    if (!PyArg_ParseTuple(args, "O", &enumfn)) {
        PyErr_SetString(YappiProfileError, "invalid param to enum_thread_stats");
        return NULL;
    }

    if (!PyCallable_Check(enumfn)) {
        PyErr_SetString(YappiProfileError, "enum function must be callable");
        return NULL;
    }
    
    henum(contexts, _ctxenumstat, enumfn);

    Py_INCREF(Py_None);
    return Py_None;
}


static int
_pitenumstat(_hitem *item, void * arg)
{
    long long cumdiff;
    PyObject *efn;
    _mstr fname_s;
    _pit *pt;

    pt = (_pit *)item->val;
    // do not show builtin pits if specified
    if  ((!flags.builtins) && (pt->builtin))
        return 0;
    
    cumdiff = _calc_cumdiff(pt->ttotal, pt->tsubtotal);
    efn = (PyObject *)arg;

    fname_s = _item2fname(pt);
    
    PyObject_CallFunction(efn, "((skff))", fname_s.c_str, pt->callcount, pt->ttotal * tickfactor(),
                          cumdiff * tickfactor());
    if (pt) {
        if (PyCode_Check(pt->co)) {
            Py_DECREF(fname_s.py_str);
        }
    }
    
    return 0;
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

static PyObject *
is_running(PyObject *self, PyObject *args)
{
    return Py_BuildValue("i", yapprunning);
}


static PyMethodDef yappi_methods[] = {
    {"start", start, METH_VARARGS, NULL},
    {"stop", stop, METH_VARARGS, NULL},
    {"enum_stats", enum_stats, METH_VARARGS, NULL},
    {"enum_thread_stats", enum_thread_stats, METH_VARARGS, NULL},
    {"clear_stats", clear_stats, METH_VARARGS, NULL},
    {"is_running", is_running, METH_VARARGS, NULL},
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
