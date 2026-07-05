# CP-700M コントローラ GUI

COMS社の3軸ポジションコントローラ **CP-700M** を PC から遠隔操作する PySide6 GUI。
CP-700M の **PC ダイレクト通信制御モード**（マニュアル §5.2）を使い、付属の CP-700Tool の
「リモート操作」画面（§5.3）相当の操作を提供する。

- 接続 / 各軸ジョグ・相対移動・絶対移動・原点復帰・座標0クリア・励磁・停止
- 現在位置（mm＋pulse）・リミット・インターロック状態のリアルタイム表示
- 直接コマンド入力コンソール
- シミュレーション（モック）モード：実機が無くても UI 動作を確認できる

初版は単体アプリ。将来 `auto-stage-control` GUI のサブウィンドウとして埋め込めるよう、
UI 本体は `Cp700ControlPanel(QWidget)` に分離してある。

## セットアップ

```powershell
cd gui
pip install -r requirements.txt
```

### 実機を接続する場合（初回のみ）

CP-700M を USB 接続すると、専用USBドライバ導入済みの PC では
**"CP-700 Communications Port (COM*)"** という仮想COMポートとして認識される。
COM が現れない場合は、マニュアル §4.3 の手順で CP-700Tool 付属 `drivers` フォルダの
ドライバを導入すること。前面 `Stop` スイッチと背面 `Interlock` コネクタが有効
（未押下・結線済み）でないとステージは動作しない（§4.4）。

## 起動

```powershell
cd gui
python main.py
```

- 「シミュレーション」にチェックしたまま「接続」すると、モックで動作確認できる。
- 実機は「シミュレーション」を外し、ポートを選択して「接続」。接続直後に `V:` を自動送信し、
  バージョン応答が返れば疎通成功。「接続テスト」ボタンでいつでも再確認できる。

## UI（レイアウト）の編集

レイアウトは `gui/ui/main_window.ui`。Qt Designer で編集する：

```powershell
cd gui
pyside6-designer ui/main_window.ui
```

`main.py` 起動時に `regen_ui.ensure_ui()` が `.ui` の更新を検出して
`pyside6-uic` で `ui_main_window.py` を自動再生成する。手動再生成は：

```powershell
python regen_ui.py
```

※ 3軸の操作グリッドだけは保守性のためコード（`ui/app.py`）で `stageContainer` に
動的生成している。通信バー・状態表示・直接コマンド・ログの枠は Designer で編集可能。

## 軸設定（単位換算）

`gui/cp700_config.json` に軸ごとの `lead_mm`（ネジリード）と `divide`（分割数）を保持し、
`mm_per_pulse = lead_mm / (500 × divide)`（マニュアル §6.1.A）で mm↔pulse を換算する。
接続ステージに合わせて値を調整すること（初期値 lead=2mm / divide=20）。

## 構成

```
gui/
  main.py            エントリ（regen_ui → GUI 起動）
  regen_ui.py        .ui → pyside6-uic 自動生成
  comm/transport.py  Cp700Transport / MockTransport / SerialTransport(CRLF)
  core/commands.py   CP-700M ASCII コマンドビルダー
  core/controller.py Cp700Controller（Q: 応答パース含む）
  core/config.py     AxisConfig / Cp700Config（mm_per_pulse）
  ui/main_window.ui  Designer 編集の UI 定義
  ui/app.py          Cp700ControlPanel / Cp700MainWindow
docs/
  command_reference.md  GUI 操作 → CP-700M コマンド対応表
```

## 対象外（次フェーズ）

- `auto-stage-control` への埋め込み（`Cp700ControlPanel` を import）
- パラメータ編集（`F:M<no>` で84パラメータ読み書き）
- プログラム運転モード（CSV 編集・書込・実行）
- COMM RES=ON 化 / デイジーチェーン対応
