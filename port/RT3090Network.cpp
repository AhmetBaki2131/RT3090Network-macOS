#include "RTConnection.hpp"
/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "RT3090Network.hpp"
#include "rt3090_core.h"
#include <IOKit/network/IONetworkData.h>
#include <IOKit/network/IOOutputQueue.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>
#include <sys/kauth.h>
#include <crypto/sha1.h>
extern int rt2860_attach(void *,int);
extern int rt2860_detach(void *);
extern void rt2860_network_detach(rt2860_softc *);
extern int rt2860_init(struct _ifnet *);
extern void rt2860_stop(struct _ifnet *,int);
extern int rt2860_intr(void *);
extern void rt2860_start(struct _ifnet *);
extern int8_t rt2860_rssi2dbm(rt2860_softc *,uint8_t,uint8_t);
IOWorkLoop *_fWorkloop=nullptr;
IOCommandGate *_fCommandGate=nullptr;
#define super IOEthernetController
OSDefineMetaClassAndStructors(RT3090Network,IOEthernetController)
OSDefineMetaClassAndStructors(CTimeout,OSObject)
bool RT3090Network::createWorkLoop() { if(!loop) loop=IOWorkLoop::workLoop(); return loop!=nullptr; }
IOWorkLoop *RT3090Network::getWorkLoop() const { return loop; }
static uint32_t rawRead(void *p,uint32_t off) { rt2860_softc *s=(rt2860_softc *)p; return bus_space_read_4(s->sc_st,s->sc_sh,off); }
static void rawWrite(void *p,uint32_t off,uint32_t v) { rt2860_softc *s=(rt2860_softc *)p; bus_space_write_4(s->sc_st,s->sc_sh,off,v); }
static void rawDelay(void *,uint32_t us) { IODelay(us); }
IOService *RT3090Network::probe(IOService *provider,SInt32 *score)
{
    IOPCIDevice *device=OSDynamicCast(IOPCIDevice,provider);
    if(!device) { IOLog("RT3090Network: probe rejected non-PCI provider\n"); return nullptr; }
    UInt16 vendor=device->configRead16(kIOPCIConfigVendorID);
    UInt16 product=device->configRead16(kIOPCIConfigDeviceID);
    UInt16 subvendor=device->configRead16(kIOPCIConfigSubSystemVendorID);
    UInt16 subsystem=device->configRead16(kIOPCIConfigSubSystemID);
    IOLog("RT3090Network: probe PCI %04x:%04x subsystem %04x:%04x\n",vendor,product,subvendor,subsystem);
    if(!rt_pci_is_target(vendor,product,subvendor,subsystem)) return nullptr;
    return super::probe(provider,score);
}
bool RT3090Network::start(IOService *provider)
{
    const char *stage="super start";
#if RT3090_ENABLE_NETWORK_EXPERIMENT
    uint8_t eeprom[512]; rt_identity identity; rt_bus bus={&chip,rawRead,rawWrite,rawDelay};
    if(_fWorkloop) { IOLog("RT3090Network: another network stack instance exists\n"); return false; }
#endif
    if(!super::start(provider)) { IOLog("RT3090Network: superclass start failed\n"); return false; }
    stage="PCI provider";
    pci=OSDynamicCast(IOPCIDevice,provider);
    if(!pci) goto fail;
    pci->retain();
    stage="PCI identity";
    if(pci->configRead16(kIOPCIConfigVendorID)!=0x1814 || pci->configRead16(kIOPCIConfigDeviceID)!=0x3090 ||
        pci->configRead16(kIOPCIConfigSubSystemVendorID)!=0x103c || pci->configRead16(kIOPCIConfigSubSystemID)!=0x1453) goto fail;
#if !RT3090_ENABLE_NETWORK_EXPERIMENT
    /* Configuration-space reads only: never open PCI, map BAR, write command,
     * touch EEPROM/firmware, create rings/IRQ, or expose a network interface. */
    setProperty("RT3090Mode","pci-diagnostic");
    setProperty("RT3090WindowsLocationHint","PCIROOT(0)#PCI(1C00)#PCI(0000)");
    setProperty("RT3090PCIMatched",true);
    setProperty("RT3090VendorID",pci->configRead16(kIOPCIConfigVendorID),32);
    setProperty("RT3090DeviceID",pci->configRead16(kIOPCIConfigDeviceID),32);
    setProperty("RT3090SubsystemVendorID",pci->configRead16(kIOPCIConfigSubSystemVendorID),32);
    setProperty("RT3090SubsystemID",pci->configRead16(kIOPCIConfigSubSystemID),32);
    setProperty("RT3090PCIRevision",pci->configRead8(kIOPCIConfigRevisionID),32);
    setProperty("RT3090Status","PCI match only; firmware, MMIO, DMA, IRQ and radio not started");
    IOLog("RT3090Network: PCI-only diagnostic attached; no device writes\n");
    registerService(); return true;
#else
    stage="PCI open";
    if(!pci->open(this)) goto fail;
    opened=true; oldCommand=pci->configRead16(kIOPCIConfigCommand);
    pci->setMemoryEnable(true);
    pci->setBusMasterEnable(false); hardwareClaimed=true;
    stage="BAR0 map";
    chip.sc_st=pci->mapDeviceMemoryWithRegister(kIOPCIConfigBaseAddress0);
    if(!chip.sc_st||chip.sc_st->getLength()<0x8000) goto fail;
    chip.sc_sh=(volatile uint8_t *)chip.sc_st->getVirtualAddress();
    stage="quiesce old DMA";
    // Exclusive PCI owner, bus mastering already off; never expose new rings
    // until the engine is idle. Reject disappearing/failed hardware reads.
    rawWrite(&chip,RT_INT_MASK,0);
    {
        uint32_t config=rawRead(&chip,RT_WPDMA);
        if(config==0xffffffffu) goto fail;
        rawWrite(&chip,RT_WPDMA,config & ~(RT2860_TX_DMA_EN|RT2860_RX_DMA_EN));
        unsigned attempt=0;
        for(;attempt<1000;attempt++) {
            config=rawRead(&chip,RT_WPDMA);
            if(config!=0xffffffffu && !(config&(RT2860_TX_DMA_BUSY|RT2860_RX_DMA_BUSY))) break;
            IODelay(10);
        }
        if(attempt==1000) { IOLog("RT3090: old DMA did not become idle\n"); goto fail; }
    }
    stage="EEPROM read";
    if(rt_read_eeprom(&bus,eeprom)) goto fail;
    stage="EEPROM parse";
    if(rt_parse_eeprom(eeprom,512,&identity)) goto fail;
    stage="EEPROM RF compatibility";
    if(identity.rf_type!=5 && identity.rf_type!=6 && identity.rf_type!=7 && identity.rf_type!=8) goto fail;
    if(!createWorkLoop()) goto fail;
    gate=IOCommandGate::commandGate(this); if(!gate||loop->addEventSource(gate)!=kIOReturnSuccess) goto fail;
    _fWorkloop=loop; _fCommandGate=gate; ownsGlobals=true;
    rtbsd_dma_clear_failure();
    chip.sc_dev.provider=this; chip.controller=this; chip.sc_ic.ic_softc=&chip;
    strlcpy(chip.sc_dev.dv_xname,"rt3090",sizeof(chip.sc_dev.dv_xname));
    stage="backend attach";
    if(rt2860_attach(&chip,0x3090)) goto fail;
    attached=true;
    if(!chip.network_attached || chip.io_failed || !chip.sc_ic.ic_bss) { IOLog("RT3090Network: incomplete BSD/firmware attachment refused\n"); goto fail; }
    irq=IOFilterInterruptEventSource::filterInterruptEventSource(this,interrupt,filter,pci);
    if(!irq||loop->addEventSource(irq)!=kIOReturnSuccess) goto fail;
    irq->disable();
    watch=IOTimerEventSource::timerEventSource(this,tick);
    if(!watch||loop->addEventSource(watch)!=kIOReturnSuccess) goto fail;
    {
        OSDictionary *media=OSDictionary::withCapacity(1);
        IONetworkMedium *medium=IONetworkMedium::medium(kIOMediumEthernetAuto,54000000);
        if(!media||!medium) { if(media) media->release(); if(medium) medium->release(); goto fail; }
        IONetworkMedium::addMedium(media,medium);
        bool valid=publishMediumDictionary(media);
        if(valid) setCurrentMedium(medium);
        medium->release(); media->release(); if(!valid) goto fail;
    }
    stage="network interface";
    if(!attachInterface(&netif,false)) goto fail;
    setProperty("RT3090Mode","network-experimental");
    setProperty("RT3090Status","Experimental network backend; hardware validation pending");
    {
        OSArray *empty=OSArray::withCapacity(1);
        if(empty) { setProperty("RT3090ScanResults",empty); empty->release(); }
    }
    setProperty("RT3090FirmwareAvailable",true);
    if(pci) pci->setProperty("RT3090LastStartError","none");
    setProperty("RT3090DriverVersion","0.3.5");
    setProperty("RT3090Attached",true);
    publishScan();
    netif->registerService(); registerService(); return true;
#endif
fail:
    IOLog("RT3090Network: start rejected at %s\n",stage);
    if(pci) { pci->setProperty("RT3090LastStartError",stage); pci->setProperty("RT3090LastAttemptVersion","0.3.5"); }
    cleanup(); super::stop(provider); return false;
}
bool RT3090Network::configureInterface(IONetworkInterface *interface)
{
    if(!super::configureInterface(interface)) return false;
    IONetworkData *d=interface->getParameter(kIONetworkStatsKey);
    if(!d||!d->getBuffer()) return false;
    chip.sc_ic.ic_ac.ac_if.netStat=(IONetworkStats *)d->getBuffer();
    chip.sc_ic.ic_ac.ac_if.iface=OSDynamicCast(IOEthernetInterface,interface);
    return chip.sc_ic.ic_ac.ac_if.iface!=nullptr;
}
IOReturn RT3090Network::getHardwareAddress(IOEthernetAddress *out)
{
    if(!out||!chip.network_attached) return kIOReturnNotReady;
    memcpy(out->bytes,chip.sc_ic.ic_myaddr,6); return kIOReturnSuccess;
}
IOReturn RT3090Network::selectMedium(const IONetworkMedium *medium)
{
    if(!medium||medium->getType()!=kIOMediumEthernetAuto) return kIOReturnUnsupported;
    return setCurrentMedium(medium)?kIOReturnSuccess:kIOReturnError;
}
IOReturn RT3090Network::updateFilters(OSObject *object,void *kind,void *active,void *,void *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object);
    if(!s) return kIOReturnBadArgument;
    if(kind==(void *)1) s->multicast=active!=nullptr;
    if(kind==(void *)2) s->promiscuous=active!=nullptr;
    if(s->running) {
        uint32_t flags=rawRead(&s->chip,RT2860_RX_FILTR_CFG);
        if(s->multicast||s->promiscuous) flags&=~RT2860_DROP_MC; else flags|=RT2860_DROP_MC;
        if(s->promiscuous) flags&=~RT2860_DROP_UC_NOME; else flags|=RT2860_DROP_UC_NOME;
        rawWrite(&s->chip,RT2860_RX_FILTR_CFG,flags);
    }
    return kIOReturnSuccess;
}
IOReturn RT3090Network::setMulticastMode(bool active) { return gate?gate->runAction(updateFilters,(void *)1,active?(void *)1:nullptr):kIOReturnNotReady; }
IOReturn RT3090Network::setPromiscuousMode(bool active) { return gate?gate->runAction(updateFilters,(void *)2,active?(void *)1:nullptr):kIOReturnNotReady; }
IOReturn RT3090Network::setMulticastList(IOEthernetAddress *addresses,UInt32 count)
{
    if(count&&!addresses) return kIOReturnBadArgument;
    /* RT3090 has a coarse multicast acceptance bit, not an Ethernet hash table.
     * Use all-multicast reception when membership exists; upper layers filter. */
    return setMulticastMode(count!=0);
}
IOReturn RT3090Network::changeState(OSObject *object,void *on,void *,void *,void *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object);
    if(!s||!s->attached) return kIOReturnNotReady;
    if(on) {
        if(s->running) return kIOReturnSuccess;
        if(s->chip.fatal_dma_stop || s->chip.io_failed || rtbsd_dma_failed()) return kIOReturnNotReady;
        s->chip.io_failed=false; rtbsd_dma_clear_failure();
        s->chip.sc_ic.ic_ac.ac_if.if_flags|=IFF_UP;
        s->pci->setBusMasterEnable(true);
        if(rt2860_init(&s->chip.sc_ic.ic_ac.ac_if) || s->chip.io_failed || rtbsd_dma_failed()) {
            rt2860_stop(&s->chip.sc_ic.ic_ac.ac_if,1);
            s->chip.sc_ic.ic_ac.ac_if.if_flags&=~IFF_UP;
            s->pci->setBusMasterEnable(false);
            s->setProperty("RT3090Status","Radio initialization failed; interface stopped");
            s->setProperty("RT3090HardwareFailed",true);
            s->setProperty("RT3090Running",false);
            s->setProperty("RT3090ControlledPortAuthorized",false);
            return kIOReturnError;
        }
        s->running=true; s->irqMask=rawRead(&s->chip,RT_INT_MASK);
        updateFilters(s,nullptr,nullptr,nullptr,nullptr);
        s->irq->enable(); s->watch->setTimeoutMS(1000);
    } else if(s->running) {
        rt_conn_cancel();
        s->irq->disable(); s->watch->cancelTimeout(); s->running=false;
        rt2860_stop(&s->chip.sc_ic.ic_ac.ac_if,1);
        s->chip.sc_ic.ic_ac.ac_if.if_flags&=~IFF_UP;
        s->pci->setBusMasterEnable(false);
        s->setLinkStatus(kIONetworkLinkValid);
    }
    if(!s->running) s->setProperty("RT3090ControlledPortAuthorized",false);
    s->setProperty("RT3090Running",s->running);
    s->setProperty("RT3090HardwareFailed",s->chip.io_failed || s->chip.fatal_dma_stop || rtbsd_dma_failed());
    return kIOReturnSuccess;
}
IOReturn RT3090Network::enable(IONetworkInterface *) { return gate?gate->runAction(changeState,(void *)1):kIOReturnNotReady; }
IOReturn RT3090Network::disable(IONetworkInterface *) { return gate?gate->runAction(changeState,nullptr):kIOReturnNotReady; }
bool RT3090Network::filter(OSObject *object,IOFilterInterruptEventSource *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object);
    if(!s||!s->running) return false;
    uint32_t source=rawRead(&s->chip,RT_INT_SOURCE);
    if(!source||source==0xffffffffu || !(source&s->irqMask)) return false;
    rawWrite(&s->chip,RT_INT_MASK,0); return true;
}
void RT3090Network::interrupt(OSObject *object,IOInterruptEventSource *,int)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object);
    if(!s||!s->running) return;
    rt2860_intr(&s->chip);
    if(s->chip.io_failed || rtbsd_dma_failed()) {
        s->setProperty("RT3090Status","Interrupt hardware error; interface stopped");
        changeState(s,nullptr,nullptr,nullptr,nullptr);
        return;
    }
    rawWrite(&s->chip,RT_INT_MASK,s->irqMask);
}
void RT3090Network::tick(OSObject *object,IOTimerEventSource *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object);
    if(!s||!s->running) return;
    ieee80211com *ic=&s->chip.sc_ic;
    if(ic->ic_bss && rt_conn_tick(ic->ic_state,ic->ic_bss->ni_rsn_supp_state,ic->ic_state==IEEE80211_S_RUN && ic->ic_bss->ni_port_valid!=0 && ic->ic_ac.ac_if.if_link_state==LINK_STATE_UP && !s->chip.io_failed && !rtbsd_dma_failed())) {
        IOLog("RT3090: connection failed code=%u phase=%u supp=%u peer=%u\n",rt_connection.error,
              (unsigned)ic->ic_state,ic->ic_bss->ni_rsn_supp_state,rt_connection.peerStatus);
        s->chip.allow_join=false;
        ieee80211_new_state(ic,IEEE80211_S_INIT,-1);
        s->setProperty("RT3090Status","Connection timed out; see ConnectionErrorCode/EAPOL counters");
    }
    s->publishScan();
    if(s->chip.sc_ic.ic_ac.ac_if.if_watchdog) s->chip.sc_ic.ic_ac.ac_if.if_watchdog(&s->chip.sc_ic.ic_ac.ac_if);
    if(rtbsd_dma_failed() || s->chip.io_failed || s->chip.fatal_dma_stop || !(s->chip.sc_ic.ic_ac.ac_if.if_flags&IFF_RUNNING)) {
        s->setProperty("RT3090Status","Hardware I/O failed; interface stopped");
        changeState(s,nullptr,nullptr,nullptr,nullptr); return;
    }
    if(s->chip.sc_ic.ic_ac.ac_if.if_start) s->chip.sc_ic.ic_ac.ac_if.if_start(&s->chip.sc_ic.ic_ac.ac_if);
    s->watch->setTimeoutMS(1000);
}
IOReturn RT3090Network::sendPacket(OSObject *object,void *arg,void *,void *,void *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object); mbuf_t m=(mbuf_t)arg;
    if(s && (s->chip.io_failed || rtbsd_dma_failed())) { if(m) mbuf_freem(m); return kIOReturnOutputDropped; }
    if(!s||!s->running||s->chip.sc_ic.ic_state!=IEEE80211_S_RUN || !(s->chip.sc_ic.ic_flags&IEEE80211_F_RSNON)) {
        /* Open networks may send once RUN; WPA networks additionally require
         * the stack to have authorized the link, not merely associated. */
        if(!s||!s->running||s->chip.sc_ic.ic_state!=IEEE80211_S_RUN) { if(m) mbuf_freem(m); return kIOReturnOutputDropped; }
    }
    if((s->chip.sc_ic.ic_flags&IEEE80211_F_RSNON)&&s->chip.sc_ic.ic_ac.ac_if.if_link_state!=LINK_STATE_UP) {
        if(m) mbuf_freem(m); return kIOReturnOutputDropped;
    }
    if(!m) return kIOReturnOutputDropped;
    // The BSD queue consumes m on both success and failure. Never free twice.
    if(if_enqueue(&s->chip.sc_ic.ic_ac.ac_if,m)) return kIOReturnOutputDropped;
    rt2860_start(&s->chip.sc_ic.ic_ac.ac_if); return kIOReturnOutputSuccess;
}
UInt32 RT3090Network::outputPacket(mbuf_t m,void *) {
    if(!gate) { if(m) mbuf_freem(m); return kIOReturnOutputDropped; }
    return (UInt32)gate->runAction(sendPacket,m);
}
void RT3090Network::publishScan()
{
    publishStatus();
    OSArray *array=OSArray::withCapacity(32); if(!array) return;
    ieee80211_node *node;
    RB_FOREACH(node,ieee80211_tree,&chip.sc_ic.ic_tree) {
        if(array->getCount()>=128) break;
        if(node->ni_esslen>32 || !node->ni_chan) continue;
        OSDictionary *item=OSDictionary::withCapacity(8); if(!item) break;
        OSData *ssid=OSData::withBytes(node->ni_essid,node->ni_esslen);
        OSData *bssid=OSData::withBytes(node->ni_bssid,6);
        OSNumber *channel=OSNumber::withNumber(ieee80211_chan2ieee(&chip.sc_ic,node->ni_chan),32);
        if(ssid&&bssid&&channel) { item->setObject("SSID",ssid); item->setObject("BSSID",bssid); item->setObject("Channel",channel);
            OSNumber *signal=OSNumber::withNumber((uint32_t)(int32_t)rt2860_rssi2dbm(&chip,node->ni_rssi,0),32);
            if(signal) { item->setObject("EstimatedRSSIdBm",signal); signal->release(); }
            const char *security=(node->ni_supported_rsnprotos&IEEE80211_PROTO_RSN)?
                ((node->ni_rsnciphers&IEEE80211_CIPHER_CCMP)?"WPA2/CCMP":"WPA2/other"):
                (node->ni_supported_rsnprotos&IEEE80211_PROTO_WPA)?"WPA":(node->ni_capinfo&IEEE80211_CAPINFO_PRIVACY)?"WEP/unknown":"Open";
            OSString *label=OSString::withCString(security);
            if(label) { item->setObject("Security",label); label->release(); }
            array->setObject(item); }
        if(ssid) ssid->release(); if(bssid) bssid->release(); if(channel) channel->release(); item->release();
    }
    setProperty("RT3090ScanResults",array); array->release();
}
void RT3090Network::publishStatus()
{
    setProperty("RT3090RSNEnabled",(chip.sc_ic.ic_flags&IEEE80211_F_RSNON)!=0);
    setProperty("RT3090ConnectionPhase",rt_connection.phase,32);
    setProperty("RT3090ConnectionPhaseTicks",rt_connection.seconds,32);
    setProperty("RT3090ConnectionErrorCode",rt_connection.error,32);
    setProperty("RT3090PeerStatusCode",rt_connection.peerStatus,32);
    setProperty("RT3090EAPOLM1RX",rt_connection.rxM1,32);
    setProperty("RT3090EAPOLM3RX",rt_connection.rxM3,32);
    setProperty("RT3090EAPOLM2Queued",rt_connection.txM2,32);
    setProperty("RT3090EAPOLM4Queued",rt_connection.txM4,32);
    setProperty("RT3090EAPOLTXFailures",rt_connection.txFailures,32);
    setProperty("RT3090KeyInstallCount",rt_connection.keyInstalls,32);
    setProperty("RT3090BadMICCount",rt_connection.badMic,32);
    setProperty("RT3090HardwareTXSubmitted",rt_connection.hardwareTx,32);
    setProperty("RT3090EAPOLHardwareTXSubmitted",rt_connection.hardwareEapolTx,32);
    setProperty("RT3090AssociationState",chip.sc_ic.ic_state,32);
    setProperty("RT3090LinkState",chip.sc_ic.ic_ac.ac_if.if_link_state,32);
    if(chip.sc_ic.ic_bss) {
        setProperty("RT3090SelectedRSNProtocol",chip.sc_ic.ic_bss->ni_rsnprotos,32);
        setProperty("RT3090SelectedCipher",chip.sc_ic.ic_bss->ni_rsncipher,32);
        setProperty("RT3090SelectedAKM",chip.sc_ic.ic_bss->ni_rsnakms,32);
        setProperty("RT3090WPA2SupplicantState",chip.sc_ic.ic_bss->ni_rsn_supp_state,32);
        setProperty("RT3090ControlledPortAuthorized",running && chip.sc_ic.ic_state==IEEE80211_S_RUN && chip.sc_ic.ic_bss->ni_port_valid!=0 && chip.sc_ic.ic_ac.ac_if.if_link_state==LINK_STATE_UP && !chip.io_failed && !rtbsd_dma_failed());
        setProperty("RT3090EAPOLRetries",chip.sc_ic.ic_bss->ni_rsn_retries,32);
    }
    if(netif) {
        char name[32]; snprintf(name,sizeof(name),"%s%u",netif->getNamePrefix(),netif->getUnitNumber());
        setProperty("RT3090InterfaceName",name);
    }
    setProperty("RT3090Running",running);
    setProperty("RT3090HardwareFailed",chip.io_failed || chip.fatal_dma_stop || rtbsd_dma_failed());
}
IOReturn RT3090Network::control(OSObject *object,void *arg,void *derived,void *,void *)
{
    RT3090Network *s=OSDynamicCast(RT3090Network,object); OSDictionary *d=(OSDictionary *)arg;
    if(!s || !d) return kIOReturnBadArgument;
    OSString *command=OSDynamicCast(OSString,d->getObject("Command"));
    if(!command||!s->running) return kIOReturnNotReady;
    ieee80211com *ic=&s->chip.sc_ic;
    if(command->isEqualTo("scan")) {
        rt_conn_cancel();
        s->chip.allow_join=false;
        ieee80211_new_state(ic,IEEE80211_S_INIT,-1);
        return ic->ic_newstate(ic,IEEE80211_S_SCAN,-1)==0?kIOReturnSuccess:kIOReturnError;
    }
    if(command->isEqualTo("disconnect")) {
        rt_conn_cancel();
        s->chip.allow_join=false; ieee80211_new_state(ic,IEEE80211_S_INIT,-1); return kIOReturnSuccess;
    }
    if(!command->isEqualTo("join")) return kIOReturnUnsupported;
    OSData *ssid=OSDynamicCast(OSData,d->getObject("SSID")); OSData *password=OSDynamicCast(OSData,d->getObject("Password"));
    if(!ssid||ssid->getLength()<1||ssid->getLength()>32||!password||password->getLength()<8||password->getLength()>63) return kIOReturnBadArgument;
    if(!derived) return kIOReturnBadArgument;
    const uint8_t *pmk=(const uint8_t *)derived;
    ieee80211_new_state(ic,IEEE80211_S_INIT,-1);
    ieee80211_disable_rsn(ic); ieee80211_disable_wep(ic);
    ic->ic_des_esslen=ssid->getLength(); bzero(ic->ic_des_essid,sizeof(ic->ic_des_essid));
    memcpy(ic->ic_des_essid,ssid->getBytesNoCopy(),ssid->getLength()); ic->ic_flags&=~IEEE80211_F_AUTO_JOIN;
    memcpy(ic->ic_psk,pmk,32); ic->ic_flags|=IEEE80211_F_PSK;
    ieee80211_wpaparams parameters={}; parameters.i_enabled=1; parameters.i_protos=IEEE80211_WPA_PROTO_WPA2;
    parameters.i_akms=IEEE80211_WPA_AKM_PSK; parameters.i_ciphers=IEEE80211_WPA_CIPHER_CCMP; parameters.i_groupcipher=IEEE80211_WPA_CIPHER_CCMP;
    int wpa_result=ieee80211_ioctl_setwpaparms(ic,&parameters);
    if(wpa_result!=0 && wpa_result!=ENETRESET) {
        IOLog("RT3090: WPA2 parameter error %d\n",wpa_result); return kIOReturnError;
    }
    // ENETRESET means settings applied; INIT was already requested above,
    // and the scan below begins association with the new parameters.
    rt_conn_reset();
    s->chip.allow_join=true;
    int result=ic->ic_newstate(ic,IEEE80211_S_SCAN,-1);
    if(result) rt_conn_cancel();
    s->publishStatus();
    return result==0?kIOReturnSuccess:kIOReturnError;
}
IOReturn RT3090Network::setProperties(OSObject *object)
{
    if(kauth_cred_getuid(kauth_cred_get()) != 0) return kIOReturnNotPrivileged;
#if !RT3090_ENABLE_NETWORK_EXPERIMENT
    (void)object;
    return kIOReturnUnsupported; /* No property may turn diagnostics into radio/DMA. */
#else
    OSDictionary *dict=OSDynamicCast(OSDictionary,object);
    if(!dict||!gate) return kIOReturnBadArgument;
    /* Never pass credentials to super::setProperties or publish them in IORegistry. */
    OSString *command=OSDynamicCast(OSString,dict->getObject("Command"));
    if(!command) return kIOReturnBadArgument;
    if(!command->isEqualTo("join")) return gate->runAction(control,dict);
    OSData *ssid=OSDynamicCast(OSData,dict->getObject("SSID"));
    OSData *password=OSDynamicCast(OSData,dict->getObject("Password"));
    if(!ssid || ssid->getLength()<1 || ssid->getLength()>32 || !password || password->getLength()<8 || password->getLength()>63)
        return kIOReturnBadArgument;
    char pass[64]={}; uint8_t pmk[32]={};
    memcpy(pass,password->getBytesNoCopy(),password->getLength());
    // Expensive key derivation must not block the IRQ/timer workloop gate.
    int rc=rt_memchr(pass,0,password->getLength()) ? -1 :
        pbkdf2_sha1(pass,(const uint8_t *)ssid->getBytesNoCopy(),ssid->getLength(),4096,pmk,32);
    for(unsigned i=0;i<sizeof(pass);i++) ((volatile char *)pass)[i]=0;
    IOReturn result=rc ? kIOReturnBadArgument : gate->runAction(control,dict,pmk);
    for(unsigned i=0;i<sizeof(pmk);i++) ((volatile uint8_t *)pmk)[i]=0;
    return result;
#endif
}
void RT3090Network::cleanup()
{
    if(gate&&running) gate->runAction(changeState,nullptr);
    if(irq) { irq->disable(); if(loop) loop->removeEventSource(irq); irq->release(); irq=nullptr; }
    if(watch) { watch->cancelTimeout(); if(loop) loop->removeEventSource(watch); watch->release(); watch=nullptr; }
    if(attached) {
        if(gate) gate->runAction([](OSObject *owner,void *,void *,void *,void *) -> IOReturn {
            RT3090Network *s=OSDynamicCast(RT3090Network,owner);
            if(!s) return kIOReturnBadArgument;
            rt2860_network_detach(&s->chip); return kIOReturnSuccess;
        });
        else rt2860_network_detach(&chip);
        rt2860_detach(&chip);
        attached=false;
    }
    if(netif) { detachInterface(netif,true); netif->release(); netif=nullptr; }
    if(ownsGlobals) { _fCommandGate=nullptr; _fWorkloop=nullptr; ownsGlobals=false; }
    if(gate) { if(loop) loop->removeEventSource(gate); gate->release(); gate=nullptr; }
    if(chip.sc_st) { chip.sc_st->release(); chip.sc_st=nullptr; chip.sc_sh=nullptr; }
    if(pci) {
        if(opened) { if(hardwareClaimed) pci->setBusMasterEnable(false); pci->configWrite16(kIOPCIConfigCommand,hardwareClaimed?(oldCommand&~kIOPCICommandBusMaster):oldCommand); pci->close(this); opened=false; }
        pci->release(); pci=nullptr;
    }
}
void RT3090Network::stop(IOService *provider) { cleanup(); super::stop(provider); }
void RT3090Network::free() { cleanup(); if(loop) { loop->release(); loop=nullptr; } super::free(); }
