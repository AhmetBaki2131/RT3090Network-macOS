/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <IOKit/network/IOEthernetController.h>
#include <libkern/libkern.h>
#include <IOKit/IOTypes.h>
#include <machine/types.h>
#define CTimeout RT3090Timeout

/* Normal build enables the network backend; diagnostic builds override this to zero. */
#ifndef RT3090_ENABLE_NETWORK_EXPERIMENT
#define RT3090_ENABLE_NETWORK_EXPERIMENT 1
#endif
