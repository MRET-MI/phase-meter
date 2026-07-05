# 自動計測スクリプト仕様 — PC GUI

**対象:** pc_gui（PySide6）
**更新日:** 2026-07-05

パラメータを変えながら計測し、各条件のデータを自動保存するための **スクリプト機能**。
GUI 側だけで完結し、**ファーム変更は不要**（既存の USB CDC コマンドのみ使用）。
実装は [`pc_gui/script_runner.py`](../pc_gui/script_runner.py) と
[`pc_gui/main.py`](../pc_gui/main.py)。

---

## 1. 使い方

1. デバイスに Connect。
2. 「Auto measure」パネルの **Load script…** でスクリプト（`.txt`）を読み込む。
3. **Run** を押し、保存先フォルダを選ぶ（既定＝スクリプトと同階層）。
4. ランナーが各行を順に実行。`RUNN` ごとに 1 CSV を自動保存。
5. **Stop** でいつでも中断（安全に `STOP` を送出）。

実行中は手動操作（RUN/STOP/Connect/Settings/Send）を無効化する。

---

## 2. スクリプト文法

- 1 行 1 ステップ。空行と `#` 以降はコメント。
- キーワードは大文字小文字を区別しない。
- **生デバイスコマンド**（`R2S1000000` / `ATTT10` / `RS` / `RA` など）はそのまま送信し、
  `OK`/`NG`（`RA` は `END`）を待って次行へ進む。`NG` で中断。

| 命令 | 説明 |
|---|---|
| `LABEL <text>` | 次に自動保存するファイル名の stem（省略時 `point`） |
| `WAIT <sec>` | 指定秒スリープ（非ブロッキング） |
| `CLEAR` | グラフ/履歴クリア（各 `RUNN` 前にも自動実行） |
| `SAVE [name]` | 現在の収集データを即保存（省略時は自動名） |
| `RUNN <n>` / `RUNN<n>` | n 点取得 → `DONE` 待ち → その点を自動保存 |
| `SWEEP <var> <start> <stop> <step>` … `ENDSWEEP` | ブロックを実行前にフラット展開（`${var}` 置換、ネスト可） |

### RUNN の同期
`RUNN<n>` 送信後、ファームは n サンプル出力し `DONE` を返す。ランナーは `DONE` を待ってから
次行へ進む（タイムアウト = n×10 ms + 3 s）。タイムアウト時はエラー中断。

### 自動保存
`RUNN` の `DONE` 到達時、その点で集めた F/T 履歴＋パラメータを
`<出力フォルダ>/<NN>_<label>.csv`（NN=01,02,… の連番）に保存する。
`SAVE <name>` を書けば任意名で即保存も可能。

---

## 2.1 パラメータの指定方法

各パラメータは `R<addr>S<val>` で設定する（整数はそのまま、float は小数可）。書込み後は
ファーム側で `Parm_set()` が即適用され、計測中なら自動で再アームされる。**DAC 電圧もパラメータ
`dac_v`（addr 10）としてスクリプトから設定できる**（`R10S<V>`）。

| addr | 名前(RA) | 型 | スクリプトでの指定 | 例 |
|---|---|---|---|---|
| 0 | firm_no | int | `R0S<n>`（通常変更しない） | — |
| 1 | adc_num | int | `R1S<2のべき>`（≤4096） | `R1S4096` |
| 2 | fs_hz | int | `R2S<Hz>`（4k–2.5M, TIM1へ実配線） | `R2S1000000` |
| 3 | target_hz | int | `R3S<Hz>`（期待信号周波数） | `R3S100000` |
| 4 | search_win | int | `R4S<bin>`（ピーク探索窓） | `R4S20` |
| 5 | band_w | int | `R5S<bin>`（帯域加算半幅） | `R5S2` |
| 6 | maxoffset | int | `R6S<bin>`（DC近傍除外） | `R6S10` |
| 7 | att_tx_db | float | **`ATTT<dB>`**（HW反映・推奨, 0–31.5 / 0.5刻み） | `ATTT10` |
| 8 | att_rx_db | float | **`ATTR<dB>`**（HW反映・推奨, 0–31.5 / 0.5刻み） | `ATTR3.5` |
| 9 | peak_mode | int | `R9S<0/1>`（0=固定ビン/1=探索） | `R9S1` |
| 10 | **dac_v** | float | **`R10S<V>`**（0–3.3V, PA5出力） | `R10S3.300` |

> **アッテネータ（7/8）の注意**: `R7S/R8S` は parm 値を更新するだけで HMC8073 ハードには
> 反映されない（ハード反映は `ATTT`/`ATTR` が担当）。スクリプトでは **`ATTT`/`ATTR` を使うこと**。
> 一方 `dac_v`（10）は `Parm_set()` が DAC 出力に反映するため `R10S<V>` でよい。
>
> **ATT の設定可能値**: HMC8073（6bit DSA）は **0.0〜31.5 dB / 0.5 dB ステップ**。
> ファームは範囲チェックのみ（`0.0 ≤ dB ≤ 31.5`、外れると `NG`）。0.5 dB に満たない端数は
> ハード側で最近傍 0.5 dB に量子化される（例 `ATTT3.7` は実効 3.5 dB 相当）。
> 例: `ATTT0` / `ATTT12.5` / `ATTR31.5`。

- 現在値の確認は `R<addr>R`（単発）または `RA`（全 parm 一覧）。
- 変更を電源off後も残すには `RS`（全 parm をフラッシュ保存）。
- 各保存 CSV 先頭の `# param <name>=<val>` は、実行開始時の `RA` ＋以後の `R<addr>S` 反映値。

---

## 3. 保存ファイル形式（1 計測点 = 1 CSV）

先頭にパラメータ・スナップショットをコメント行で記録し、続けて F と T を時刻順に結合。

```
# saved 2026-07-05T10:20:30
# param firm_no=1
# param adc_num=4096
# param fs_hz=1000000
# param target_hz=100000
...
time_s,phase_deg,amp_v,freq_hz,temp_t1_c,temp_t2_c,temp_t3_c
0.0000,-12.345,0.482156,100000.0,,,
0.0100,-12.301,0.481902,100000.0,,,
0.1000,,,,25.1875,25.2500,24.9375
...
```

- `# param <name>=<val>`: 実行開始時に `RA` で取得した全 parm を辞書化し、以後 `R<addr>S<val>`
  送信のたびに更新した値。名前は `RA` の `addr:name:unit:val` から取得。
- F 行（位相/振幅/周波数）は温度列が空、T 行（温度3ch）は F 列が空のスパース形式。

---

## 4. 例

### 明示列挙
```
# 100kHz と 200kHz を各 3 秒（300点）計測
R3S100000
LABEL f100k
RUNN 300

R3S200000
LABEL f200k
RUNN 300
```

### スイープ
```
# fs を 0.5→2.5MHz まで 0.5MHz 刻み、各点 500 点
SWEEP fs 500000 2500000 500000
  R2S${fs}
  LABEL fs${fs}
  RUNN 500
ENDSWEEP
```

### DAC 電圧スイープ
```
# DAC(PA5) を 1.0→3.0V まで 0.5V 刻みで振り、各点 200 点
SWEEP v 1.0 3.0 0.5
  R10S${v}
  LABEL dac${v}
  RUNN 200
ENDSWEEP
```

### ネスト（TX アッテネータ × target 周波数）
```
SWEEP att 0 10 5
  ATTT${att}
  SWEEP tgt 90000 110000 10000
    R3S${tgt}
    LABEL a${att}_f${tgt}
    RUNN 200
  ENDSWEEP
ENDSWEEP
```
展開後は `01_a0_f90000.csv` … の順に自動保存される。
