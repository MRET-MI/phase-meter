/**
 * @file tmp126_driver.c
 * @brief TI TMP126 SPI temperature sensor driver for STM32 HAL.
 */

#include "tmp126_driver.h"

static void TMP126_CS_Low(TMP126_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->cs_port, dev->cs_pin, GPIO_PIN_RESET);
}

static void TMP126_CS_High(TMP126_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->cs_port, dev->cs_pin, GPIO_PIN_SET);
}

void TMP126_InitPins(TMP126_HandleTypeDef *dev)
{
    if (dev == NULL) return;

    if (dev->cs_port != NULL) {
        TMP126_CS_High(dev);   /* /CS idle high */
    }
    dev->last_temp_c = 0.0f;
    dev->last_raw    = 0;
}

TMP126_StatusTypeDef TMP126_ReadRegister(TMP126_HandleTypeDef *dev,
                                         uint8_t addr, uint16_t *val)
{
    if ((dev == NULL) || (dev->hspi == NULL) ||
        (dev->cs_port == NULL) || (val == NULL)) {
        return TMP126_ERROR;
    }

    /*
     * The SPI peripheral is shared with the HMC8073 attenuator (8-bit, LSB
     * first, transmit-only). Save its Init, switch to the TMP126 format, run
     * the transaction, then restore. CPOL/CPHA (Mode 0) are already correct.
     *   - DataSize : 16 bits (command word + data word)
     *   - FirstBit : MSB first
     *   - Direction: full-duplex (need MISO to read data back)
     *   - Prescaler: /16 -> 7.5 MHz on a 120 MHz APB clock (<= 10 MHz limit)
     */
    SPI_InitTypeDef saved = dev->hspi->Init;
    dev->hspi->Init.DataSize          = SPI_DATASIZE_16BIT;
    dev->hspi->Init.FirstBit          = SPI_FIRSTBIT_MSB;
    dev->hspi->Init.Direction         = SPI_DIRECTION_2LINES;
    dev->hspi->Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;
    if (HAL_SPI_Init(dev->hspi) != HAL_OK) {
        dev->hspi->Init = saved;
        (void)HAL_SPI_Init(dev->hspi);
        return TMP126_ERROR;
    }

    /* Frame 1: command word (data read back is discarded).
     * Frame 2: dummy TX (0x0000); the register value is clocked in on MISO. */
    uint16_t tx[2] = { TMP126_CMD_READ(addr), 0x0000u };
    uint16_t rx[2] = { 0u, 0u };

    TMP126_CS_Low(dev);
    for (volatile uint32_t i = 0; i < 20u; i++) { __NOP(); }   /* tLEAD margin */

    HAL_StatusTypeDef hret =
        HAL_SPI_TransmitReceive(dev->hspi, (uint8_t *)tx, (uint8_t *)rx, 2u, 100u);

    for (volatile uint32_t i = 0; i < 20u; i++) { __NOP(); }   /* tLAG margin */
    TMP126_CS_High(dev);

    /* Restore the previous (HMC8073) SPI configuration on the shared bus. */
    dev->hspi->Init = saved;
    (void)HAL_SPI_Init(dev->hspi);

    if (hret != HAL_OK) {
        return TMP126_ERROR;
    }

    *val = rx[1];
    return TMP126_OK;
}

TMP126_StatusTypeDef TMP126_ReadTemperature(TMP126_HandleTypeDef *dev,
                                            float *temp_c)
{
    if ((dev == NULL) || (temp_c == NULL)) return TMP126_ERROR;

    uint16_t raw = 0u;
    if (TMP126_ReadRegister(dev, TMP126_REG_TEMP_RESULT, &raw) != TMP126_OK) {
        return TMP126_ERROR;
    }

    /* 14-bit two's-complement value in bits [15:2]; bits [1:0] are always 00.
     * Arithmetic right-shift by 2 keeps the sign and gives the 14-bit code. */
    int16_t code = (int16_t)((int16_t)raw >> 2);
    float   c    = (float)code * TMP126_LSB_C;

    dev->last_raw    = (int16_t)raw;
    dev->last_temp_c = c;
    *temp_c = c;
    return TMP126_OK;
}

TMP126_StatusTypeDef TMP126_ReadDeviceId(TMP126_HandleTypeDef *dev,
                                         uint16_t *id)
{
    return TMP126_ReadRegister(dev, TMP126_REG_DEVICE_ID, id);
}
