/* SPDX-License-Identifier: GPL-2.0-or-later
 * Explicit kmod metadata for the Linux cross-link only.
 * Xcode generates its own metadata: do not add this file to that target.
 */
#include <mach/mach_types.h>
#include <mach/kmod.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(org.rt3090.experimental, "0.1.0", _start, _stop)
kmod_start_func_t *_realmain = 0;
kmod_stop_func_t *_antimain = 0;
