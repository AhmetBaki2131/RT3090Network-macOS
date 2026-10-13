//
//  CTimeout.cpp
//  AppleIntelWifiAdapter
//
//  Created by 钟先耀 on 2020/1/30.
//  Copyright © 2020 钟先耀. All rights reserved.
//

/*
* Copyright (C) 2020  钟先耀
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation; either version 2 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*/

#include <sys/CTimeout.hpp>

void CTimeout::timeoutOccurred(OSObject* owner, IOTimerEventSource* timer)
{
//    IOLog("itlwm %s\n", __FUNCTION__);
    if (owner == NULL) {
        IOLog("itlwm tm owner == NULL!!!\n");
    }
    CTimeout *tm = OSDynamicCast(CTimeout, owner);
    if (tm == NULL) {
        IOLog("itlwm tm == NULL!!!\n");
        return;
    }
    //callback
    if (tm->tm != timer || !tm->isPending || !tm->to_func) return;
    // The callback may free its own timeout. Retain until it returns.
    tm->retain();
    tm->isPending = false;
    tm->to_func(tm->to_arg);
    tm->release();
}

IOReturn CTimeout::timeout_add_msec(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    IOWorkLoop *wl = (IOWorkLoop*)arg1;
    if(!wl || !arg2) return kIOReturnBadArgument;
    int msecs = *(int*)arg2;
    if(msecs < 0) return kIOReturnBadArgument;
    CTimeout **ccto = (CTimeout **)arg0;
    
    if (ccto == NULL || *ccto == NULL) {
        return kIOReturnError;
    }
    CTimeout *cto = *ccto;
    if (cto->tm == NULL) {
        cto->tm = IOTimerEventSource::timerEventSource(cto, &CTimeout::timeoutOccurred);
        if (cto->tm == NULL) {
            return kIOReturnError;
        }
        cto->tm->enable();
        if(wl->addEventSource(cto->tm)!=kIOReturnSuccess) {
            cto->tm->disable(); cto->tm->release(); cto->tm=nullptr;
            return kIOReturnError;
        }
    }
    if(cto->tm->setTimeoutMS(msecs)!=kIOReturnSuccess) return kIOReturnError;
    cto->isPending = true;
    return kIOReturnSuccess;
}

IOReturn CTimeout::timeout_del(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    CTimeout **ccto = (CTimeout **)arg0;
    if (ccto == NULL || *ccto == NULL) {
        return kIOReturnSuccess;
    }
    CTimeout *cto = *ccto;
    if (cto->tm == NULL) {
        return kIOReturnSuccess;
    }
    cto->tm->cancelTimeout();
    cto->isPending = false;
    return kIOReturnSuccess;
}

IOReturn CTimeout::timeout_free(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    CTimeout **cto = (CTimeout **)arg0;
    IOWorkLoop *wl = (IOWorkLoop*)arg1;
    if (cto == NULL || *cto == NULL) {
        return kIOReturnSuccess;
    }
    CTimeout *tm = *cto;
    if (tm->tm != NULL && !wl) return kIOReturnBadArgument;
    *cto = NULL; // Clear caller slot before releasing the owner.
    tm->isPending = false;
    if (tm->tm != NULL) {
        tm->tm->cancelTimeout();
        tm->tm->disable();
        wl->removeEventSource(tm->tm);
        tm->tm->release();
        tm->tm = NULL;
    }
    tm->release();
    *cto = NULL;
    return kIOReturnSuccess;
}

typedef void (*callback)(void *);

IOReturn CTimeout::timeout_set(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    CTimeout *tm;
    CTimeout **cto = (CTimeout **)arg0;
    if (cto == NULL || arg1 == NULL) {
        return kIOReturnBadArgument;
    }
    if ((*cto) == NULL) {
        *cto = new CTimeout;
        if(!*cto) return kIOReturnNoMemory;
        if(!(*cto)->init()) { (*cto)->release(); *cto=nullptr; return kIOReturnNoMemory; }
        (*cto)->tm=nullptr;
        (*cto)->isPending=false;
    }
    tm = *cto;
    if (tm->tm) tm->tm->cancelTimeout();
    tm->isPending = false;
    tm->to_func = (callback)arg1;
    tm->to_arg = arg2;
    return kIOReturnSuccess;
}

IOReturn CTimeout::timeout_pending(OSObject *target, void *arg0, void *arg1, void *arg2, void *arg3)
{
    CTimeout **cto = (CTimeout **)arg0;
    CTimeout *tm;
    if (cto == NULL) {
        return kIOReturnError;
    }
    tm = *cto;
    if (tm != NULL && tm->isPending) {
        return kIOReturnSuccess;
    }
    return kIOReturnError;
}
