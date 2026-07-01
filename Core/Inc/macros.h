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

/* Amplitude scaling: 16-bit ADC, Vref+ = 3.3 V (NUCLEO-H753ZI VDDA). */
#define ADC_VREF_V      3.3f
#define ADC_FULLSCALE   65536.0f

/* ── Register table ──────────────────────────────────────────────────────── */
/* reg_t / unit_t / UNIT_* / REG_NAME_SIZE come from the shared reg_store.h. */
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
#define P_PEAK_MODE     9   /* 0 = fixed bin (target_hz), 1 = peak search */

/* ── Defaults for measurement parameters ─────────────────────────────────── */
#define DEF_FS_HZ       1000000   /* 1 MHz sampling (TIM1 240MHz/240)          */
#define DEF_TARGET_HZ   100000    /* expected 100 kHz signal                   */
#define DEF_SEARCH_WIN  20        /* peak search half-window [bins]            */
#define DEF_BAND_W      2         /* cross-spectrum accumulation half-band     */
#define DEF_MAXOFFSET   10        /* bins skipped near DC                       */
#define DEF_PEAK_MODE   1         /* 0 = fixed bin, 1 = peak search            */

/* Sampling-rate limits (fs = TIM1 clock / (ARR+1)). */
#define FS_HZ_MIN       4000u
#define FS_HZ_MAX       2500000u  /* ADC conversion time ceiling (~340 ns)     */

/* ── USB CDC response / command-line buffers ─────────────────────────────── */
#define RESP_SZ         64
#define CMD_LINE_MAX    128

#endif /* INC_MACROS_H_ */
