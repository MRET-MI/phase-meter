# ファームウェア仕様書 — 2ch 位相差計

**対象:** phase_meter_firm_v0
**MCU:** STM32H7 系（型番確定後に最終化。姉妹PJ `stage_controller_firm_v0` = STM32H7A3VIT6 を基準）
**更新日:** 2026-07-05

> 本書は MCU 型番確定前の設計指示書。CubeMX 生成後、`Core/Src` 等のユーザコード領域に
> 本リポジトリの `firmware/phase_meter_firm_v0/` 配下のソースを統合する。

---

## 1. 機能概要

100 kHz のアナログ波形 2ch を **同時 ADC** し、FFT により 2ch 間の **位相差**[deg] を
算出、USB CDC（仮想COM）で PC へ連続送信する。送受信パスの可変アッテネータ
（HMC8073 ×2）を SPI で制御する。併せて TMP126 温度センサ ×3 を SPI で読み、
計測中は温度を 10 Hz でストリーミングする。

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
| TIM1 | ADC トリガ | **TRGO = Update** を ADC 外部トリガに使用（`ADC_EXTERNALTRIG_T1_TRGO`）。内部モード: 内部クロック `ARR=239`（240 MHz/240 = 1 MHz）。外部モード: **ETR(PE7) 外部クロックモード2**, `ARR=0`（1 パルス=1 update=1 変換） |
| TIM6 | 100 Hz 状態ティック | 10 ms 周期。内部モードの算出トリガ・時間基準・温度10Hz |

> 外部クロックモード（`trig_src=1`）: 外部パルス(PE7=TIM1_ETR)を ADC のサンプリングクロックにする。
> クロック源の内部/外部切替は実行時に `HAL_TIM_ConfigClockSource`（`Tim1_SetExternalClock()`）で行い、
> ADC/DMA は両モードとも**連続サーキュラのまま停止しない**（H7 dual-ADC 再アーム不具合を回避）。
> ADC トリガはどちらも TRGO=Update に統一（内部は 1 MHz update、外部はパルス毎 update）。
> OCR ドラフトの TIM2 と RCR トリックは廃止。

### 3.3 SPI（HMC8073 TX/RX）

SPI2/SPI3 を **Full-Duplex Master** で使用（TMP126 の読出しに MISO が要るため、
HMC8073 単独時の 8bit/Transmit-Only から変更）。TX/RX 各 1 系統。

| 系統 | SPI | SCK | MOSI | MISO | LE(CS) |
|---|---|---|---|---|---|
| HMC8073 TX | SPI2 | PB13 | PB15 | PB14 | PB4 |
| HMC8073 RX | SPI3 | PC10 | PC12 | PC11 | PC15 |

HMC8073 は 8bit/LSB-first/書込専用。ドライバは各アクセス時に SPI Init を保存/復元し、
同一バス上の TMP126（16bit/MSB-first）と共存する（3.4 参照）。

### 3.4 SPI（TMP126 温度センサ ×3）

TI TMP126（14bit 温度センサ, SPI Mode 0, 16bit ワード MSB-first, デバイスID=0x2126）を
HMC8073 と同じ SPI2/SPI3 バスに相乗りさせる。CS は個別 GPIO。

| センサ | SPI | CS ピン |
|---|---|---|
| `g_tmp126_1` | SPI2 | PB1 |
| `g_tmp126_2` | SPI2 | PB2 |
| `g_tmp126_3` | SPI3 | PC13 |

- ドライバ `tmp126_driver.{c,h}`：`TMP126_HandleTypeDef{hspi, cs_port, cs_pin, last_temp_c, last_raw}`、
  `TMP126_InitPins` / `TMP126_ReadRegister` / `TMP126_ReadTemperature` / `TMP126_ReadDeviceId`。
  LSB = 0.03125 ℃。
- 各読出しは HMC8073 用の SPI Init（8bit/LSB）と衝突しないよう **Init を保存/復元**する。
- `TMP126_ENABLED`（既定 1）で有効、`TMP126_STREAM_DIV`（既定 10）でストリーム間引き。
  `TMP126_ENABLED=0` で温度機能をビルド時に無効化できる。

### 3.5 SPI（MCP41HV51-104 デジタルポテンショメータ ×2）

Microchip MCP41HV51-104（8bit・257タップ・100kΩ, SPI Mode 0, MSB-first, ≤10MHz）を TX/RX 各1個、
HMC8073・TMP126 と同じ SPI2/SPI3 に相乗りさせる。CS は個別 GPIO。

| デバイス | SPI | CS ピン |
|---|---|---|
| `g_mcp41hv51_tx` | SPI2 | PB3 |
| `g_mcp41hv51_rx` | SPI3 | **PC14** |

- ドライバ `mcp41hv51_driver.{c,h}`：`MCP41HV51_HandleTypeDef{hspi, cs_port, cs_pin, last_wiper}`、
  `InitPins` / `WriteRegister` / `ReadRegister` / `SetWiper`(0..256) / `GetWiper` / `Increment` / `Decrement`。
  16bit コマンドフレーム（コマンドバイト＋データ）。各アクセスで **Init を 8bit/MSB に保存/復元**。
- `MCP41HV51_AppInit()` が parm[13]/[14] のワイパ値を書き込む。`POTT<v>`/`POTR<v>` で変更、`RS` で保存。
- **注意**: **PC14 は OSC32_IN(LSE)** ＝ PC15 と同じバックアップドメイン。GPIO 化には RCC で LSE を
  Disable し PC14 を解放する必要がある。PB3 は JTDO/SWO（SWO トレース不使用時は GPIO 出力可）。
- `MCP41HV51_ENABLED=0` でビルド時に無効化できる。

---

## 4. ソフトウェア構成

```
Core/Inc/  functions.h  macros.h  DWT.h  reg_store.h  hmc8073_driver.h  tmp126_driver.h
Core/Src/  functions.c  DWT.c     reg_store.c  hmc8073_driver.c  tmp126_driver.c
           main.c(生成, USER CODE に StartUp/Main_Processing を追加)
USB_DEVICE/App/   usbd_cdc_if.c (USER CODE に RX リング/送信ヘルパーを追加 → INTEGRATION.md)
```

### 4.1 状態機械（`main_state`）

| 状態 | 値 | 動作 |
|---|---|---|
| `WAIT` | 0 | コマンド待ち。取得停止。 |
| `START` | 1 | 100 Hz で位相差算出 → `F,<deg>\r\n` 連続送信。 |
| `WAVECHECK` | 2 | 未使用（生波形は START 中の `WAVE` 単発ダンプで実装）。 |

**生波形ダンプ（`WAVE`）**: START 中のみ有効。`snapshot_frame()` で現フレームをライブ・
スナップショットし、`WaveDump()` が `H,<adc_num>,<fs_hz>` → `W,<hex>`×N → `WEND` を送出（生16bit
カウント, ch1=下位/ch2=上位）。start/stop を伴わないため H7 再アーム不具合を回避。WAIT 中は `NG`。

**取得の起動/停止（`RUN`/`RUNN`/`STOP`）**: `RUN`＝フリーラン（`STOP` まで無限）。
`RUNN<n>`＝時間指定取得：`F,` 出力を `g_out_count` で数え、`g_target_count`(=n) に達したら
`DONE\r\n` を送って `ADC_Stop()`（WAIT へ）＝温度ストリームも停止。`g_out_count` は `ADC_Start()`
で 0 リセット（`R<addr>S` 由来の再アームでも窓は継続・再スタート）。`STOP`/`RUN` は
`g_target_count=0` に戻す。GUI は「秒×100」または「点数直接」で `n` を決めて送出する。

### 4.2 起動シーケンス（main.c USER CODE BEGIN 2）

```
HAL/クロック/ペリフェラル初期化（CubeMX 生成）
  → StartUp()  = GetCLK() → Reg_prepare() → Parm_Flash_Load() → Parm_set()
                 → ADC_Init() → DAC_Init() → HMC8073_AppInit() → TMP126_AppInit()
  → Start_Main() = TIM6 10ms ティック有効化（main_state=WAIT）
while(1) → Main_Processing()
```

### 4.3 データフロー（割込 → メインループ）

ADC1/2 dual + TIM1 トリガの**連続サーキュラ DMA** は `ADC_Start()` で一度起動し、以後停止しない
（`adc12_buff[adc_num]` を周回）。「いつ算出するか」を `trig_src` で切替える。

```
算出トリガ（どちらか一方が g_process=1 をセット）
  internal (trig_src=0): TIM6 100Hz ISR (OnTick100Hz) → g_process=1
  external (trig_src=1): ADC ConvCplt ISR (OnAdcConvCplt, DMA1周=adc_numパルス毎) → g_process=1
  ※ dbg_tick は常時加算（g_seq の時間基準・温度10Hz に使用）

メインループ Main_Processing()
   ① Cmd_Process() : USB 受信コマンド処理（全状態共通）
   ② g_process → g_seq=dbg_tick; snapshot_frame()（サーキュラバッファから1フレーム複製）;
        CalcMain(): 位相差算出 → F,<seq>,<deg>,<amp>,<freq> 送信;
        g_out_count++ → RUNN の目標到達なら DONE→ADC_Stop()
   ③ TempStream(): START 中は TMP126_STREAM_DIV ティック毎（10 Hz）に
        3センサを読み T,<tick>,<t1>,<t2>,<t3> を送信
```

FFT などの重い処理は**メインループ**で実行（ISR は `g_process=1` を立てるだけで短く保つ）。
位相差はクロススペクトル（ch 間相対）のため、スナップショット開始位置の回転は結果に影響しない。

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
| 1 | adc_num | int | 4096 | 1取得サンプル数（2のべき, ≤4096, `arm_rfft_fast`制約） |
| 2 | fs_hz | int | 1000000 | サンプリング周波数 [Hz]。**TIM1 ARR に実配線**（達成値を書戻し）。範囲 4k–2.5M |
| 3 | target_hz | int | 100000 | 期待信号周波数 [Hz]（期待ビン k0 算出） |
| 4 | search_win | int | 20 | ピーク探索窓 [bin]（peak_mode=1時） |
| 5 | band_w | int | 2 | クロススペクトル加算半幅 [bin] |
| 6 | maxoffset | int | 10 | DC 近傍除外ビン数 |
| 7 | att_tx_db | float | 0.0 | TX アッテネータ [dB] |
| 8 | att_rx_db | float | 0.0 | RX アッテネータ [dB] |
| 9 | peak_mode | int | 1 | 0=固定ビン(target_hz) / 1=ピーク探索(±search_win) |
| 10 | dac_v | float | 3.3 | DAC1_OUT2(PA5) 出力電圧 [V]。起動時から出力、`R10S<V>` で変更 |
| 11 | trig_src | int | 0 | ADC トリガ源。0=内部(TIM6 100Hz 連続) / 1=外部(TIM1 ETR=PE7 の外部クロック) |
| 12 | trig_edge | int | 0 | 外部(ETR)極性。0=立上がり / 1=立下がり |
| 13 | pot_tx | int | 128 | MCP41HV51 TX ワイパ（SPI2/CS PB3）。0..256。`POTT<v>` で設定 |
| 14 | pot_rx | int | 128 | MCP41HV51 RX ワイパ（SPI3/CS PC14）。0..256。`POTR<v>` で設定 |

- `R<addr>S<val>` で変更すると `Parm_set()` 再適用＋（動作中なら）自動再アームで即反映。
- `RS` で全 parm をフラッシュ保存（共有 `reg_store`）、起動時 `Parm_Flash_Load()` で復元。
- 出力 `F,<deg>,<amp_v>,<freq_hz>` に **ピーク振幅[V]・ピーク周波数[Hz]** を含む。

---

## 7. 検証

- 信号発生器で 2ch に既知位相差（0/45/90/180°）→ GUI 表示値と照合。
- オシロで TIM1 TRGO 1 MHz / 取得 4.096 ms を確認。
- GUI 受信タイムスタンプで 100 Hz を確認。
- ホスト側で FFT/位相差関数を既知正弦波データで単体検算（型番確定前でも可能）。
