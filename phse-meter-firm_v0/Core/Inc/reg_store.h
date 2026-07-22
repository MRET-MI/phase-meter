/*
 * reg_store.h — shared parameter-register type + flash persistence.
 *
 * Common module used by multiple STM32H7 projects (auto-stage-control,
 * phase-meter, ...). Only the generic mechanism lives here; the meaning of
 * each register (defaults, hardware mapping) stays in each project.
 *
 * Flash geometry differs per MCU (H7A3: 16 B word / 8 KB sector; H753: 32 B
 * word / 128 KB sector) and is supplied at runtime via RegStore_t.
 */

#ifndef REG_STORE_H
#define REG_STORE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include "stm32h7xx_hal.h"   /* HAL_StatusTypeDef, FLASH_* (both projects are H7) */

/* ── Register value types ────────────────────────────────────────────────── */
#define UNIT_INT    0
#define UNIT_FLOAT  1
#define UNIT_CHAR   2

#ifndef REG_NAME_SIZE
#define REG_NAME_SIZE 12
#endif

typedef uint8_t unit_t;

typedef struct st_reg {
    char    name[REG_NAME_SIZE];
    unit_t  unit;
    int32_t data;
    char    data_c[4];
    float   data_f;
} reg_t;

/* ── Flash persistence configuration (per project / per MCU) ─────────────── */
typedef struct {
    reg_t   *parm;          /* parameter array                                */
    uint32_t count;         /* number of entries                              */
    uint32_t flash_addr;    /* sector base address (e.g. 0x08100000)          */
    uint32_t bank;          /* FLASH_BANK_x                                    */
    uint32_t sector;        /* FLASH_SECTOR_x                                  */
    uint32_t flashword;     /* bytes per flash word (16 for H7A3, 32 for H753) */
    uint32_t voltage_range; /* FLASH_VOLTAGE_RANGE_x, or 0 if not applicable   */
    uint32_t magic;         /* validity marker written to the header          */
} RegStore_t;

/* CRC32 (poly 0x04C11DB7, MSB-first) — matches all projects' stored data. */
uint32_t          RegStore_CRC32(const void *data, uint32_t len);

/* Load parm[] from flash. HAL_OK if valid data was found; HAL_ERROR keeps
 * whatever is currently in parm[] (i.e. the defaults). */
HAL_StatusTypeDef RegStore_Load(const RegStore_t *rs);

/* Erase the sector and write header + parm[]. */
HAL_StatusTypeDef RegStore_Save(const RegStore_t *rs);

#ifdef __cplusplus
}
#endif

#endif /* REG_STORE_H */
