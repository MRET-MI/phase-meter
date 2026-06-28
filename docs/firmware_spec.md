# ファームウェア仕様書 — 2ch 位相差計

**対象:** phase_meter_firm_v0
**MCU:** STM32H7 系（型番確定後に最終化。姉妹PJ `stage_controller_firm_v0` = STM32H7A3VIT6 を基準）
**更新日:** 2026-06-24

> 本書は MCU 型番確定前の設計指示書。CubeMX 生成後、`Core/Src` 等のユーザコード領域に
> 本リポジトリの `firmware/phase_meter_firm_v0/` 配下のソースを統合する。

---

## 1. 機能概要

100 kHz のアナログ波形 2ch を **同時 ADC** し、FFT により 2ch 間の **位相差**[deg] を
算出、USB CDC（仮想COM）で PC へ連続送信する。送受信パスの可変アッテネータ
（HMC8073 ×2）を SPI で制御する。

| 項目 | 値 |
|---|---|
| 入力信号 | 100 kHz 正弦波 2ch（PA2 / PA3） |
| サンプリング | 1 MHz（TIM1 トリガ）、デュアル同時変換 |
| 1取得サンプル数 | 4096 点（既定, `adc_num`） |
| 位相算出レート | 100 Hz（TIM6 10 ms ティック） |
| 出力 | USB CDC `F,<deg>\r\n` 連続ストリーム |

---

## 2. クロック構成（CubeMX 設定目標）

| パラメータ | 値 | 備考 |
|---|---|---|
| CPU (SYSCLK) | **480 MHz** | HSE 8 MHz → PLL1 |
| HCLK / APB タイマクロック | **240 MHz** | TIM1: 240 MHz / 240 = **1.000 MHz** トリガ |
| 電源スケール | **VOS0** | 480 MHz / 50 MHz ADC に必須 |
| ADC カーネルクロック | **≒50.5 MHz** | PLL2P, prescaler DIV1 |
| USB | **OTG_FS** + HSI48 | NUCLEO-H753ZI の User USB |

> 実機 NUCLEO-H753ZI の確定値。USB は OTG_**FS**（送信 `CDC_Transmit_FS`）。
> 詳細な CubeMX 設定は `docs/cubemx_setup.md` 参照。

---

## 3. ペリフェラル

### 3.1 ADC（ADC1 master + ADC2 slave / Dual regular simultaneous）

| 項目 | 設定 |
|---|---|
| API | `HAL_ADCEx_MultiModeStart_DMA(&hadc1, adc12_buff, adc_num)` |
| ch1 | ADC1 rank1 = **PA2 (ADC1_INP14)** ※型番で番号再確認 |
| ch2 | ADC2 rank1 = **PA3 (ADC2_INP15)** ※型番で番号再確認 |
| 分解能 | **16 bit** |
| サンプリング時間 | **8.5 cycle** |
| 変換時間 | (8.5 + 8.5) = 17 cyc @50 MHz = **340 ns** < 1 µs（余裕） |
| 外部トリガ | **TIM1_TRGO**（立ち上がり） |
| DMA | master CDR を 32bit Word でメモリへ。**Normal モード**、長さ `adc_num` |
| データ配置 | CDR = `(ADC2 << 16) \| ADC1`（下位=ch1, 上位=ch2） |
| HT/TE 割込 | 無効 |

**D-Cache**: 姉妹PJに倣い無効。有効化する場合は読出前に
`SCB_InvalidateDCache_by_Addr(adc12_buff, sizeof(adc12_buff))` を入れること。
`adc12_buff` は `__attribute__((aligned(32)))` 配置。

### 3.2 タイマ

| タイマ | 用途 | 設定 |
|---|---|---|
| TIM1 | ADC トリガ | `ARR = 239`（240 MHz/240 = 1 MHz）, Update→TRGO |
| TIM6 | 100 Hz 状態ティック | 10 ms 周期で取得を起動 |

> OCR ドラフトの TIM2（calc タイミング）と TIM1 の RCR トリックは**廃止**。
> ADC DMA 完了コールバックで算出を駆動する。

### 3.3 SPI（HMC8073 TX/RX）

姉妹PJの SPI（Master, 8bit, ソフト NSS）を流用。TX/RX 各 1 系統。
実 SPI 番号・CS/LE ピンは回路図で確定（`hmc8073_driver.h` のハンドルに設定）。

---

## 4. ソフトウェア構成

```
Core/Inc/  functions.h  macros.h  DWT.h
Core/Src/  functions.c  DWT.c     main.c(生成, USER CODE に StartUp/Main_Processing を追加)
Drivers/hmc8073/  hmc8073_driver.{c,h}
USB_DEVICE/App/   usbd_cdc_if.c (USER CODE に RX リング/送信ヘルパーを追加 → INTEGRATION.md)
```

### 4.1 状態機械（`main_state`）

| 状態 | 値 | 動作 |
|---|---|---|
| `WAIT` | 0 | コマンド待ち。取得停止。 |
| `START` | 1 | 100 Hz で位相差算出 → `F,<deg>\r\n` 連続送信。 |
| `WAVECHECK` | 2 | 生波形ダンプ（フェーズ2, 後日）。 |

### 4.2 起動シーケンス（main.c USER CODE BEGIN 2）

```
HAL/クロック/ペリフェラル初期化（CubeMX 生成）
  → StartUp()  = GetCLK() → Reg_prepare() → Parm_set() → ADC_Init() → HMC8073_AppInit()
  → Start_Main() = TIM6 10ms ティック有効化（main_state=WAIT）
while(1) → Main_Processing()
```

### 4.3 データフロー（割込 → メインループ）

```
TIM6 100Hz ISR (HAL_TIM_PeriodElapsedCallback)
   main_state==START/WAVECHECK かつ 取得中でない → g_acq_request=1
メインループ Main_Processing()
   ① Cmd_Process()  : USB 受信コマンド処理（WAIT/START 共通）
   ② g_acq_request かつ !g_acq_busy → Acquire開始:
        HAL_ADCEx_MultiModeStart_DMA(...); g_acq_busy=1
   ③ g_data_ready → CalcMain(): 位相差算出 → USB送信; g_data_ready=0
ADC ConvCplt ISR (HAL_ADC_ConvCpltCallback)
   HAL_ADCEx_MultiModeStop_DMA(...); g_data_ready=1; g_acq_busy=0
```

FFT などの重い処理は**メインループ**で実行（ISR は短く保つ）。

---

## 5. 位相差アルゴリズム（CMSIS-DSP, クロススペクトル法）

```
1. adc12_buff を ch1/ch2 に分離し float へ変換（16bit、ミッドスケール 32768 を減算）
2. arm_rfft_fast_f32 で各 ch の実FFT → 複素スペクトル X1, X2 (N=adc_num)
   出力配置: out[0]=DC, out[1]=Nyquist, out[2k]=Re(k), out[2k+1]=Im(k)
3. ピークビン k を決定:
   既知 100kHz の期待ビン k0 = round(target_hz * N / fs) を中心に、
   ch1 マグニチュードのピークを ±search_win で探索（DC近傍は maxoffset で除外）
4. ピーク近傍帯域 [k-band_w, k+band_w] で X1·conj(X2) を加算:
     Sre += a*c + b*d ;  Sim += b*c - a*d     (X1=a+jb, X2=c+jd)
5. phase_diff[rad] = atan2f(Sim, Sre)          // = phase(X1) - phase(X2)
6. deg へ変換し (-180, 180] に wrap
```

**OCR ドラフトからの修正**
- `atan2(I,Q)` → クロススペクトルの `atan2f(Sim,Sre)`（虚部, 実部）。符号反転バグ解消。
- 2ch が別々のピークビンを選ぶ不整合 → **共通ビン**を使用。
- 帯域加算でリーク・ノイズに頑健化。

**リーク注意**: fs=1 MHz, N=4096 でビン幅 244 Hz、100 kHz≈ビン 409.6（非整数）。
両 ch 同一周波数のため位相差では同相成分が相殺。**窓関数は使わない**（矩形窓）。
`adc_num` は 2 のべき（rfft_fast 制約, 既定 4096）。

---

## 6. パラメータ（`parm[]`, reg_t 配列）

| addr | 名前 | 型 | 既定 | 説明 |
|---|---|---|---|---|
| 0 | firm_no | int | 1 | ファーム番号 |
| 1 | adc_num | int | 4096 | 1取得サンプル数（2のべき, ≤4096） |
| 2 | fs_hz | int | 1000000 | ADC サンプリング周波数 [Hz] |
| 3 | target_hz | int | 100000 | 期待信号周波数 [Hz] |
| 4 | search_win | int | 20 | ピーク探索窓 [bin] |
| 5 | band_w | int | 2 | クロススペクトル加算半幅 [bin] |
| 6 | maxoffset | int | 10 | DC 近傍除外ビン数 |
| 7 | att_tx_db | float | 0.0 | TX アッテネータ [dB] |
| 8 | att_rx_db | float | 0.0 | RX アッテネータ [dB] |

フラッシュ保存（`RS`）は姉妹PJ実装を流用可能だが**オプション（フェーズ2）**。

---

## 7. 検証

- 信号発生器で 2ch に既知位相差（0/45/90/180°）→ GUI 表示値と照合。
- オシロで TIM1 TRGO 1 MHz / 取得 4.096 ms を確認。
- GUI 受信タイムスタンプで 100 Hz を確認。
- ホスト側で FFT/位相差関数を既知正弦波データで単体検算（型番確定前でも可能）。
