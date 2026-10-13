#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=r'''
#include <cassert>
#include "RTConnection.hpp"
int main(){
 rt_conn_reset();rt_conn_rx(1);rt_conn_tx(2,0);rt_conn_rx(3);rt_conn_tx(4,0);rt_conn_key(0);
 assert(rt_connection.rxM1==1&&rt_connection.rxM3==1&&rt_connection.txM2==1&&rt_connection.txM4==1);
 assert(!rt_conn_tick(4,3,true)&&!rt_connection.active&&!rt_connection.error);
 rt_conn_reset();rt_conn_tx(2,12);assert(rt_connection.txM2==0&&rt_connection.txFailures==1&&rt_connection.error==301);
 rt_conn_reset();for(int i=0;i<14;i++)assert(!rt_conn_tick(2,0,false));assert(rt_conn_tick(2,0,false)&&rt_connection.error==102);
 rt_conn_reset();for(int i=0;i<15;i++)rt_conn_tick(3,0,false);assert(rt_connection.error==103);
 rt_conn_reset();for(int i=0;i<15;i++)rt_conn_tick(4,1,false);assert(rt_connection.error==104);
 rt_conn_reset();for(int i=0;i<14;i++)rt_conn_tick(4,1,false);assert(!rt_conn_tick(4,2,false));
 for(int i=0;i<14;i++)rt_conn_tick(4,2,false);assert(rt_connection.error==105);
 rt_conn_reset();rt_conn_error(RT_CONN_BAD_MIC);for(int i=0;i<15;i++)rt_conn_tick(4,2,false);assert(rt_connection.error==303&&rt_connection.badMic==1);
 rt_conn_reset();rt_conn_peer(3,17);for(int i=0;i<15;i++)rt_conn_tick(3,0,false);assert(rt_connection.error==202&&rt_connection.peerStatus==17);
 rt_conn_reset();rt_conn_cancel();for(int i=0;i<99;i++)assert(!rt_conn_tick(4,0,false));assert(!rt_connection.error);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(s)
 subprocess.run(['c++','-fsanitize=address,undefined','-I'+str(r/'port'),str(p/'test.cpp'),str(r/'port/RTConnection.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real progress model: M1/M2/M3/M4 counters, failed queues, AUTH/ASSOC/M1/M3 timeouts, phase reset, MIC/peer failure, authorized/cancelled stop; no handshake or hardware proof.')
