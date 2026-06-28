/*
 * DWT.h — cycle-counter based microsecond timing (Cortex-M7 DWT)
 *
 *  Created on: 2026-06-25
 *      Author: tm472
 */

#ifndef INC_DWT_H_
#define INC_DWT_H_

#include <stdint.h>

void     DWT_Init(void);          /* enable the cycle counter (call once)       */
void     startCycleCounter(void);
uint32_t endCycleCounter(void);   /* elapsed cycles since startCycleCounter()   */
float    getTimeUs(uint32_t cycles);
float    getTimeMs(uint32_t cycles);

#endif /* INC_DWT_H_ */
