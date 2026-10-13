/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include <stdint.h>
// Accessed only under the singleton driver's workloop gate.
enum RTConnectionError { RT_CONN_OK=0, RT_CONN_SCAN_TIMEOUT=101, RT_CONN_AUTH_TIMEOUT=102,
 RT_CONN_ASSOC_TIMEOUT=103, RT_CONN_M1_TIMEOUT=104, RT_CONN_M3_TIMEOUT=105, RT_CONN_PORT_TIMEOUT=106,
 RT_CONN_AUTH_REJECT=201, RT_CONN_ASSOC_REJECT=202, RT_CONN_UNEXPECTED_M1=203,
 RT_CONN_TX_M2=301, RT_CONN_TX_M4=302, RT_CONN_BAD_MIC=303, RT_CONN_KEY_INSTALL=304 };
struct RTConnectionTrace {
 bool active; uint32_t phase,supp,seconds,error,peerStatus;
 uint32_t rxM1,rxM3,txM2,txM4,txFailures,keyInstalls,badMic,hardwareTx,hardwareEapolTx;
};
extern RTConnectionTrace rt_connection;
void rt_conn_reset();
void rt_conn_cancel();
void rt_conn_rx(unsigned message);
void rt_conn_tx(unsigned message,int result);
void rt_conn_peer(unsigned phase,unsigned status);
void rt_conn_error(unsigned error);
int rt_conn_key(int result);
bool rt_conn_tick(unsigned phase,unsigned supp,bool authorized);
