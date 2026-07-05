/**
 * @file hmc8073_driver.h
 * @brief HMC8073LP3DE 6-bit digital step attenuator driver for STM32 HAL.
 *
 * Device summary:
 *   - 0.6 GHz to 3.0 GHz digital step attenuator
 *   - 0 dB to 31.5 dB, 0.5 dB step
 *   - 3-wire serial control: SI, CLK, LE
 *   - 16-bit word, LSB first
 *   - First 8 bits : attenuation data D[7:0]
 *   - Last 8 bits  : address data A[7:0]
 *
 * IMPORTANT:
 *   HMC8073 is write-only from the MCU viewpoint. There is no MISO/readback.
 *   Verify operation by RF level measurement or logic analyzer.
 *
 * Recommended CubeMX SPI setting for HAL SPI mode:
 *   - Master
 *   - Transmit only, or 2-line with MISO unused
 *   - Data Size: 8 bits
 *   - First Bit: LSB First
 *   - CPOL: Low
 *   - CPHA: 1 Edge
 *   - NSS: Software
 *
 * If your SPI peripheral is shared with devices that need MSB first,
 * use HMC8073_USE_BITBANG=1 and connect SI/CLK/LE to GPIOs.
 */

#ifndef HMC8073_DRIVER_H
#define HMC8073_DRIVER_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>

#ifndef HMC8073_USE_BITBANG
#define HMC8073_USE_BITBANG  (0)
#endif

#ifndef HMC8073_BITBANG_DELAY_LOOP
#define HMC8073_BITBANG_DELAY_LOOP  (20u)
#endif

#define HMC8073_ATTEN_DB_MIN_X2     ((uint8_t)0u)   /* 0.0 dB * 2 */
#define HMC8073_ATTEN_DB_MAX_X2     ((uint8_t)63u)  /* 31.5 dB * 2 */
#define HMC8073_ADDR_MAX            ((uint8_t)7u)

/* D[6:1] attenuation code, D0/D7 don't care set to 0. */
#define HMC8073_DATA_FROM_CODE(code)   ((uint8_t)(((code) & 0x3Fu) << 1))

/* A[2:0] address code must match external A2/A1/A0 pins. A[7:3]=0. */
#define HMC8073_ADDR_BYTE(addr)        ((uint8_t)((addr) & 0x07u))

typedef struct {
#if HMC8073_USE_BITBANG == 0
    SPI_HandleTypeDef *hspi;
#endif

    GPIO_TypeDef *le_port;
    uint16_t le_pin;

#if HMC8073_USE_BITBANG != 0
    GPIO_TypeDef *si_port;
    uint16_t si_pin;

    GPIO_TypeDef *clk_port;
    uint16_t clk_pin;
#endif

    uint8_t address;    /* External A2:A1:A0 pin setting, 0 to 7 */
    uint8_t last_code;  /* Last commanded attenuation code */

} HMC8073_HandleTypeDef;

typedef enum {
    HMC8073_OK = 0,
    HMC8073_ERROR = 1,
    HMC8073_ERROR_RANGE = 2
} HMC8073_StatusTypeDef;

void HMC8073_InitPins(HMC8073_HandleTypeDef *dev);

HMC8073_StatusTypeDef HMC8073_SetAttenuationCode(HMC8073_HandleTypeDef *dev,
                                                 uint8_t code);

HMC8073_StatusTypeDef HMC8073_SetAttenuationDbX2(HMC8073_HandleTypeDef *dev,
                                                 uint8_t atten_db_x2);

HMC8073_StatusTypeDef HMC8073_SetAttenuationDb(HMC8073_HandleTypeDef *dev,
                                               float atten_db);

uint8_t HMC8073_AttenuationDbToCode(float atten_db);
float HMC8073_CodeToAttenuationDb(uint8_t code);

/*
 * Sends raw 16-bit word.
 * Wire bit order on SI: D0,D1,...,D7,A0,A1,...,A7
 * C word layout       : bit0..7=D0..D7, bit8..15=A0..A7
 */
HMC8073_StatusTypeDef HMC8073_WriteWord(HMC8073_HandleTypeDef *dev,
                                        uint16_t word);

#ifdef __cplusplus
}
#endif

#endif /* HMC8073_DRIVER_H */
