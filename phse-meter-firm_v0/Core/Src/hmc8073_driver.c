/**
 * @file hmc8073_driver.c
 * @brief HMC8073LP3DE 6-bit DSA driver for STM32 HAL.
 */

#include "hmc8073_driver.h"

static void HMC8073_DelayLoop(void)
{
#if HMC8073_USE_BITBANG != 0
    for (volatile uint32_t i = 0; i < HMC8073_BITBANG_DELAY_LOOP; i++) {
        __NOP();
    }
#endif
}

static void HMC8073_LE_Low(HMC8073_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->le_port, dev->le_pin, GPIO_PIN_RESET);
}

static void HMC8073_LE_High(HMC8073_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->le_port, dev->le_pin, GPIO_PIN_SET);
}

#if HMC8073_USE_BITBANG != 0
static void HMC8073_SI_Write(HMC8073_HandleTypeDef *dev, uint8_t bit)
{
    HAL_GPIO_WritePin(dev->si_port, dev->si_pin,
                      bit ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

static void HMC8073_CLK_Low(HMC8073_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->clk_port, dev->clk_pin, GPIO_PIN_RESET);
}

static void HMC8073_CLK_High(HMC8073_HandleTypeDef *dev)
{
    HAL_GPIO_WritePin(dev->clk_port, dev->clk_pin, GPIO_PIN_SET);
}

static HMC8073_StatusTypeDef HMC8073_WriteWordBitBang(HMC8073_HandleTypeDef *dev,
                                                      uint16_t word)
{
    if ((dev == NULL) || (dev->le_port == NULL) ||
        (dev->si_port == NULL) || (dev->clk_port == NULL)) {
        return HMC8073_ERROR;
    }

    /* LE low during data transmission. Data is latched on CLK rising edge. */
    HMC8073_LE_Low(dev);
    HMC8073_CLK_Low(dev);
    HMC8073_DelayLoop();

    for (uint8_t i = 0; i < 16u; i++) {
        HMC8073_SI_Write(dev, (word >> i) & 0x1u);  /* LSB first */
        HMC8073_DelayLoop();

        HMC8073_CLK_High(dev);
        HMC8073_DelayLoop();

        HMC8073_CLK_Low(dev);
        HMC8073_DelayLoop();
    }

    /* High-going LE pulse updates attenuation state. */
    HMC8073_LE_High(dev);
    HMC8073_DelayLoop();
    HMC8073_LE_Low(dev);
    HMC8073_DelayLoop();

    return HMC8073_OK;
}
#endif

void HMC8073_InitPins(HMC8073_HandleTypeDef *dev)
{
    if (dev == NULL) return;

    if (dev->le_port != NULL) {
        HMC8073_LE_Low(dev);
    }

#if HMC8073_USE_BITBANG != 0
    if (dev->clk_port != NULL) HMC8073_CLK_Low(dev);
    if (dev->si_port  != NULL) HMC8073_SI_Write(dev, 0u);
#endif

    dev->last_code = 0u;
}

uint8_t HMC8073_AttenuationDbToCode(float atten_db)
{
    if (atten_db <= 0.0f) return 0u;
    if (atten_db >= 31.5f) return 63u;

    /* Round to nearest 0.5 dB step. */
    return (uint8_t)((atten_db * 2.0f) + 0.5f);
}

float HMC8073_CodeToAttenuationDb(uint8_t code)
{
    if (code > 63u) code = 63u;
    return ((float)code) * 0.5f;
}

HMC8073_StatusTypeDef HMC8073_SetAttenuationDb(HMC8073_HandleTypeDef *dev,
                                               float atten_db)
{
    return HMC8073_SetAttenuationCode(dev,
                                      HMC8073_AttenuationDbToCode(atten_db));
}

HMC8073_StatusTypeDef HMC8073_SetAttenuationDbX2(HMC8073_HandleTypeDef *dev,
                                                 uint8_t atten_db_x2)
{
    return HMC8073_SetAttenuationCode(dev, atten_db_x2);
}

HMC8073_StatusTypeDef HMC8073_SetAttenuationCode(HMC8073_HandleTypeDef *dev,
                                                 uint8_t code)
{
    if (dev == NULL) return HMC8073_ERROR;
    if (code > HMC8073_ATTEN_DB_MAX_X2) return HMC8073_ERROR_RANGE;
    if (dev->address > HMC8073_ADDR_MAX) return HMC8073_ERROR_RANGE;

    uint8_t data_byte = HMC8073_DATA_FROM_CODE(code);
    uint8_t addr_byte = HMC8073_ADDR_BYTE(dev->address);
    uint16_t word = ((uint16_t)addr_byte << 8) | data_byte;

    HMC8073_StatusTypeDef ret = HMC8073_WriteWord(dev, word);
    if (ret == HMC8073_OK) dev->last_code = code;
    return ret;
}

HMC8073_StatusTypeDef HMC8073_WriteWord(HMC8073_HandleTypeDef *dev,
                                        uint16_t word)
{
    if (dev == NULL) return HMC8073_ERROR;

#if HMC8073_USE_BITBANG != 0
    return HMC8073_WriteWordBitBang(dev, word);
#else
    if ((dev->hspi == NULL) || (dev->le_port == NULL)) {
        return HMC8073_ERROR;
    }

    /*
     * HMC8073 requires LSB-first serial input.
     * Configure SPI as First Bit = LSB First.
     * tx[0] sends D0,D1,...D7. tx[1] sends A0,A1,...A7.
     */
    uint8_t tx[2];
    tx[0] = (uint8_t)(word & 0x00FFu);
    tx[1] = (uint8_t)((word >> 8) & 0x00FFu);

    HMC8073_LE_Low(dev);

    HAL_StatusTypeDef hret = HAL_SPI_Transmit(dev->hspi, tx, 2u, 100u);

    /* Hold margin before LE pulse. */
    for (volatile uint32_t i = 0; i < 200u; i++) { __NOP(); }

    HMC8073_LE_High(dev);

    /* LE pulse width margin. */
    for (volatile uint32_t i = 0; i < 200u; i++) { __NOP(); }

    HMC8073_LE_Low(dev);

    return (hret == HAL_OK) ? HMC8073_OK : HMC8073_ERROR;
#endif
}
