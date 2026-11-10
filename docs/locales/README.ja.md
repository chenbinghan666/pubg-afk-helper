# PUBG AFK Helper

[简体中文](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/README.md) · [English](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.en.md) · **日本語** · [Deutsch](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.es.md) · [Português](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.pt.md)

OpenCV で PUBG の画面を認識し、認識状況を表示して、Windows 上で設定可能な処理を実行します。認識専用のプレビューとオフライン回帰テストを備えています。

Python · OpenCV · Windows

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

**OpenCV画面認識、Windowsシミュレーション入力、ミニマップ変更検出**に基づくPUBG自動処理ツール。
ロビーとチェックアウト インターフェイスを識別し、設定可能なマッチング、ジャンプ、移動、ピックアップ、エスケープのプロセスを実行し、オーバーヘッド ステータス ウィンドウに現在のステップを表示します。

## 機能

- **インターフェイスは** を認識します: ロビー、ロビーに戻る、終了確認、キャラクター決済および報酬ページ。継続的な認識確認と繰り返し操作の制限。
- **相対位置**: 画面サイズに応じてテンプレートと座標を拡大縮小し、一部のワイドスクリーン レイアウトの端揃え検索をサポートします。
- **ゲームプロセス**: ホールが消えた後にタイムジャンプし、一度右に曲がり、W+左 Shift で前進を続け、下を向いた後 F をクリックして拾います。
- **ミニマップの立ち往生防止壁**: 右下隅のマップの地形のみを比較し、中央の文字マークをブロックします。最初に Shift+C を試してから、検出結果に応じて元に戻り、左右に移動します。
- **トップステータスウィンドウ**: カウントダウン、アクション、一時停止理由、ミニマップ検出インジケーターを表示します。マウスの侵入によってゲームの焦点が奪われることはありません。
- **構成可能でテスト可能な**: JSON 構成、テンプレート記録ツール、オフライン回帰テスト、Windows CI。

このプログラムはスクリーンショットと通常のオペレーティング システム入力を通じて動作し、ゲーム メモリを読み取ったり、ゲーム プロセスを挿入したりしません。
このプロジェクトはまだ初期段階にあります。固定タイミングとミニマップの変更はおおよそのものであり、航空機、実際の着陸、ピックアップの成功、報酬の受け取りを確認することはできません。
ご利用前にゲームルールやアカウントのリスク等をご自身でご確認ください。このプロジェクトは不正行為防止バイパス機能を提供しません。

## クイックスタート

**Windows 10/11、Python 3.11+**が必要です。ゲームはメイン モニターのボーダーレス ウィンドウ モードを使用します。

1. [の最新リリース](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) の `PUBG-helper.zip` をダウンロードするか、このリポジトリのクローンを作成します。
2. Python をインストールし、**にチェックを入れます。Python を PATH** に追加します。
3. `install.cmd` をダブルクリックし、依存関係のインストールが完了するまで待ちます。
4. 初めて使用する場合はダブルクリックしてください **`preview.cmd`**、ゲームに戻り、認識ログを確認します。このモードでは入力は送信されません。
5. 正しく認識されていることを確認したら、プレビューを閉じてダブルクリックします。 **`launch.cmd`** 自動アクションを有効にします。

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # 認識するだけ
.\.venv\Scripts\python.exe bot.py --live      # 入力を有効にする
```

Git クローンはデフォルトで `config.example.json` を読み取ります。カスタマイズする前にそれを `config.json` にコピーすると、ローカル構成は Git に送信されません。

```powershell
Copy-Item config.example.json config.json
```

ウェアハウスには、繁体字中国語インターフェイス用のボタン トリミング テンプレートのセットが付属しています。言語、ゲームのバージョン、HUD のスケールやレイアウトが異なる場合、テンプレートを再記録する必要があり、すべてのコンピューターに直接適用できるかどうかは保証できません。

## デフォルトのプロセス

```text
ホールを特定する → F がマッチングを開始します
  → ロビーの失踪を3回連続で検知 → 120秒待ちます
  → F スカイダイビングに挑戦してみよう → 一度右折してください → W + 左シフト
  → スカイダイビングの30秒後: 地上を見下ろします → 0.5秒ごとにFをタップ
  → ミニマップは約 1 秒間安定します。必要に応じて、横切ったり、戻ったり、横断したりしてください。
  → 死亡/決済：ボタンを放す → ロビーに戻る → 次のラウンド
```

ロビーが消えるのはローディング画面の場合もありますが、これは部屋に入ったことを証明するものではありません。時間はすべて調整可能です。
右折のデフォルトの変位 **4050** と上向きの変位 **5000** は単なる参考パラメータです。実際の角度はゲームの感度とマウスの設定によって異なります。
スプリントと Shift+C のジャンプは、ゲーム キーとホールド/トグル設定と一致している必要があります。

## 操作キー

| ボタン | 機能 |
| --- | --- |
| **F8** | 一時停止のみ。スクリプトが保持しているキーを解放します。 |
| **F7** | ただ続けてください |
| **F9** | 終了してキーを放します |
| **Ctrl+C** | 端末でプログラムを停止する |

ゲームから切り替えると入力は一時停止され、再び切り替えた後は自動的に再開されます。開始されたカウントダウンは実際の経過時間に基づいて計算されます。
マウスコーナーポーズは、トリガー保護の自動見落としを避けるためにデフォルトでオフになっており、`mouse_corner_pause` を使用して個別に有効にすることができます。
プロセスが強制終了している場合やコンピュータの電源がオフの場合、キーストロークのクリーニングは実行できません。

## 設定とトラブルシューティング

完全なパラメータ、テンプレート記録コマンド、ミニマップ相対エリア、感度校正方法については、[設定および使用マニュアル](../../docs/CONFIGURATION.md) を参照してください。

| 質問 | 優先順位のチェック |
| --- | --- |
| 認識もアクションもなし | 上部のウィンドウに一時停止が表示されているかどうか、ゲームがフォアグラウンドにあるかどうか、ウィンドウのタイトルに `PUBG` が含まれているかどうか |
| 開始または決済の認識に失敗しました | インターフェイス言語、解像度、HUD スケールがテンプレートと一致するかどうか |
| スカイダイビングが早すぎる/遅すぎる | `movement.jump_delay_seconds` |
| 立ち上がるのが早すぎる/見下ろす方向が間違っている | `pickup_delay_after_jump_seconds`、`look_down_pixels`、Y軸反転設定 |
| 右折角度が間違っている | 実際の回転角度に従って校正します `turn_right_pixels` |
| スプリントやジャンプは効果なし | キーバインド、ホールドモード、実行権限、およびゲームがアナログ入力を受け入れるかどうか |
| アンチジャミングウォールの誤判定/欠落 | ミニマップエリア、ズーム、回転設定、オーバーヘッドウィンドウの安定したスケールインジケーター |

ログはローカル `bot.log` に書き込まれます。フィードバックを送信する前に、アカウント、チャット、プライベート パス、その他の情報を削除してください。

## 開発する

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

このテストでは、ゲームを操作せずにキーボードとマウスの入力をシミュレートします。公開バージョンでは、テスト用の合成画像が自動的に生成されます。ローカルに存在する場合
`reference_screens/`、追加の回帰のために、対応する個人的な参照スクリーンショットを使用できます。このディレクトリは、ウェアハウスまたは配布パッケージには含まれていません。
CI は、Python 3.11 および 3.12 を使用して Windows 上でテストを実行します。
オフライン テストは、さまざまなハードウェア、ゲーム バージョン、感度での実際のゲーム検証に代わることはできません。

メイン ファイル: `bot.py` はステート マシン、認識および入力の実装、`status_overlay.py` はステータス ウィンドウ、
`prepare_templates.py` は 5 つのインターフェイスのテンプレート生成ツールであり、`package.py` は配布パッケージ構築スクリプトです。

[Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues) を通じて再現可能な問題を報告することを歓迎します。
変更を送信する前に、[の投稿手順](../../CONTRIBUTING.md) をお読みください。バージョン レコードについては、[CHANGELOG](../../CHANGELOG.md) を参照してください。

## ライセンス

オリジナルのコードとドキュメントは、[MIT License](../../LICENSE) に基づいてライセンスされています。ゲーム インターフェイスのカット、名前、商標はそれぞれの権利所有者に帰属します。詳細については、[サードパーティの声明](../../NOTICE.md) を参照してください。このプロジェクトはKRAFTON / PUBGとの提携や公式パートナーシップはありません。
