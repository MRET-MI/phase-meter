# phase-meter — 2ch 位相差計（STM32H753 + PySide6）

100 kHz のアナログ波形 2ch を同時 ADC し、FFT で 2ch 間の位相差を算出して
USB CDC で PC に連続送信、PySide6 GUI でライブ表示する。

## 構成

```
phase-meter/
  docs/
    firmware_spec.md   ファーム設計仕様
    command_spec.md    USB CDC コマンド仕様（ファーム/GUI 共通）
    cubemx_setup.md    CubeMX 設定ガイド（NUCLEO-H753ZI）
    build_notes.md     CubeIDE ビルド手順（CMSIS-DSP 追加など）
  phse-meter-firm_v0/  STM32CubeIDE プロジェクト（ファーム）
  pc_gui/              PySide6 GUI
```

## ハードウェア

- 基板: NUCLEO-H753ZI（STM32H753ZIT6）
- 入力: PA2 = ch1 (ADC1_INP14), PA3 = ch2 (ADC2_INP15)
- 通信: User USB（CN13）= USB CDC 仮想COM
- ADC: デュアル同時 16bit / 8.5cyc、TIM1_CH1 @1MHz トリガ、DMA で 4096 点取得
- 位相算出: 100 Hz（TIM6）、クロススペクトル法

## ファーム（CubeIDE）

1. `docs/cubemx_setup.md` どおりに CubeMX 設定（適用済み）。
2. `docs/build_notes.md` §2 に従い **CMSIS-DSP** を追加。
3. ビルド → ST-LINK で書込み。

## GUI

```
cd pc_gui
pip install -r requirements.txt
python main.py
```

1. ポートを選んで **Connect**
2. **RUN** で計測開始 → 位相差・振幅がグラフ（縦2段）、周波数はテキストにライブ表示
3. **Settings** で adc_num / fs / target / peak_mode 等を Read/Apply/Save→Flash
4. データ保存:
   - **Save all data…**：接続中に受信した全サンプルをワンクリックで CSV 保存（自動ファイル名）
   - **Start/Stop CSV log**：長時間の連続記録をファイルへ逐次書き出し
5. Attenuator（TX/RX dB）は HMC8073 配線後に有効

## コマンド（抜粋, `\n` 終端）

| 送信 | 動作 | 応答 |
|---|---|---|
| `RUN` | 連続ストリーミング開始 | `OK` ＋ `F,<deg>` 連続 |
| `STOP` | 停止 | `OK` |
| `VER` | 版数 | `phse-meter-firm_v0` |
| `ATTT<dB>` / `ATTR<dB>` | TX/RX 減衰設定 | `OK` |

詳細は `docs/command_spec.md`。

## 今後

- HMC8073（TX/RX アッテネータ, SPI）ドライバ — コア動作確認後に追加
- 生波形ダンプ（`WAVE`）とその GUI 表示 — フェーズ2
