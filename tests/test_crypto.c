/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "crypto-host/windows.h"
#include <crypto/sha1.h>
#include <crypto/hmac.h>
#include <crypto/rijndael.h>
static unsigned checks;
#define CHECK(x) do { checks++; if(!(x)) { fprintf(stderr,"crypto test failed line %d\n",__LINE__); exit(1); } } while(0)
static void expect(const unsigned char *p,unsigned n,const char *hex)
{
    for(unsigned i=0;i<n;i++) {
        unsigned value; CHECK(sscanf(hex+i*2,"%2x",&value)==1); CHECK(p[i]==value);
    }
}
int main(void)
{
    SHA1_CTX sha; unsigned char digest[32];
    SHA1Init(&sha); SHA1Update(&sha,"abc",3); SHA1Final(digest,&sha);
    expect(digest,20,"a9993e364706816aba3e25717850c26c9cd0d89d");
    unsigned char key[20]; memset(key,0x0b,sizeof(key));
    CHECK(hmac_sha1(key,20,(const unsigned char *)"Hi There",8,digest)==0);
    expect(digest,20,"b617318655057264e28bc0b6fb378c8ef146be00");
    CHECK(pbkdf2_sha1("password",(const unsigned char *)"salt",4,1,digest,20)==0);
    expect(digest,20,"0c60c80f961f0e71f3a9b524af6012062fe037a6");
    CHECK(pbkdf2_sha1("password",(const unsigned char *)"IEEE",4,4096,digest,32)==0);
    expect(digest,32,"f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e");
    rijndael_ctx aes; unsigned char aeskey[16],plain[16],cipher[16],back[16];
    for(unsigned i=0;i<16;i++) { aeskey[i]=i; plain[i]=i*17; }
    rijndael_set_key(&aes,aeskey,128);
    rijndael_encrypt(&aes,plain,cipher);
    expect(cipher,16,"69c4e0d86a7b0430d8cdb78070b4c55a");
    rijndael_decrypt(&aes,cipher,back); CHECK(memcmp(back,plain,16)==0);
    printf("PASS: %u cryptographic vector assertions; not a WPA2 association test\n",checks);
}
