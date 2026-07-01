/*
 * reg_store.c — shared parameter-register flash persistence for STM32H7.
 * See reg_store.h.
 */

#include "reg_store.h"
#include <string.h>

#define REG_STORE_MAX_FLASHWORD  32u   /* largest supported flash word (H753) */

uint32_t RegStore_CRC32(const void *data, uint32_t len)
{
    const uint8_t *p = (const uint8_t *)data;
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0u; i < len; i++) {
        uint8_t b = p[i];
        for (uint8_t bit = 0u; bit < 8u; bit++) {
            if (((crc >> 31) ^ (b >> 7)) & 1u) {
                crc = (crc << 1) ^ 0x04C11DB7u;
            } else {
                crc <<= 1;
            }
            b <<= 1;
        }
    }
    return crc ^ 0xFFFFFFFFu;
}

HAL_StatusTypeDef RegStore_Load(const RegStore_t *rs)
{
    if (rs == NULL || rs->parm == NULL) return HAL_ERROR;

    const uint32_t data_size = rs->count * (uint32_t)sizeof(reg_t);
    const uint32_t *hdr = (const uint32_t *)rs->flash_addr;   /* magic,size,crc */

    if (hdr[0] != rs->magic)   return HAL_ERROR;
    if (hdr[1] != data_size)   return HAL_ERROR;

    const void *data = (const void *)(rs->flash_addr + rs->flashword);
    if (RegStore_CRC32(data, data_size) != hdr[2]) return HAL_ERROR;

    memcpy(rs->parm, data, data_size);
    return HAL_OK;
}

/* Program one flash word from a source address. */
static HAL_StatusTypeDef prog_word(uint32_t faddr, const void *src)
{
    return HAL_FLASH_Program(FLASH_TYPEPROGRAM_FLASHWORD,
                             faddr, (uint32_t)(uintptr_t)src);
}

HAL_StatusTypeDef RegStore_Save(const RegStore_t *rs)
{
    if (rs == NULL || rs->parm == NULL) return HAL_ERROR;
    if (rs->flashword == 0u || rs->flashword > REG_STORE_MAX_FLASHWORD) return HAL_ERROR;

    const uint32_t data_size = rs->count * (uint32_t)sizeof(reg_t);

    /* Header occupies exactly one flash word. */
    uint8_t hdr[REG_STORE_MAX_FLASHWORD] __attribute__((aligned(REG_STORE_MAX_FLASHWORD)));
    memset(hdr, 0, sizeof(hdr));
    uint32_t *hw = (uint32_t *)(void *)hdr;
    hw[0] = rs->magic;
    hw[1] = data_size;
    hw[2] = RegStore_CRC32(rs->parm, data_size);

    if (HAL_FLASH_Unlock() != HAL_OK) return HAL_ERROR;

    FLASH_EraseInitTypeDef er = {0};
    er.TypeErase    = FLASH_TYPEERASE_SECTORS;
    er.Banks        = rs->bank;
    er.Sector       = rs->sector;
    er.NbSectors    = 1u;
    er.VoltageRange = rs->voltage_range;

    uint32_t serr = 0u;
    HAL_StatusTypeDef st = HAL_FLASHEx_Erase(&er, &serr);
    if (st != HAL_OK) { (void)HAL_FLASH_Lock(); return st; }

    /* Header word. */
    st = prog_word(rs->flash_addr, hdr);

    /* parm[] — full flash words programmed directly from the array. */
    uint32_t faddr = rs->flash_addr + rs->flashword;
    const uint8_t *src = (const uint8_t *)rs->parm;
    uint32_t full = data_size / rs->flashword;
    for (uint32_t w = 0u; (st == HAL_OK) && (w < full); w++) {
        st = prog_word(faddr, src);
        faddr += rs->flashword;
        src   += rs->flashword;
    }

    /* Trailing partial word (if data_size is not a multiple of flashword). */
    uint32_t rem = data_size - full * rs->flashword;
    if ((st == HAL_OK) && (rem != 0u)) {
        uint8_t last[REG_STORE_MAX_FLASHWORD] __attribute__((aligned(REG_STORE_MAX_FLASHWORD)));
        memset(last, 0, sizeof(last));
        memcpy(last, src, rem);
        st = prog_word(faddr, last);
    }

    (void)HAL_FLASH_Lock();
    return st;
}
