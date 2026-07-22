/**
 * @file mcp41hv51_driver.h
 * @brief Microchip MCP41HV51-104 8-bit high-voltage digital potentiometer
 *        (100 kOhm) SPI driver for STM32 HAL.
 *
 * Device summary:
 *   - Single 8-bit rheostat/potentiometer, 257 taps (wiper 0..256), 100 kOhm.
 *   - SPI Mode 0,0 (CPOL=0, CPHA=0) or 1,1; MSB first; fSCK <= 10 MHz.
 *   - 16-bit write frame: command byte + data byte. /CS low per transaction.
 *   - Command byte: [AD3:AD0 address][C1:C0 command][D9:D8 data high bits]
 *       command  00=Write, 11=Read, 01=Increment, 10=Decrement
 *       address  0x00=Volatile Wiper0, 0x04=TCON, 0x05=Status
 *   - Wiper is 9-bit data (D8:D0) so full-scale 256 (=0x100) is reachable.
 *
 * Wiring (this board):
 *   TX = SPI2 (SCK PB13, MOSI PB15, MISO PB14), /CS = PB3
 *   RX = SPI3 (SCK PC10, MOSI PC12, MISO PC11), /CS = PC14
 *
 * Shared-bus note (same approach as tmp126_driver):
 *   SPI2/SPI3 are shared with the HMC8073 attenuator (8-bit, LSB first) and the
 *   TMP126 sensors (16-bit, MSB first). Every transaction saves the current SPI
 *   Init, switches to 8-bit / MSB first / full-duplex / <=10 MHz, then restores
 *   the saved Init so the other devices on the same bus keep their format.
 *
 * Required CubeMX setting:
 *   - /CS pins PB3 and PC14 as GPIO_Output, push-pull, idle high, low speed.
 *   - CPOL = Low, CPHA = 1 Edge (Mode 0) — matches the existing SPI2/SPI3 config.
 *   - NOTE: PC14 is OSC32_IN (LSE). It only works as GPIO when the LSE oscillator
 *     is DISABLED and PC14 is freed in RCC (same caveat as PC15). PB3 is JTDO/SWO;
 *     usable as GPIO output when SWO trace is not needed.
 */

#ifndef MCP41HV51_DRIVER_H
#define MCP41HV51_DRIVER_H

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include <stdint.h>

/* Register (sub-)addresses AD3:AD0 (datasheet §7.0). */
#define MCP41HV51_REG_WIPER0     ((uint8_t)0x00u)
#define MCP41HV51_REG_TCON       ((uint8_t)0x04u)
#define MCP41HV51_REG_STATUS     ((uint8_t)0x05u)

/* Commands C1:C0. */
#define MCP41HV51_CMD_WRITE      ((uint8_t)0x0u)
#define MCP41HV51_CMD_READ       ((uint8_t)0x3u)
#define MCP41HV51_CMD_INCR       ((uint8_t)0x1u)
#define MCP41HV51_CMD_DECR       ((uint8_t)0x2u)

/* 8-bit device full-scale wiper code (0..256). */
#define MCP41HV51_WIPER_MAX      256u

/* Command byte = address[7:4] | command[3:2] | data9:8[1:0]. */
#define MCP41HV51_CMDBYTE(addr, cmd, data) \
    ((uint8_t)((((uint8_t)(addr) & 0x0Fu) << 4) | \
               (((uint8_t)(cmd)  & 0x03u) << 2) | \
               (((uint16_t)(data) >> 8) & 0x03u)))

typedef enum {
    MCP41HV51_OK    = 0,
    MCP41HV51_ERROR = 1
} MCP41HV51_StatusTypeDef;

typedef struct {
    SPI_HandleTypeDef *hspi;        /* Shared SPI peripheral (hspi2 / hspi3) */
    GPIO_TypeDef      *cs_port;     /* Chip-select (/CS) port                */
    uint16_t           cs_pin;      /* Chip-select (/CS) pin                 */
    uint16_t           last_wiper;  /* Last wiper value written (0..256)     */
} MCP41HV51_HandleTypeDef;

/* Set /CS idle-high and clear cached state. Call once at startup per device. */
void MCP41HV51_InitPins(MCP41HV51_HandleTypeDef *dev);

/* Low-level register write (9-bit data). Saves/restores the shared SPI Init. */
MCP41HV51_StatusTypeDef MCP41HV51_WriteRegister(MCP41HV51_HandleTypeDef *dev,
                                                uint8_t addr, uint16_t data);

/* Low-level register read (9-bit data). Saves/restores the shared SPI Init. */
MCP41HV51_StatusTypeDef MCP41HV51_ReadRegister(MCP41HV51_HandleTypeDef *dev,
                                               uint8_t addr, uint16_t *val);

/* Set the volatile wiper (0..256). Value is clamped to the valid range. */
MCP41HV51_StatusTypeDef MCP41HV51_SetWiper(MCP41HV51_HandleTypeDef *dev,
                                           uint16_t value);

/* Read the volatile wiper (0..256). */
MCP41HV51_StatusTypeDef MCP41HV51_GetWiper(MCP41HV51_HandleTypeDef *dev,
                                           uint16_t *value);

/* Increment / decrement the wiper by one step (single-byte command). */
MCP41HV51_StatusTypeDef MCP41HV51_Increment(MCP41HV51_HandleTypeDef *dev);
MCP41HV51_StatusTypeDef MCP41HV51_Decrement(MCP41HV51_HandleTypeDef *dev);

#ifdef __cplusplus
}
#endif

#endif /* MCP41HV51_DRIVER_H */
