/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "RTConnection.hpp"
RTConnectionTrace rt_connection={};
void rt_conn_reset() { rt_connection=RTConnectionTrace{};rt_connection.active=true; }
void rt_conn_cancel() { rt_connection.active=false; }
void rt_conn_error(unsigned error) { rt_connection.error=error;if(error==RT_CONN_BAD_MIC)++rt_connection.badMic; }
void rt_conn_rx(unsigned message) { if(message==1)++rt_connection.rxM1;if(message==3)++rt_connection.rxM3; }
void rt_conn_tx(unsigned message,int result) {
 if(result) { ++rt_connection.txFailures;rt_conn_error(message==2?RT_CONN_TX_M2:RT_CONN_TX_M4); }
 else { if(message==2)++rt_connection.txM2;if(message==4)++rt_connection.txM4; }
}
void rt_conn_peer(unsigned phase,unsigned status) { rt_connection.peerStatus=status;if(status)rt_conn_error(phase==2?RT_CONN_AUTH_REJECT:RT_CONN_ASSOC_REJECT); }
int rt_conn_key(int result) { if(result)rt_conn_error(RT_CONN_KEY_INSTALL);else ++rt_connection.keyInstalls;return result; }
bool rt_conn_tick(unsigned phase,unsigned supp,bool authorized) {
 if(!rt_connection.active)return false;
 if(authorized) {rt_connection.active=false;rt_connection.error=0;return false;}
 if(phase!=rt_connection.phase || supp!=rt_connection.supp) {rt_connection.phase=phase;rt_connection.supp=supp;rt_connection.seconds=0;}
 ++rt_connection.seconds;
 unsigned limit=phase==1?30:15;
 if(phase==4)limit=supp==3?5:15;
 if(rt_connection.seconds<limit)return false;
 unsigned error=phase==1?RT_CONN_SCAN_TIMEOUT:phase==2?RT_CONN_AUTH_TIMEOUT:phase==3?RT_CONN_ASSOC_TIMEOUT:
     supp<=1?RT_CONN_M1_TIMEOUT:supp==2?RT_CONN_M3_TIMEOUT:RT_CONN_PORT_TIMEOUT;
 // Preserve explicit peer rejection/MIC/key failure as the more precise reason.
 if(!rt_connection.error)rt_connection.error=error;
 rt_connection.active=false;return true;
}
