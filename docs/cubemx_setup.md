# CubeMX 設定ガイド — phse-meter-firm_v0 (NUCLEO-H753ZI)

CubeMX で生成したベースプロジェクトに対し、本ファームを動かすために必要な設定。
✅=設定済み / ⚠️=要設定（このままでは動作しない）。設定後、Project → Generate Code。

---

## 0. ボード前提（NUCLEO-H753ZI / STM32H753ZIT6）

- USB は **OTG_FS + CDC**（User USB CN13, PA11/PA12）。送信=`CDC_Transmit_FS`, 受信=`CDC_Receive_FS`, ハンドル=`hUsbDeviceFS`。
- ST-LINK 仮想COM = USART3(PD8/PD9)。本通信は USB CDC を使用。
- D-Cache 無効（DMA キャッシュメンテ不要）。

---

## 1. クロック ✅（設定済み・確認のみ）

| 項目 | 値 |
|---|---|
| PLL ソース | HSE 8 MHz |
| SYSCLK / CPU | 480 MHz |
| HCLK(AHB) / APB タイマクロック | **240 MHz** |
| 電源スケール | **VOS0** |
| ADC カーネルクロック | **≒50.5 MHz**（PLL2P, prescaler DIV1） |
| USB クロック | HSI48 |

> TIM1 で 240 MHz ÷ 240 = **1.000 MHz** トリガ。ADC 50.5 MHz, 16bit 変換 17cyc ≒ 337 ns < 1 µs。

---

## 2. ADC1 / ADC2 ⚠️

| 設定 | 値 | 状態 |
|---|---|---|
| Mode (multimode) | Dual regular simultaneous | ✅ |
| ADC1 ch | INP14 (PA2), Rank1 | ✅ |
| ADC2 ch | INP15 (PA3), Rank1 | ✅ |
| **Resolution** | **16 bits**（推奨。12bit も可） | ⚠️ 現状 12bit |
| **Sampling Time** | **8.5 Cycles**（ADC1・ADC2 両方） | ⚠️ 現状 1.5 |
| Clock Prescaler | Asynchronous **DIV1**（ADC1/ADC2 一致） | ⚠️ ADC1 要確認 |
| External Trigger Conv | **TIM1 Trigger Out event (TIM1_TRGO)** | ✅ **コードで上書き**（`ADC_Init()` が `T1_TRGO` に再設定）。CubeMX 設定は任意 |
| External Trigger Edge | **Rising** | ✅ コードで Rising に上書き |
| Continuous Conv Mode | Disabled | （1トリガ1変換） |
| **Conversion Data Management** | **DMA Circular Mode** | ⚠️ 連続取得。One Shot だと1フレームで停止 |
| Overrun behaviour | Overrun data overwritten | 既定可 |

---

## 3. DMA（ADC1）⚠️

| 設定 | 値 | 状態 |
|---|---|---|
| Stream | DMA1_Stream0 | ✅ |
| Direction | Periph → Memory | ✅ |
| Peripheral/Memory data width | **Word / Word** (32-bit) | ✅ |
| Memory increment | Enable | ✅ |
| **Mode** | **Circular** | 連続取得（停止/再アーム不要で堅牢） |
| Priority | High 以上推奨 | — |
| NVIC DMA1_Stream0 割込 | Enable | ✅ |

> Circular 連続取得を採用: ADC/DMA は回しっぱなしにし、100 Hz ごとに DMA 書込み位置
> (NDTR) を基準に時間連続な1フレームを `s_snapshot` へコピーして FFT する（`functions.c`
> の `snapshot_frame`）。H7 でデュアル ADC を毎フレーム start/stop すると再アームが不安定に
> なる問題（2フレーム目以降が完了しない）を回避できる。

---

## 4. TIM1（ADC トリガ）⚠️

| 設定 | 値 |
|---|---|
| Clock Source | **Internal Clock**（既定。外部モードはコードで ETR に切替） |
| **Trigger Event Selection (TRGO)** | **Update Event**（`TIM_TRGO_UPDATE`）→ ADC トリガ源 | 
| Prescaler (PSC) | **0** |
| Counter Period (ARR) | **239**（内部モード: 240 MHz / 240 = 1 MHz） |
| PWM CH1 (PE9) | 不要（TRGO=update をトリガにするため。設定してあっても無害） |

> ADC トリガを **CC1→TRGO(update)** に統一。内部モードは ARR=239 の update=1MHz、
> 外部モードは ETR パルス毎の update。クロック源の内外切替は `functions.c` の
> `Tim1_SetExternalClock()`（`HAL_TIM_ConfigClockSource`）で実行時に行うため、
> CubeMX は Internal のままでよい。

---

## 4.5 外部トリガ（TIM1_ETR = PE7）⚠️ 新規追加 — 外部クロックモード用

外部パルスを ADC サンプリングクロックにする（`trig_src=1`）場合に必要。

| 設定 | 値 |
|---|---|
| **PE7** | **TIM1_ETR**（AF1）に割当 |
| ETR 極性 | Rising（既定。実行時に parm `trig_edge` で反転可） |

> CubeMX で PE7 を TIM1_ETR に割り当てると ETR ピンの AF が構成される。External Clock
> Mode 2（ETRMODE2）への切替と ARR=0 はコード（`Tim1_SetExternalClock`）で行う。
> 内部モードのみ使う場合は本ステップ不要（PE7 未使用のまま）。

---

## 5. TIM6（100 Hz ティック）⚠️ 未追加

| 設定 | 値 |
|---|---|
| 有効化 | Activated（Internal Clock） |
| Prescaler (PSC) | **2399** |
| Counter Period (ARR) | **999** |
| 周期 | 240 MHz / 2400 / 1000 = **100 Hz (10 ms)** |
| NVIC TIM6 global interrupt | **Enable** |

---

## 5.5 DAC1（PA5 アナログ出力）⚠️ 新規追加

| 設定 | 値 |
|---|---|
| DAC1 | 有効化、**OUT2（channel 2）= PA5** |
| Output Buffer | Enable |
| Trigger | None（ソフト設定, `HAL_DAC_SetValue`） |
| Sample&Hold | Disable |

> 生成後、ハンドル `hdac1` / `MX_DAC1_Init` ができる。`functions.c` の `DAC_Init()` で
> `HAL_DAC_Start(&hdac1, DAC_CHANNEL_2)` → 起動時から parm[10]=dac_v（既定 3.3V）を出力。
> `R10S<V>` で変更、`RS` で保存。**このステップ未実施だと `hdac1` 未定義でビルドエラー**
> （暫定回避は `functions.c` の `DAC_ENABLED` を 0）。

---

## 6. USB ✅

- USB_OTG_FS = Device_Only、Class = CDC、HSI48。確認のみ。

---

## 7. SPI（HMC8073 アッテネータ）— 設定済み ✅

HMC8073LP3DE ×2（TX/RX）を別バスで制御。共通設定: **Transmit Only Master,
8bit, LSB First, CPOL Low, CPHA 1Edge, NSS Software**, BaudRate prescaler 8。

| 用途 | SPI | SCK | MOSI | LE(GPIO out, 初期Low) |
|---|---|---|---|---|
| TX (`g_hmc8073_transmitter`) | SPI2 | PB13 | PB15 | **PB4** |
| RX (`g_hmc8073_receiver`) | SPI3 | PC10 | PC12 | **PC15** |

- MISO は HMC8073 が書き込み専用のため不要（PB14 等は未使用で可）。
- **PC15 は元 RCC_OSC32_OUT(LSE)**。GPIO 化のため RCC の LSE を Disable 済み。
- ドライバ `Core/{Inc,Src}/hmc8073_driver.{h,c}`、実体化・駆動は `functions.c`
  （`HMC8073_ENABLED=1`）。**要確認**: TX/RX とバスの対応、各デバイスの
  アドレス strap A2:A1:A0（現状コードは両方 0 を仮定）。

---

## 7.5 SPI（MCP41HV51-104 デジタルポテンショメータ ×2）⚠️ 新規追加

TMP126 と同じく SPI2/SPI3 に相乗り（8bit/MSB/Mode0, Init 保存復元）。CS は個別 GPIO。

| 用途 | SPI | /CS（GPIO out, 初期 High, Low speed） |
|---|---|---|
| TX (`g_mcp41hv51_tx`) | SPI2 | **PB3** |
| RX (`g_mcp41hv51_rx`) | SPI3 | **PC14** |

- **PB3・PC14 を `GPIO_Output`（push-pull, 初期 High, Low speed）** に設定して Generate Code。
  未設定だと CS が構成されず動作しません。
- **PC14 は RCC_OSC32_IN(LSE)** ＝ PC15 と同じバックアップドメイン。GPIO 化には **RCC で LSE を
  Disable し PC14 を解放**する必要がある（未対応だと PC14 が駆動しない）。
- **PB3 は JTDO/SWO**。GPIO 出力として使えるが SWO トレースは無効になる。
- ドライバ `Core/{Inc,Src}/mcp41hv51_driver.{h,c}`、実体化・駆動は `functions.c`（`MCP41HV51_ENABLED=1`）。
  `POTT<v>`/`POTR<v>`（0..256）で設定、`RS` で保存、起動時 `MCP41HV51_AppInit()` が parm[13]/[14] を適用。

---

## 8. 生成後に追記するユーザコード（USER CODE ブロック）

| ファイル | 追記内容 |
|---|---|
| `Core/Src/main.c` | `StartUp()`（BEGIN 2）、`Main_Processing()`（BEGIN 3 / while ループ） |
| `Core/Src/functions.c` (新規) | 状態機械・ADC 取得・位相差・コマンド処理 |
| `Core/Inc/functions.h`, `macros.h` (新規) | 型・定数・プロトタイプ |
| `Core/Src/DWT.c`, `Core/Inc/DWT.h` (新規) | サイクルカウンタ計測 |
| `Core/Src/stm32h7xx_it.c` | HAL コールバックは functions.c 側で weak override するため原則変更不要 |
| `USB_DEVICE/App/usbd_cdc_if.c` | RX リングバッファ + `CDC_RxReadByte` / `CDC_SendString`（FS 版） |

> コールバック対応:
> - `HAL_TIM_PeriodElapsedCallback`（htim6）→ `OnTick100Hz()`
> - `HAL_ADC_ConvCpltCallback`（hadc1）→ `OnAdcConvCplt()`
> これらは functions.c で HAL の weak 関数を override して実装する。
