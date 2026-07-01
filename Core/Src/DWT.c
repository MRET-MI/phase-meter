/*
 * DWT.c — cycle-counter based timing (Cortex-M7 DWT)
 *
 *  Created on: 2026-06-25
 *      Author: tm472
 */

#include "DWT.h"
#include "main.h"   /* CMSIS core (CoreDebug, DWT, SystemCoreClock) */

static uint32_t s_start = 0;

void DWT_Init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;
}

void startCycleCounter(void)
{
    s_start = DWT->CYCCNT;
}

uint32_t endCycleCounter(void)
{
    return DWT->CYCCNT - s_start;   /* wrap-safe unsigned subtraction */
}

float getTimeUs(uint32_t cycles)
{
    return (float)cycles / ((float)SystemCoreClock / 1e6f);
}

float getTimeMs(uint32_t cycles)
{
    return (float)cycles / ((float)SystemCoreClock / 1e3f);
}
