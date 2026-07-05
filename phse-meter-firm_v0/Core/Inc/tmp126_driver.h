/**
 * @file tmp126_driver.h
 * @brief TI TMP126 SPI temperature sensor driver for STM32 HAL.
 *
 * Device summary:
 *   - 14-bit SPI temperature sensor, LSB = 0.03125 C (bits [15:2], [1:0]=00)
 *   - 3-wire SPI (SIO), SPI Mode 0 (CPOL=0, CPHA=0), fCLK <= 10 MHz
 *   - 16-bit command word + 16-bit data word, MSB first, /CS low per transaction
 *   - Command word: [15]X [14]CRC [13:10]len [9]auto-inc [8]R/W [7:0]sub-address
 *   - Temperature read : cmd = 0x0100 | 0x00 (Temp_Result), R/W=1
 *   - Device_ID (0x0C) : returns 0x2126 (implementation / link check)
 *
 * Wiring (4-wire full-duplex, datasheet section 9.2):
 *   host MOSI --[10k]--> SIO,  host MISO --> SIO,  SCK --> SCLK,  CS(GPIO) --> /CS
 *
 * Shared-bus note:
 *   The SPI peripheral is shared with the HMC8073 attenuator (8-bit, LSB first,
 *   transmit-only). Every TMP126 transaction saves the current SPI Init, switches
 *   to 16-bit / MSB first / full-duplex / <=10 MHz, then restores the saved Init
 *   so the HMC8073 configuration on the same bus is preserved.
 *
 * Required CubeMX setting:
 *   - SPI Direction = Full-Duplex Master, MISO pin assigned
 *     (SPI2 MISO=PB14/AF5, SPI3 MISO=PC11/AF6)
 *   - CS pins (PB1, PB2, PC13) as GPIO_Output, push-pull, idle high
 *   - CPOL = Low, CPHA = 1 Edge (Mode 0); this matches the existing setting
 */

#ifndef TMP126_DRIVER_H
#define TMP126_DRIVER_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>

/* Register sub-addresses (datasheet section 8.6). */
#define TMP126_REG_TEMP_RESULT   ((uint8_t)0x00u)
#define TMP126_REG_DEVICE_ID     ((uint8_t)0x0Cu)
#define TMP126_DEVICE_ID_VALUE   ((uint16_t)0x2126u)

/* Read command word: R/W=1 (read), CRC=0, len=0, auto-inc=0. */
#define TMP126_CMD_READ(addr)    ((uint16_t)(0x0100u | ((uint16_t)(addr) & 0x00FFu)))

/* Temperature LSB weight after the 14-bit value is right-aligned (>>2). */
#define TMP126_LSB_C             (0.03125f)

typedef enum {
    TMP126_OK = 0,
    TMP126_ERROR = 1
} TMP126_StatusTypeDef;

typedef struct {
    SPI_HandleTypeDef *hspi;         /* Shared SPI peripheral (hspi2 / hspi3) */
    GPIO_TypeDef      *cs_port;      /* Chip-select (/CS) port                */
    uint16_t           cs_pin;       /* Chip-select (/CS) pin                 */
    float              last_temp_c;  /* Last successfully read temperature [C]*/
    int16_t            last_raw;     /* Last raw Temp_Result register value   */
} TMP126_HandleTypeDef;

/* Set /CS idle-high and clear cached state. Call once at startup per device. */
void TMP126_InitPins(TMP126_HandleTypeDef *dev);

/* Read a 16-bit register. Saves/restores the shared SPI Init internally. */
TMP126_StatusTypeDef TMP126_ReadRegister(TMP126_HandleTypeDef *dev,
                                         uint8_t addr, uint16_t *val);

/* Read Temp_Result and convert to degrees Celsius. */
TMP126_StatusTypeDef TMP126_ReadTemperature(TMP126_HandleTypeDef *dev,
                                            float *temp_c);

/* Read Device_ID (expected TMP126_DEVICE_ID_VALUE = 0x2126). */
TMP126_StatusTypeDef TMP126_ReadDeviceId(TMP126_HandleTypeDef *dev,
                                         uint16_t *id);

#ifdef __cplusplus
}
#endif

#endif /* TMP126_DRIVER_H */
