/*
 * functions.c — 2ch phase-difference meter: ADC acquisition, FFT phase diff,
 *               USB CDC command parser & streaming.
 *
 *  Created on: 2026-06-25
 *      Author: tm472
 *
 *  Flow (see docs/firmware_spec.md):
 *    TIM1 CH1 compare @1MHz triggers ADC1+ADC2 dual simultaneous conversion.
 *    Single DMA reads the common data register (CDR = ADC2<<16 | ADC1, DAMDF=32/10b)
 *    into adc12_buff[adc_num] (Normal/one-shot).
 *    TIM6 @100Hz requests one acquisition every 10 ms.
 *    DMA-complete sets a flag; the heavy FFT runs in the main loop, not in ISR.
 */

#include "main.h"
#include "functions.h"
#include "macros.h"
#include "DWT.h"
#include "hmc8073_driver.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ── External handles (CubeMX generated, main.c) ─────────────────────────── */
extern ADC_HandleTypeDef  hadc1;
extern ADC_HandleTypeDef  hadc2;
extern TIM_HandleTypeDef  htim1;
extern TIM_HandleTypeDef  htim6;

/* ── Module state ────────────────────────────────────────────────────────── */
static volatile int16_t  main_state = WAIT;

static volatile uint8_t  g_acq_request = 0;   /* TIM6 -> "start one acquisition" */
static volatile uint8_t  g_acq_busy    = 0;   /* DMA in flight                    */
static volatile uint8_t  g_data_ready  = 0;   /* DMA complete -> compute in main  */

reg_t parm[REG_SIZE];

uint32_t sysclk_hz;
uint32_t apb1_clocks, apb2_clocks;
uint32_t apb1_timer_clocks, apb2_timer_clocks;

/* Measurement parameters (loaded from parm[] in Parm_set). */
static uint32_t adc_num    = ADC_NUM_DEFAULT;
static uint32_t fs_hz      = DEF_FS_HZ;
static uint32_t target_hz  = DEF_TARGET_HZ;
static uint32_t search_win = DEF_SEARCH_WIN;
static uint32_t band_w     = DEF_BAND_W;
static uint32_t maxoffset  = DEF_MAXOFFSET;

/* DMA destination: CDR per sample = (ADC2 << 16) | ADC1. 32-byte aligned. */
static uint32_t adc12_buff[ADC_NUM_MAX] __attribute__((aligned(32)));

/* FFT work buffers (static — too large for the stack). */
static float32_t s_fin1[ADC_NUM_MAX];
static float32_t s_fin2[ADC_NUM_MAX];
static float32_t s_fft1[ADC_NUM_MAX];
static float32_t s_fft2[ADC_NUM_MAX];
static float32_t s_mag[ADC_NUM_MAX / 2];

static arm_rfft_fast_instance_f32 s_fft_inst;
static uint32_t s_fft_size = 0;   /* size the instance was initialised for */

/* ============================================================ */
/* HMC8073 attenuators (TX = SPI2/PB4, RX = SPI3/PC15)           */
/* ------------------------------------------------------------ */
/* Set HMC8073_ENABLED to 0 to fall back to "store dB only".     */
/* ============================================================ */
#ifndef HMC8073_ENABLED
#define HMC8073_ENABLED 1
#endif

#if HMC8073_ENABLED
extern SPI_HandleTypeDef hspi2;   /* TX: SCK PB13, MOSI PB15, LE PB4   */
extern SPI_HandleTypeDef hspi3;   /* RX: SCK PC10, MOSI PC12, LE PC15  */

HMC8073_HandleTypeDef g_hmc8073_transmitter = {
    .hspi    = &hspi2,
    .le_port = GPIOB, .le_pin = GPIO_PIN_4,
    .address = 0,    /* 要確認: board A2:A1:A0 strap */
};
HMC8073_HandleTypeDef g_hmc8073_receiver = {
    .hspi    = &hspi3,
    .le_port = GPIOC, .le_pin = GPIO_PIN_15,
    .address = 0,    /* 要確認: board A2:A1:A0 strap */
};

static void HMC8073_AppInit(void)
{
    HMC8073_InitPins(&g_hmc8073_transmitter);
    HMC8073_InitPins(&g_hmc8073_receiver);
    HMC8073_SetAttenuationDb(&g_hmc8073_transmitter, parm[P_ATT_TX_DB].data_f);
    HMC8073_SetAttenuationDb(&g_hmc8073_receiver,    parm[P_ATT_RX_DB].data_f);
}
#endif

/* ============================================================ */
/* Initialization                                                */
/* ============================================================ */

void StartUp(void)
{
    DWT_Init();
    GetCLK();
    Reg_prepare();
    Parm_set();
    ADC_Init();
#if HMC8073_ENABLED
    HMC8073_AppInit();
#endif
}

void Start_Main(void)
{
    main_state = WAIT;
    __HAL_TIM_ENABLE_IT(&htim6, TIM_IT_UPDATE);
    __HAL_TIM_ENABLE(&htim6);
}

void GetCLK(void)
{
    sysclk_hz   = HAL_RCC_GetSysClockFreq();
    apb1_clocks = HAL_RCC_GetPCLK1Freq();
    apb2_clocks = HAL_RCC_GetPCLK2Freq();
    apb1_timer_clocks = apb1_clocks * 2u;
    apb2_timer_clocks = apb2_clocks * 2u;
}

/* ── parm[] defaults ─────────────────────────────────────────────────────── */
static void reg_set(int i, const char *name, unit_t unit, int32_t d, float f)
{
    strncpy(parm[i].name, name, REG_NAME_SIZE - 1);
    parm[i].name[REG_NAME_SIZE - 1] = '\0';
    parm[i].unit   = unit;
    parm[i].data   = d;
    parm[i].data_f = f;
}

void Reg_prepare(void)
{
    memset(parm, 0, sizeof(parm));
    for (int i = 0; i < REG_SIZE; i++) {
        snprintf(parm[i].name, REG_NAME_SIZE, "reg%d", i);
        parm[i].unit = UNIT_INT;
    }

    reg_set(P_FIRM_NO,    "firm_no",    UNIT_INT,   1,               0.0f);
    reg_set(P_ADC_NUM,    "adc_num",    UNIT_INT,   ADC_NUM_DEFAULT, 0.0f);
    reg_set(P_FS_HZ,      "fs_hz",      UNIT_INT,   DEF_FS_HZ,       0.0f);
    reg_set(P_TARGET_HZ,  "target_hz",  UNIT_INT,   DEF_TARGET_HZ,   0.0f);
    reg_set(P_SEARCH_WIN, "search_win", UNIT_INT,   DEF_SEARCH_WIN,  0.0f);
    reg_set(P_BAND_W,     "band_w",     UNIT_INT,   DEF_BAND_W,      0.0f);
    reg_set(P_MAXOFFSET,  "maxoffset",  UNIT_INT,   DEF_MAXOFFSET,   0.0f);
    reg_set(P_ATT_TX_DB,  "att_tx_db",  UNIT_FLOAT, 0,               0.0f);
    reg_set(P_ATT_RX_DB,  "att_rx_db",  UNIT_FLOAT, 0,               0.0f);
}

/* Apply parm[] to module variables. Re-init the FFT instance if adc_num changed. */
void Parm_set(void)
{
    uint32_t n = (uint32_t)parm[P_ADC_NUM].data;

    /* Clamp adc_num to a supported power of two (<= ADC_NUM_MAX). */
    if (n < 32u) n = 32u;
    if (n > ADC_NUM_MAX) n = ADC_NUM_MAX;
    uint32_t p = 32u;
    while ((p << 1) <= n) p <<= 1;
    adc_num = p;
    parm[P_ADC_NUM].data = (int32_t)adc_num;

    fs_hz      = (uint32_t)parm[P_FS_HZ].data;
    target_hz  = (uint32_t)parm[P_TARGET_HZ].data;
    search_win = (uint32_t)parm[P_SEARCH_WIN].data;
    band_w     = (uint32_t)parm[P_BAND_W].data;
    maxoffset  = (uint32_t)parm[P_MAXOFFSET].data;
    if (maxoffset < 1u) maxoffset = 1u;

    if (s_fft_size != adc_num) {
        arm_rfft_fast_init_f32(&s_fft_inst, adc_num);
        s_fft_size = adc_num;
    }
}

/* ============================================================ */
/* ADC / Timer setup                                             */
/* ============================================================ */

void ADC_Init(void)
{
    /*
     * Override the dual-mode data format: CubeMX generates
     * ADC_DUALMODEDATAFORMAT_DISABLED, but to read both channels packed into
     * the common data register (CDR) with a single DMA we need 32/10-bit format.
     */
    ADC_MultiModeTypeDef mm = {0};
    mm.Mode             = ADC_DUALMODE_REGSIMULT;
    mm.DualModeData     = ADC_DUALMODEDATAFORMAT_32_10_BITS;
    mm.TwoSamplingDelay = ADC_TWOSAMPLINGDELAY_1CYCLE;
    if (HAL_ADCEx_MultiModeConfigChannel(&hadc1, &mm) != HAL_OK) {
        Error_Handler();
    }

    /* Calibrate both ADCs (single-ended, offset) before first use. */
    HAL_ADCEx_Calibration_Start(&hadc1, ADC_CALIB_OFFSET, ADC_SINGLE_ENDED);
    HAL_ADCEx_Calibration_Start(&hadc2, ADC_CALIB_OFFSET, ADC_SINGLE_ENDED);

    /* TIM1 free-runs and its CH1 compare event (@1MHz) triggers the ADC.
     * Starting the PWM channel enables CC1 and the counter. */
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}

/* Arm one acquisition of adc_num samples (TIM1-triggered, one-shot DMA). */
static void Acquire_Start(void)
{
    HAL_ADCEx_MultiModeStart_DMA(&hadc1, adc12_buff, adc_num);
    g_acq_busy = 1;
}

static void Acquire_Stop(void)
{
    HAL_ADCEx_MultiModeStop_DMA(&hadc1);
    g_acq_busy = 0;
}

void ADC_Start(void) { main_state = START; }

void ADC_Stop(void)
{
    main_state = WAIT;
    if (g_acq_busy) Acquire_Stop();
    g_acq_request = 0;
    g_data_ready  = 0;
}

/* ============================================================ */
/* HAL weak-callback overrides + ISR hooks                       */
/* ============================================================ */

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM6) {
        OnTick100Hz();
    }
}

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        OnAdcConvCplt();
    }
}

/* 100 Hz tick: request a new acquisition when measuring and not already busy. */
void OnTick100Hz(void)
{
    if (main_state != WAIT && !g_acq_busy) {
        g_acq_request = 1;
    }
}

/* DMA transfer complete: just flag it; stop + FFT happen in the main loop. */
void OnAdcConvCplt(void)
{
    g_data_ready = 1;
}

/* ============================================================ */
/* Phase difference (FFT cross-spectrum)                         */
/* ============================================================ */

/* Deinterleave adc12_buff -> two float arrays with the DC (mean) removed.
 * Mean removal is resolution-independent (works for 12/16-bit). */
static void deinterleave(void)
{
    float32_t s1 = 0.0f, s2 = 0.0f;
    for (uint32_t i = 0; i < adc_num; i++) {
        uint32_t w = adc12_buff[i];
        float32_t a = (float32_t)(w & 0xFFFFu);
        float32_t b = (float32_t)((w >> 16) & 0xFFFFu);
        s_fin1[i] = a;  s1 += a;
        s_fin2[i] = b;  s2 += b;
    }
    float32_t m1 = s1 / (float32_t)adc_num;
    float32_t m2 = s2 / (float32_t)adc_num;
    for (uint32_t i = 0; i < adc_num; i++) {
        s_fin1[i] -= m1;
        s_fin2[i] -= m2;
    }
}

static inline float32_t re_bin(const float32_t *fft, uint32_t k) { return fft[2u * k];      }
static inline float32_t im_bin(const float32_t *fft, uint32_t k) { return fft[2u * k + 1u]; }

/*
 * Cross-spectrum phase difference [deg], in (-180, 180].
 *   phase_diff = phase(X1) - phase(X2), accumulated over a band around the peak.
 */
float32_t CalcPhaseDiff_deg(void)
{
    const uint32_t half = adc_num / 2u;

    deinterleave();

    arm_rfft_fast_f32(&s_fft_inst, s_fin1, s_fft1, 0);
    arm_rfft_fast_f32(&s_fft_inst, s_fin2, s_fft2, 0);

    /* Magnitude of ch1 over usable bins. */
    arm_cmplx_mag_f32(s_fft1, s_mag, half);

    /* Peak search window centred on the expected (100 kHz) bin. */
    uint32_t k0 = (uint32_t)lroundf((float)target_hz * (float)adc_num / (float)fs_hz);
    uint32_t lo = (k0 > search_win + maxoffset) ? (k0 - search_win) : maxoffset;
    uint32_t hi = k0 + search_win;
    if (hi >= half) hi = half - 1u;
    if (lo < maxoffset) lo = maxoffset;
    if (lo > hi) lo = hi;

    uint32_t  kpeak = lo;
    float32_t mpeak = -1.0f;
    for (uint32_t k = lo; k <= hi; k++) {
        if (s_mag[k] > mpeak) { mpeak = s_mag[k]; kpeak = k; }
    }

    /* Accumulate X1 * conj(X2) over [kpeak-band_w, kpeak+band_w].
     *   X1 = a+jb, X2 = c+jd  ->  X1*conj(X2) = (ac+bd) + j(bc-ad) */
    uint32_t blo = (kpeak > band_w) ? (kpeak - band_w) : 1u;
    uint32_t bhi = kpeak + band_w;
    if (bhi >= half) bhi = half - 1u;

    float32_t sre = 0.0f, sim = 0.0f;
    for (uint32_t k = blo; k <= bhi; k++) {
        float32_t a = re_bin(s_fft1, k), b = im_bin(s_fft1, k);
        float32_t c = re_bin(s_fft2, k), d = im_bin(s_fft2, k);
        sre += a * c + b * d;
        sim += b * c - a * d;
    }

    if (sre == 0.0f && sim == 0.0f) return 0.0f;

    float32_t deg = atan2f(sim, sre) * (180.0f / (float32_t)M_PI);
    while (deg <= -180.0f) deg += 360.0f;
    while (deg >   180.0f) deg -= 360.0f;
    return deg;
}

/* ============================================================ */
/* Float -> "[-]int.frac" (3 decimals), printf-float independent */
/* ============================================================ */
static void ftoa3(float v, char *out, size_t n)
{
    int neg = (v < 0.0f);
    if (neg) v = -v;
    long ip = (long)v;
    long fp = (long)((v - (float)ip) * 1000.0f + 0.5f);
    if (fp >= 1000) { ip++; fp -= 1000; }
    snprintf(out, n, "%s%ld.%03ld", neg ? "-" : "", ip, fp);
}

/* ============================================================ */
/* Main calculation / transmission                               */
/* ============================================================ */

void CalcMain(void)
{
    if (main_state == START) {
        float32_t deg = CalcPhaseDiff_deg();

        char num[16], line[24];
        ftoa3(deg, num, sizeof(num));
        snprintf(line, sizeof(line), "F,%s\r\n", num);
        CDC_SendString(line);
    }
    /* WAVECHECK (raw waveform dump) — phase 2, see firmware_spec.md */
}

/* ============================================================ */
/* Command parser                                                */
/* ============================================================ */

static int ParseSubCmd(const char *tok, char *resp)
{
    if (tok == NULL || tok[0] == '\0') return 0;

    if (strcmp(tok, "RUN") == 0)  { ADC_Start(); snprintf(resp, RESP_SZ, "OK"); return 1; }
    if (strcmp(tok, "STOP") == 0) { ADC_Stop();  snprintf(resp, RESP_SZ, "OK"); return 1; }
    if (strcmp(tok, "VER") == 0)  { snprintf(resp, RESP_SZ, "phse-meter-firm_v0"); return 1; }

    /* Attenuators: ATTT<dB> (transmitter, SPI2) / ATTR<dB> (receiver, SPI3). */
    if (tok[0]=='A' && tok[1]=='T' && tok[2]=='T') {
        int paddr; uint8_t is_tx;
        if      (tok[3]=='T') { paddr = P_ATT_TX_DB; is_tx = 1; }
        else if (tok[3]=='R') { paddr = P_ATT_RX_DB; is_tx = 0; }
        else { snprintf(resp, RESP_SZ, "NG"); return 1; }

        float db = (float)atof(tok + 4);
        if (db < 0.0f || db > 31.5f) { snprintf(resp, RESP_SZ, "NG"); return 1; }
#if HMC8073_ENABLED
        HMC8073_HandleTypeDef *h = is_tx ? &g_hmc8073_transmitter : &g_hmc8073_receiver;
        if (HMC8073_SetAttenuationDb(h, db) != HMC8073_OK) { snprintf(resp, RESP_SZ, "NG"); return 1; }
#else
        (void)is_tx;
#endif
        parm[paddr].data_f = db;
        snprintf(resp, RESP_SZ, "OK");
        return 1;
    }

    /* Register commands: R<addr>S<val> / R<addr>R / RA / RS */
    if (tok[0] == 'R') {
        if (tok[1] == 'S') {            /* flash save — phase 2 stub */
            snprintf(resp, RESP_SZ, "NG");
            return 1;
        }
        if (tok[1] == 'A') {
            char l[64], vbuf[20];
            for (int i = 0; i < REG_SIZE; i++) {
                if (parm[i].unit == UNIT_FLOAT) {
                    ftoa3(parm[i].data_f, vbuf, sizeof(vbuf));
                    snprintf(l, sizeof(l), "%d:%.11s:%d:%s\n",
                             i, parm[i].name, (int)parm[i].unit, vbuf);
                } else {
                    snprintf(l, sizeof(l), "%d:%.11s:%d:%ld\n",
                             i, parm[i].name, (int)parm[i].unit, (long)parm[i].data);
                }
                CDC_SendString(l);
            }
            snprintf(resp, RESP_SZ, "END");
            return 1;
        }
        {
            int addr = atoi(tok + 1);
            if (addr < 0 || addr >= REG_SIZE) { snprintf(resp, RESP_SZ, "NG"); return 1; }
            const char *p = tok + 1;
            while (*p >= '0' && *p <= '9') p++;
            if (*p == 'S') {
                if (parm[addr].unit == UNIT_FLOAT) parm[addr].data_f = (float)atof(p + 1);
                else                               parm[addr].data   = (int32_t)atoi(p + 1);
                Parm_set();   /* re-apply (handles adc_num change etc.) */
                snprintf(resp, RESP_SZ, "OK");
            } else if (*p == 'R') {
                if (parm[addr].unit == UNIT_FLOAT) ftoa3(parm[addr].data_f, resp, RESP_SZ);
                else                               snprintf(resp, RESP_SZ, "%ld", (long)parm[addr].data);
            } else {
                snprintf(resp, RESP_SZ, "NG");
            }
            return 1;
        }
    }

    snprintf(resp, RESP_SZ, "NG");
    return 1;
}

static void Cmd_Execute(const char *line)
{
    char buf[CMD_LINE_MAX], resp[RESP_SZ], out[RESP_SZ + 2u];
    char *tok;

    strncpy(buf, line, sizeof(buf) - 1u);
    buf[sizeof(buf) - 1u] = '\0';
    resp[0] = '\0';

    tok = strtok(buf, ";");
    while (tok != NULL) {
        ParseSubCmd(tok, resp);
        tok = strtok(NULL, ";");
    }

    if (resp[0] == '\0') {
        CDC_SendString("OK\n");
    } else {
        snprintf(out, sizeof(out), "%s\n", resp);
        CDC_SendString(out);
    }
}

void Cmd_Process(void)
{
    static char     cmd_line[CMD_LINE_MAX];
    static uint16_t cmd_len = 0u;
    uint8_t b;

    while (CDC_RxReadByte(&b)) {
        if (b == (uint8_t)'\r') continue;
        if (b == (uint8_t)'\n') {
            if (cmd_len > 0u) {
                cmd_line[cmd_len] = '\0';
                Cmd_Execute(cmd_line);
                cmd_len = 0u;
            }
        } else if (cmd_len < (uint16_t)(sizeof(cmd_line) - 1u)) {
            cmd_line[cmd_len++] = (char)b;
        }
    }
}

/* ============================================================ */
/* Main loop                                                     */
/* ============================================================ */

void Main_Processing(void)
{
    /* 1. service host commands (any state) */
    Cmd_Process();

    /* 2. a completed acquisition: stop DMA, compute, transmit */
    if (g_data_ready) {
        g_data_ready = 0;
        Acquire_Stop();
        CalcMain();
    }

    /* 3. arm the next acquisition requested by the 100 Hz tick */
    if (g_acq_request && !g_acq_busy) {
        g_acq_request = 0;
        Acquire_Start();
    }
}
