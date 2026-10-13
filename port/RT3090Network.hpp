/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RT3090_NETWORK_HPP
#define RT3090_NETWORK_HPP
#include "RTBSDCompat.hpp"
#include <IOKit/IOCommandGate.h>
#include <IOKit/IOFilterInterruptEventSource.h>
#include <IOKit/IOTimerEventSource.h>
#include <IOKit/network/IOEthernetInterface.h>
class RT3090Network : public IOEthernetController {
    OSDeclareDefaultStructors(RT3090Network)
public:
    IOService *probe(IOService *,SInt32 *) override;
    bool start(IOService *) override;
    void stop(IOService *) override;
    void free() override;
    bool createWorkLoop() override;
    IOWorkLoop *getWorkLoop() const override;
    IOReturn getHardwareAddress(IOEthernetAddress *) override;
    bool configureInterface(IONetworkInterface *) override;
    IOReturn enable(IONetworkInterface *) override;
    IOReturn disable(IONetworkInterface *) override;
    UInt32 outputPacket(mbuf_t,void *) override;
    IOReturn selectMedium(const IONetworkMedium *) override;
    IOReturn setMulticastMode(bool) override;
    IOReturn setPromiscuousMode(bool) override;
    IOReturn setMulticastList(IOEthernetAddress *,UInt32) override;
    IOReturn setProperties(OSObject *) override;
private:
    rt2860_softc chip={};
    IOPCIDevice *pci=nullptr;
    IOWorkLoop *loop=nullptr;
    IOCommandGate *gate=nullptr;
    IOFilterInterruptEventSource *irq=nullptr;
    IOTimerEventSource *watch=nullptr;
    IONetworkInterface *netif=nullptr;
    bool opened=false, attached=false, running=false, ownsGlobals=false, hardwareClaimed=false;
    UInt16 oldCommand=0;
    UInt32 irqMask=0;
    bool multicast=false, promiscuous=false;
    static IOReturn updateFilters(OSObject *,void *,void *,void *,void *);
    static bool filter(OSObject *,IOFilterInterruptEventSource *);
    static void interrupt(OSObject *,IOInterruptEventSource *,int);
    static void tick(OSObject *,IOTimerEventSource *);
    static IOReturn changeState(OSObject *,void *,void *,void *,void *);
    static IOReturn sendPacket(OSObject *,void *,void *,void *,void *);
    static IOReturn control(OSObject *,void *,void *,void *,void *);
    void publishScan();
    void publishStatus();
    void cleanup();
};
#endif
