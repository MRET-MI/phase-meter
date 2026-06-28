/*
 * functions.h — application layer for the 2ch phase-difference meter
 *
 *  Created on: 2026-06-25
 *      Author: tm472
 */

#ifndef INC_FUNCTIONS_H_
#define INC_FUNCTIONS_H_

#include <stdint.h>
#include "macros.h"
#include "arm_math.h"

/* ── Register entry ──────────────────────────────────────────────────────── */
typedef uint8_t unit_t;

typedef struct st_reg
{
    char    name[REG_NAME_SIZE];
    unit_t  unit;
    int32_t data;
    char    data_c[4];
    float   data_f;
} reg_t;

/* ── Lifecycle ───────────────────────────────────────────────────────────── */
void StartUp(void);        /* call once from main() USER CODE BEGIN 2          */
void Start_Main(void);     /* enable the 100 Hz TIM6 tick                       */
void Main_Processing(void);/* call from the while(1) loop                       */

void GetCLK(void);
void Reg_prepare(void);
void Parm_set(void);
void ADC_Init(void);

/* ── Acquisition / measurement ───────────────────────────────────────────── */
void      ADC_Start(void);   /* main_state = START  (begin streaming)          */
void      ADC_Stop(void);    /* main_state = WAIT                               */
void      CalcMain(void);    /* run on data-ready: compute + transmit           */
float32_t CalcPhaseDiff_deg(void); /* cross-spectrum phase diff [deg]           */

/* ── ISR hooks (called from HAL weak-callback overrides in functions.c) ───── */
void OnTick100Hz(void);      /* TIM6 period elapsed (100 Hz)                    */
void OnAdcConvCplt(void);    /* ADC1 dual DMA transfer complete                 */

/* ── Command processing ──────────────────────────────────────────────────── */
void Cmd_Process(void);

/* ── Exported variables ──────────────────────────────────────────────────── */
extern reg_t parm[REG_SIZE];

extern uint32_t sysclk_hz;
extern uint32_t apb1_clocks, apb2_clocks;
extern uint32_t apb1_timer_clocks, apb2_timer_clocks;

/* ── USB CDC helpers (defined in usbd_cdc_if.c) ──────────────────────────── */
uint8_t CDC_RxReadByte(uint8_t *b);
void    CDC_SendString(const char *str);

#endif /* INC_FUNCTIONS_H_ */
