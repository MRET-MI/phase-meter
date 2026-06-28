/*
 * macros.h — project-wide constants for phse-meter-firm_v0
 *
 *  Created on: 2026-06-25
 *      Author: tm472
 */

#ifndef INC_MACROS_H_
#define INC_MACROS_H_

/* ── Main state machine ──────────────────────────────────────────────────── */
#define WAIT        0
#define START       1
#define WAVECHECK   2

/* ── ADC ─────────────────────────────────────────────────────────────────── */
/* Max samples per acquisition. Must be a power of two (arm_rfft_fast_f32). */
#define ADC_NUM_MAX     4096u
#define ADC_NUM_DEFAULT 4096u

/* ── Register table (reg_t parm[]) ───────────────────────────────────────── */
#define UNIT_INT        0
#define UNIT_FLOAT      1
#define UNIT_CHAR       2

#define REG_NAME_SIZE   12
#define REG_SIZE        64

/* parm[] address map (see docs/firmware_spec.md §6) */
#define P_FIRM_NO       0
#define P_ADC_NUM       1
#define P_FS_HZ         2
#define P_TARGET_HZ     3
#define P_SEARCH_WIN    4
#define P_BAND_W        5
#define P_MAXOFFSET     6
#define P_ATT_TX_DB     7
#define P_ATT_RX_DB     8

/* ── Defaults for measurement parameters ─────────────────────────────────── */
#define DEF_FS_HZ       1000000   /* 1 MHz sampling (TIM1 240MHz/240)          */
#define DEF_TARGET_HZ   100000    /* expected 100 kHz signal                   */
#define DEF_SEARCH_WIN  20        /* peak search half-window [bins]            */
#define DEF_BAND_W      2         /* cross-spectrum accumulation half-band     */
#define DEF_MAXOFFSET   10        /* bins skipped near DC                       */

/* ── USB CDC response / command-line buffers ─────────────────────────────── */
#define RESP_SZ         64
#define CMD_LINE_MAX    128

#endif /* INC_MACROS_H_ */
