#define _GNU_SOURCE
#include <mujoco/mujoco.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

typedef void (*FD)(const mjModel*, mjData*, mjtNum, mjtByte,
                   mjtNum*, mjtNum*, mjtNum*, mjtNum*);
static FD real_fd;
static int clear_seed, log_fd;
static _Atomic unsigned long count;
static uint64_t now_ns(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC, &ts)) _exit(91);
  return (uint64_t)ts.tv_sec*1000000000ULL + (uint64_t)ts.tv_nsec;
}
static uint64_t hash(const mjtNum* x, int n) {
  uint64_t h=14695981039346656037ULL;
  const unsigned char* p=(const unsigned char*)x;
  for (size_t i=0;i<(size_t)n*sizeof(mjtNum);++i) { h^=p[i]; h*=1099511628211ULL; }
  return h;
}
static void append(const char* text, int n) {
  if (n<=0 || n>=768 || write(log_fd,text,(size_t)n)!=n) _exit(92);
}
__attribute__((constructor)) static void init(void) {
  const char* mode=getenv("GO2_FD_WARMSTART_MODE");
  const char* path=getenv("GO2_FD_WARMSTART_LOG");
  if (!mode || !path || (strcmp(mode,"retain") && strcmp(mode,"zero"))) _exit(93);
  clear_seed=!strcmp(mode,"zero");
  real_fd=(FD)dlsym(RTLD_NEXT,"mjd_transitionFD");
  Dl_info info;
  if (!real_fd || !dladdr((void*)real_fd,&info) || !info.dli_fname) _exit(94);
  log_fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_APPEND,0600);
  if (log_fd<0) _exit(95);
  char record[768];
  int n=snprintf(record,sizeof(record),"{\"mode\":\"%s\",\"delegate\":\"%s\"}\n",
                 mode,info.dli_fname);
  append(record,n);
}
void mjd_transitionFD(const mjModel* m, mjData* d, mjtNum eps, mjtByte centered,
                      mjtNum* A, mjtNum* B, mjtNum* C, mjtNum* D) {
  if (m->nv!=18 || !d->qacc_warmstart) _exit(96);
  unsigned long index=atomic_fetch_add(&count,1)+1;
  uint64_t start=now_ns(), before=hash(d->qacc_warmstart,m->nv);
  if (clear_seed) for (int i=0;i<m->nv;++i) d->qacc_warmstart[i]=0.0;
  uint64_t effective=hash(d->qacc_warmstart,m->nv);
  int zero=1;
  for (int i=0;i<m->nv;++i) if (d->qacc_warmstart[i]!=0.0) zero=0;
  real_fd(m,d,eps,centered,A,B,C,D);
  uint64_t end=now_ns();
  char record[768];
  int n=snprintf(record,sizeof(record),
       "{\"index\":%lu,\"tid\":%ld,\"start_ns\":%llu,\"end_ns\":%llu,"
       "\"before_hash\":\"%016llx\",\"effective_hash\":\"%016llx\",\"effective_zero\":%s}\n",
       index,(long)syscall(SYS_gettid),(unsigned long long)start,(unsigned long long)end,
       (unsigned long long)before,(unsigned long long)effective,zero?"true":"false");
  append(record,n);
}
