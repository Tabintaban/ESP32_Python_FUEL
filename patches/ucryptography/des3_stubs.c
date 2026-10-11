#include "mbedtls/des.h"

void mbedtls_des3_init(mbedtls_des3_context *ctx) { (void)ctx; }
void mbedtls_des3_free(mbedtls_des3_context *ctx) { (void)ctx; }

int mbedtls_des3_set3key_enc(mbedtls_des3_context *ctx, const unsigned char key[24]) {
    (void)ctx; (void)key; return -1;
}
int mbedtls_des3_set3key_dec(mbedtls_des3_context *ctx, const unsigned char key[24]) {
    (void)ctx; (void)key; return -1;
}
int mbedtls_des3_crypt_ecb(mbedtls_des3_context *ctx, const unsigned char input[8], unsigned char output[8]) {
    (void)ctx; (void)input; (void)output; return -1;
}
int mbedtls_des3_crypt_cbc(mbedtls_des3_context *ctx, int mode, size_t length, unsigned char iv[8], const unsigned char *input, unsigned char *output) {
    (void)ctx; (void)mode; (void)length; (void)iv; (void)input; (void)output; return -1;
}
