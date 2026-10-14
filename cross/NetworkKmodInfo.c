/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <mach/mach_types.h>
#include <mach/kmod.h>
extern kern_return_t _start(kmod_info_t *,void *);
extern kern_return_t _stop(kmod_info_t *,void *);
KMOD_EXPLICIT_DECL(org.rt3090.network,"0.3.5",_start,_stop)
kmod_start_func_t *_realmain=0;
kmod_stop_func_t *_antimain=0;
