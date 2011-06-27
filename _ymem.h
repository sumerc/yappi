#ifndef YMEM_H
#define YMEM_H

#include "_ystatic.h"
#include "_ydebug.h"

struct dnode {
    void *ptr;
    unsigned int size;
    struct dnode *next;
};
typedef struct dnode dnode_t;

void *ymalloc(size_t size);
void yfree(void *p);
unsigned long ymemusage(void);
void YMEMLEAKCHECK(void);

#endif

