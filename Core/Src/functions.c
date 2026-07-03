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
extern DMA_HandleTypeDef  hdma_adc1;

/* ── Module state ────────────────────────────────────────────────────────── */
static volatile int16_t  main_state = WAIT;

static volatile uint8_t  g_process = 0;   /* TIM6 -> snapshot & compute now  */

/* Diagnostic counters (queried via the "DBG" command). */
static volatile uint32_t dbg_tick = 0;   /* TIM6 100 Hz ticks              */
static volatile uint32_t dbg_proc = 0;   /* phase computations done        */
static volatile uint32_t dbg_conv = 0;   /* ADC DMA wrap completions       */

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
static uint32_t peak_mode  = DEF_PEAK_MODE;

/* Latest results (set by CalcPhaseDiff_deg, sent by CalcMain). */
static float32_t g_amp_v   = 0.0f;   /* ch1 peak amplitude [V]  */
static float32_t g_freq_hz = 0.0f;   /* peak frequency [Hz]     */
static uint32_t  g_seq     = 0;      /* 100 Hz tick index of the frame (time base) */

/* DAC1_OUT2 (PA5) output voltage. Set DAC_ENABLED=0 to build before DAC1 is
 * added in CubeMX (then the hardware writes become no-ops). */
#ifndef DAC_ENABLED
#define DAC_ENABLED 1
#endif
#if DAC_ENABLED
extern DAC_HandleTypeDef hdac1;
#endif
static float   dac_v       = 3.3f;   /* requested DAC output [V] */
static uint8_t g_dac_ready = 0;
static void    DAC_SetVoltage(float v);

/* DMA destination: CDR per sample = (ADC2 << 16) | ADC1. 32-byte aligned. */
static uint32_t adc12_buff[ADC_NUM_MAX] __attribute__((aligned(32)));

/* FFT work buffers (static — too large for the stack). */
static float32_t s_fin1[ADC_NUM_MAX];
static float32_t s_fin2[ADC_NUM_MAX];
static float32_t s_fft1[ADC_NUM_MAX];
static float32_t s_fft2[ADC_NUM_MAX];
static float32_t s_mag[ADC_NUM_MAX / 2];

/* Coherent, time-ordered copy of one frame taken from the circular DMA buffer. */
static uint32_t  s_snapshot[ADC_NUM_MAX];

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
    Parm_Flash_Load();   /* override defaults with saved params if valid */
    Parm_set();
    ADC_Init();
    DAC_Init();
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
    reg_set(P_PEAK_MODE,  "peak_mode",  UNIT_INT,   DEF_PEAK_MODE,   0.0f);
    reg_set(P_DAC_V,      "dac_v",      UNIT_FLOAT, 0,               3.3f);
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
    peak_mode  = (uint32_t)parm[P_PEAK_MODE].data ? 1u : 0u;
    if (maxoffset < 1u) maxoffset = 1u;

    /* DAC output voltage — apply immediately if the DAC is already running. */
    dac_v = parm[P_DAC_V].data_f;
    if (g_dac_ready) DAC_SetVoltage(dac_v);

    /* Apply the sampling rate to TIM1: fs = timer_clock / (ARR + 1).
     * TIM1 is on APB2 (240 MHz). ARR/CCR1 take effect on the next frame. */
    uint32_t tclk = apb2_timer_clocks ? apb2_timer_clocks : 240000000u;
    if (fs_hz < FS_HZ_MIN) fs_hz = FS_HZ_MIN;
    if (fs_hz > FS_HZ_MAX) fs_hz = FS_HZ_MAX;
    uint32_t divi = (tclk + fs_hz / 2u) / fs_hz;      /* rounded tclk/fs */
    if (divi < (tclk / FS_HZ_MAX)) divi = tclk / FS_HZ_MAX;
    if (divi < 2u)      divi = 2u;
    if (divi > 65536u)  divi = 65536u;
    __HAL_TIM_SET_AUTORELOAD(&htim1, divi - 1u);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, divi / 2u);
    fs_hz = tclk / divi;                              /* achieved rate */
    parm[P_FS_HZ].data = (int32_t)fs_hz;              /* reflect achieved value */

    if (s_fft_size != adc_num) {
        arm_rfft_fast_init_f32(&s_fft_inst, adc_num);
        s_fft_size = adc_num;
    }
}

/* ── Parameter persistence via shared reg_store (Flash Bank 2, Sector 0) ──── */
static const RegStore_t s_regstore = {
    .parm          = parm,
    .count         = REG_SIZE,
    .flash_addr    = 0x08100000u,          /* Bank 2, Sector 0 (128 KB)     */
    .bank          = FLASH_BANK_2,
    .sector        = FLASH_SECTOR_0,
    .flashword     = 32u,                  /* STM32H753: 256-bit flash word  */
    .voltage_range = FLASH_VOLTAGE_RANGE_3,
    .magic         = 0x50524D31u,          /* "PRM1"                        */
};

HAL_StatusTypeDef Parm_Flash_Save(void) { return RegStore_Save(&s_regstore); }
HAL_StatusTypeDef Parm_Flash_Load(void) { return RegStore_Load(&s_regstore); }

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

    /* TIM1 (CH1 compare @1MHz) and the circular DMA are started in ADC_Start. */
}

/* Start continuous circular acquisition: TIM1 triggers ADC at 1 MHz, DMA loops
 * over adc12_buff forever. Started once; never re-armed (robust on H7). */
void ADC_Start(void)
{
    if (main_state == START) return;   /* already running */
    main_state = START;
    HAL_ADCEx_MultiModeStart_DMA(&hadc1, adc12_buff, adc_num);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
}

void ADC_Stop(void)
{
    HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
    HAL_ADCEx_MultiModeStop_DMA(&hadc1);
    main_state = WAIT;
    g_process  = 0;
}

/* ============================================================ */
/* DAC1_OUT2 (PA5)                                               */
/* ============================================================ */

/* Write the DAC output voltage, clamped to [0, Vref]. 12-bit, right-aligned. */
static void DAC_SetVoltage(float v)
{
    if (v < 0.0f)         v = 0.0f;
    if (v > ADC_VREF_V)   v = ADC_VREF_V;
    dac_v = v;
#if DAC_ENABLED
    uint32_t code = (uint32_t)lroundf(v / ADC_VREF_V * 4095.0f);
    if (code > 4095u) code = 4095u;
    HAL_DAC_SetValue(&hdac1, DAC_CHANNEL_2, DAC_ALIGN_12B_R, code);
#endif
}

/* Start DAC channel 2 and drive the current (parameter) voltage. */
void DAC_Init(void)
{
#if DAC_ENABLED
    HAL_DAC_Start(&hdac1, DAC_CHANNEL_2);
    g_dac_ready = 1;
#endif
    DAC_SetVoltage(dac_v);
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
    dbg_tick++;
    if (main_state == START) {
        g_process = 1;   /* snapshot + compute on the next main-loop pass */
    }
}

/* Circular DMA wrap — counted only; the frame is snapshotted on the 100 Hz tick. */
void OnAdcConvCplt(void)
{
    dbg_conv++;
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
        uint32_t w = s_snapshot[i];
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

    /* Expected bin from the known target frequency. */
    uint32_t k0 = (uint32_t)lroundf((float)target_hz * (float)adc_num / (float)fs_hz);
    uint32_t kpeak;

    if (peak_mode == 0u) {
        /* Fixed bin: trust target_hz (most stable when frequency is known). */
        kpeak = k0;
    } else {
        /* Search for the magnitude peak of ch1 around the expected bin. */
        arm_cmplx_mag_f32(s_fft1, s_mag, half);
        uint32_t lo = (k0 > search_win + maxoffset) ? (k0 - search_win) : maxoffset;
        uint32_t hi = k0 + search_win;
        if (hi >= half) hi = half - 1u;
        if (lo < maxoffset) lo = maxoffset;
        if (lo > hi) lo = hi;

        kpeak = lo;
        float32_t mpeak = -1.0f;
        for (uint32_t k = lo; k <= hi; k++) {
            if (s_mag[k] > mpeak) { mpeak = s_mag[k]; kpeak = k; }
        }
    }
    if (kpeak < 1u) kpeak = 1u;
    if (kpeak >= half) kpeak = half - 1u;

    /* Peak frequency. Amplitude is computed below from the band power sum
     * (energy over the main lobe): A = 2*sqrt(Sum|X1|^2)/N. Summing the leaked
     * energy in neighbouring bins makes it insensitive to spectral leakage /
     * scalloping when the tone is not bin-aligned. */
    g_freq_hz = (float32_t)kpeak * (float32_t)fs_hz / (float32_t)adc_num;

    /* Accumulate X1 * conj(X2) over [kpeak-band_w, kpeak+band_w].
     *   X1 = a+jb, X2 = c+jd  ->  X1*conj(X2) = (ac+bd) + j(bc-ad) */
    uint32_t blo = (kpeak > band_w) ? (kpeak - band_w) : 1u;
    uint32_t bhi = kpeak + band_w;
    if (bhi >= half) bhi = half - 1u;

    float32_t sre = 0.0f, sim = 0.0f, p1 = 0.0f;
    for (uint32_t k = blo; k <= bhi; k++) {
        float32_t a = re_bin(s_fft1, k), b = im_bin(s_fft1, k);
        float32_t c = re_bin(s_fft2, k), d = im_bin(s_fft2, k);
        sre += a * c + b * d;
        sim += b * c - a * d;
        p1  += a * a + b * b;          /* ch1 power over the band */
    }

    /* Amplitude of ch1 [V] from the band energy (leakage-robust). */
    g_amp_v = (2.0f * sqrtf(p1) / (float32_t)adc_num) * (ADC_VREF_V / ADC_FULLSCALE);

    if (sre == 0.0f && sim == 0.0f) return 0.0f;

    float32_t deg = atan2f(sim, sre) * (180.0f / (float32_t)M_PI);
    while (deg <= -180.0f) deg += 360.0f;
    while (deg >   180.0f) deg -= 360.0f;
    return deg;
}

/* ============================================================ */
/* Float -> "[-]int.frac" (3 decimals), printf-float independent */
/* ============================================================ */
static void ftoa_dec(float v, char *out, size_t n, unsigned dec)
{
    int neg = (v < 0.0f);
    if (neg) v = -v;
    uint32_t scale = 1u;
    for (unsigned i = 0; i < dec; i++) scale *= 10u;
    long ip = (long)v;
    long fp = (long)((v - (float)ip) * (float)scale + 0.5f);
    if (fp >= (long)scale) { ip++; fp -= (long)scale; }
    snprintf(out, n, "%s%ld.%0*ld", neg ? "-" : "", ip, (int)dec, fp);
}

static void ftoa3(float v, char *out, size_t n) { ftoa_dec(v, out, n, 3u); }

/* ============================================================ */
/* Main calculation / transmission                               */
/* ============================================================ */

void CalcMain(void)
{
    if (main_state == START) {
        float32_t deg = CalcPhaseDiff_deg();   /* also sets g_amp_v, g_freq_hz */

        char sdeg[16], samp[16], sfreq[16], line[64];
        ftoa3(deg,           sdeg,  sizeof(sdeg));
        ftoa_dec(g_amp_v,    samp,  sizeof(samp), 6u);   /* 6 dp: µV visible */
        ftoa3(g_freq_hz,     sfreq, sizeof(sfreq));
        snprintf(line, sizeof(line), "F,%lu,%s,%s,%s\r\n",
                 (unsigned long)g_seq, sdeg, samp, sfreq);
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

    /* Diagnostic: TIM6 ticks / acquisitions started / DMA completions / busy / state. */
    if (strcmp(tok, "DBG") == 0) {
        snprintf(resp, RESP_SZ, "T=%lu P=%lu C=%lu S=%d",
                 (unsigned long)dbg_tick, (unsigned long)dbg_proc,
                 (unsigned long)dbg_conv, (int)main_state);
        return 1;
    }

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
        if (tok[1] == 'S') {            /* flash save all parameters */
            snprintf(resp, RESP_SZ, (Parm_Flash_Save() == HAL_OK) ? "OK" : "NG");
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
                Parm_set();   /* re-apply (adc_num, fs->TIM1, peak_mode, ...) */
                /* Re-arm so adc_num / sampling-rate changes take effect now. */
                if (main_state == START) { ADC_Stop(); ADC_Start(); }
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

/* Copy one contiguous, time-ordered frame out of the circular DMA buffer,
 * starting at the current DMA write index (the oldest sample). The DMA keeps
 * writing during the copy, but only ~a few samples near the wrap boundary can
 * be affected — negligible for the phase estimate. */
static void snapshot_frame(void)
{
    uint32_t ndtr = __HAL_DMA_GET_COUNTER(&hdma_adc1);   /* samples remaining */
    uint32_t w = (ndtr <= adc_num) ? (adc_num - ndtr) : 0u;   /* write index */
    if (w >= adc_num) w = 0u;

    uint32_t first = adc_num - w;
    memcpy(&s_snapshot[0],     (const void *)&adc12_buff[w], first * sizeof(uint32_t));
    memcpy(&s_snapshot[first], (const void *)&adc12_buff[0], w     * sizeof(uint32_t));
}

void Main_Processing(void)
{
    /* 1. service host commands (any state) */
    Cmd_Process();

    /* 2. on the 100 Hz tick, snapshot the latest frame, compute, transmit */
    if (g_process) {
        g_process = 0;
        g_seq = dbg_tick;      /* 10 ms tick index -> jitter-free host time base */
        snapshot_frame();
        dbg_proc++;
        CalcMain();
    }
}
