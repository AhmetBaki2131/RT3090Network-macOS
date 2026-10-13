
/* Regression fixture: released 0.3.2 RUN callback. Not a compiled kext source. */
int
rt2860_newstate(struct ieee80211com *ic, enum ieee80211_state nstate, int arg)
{
    if (nstate != ic->ic_state) IOLog("RT3090: state %d -> %d\n",(int)ic->ic_state,(int)nstate);

	struct rt2860_softc *sc = (struct rt2860_softc *)ic->ic_ac.ac_if.if_softc;
	enum ieee80211_state ostate;
	uint32_t tmp;

	ostate = ic->ic_state;
	if (!sc->allow_join && (nstate == IEEE80211_S_AUTH ||
	    nstate == IEEE80211_S_ASSOC || nstate == IEEE80211_S_RUN)) {
		/* Listing nearby networks must not silently join an arbitrary AP. */
		rt2860_set_gp_timer(sc, 0);
		return EBUSY;
	}

	if (ostate == IEEE80211_S_RUN) {
		/* turn link LED off */
		rt2860_set_leds(sc, RT2860_LED_RADIO);
	}

	switch (nstate) {
	case IEEE80211_S_INIT:
		if (ostate == IEEE80211_S_RUN) {
			/* abort TSF synchronization */
			tmp = RAL_READ(sc, RT2860_BCN_TIME_CFG);
			RAL_WRITE(sc, RT2860_BCN_TIME_CFG,
			    tmp & ~(RT2860_BCN_TX_EN | RT2860_TSF_TIMER_EN |
			    RT2860_TBTT_TIMER_EN));
		}
		rt2860_set_gp_timer(sc, 0);
		break;

	case IEEE80211_S_SCAN:
		rt2860_switch_chan(sc, ic->ic_bss->ni_chan);
		if (ostate != IEEE80211_S_SCAN)
			rt2860_set_gp_timer(sc, 150);
		break;

	case IEEE80211_S_AUTH:
	case IEEE80211_S_ASSOC:
		rt2860_set_gp_timer(sc, 0);
		rt2860_switch_chan(sc, ic->ic_bss->ni_chan);
		break;

	case IEEE80211_S_RUN:
		rt2860_set_gp_timer(sc, 0);
		rt2860_switch_chan(sc, ic->ic_bss->ni_chan);

		if (ic->ic_opmode != IEEE80211_M_MONITOR) {
			rt2860_updateslot(ic);
			rt2860_enable_mrr(sc);
			rt2860_set_txpreamble(sc);
			rt2860_set_basicrates(sc);
			rt2860_set_bssid(sc, ic->ic_bss->ni_bssid);
		}

#ifndef IEEE80211_STA_ONLY
		if (ic->ic_opmode == IEEE80211_M_HOSTAP ||
		    ic->ic_opmode == IEEE80211_M_IBSS)
			(void)rt2860_setup_beacon(sc);
#endif

		if (ic->ic_opmode == IEEE80211_M_STA) {
			/* fake a join to init the tx rate */
			rt2860_newassoc(ic, ic->ic_bss, 1);
		}

		if (ic->ic_opmode != IEEE80211_M_MONITOR) {
			rt2860_enable_tsf_sync(sc);
			rt2860_set_gp_timer(sc, 500);
		}

		/* turn link LED on */
		rt2860_set_leds(sc, RT2860_LED_RADIO |
		    (IEEE80211_IS_CHAN_2GHZ(ic->ic_bss->ni_chan) ?
		     RT2860_LED_LINK_2GHZ : RT2860_LED_LINK_5GHZ));
		break;
	}

	return sc->sc_newstate(ic, nstate, arg);
}
