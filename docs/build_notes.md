# ビルド手順 — phse-meter-firm_v0 (STM32CubeIDE)

CubeMX 生成プロジェクトにアプリ層を統合した後の、ビルドに必要な追加設定。

---

## 1. 追加したファイル（USER CODE / 新規）

| ファイル | 区分 |
|---|---|
| `Core/Inc/macros.h` | 新規 |
| `Core/Inc/functions.h` | 新規 |
| `Core/Inc/DWT.h` | 新規 |
| `Core/Src/functions.c` | 新規 |
| `Core/Src/DWT.c` | 新規 |
| `Core/Src/main.c` | USER CODE（include / BEGIN 2 / BEGIN 3） |
| `USB_DEVICE/App/usbd_cdc_if.c` | USER CODE（RXリング・`CDC_RxReadByte`・`CDC_SendString`） |
| `Core/Inc/hmc8073_driver.h` / `Core/Src/hmc8073_driver.c` | 新規（アッテネータ） |

> 新規 `.c` は `Core/Src` に置けば CubeIDE が自動でビルド対象にする（要 Refresh / Build）。

---

## 1.5 共有モジュール reg_store の取り込み ★必須

パラメータのフラッシュ保存は複数プロジェクト共通の
`C:\Users\tm472\Documents\Claude\common\reg_store\{reg_store.c,reg_store.h}` を使う。
これはプロジェクト外にあるため、CubeIDE に**リンクして取り込む**:

1. **ソースをビルド対象に**（リンクフォルダ）:
   プロジェクト右クリック → New → Folder → **Advanced** →
   「Link to alternate location (Linked Folder)」にチェック →
   `C:\Users\tm472\Documents\Claude\common\reg_store` を指定 → Finish。
   （`reg_store.c` がビルドに含まれる）
2. **インクルードパス追加**:
   Project → Properties → C/C++ General → Paths and Symbols → Includes →
   GNU C → Add → 上でリンクしたフォルダ（Workspace…）を追加。
   → `#include "reg_store.h"` が解決する。

> 他プロジェクト（auto-stage-control）でも同じ手順でリンクすれば共通利用できる。
> フラッシュ諸元（ワード 16/32B・セクタ・電圧レンジ）は各プロジェクトの `RegStore_t`
> 初期化で与える（phase-meter は `functions.c` の `s_regstore`）。

---

## 2. CMSIS-DSP（FFT）の追加 ★必須

`functions.c` は `arm_rfft_fast_f32` / `arm_cmplx_mag_f32` 等を使うため CMSIS-DSP が必要。
CubeIDE 標準生成では DSP は入らないので追加する。**プリビルドライブラリ方式**が簡単。

### 2.1 プリビルドライブラリ方式（推奨）

1. STM32Cube FW_H7 パッケージ内の DSP を入手:
   `…/STM32Cube/Repository/STM32Cube_FW_H7_V1.12.1/Drivers/CMSIS/`
   - `Lib/GCC/libarm_cortexM7lfdp_math.a`（Cortex-M7 + 倍精度FPU 用）
   - `DSP/Include/`（ヘッダ群）
2. プロジェクトにコピー（例）:
   - `libarm_cortexM7lfdp_math.a` → `Drivers/CMSIS/Lib/GCC/`
   - `DSP/Include/*` → `Drivers/CMSIS/DSP/Include/`
3. CubeIDE 設定:
   - **C/C++ Build → Settings → MCU GCC Compiler → Include paths** に
     `Drivers/CMSIS/DSP/Include` を追加
   - **MCU GCC Linker → Libraries**:
     - Libraries (-l) に **`arm_cortexM7lfdp_math`**
       ※ `-l<name>` は自動で先頭`lib`・末尾`.a`を付ける。ファイル名
       `libarm_cortexM7lfdp_math.a` から **`lib` と `.a` を外した名前**を書く
       （`libarm_cortexM7lfdp_math` と書くと `liblib….a` を探して失敗する）。
     - Library search path (-L) に `../Drivers/CMSIS/Lib/GCC`（`.a` の実在フォルダ）
   - 別法: Libraries を使わず **Linker → Miscellaneous → Other objects** に
     `.a` のフルパスを直接追加（この場合はファイル名そのままで可）。
   - **MCU GCC Compiler → Preprocessor** に `ARM_MATH_CM7` を定義
     （`__FPU_PRESENT=1` は H7 で定義済み）

### 2.2 ソース追加方式（代替）

ライブラリではなく DSP ソースをビルドに含める場合は、最低限以下を追加:
`arm_rfft_fast_f32.c`, `arm_rfft_fast_init_f32.c`, `arm_cfft_f32.c`,
`arm_cfft_radix8_f32.c`, `arm_bitreversal2.c`, `arm_cmplx_mag_f32.c`,
`arm_common_tables.c`, `arm_const_structs.c` ＋ `DSP/Include` をパスに追加、
`ARM_MATH_CM7` を定義。

---

## 3. printf について

位相ストリーミングおよびレジスタ float 表示は自前の `ftoa3()` を使うため、
**printf の float 対応（-u _printf_float）は不要**。

---

## 4. ビルド & 書き込み

1. Project → Build（エラー0を確認）
2. NUCLEO-H753ZI を ST-LINK で接続し Run/Debug で書き込み
3. **User USB（CN13, micro-AB）** を PC に接続 → 仮想COMポートが現れる
   （ST-LINK 側の VCP ではなく、こちらが本通信ポート）

---

## 5. 動作確認

| 操作 | 期待 |
|---|---|
| `VER`+改行 送信 | `phse-meter-firm_v0` 応答 |
| `RUN`+改行 | `OK` 応答後、`F,<deg>` が ~100Hz で連続出力 |
| 信号発生器で2chに既知位相差 | 表示が一致（0/45/90/180°で検証） |
| `STOP`+改行 | `OK`、ストリーム停止 |
| オシロで PE9 | 1 MHz の TIM1 CH1 波形 |

詳細コマンドは `docs/command_spec.md`、設計は `docs/firmware_spec.md` 参照。
