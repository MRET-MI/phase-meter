/**
 * @file mcp41hv51_driver.c
 * @brief Microchip MCP41HV51-104 8-bit digital potentiometer SPI driver.
 */

#include "mcp41hv51_driver.h"

static void MCP41HV51_CS_Low(MCP41HV51_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->cs_port, dev->cs_pin, GPIO_PIN_RESET);
}

static void MCP41HV51_CS_High(MCP41HV51_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->cs_port, dev->cs_pin, GPIO_PIN_SET);
}

void MCP41HV51_InitPins(MCP41HV51_HandleTypeDef *dev)
{
    if (dev == NULL) return;

    if (dev->cs_port != NULL) {
        MCP41HV51_CS_High(dev);   /* /CS idle high */
    }
    dev->last_wiper = 0u;
}

/*
 * Run one SPI transaction on the shared bus.
 *   - Saves the current SPI Init (HMC8073 / TMP126 format), switches to the
 *     MCP41HV51 format (8-bit, MSB first, full-duplex, <=10 MHz), then restores.
 *   - CPOL/CPHA (Mode 0) are already correct on the shared bus.
 *   - If rx is NULL a transmit-only transfer is done, otherwise full-duplex.
 */
static MCP41HV51_StatusTypeDef MCP41HV51_Xfer(MCP41HV51_HandleTypeDef *dev,
                                              const uint8_t *tx, uint8_t *rx,
                                              uint16_t len)
{
    if ((dev == NULL) || (dev->hspi == NULL) ||
        (dev->cs_port == NULL) || (tx == NULL) || (len == 0u)) {
        return MCP41HV51_ERROR;
    }

    SPI_InitTypeDef saved = dev->hspi->Init;
    dev->hspi->Init.DataSize          = SPI_DATASIZE_8BIT;
    dev->hspi->Init.FirstBit          = SPI_FIRSTBIT_MSB;
    dev->hspi->Init.Direction         = SPI_DIRECTION_2LINES;
    dev->hspi->Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;   /* ~7.5 MHz */
    if (HAL_SPI_Init(dev->hspi) != HAL_OK) {
        dev->hspi->Init = saved;
        (void)HAL_SPI_Init(dev->hspi);
        return MCP41HV51_ERROR;
    }

    MCP41HV51_CS_Low(dev);
    for (volatile uint32_t i = 0; i < 20u; i++) { __NOP(); }   /* /CS setup margin */

    HAL_StatusTypeDef hret;
    if (rx != NULL) {
        hret = HAL_SPI_TransmitReceive(dev->hspi, (uint8_t *)tx, rx, len, 100u);
    } else {
        hret = HAL_SPI_Transmit(dev->hspi, (uint8_t *)tx, len, 100u);
    }

    for (volatile uint32_t i = 0; i < 20u; i++) { __NOP(); }   /* /CS hold margin */
    MCP41HV51_CS_High(dev);

    /* Restore the previous (HMC8073 / TMP126) SPI configuration. */
    dev->hspi->Init = saved;
    (void)HAL_SPI_Init(dev->hspi);

    return (hret == HAL_OK) ? MCP41HV51_OK : MCP41HV51_ERROR;
}

MCP41HV51_StatusTypeDef MCP41HV51_WriteRegister(MCP41HV51_HandleTypeDef *dev,
                                                uint8_t addr, uint16_t data)
{
    uint8_t tx[2] = {
        MCP41HV51_CMDBYTE(addr, MCP41HV51_CMD_WRITE, data),
        (uint8_t)(data & 0xFFu),
    };
    return MCP41HV51_Xfer(dev, tx, NULL, 2u);
}

MCP41HV51_StatusTypeDef MCP41HV51_ReadRegister(MCP41HV51_HandleTypeDef *dev,
                                               uint8_t addr, uint16_t *val)
{
    if (val == NULL) return MCP41HV51_ERROR;

    /* Read frame: command byte (READ) + dummy. Data returns on MISO:
     * rx[0] bits[1:0] = D9:D8, rx[1] = D7:D0. */
    uint8_t tx[2] = { MCP41HV51_CMDBYTE(addr, MCP41HV51_CMD_READ, 0u), 0x00u };
    uint8_t rx[2] = { 0u, 0u };

    MCP41HV51_StatusTypeDef st = MCP41HV51_Xfer(dev, tx, rx, 2u);
    if (st != MCP41HV51_OK) {
        return st;
    }
    *val = (uint16_t)(((uint16_t)(rx[0] & 0x03u) << 8) | rx[1]);
    return MCP41HV51_OK;
}

MCP41HV51_StatusTypeDef MCP41HV51_SetWiper(MCP41HV51_HandleTypeDef *dev,
                                           uint16_t value)
{
    if (value > MCP41HV51_WIPER_MAX) value = MCP41HV51_WIPER_MAX;

    MCP41HV51_StatusTypeDef st =
        MCP41HV51_WriteRegister(dev, MCP41HV51_REG_WIPER0, value);
    if (st == MCP41HV51_OK) {
        dev->last_wiper = value;
    }
    return st;
}

MCP41HV51_StatusTypeDef MCP41HV51_GetWiper(MCP41HV51_HandleTypeDef *dev,
                                           uint16_t *value)
{
    return MCP41HV51_ReadRegister(dev, MCP41HV51_REG_WIPER0, value);
}

MCP41HV51_StatusTypeDef MCP41HV51_Increment(MCP41HV51_HandleTypeDef *dev)
{
    uint8_t tx = MCP41HV51_CMDBYTE(MCP41HV51_REG_WIPER0, MCP41HV51_CMD_INCR, 0u);
    return MCP41HV51_Xfer(dev, &tx, NULL, 1u);
}

MCP41HV51_StatusTypeDef MCP41HV51_Decrement(MCP41HV51_HandleTypeDef *dev)
{
    uint8_t tx = MCP41HV51_CMDBYTE(MCP41HV51_REG_WIPER0, MCP41HV51_CMD_DECR, 0u);
    return MCP41HV51_Xfer(dev, &tx, NULL, 1u);
}
