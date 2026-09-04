# API比較ツール

DryNowで使用する天気APIを選定するための比較ツールです。

複数の天気APIから同じ地点・同じ時刻の気象データを取得し、
気象庁のAMeDAS観測値と比較することで、
DryNowに適したAPIを検証することを目的としています。

## 比較予定のAPI

- OpenWeather
- Open-Meteo
- Visual Crossing
- Tomorrow.io

比較地点は、熊谷・東京・静岡・大阪・松山の5地点です。

主に以下の項目を比較する予定です。

- 気温
- 湿度
- 風速
- 降水
- データの取得成功率
- データの鮮度

## 現在の実装・運用状況

Phase 1-Bとして、以下の収集基盤を実装・運用しています。

- 比較地点の定義
- SQLiteデータベースの初期化
- `.env` からのAPIキー読み込み
- APIごとの収集処理を分離するための構成
- 取得データ・ログをGit管理から除外する設定
- OpenWeatherとOpen-Meteoの現在値取得
- 5都市のprimary地点を対象にしたSQLite保存
- 1回につき5都市 × 5ソース = 25レコードの保存
- Windows Task Schedulerによる毎時05分・35分の自動実行
- API collector、AMeDAS、`target_time`丸めの単体テスト（49 tests / OK）

実API取得とSQLite保存を確認済みです。また、16:35のTask Scheduler自動実行で、
全レコードが`target_time=16:30`となる25レコードの保存を確認しています。

AMeDAS収集は実装済みです。Visual CrossingとTomorrow.ioは未実装です。

APIから取得したデータは、比較用に整形した値だけでなく、
元のレスポンスも保存できる構成にしています。

これにより、後から取得項目や変換処理を確認したり、
比較方法を変更した場合でも再検証できるようにします。

## 現在値の手動収集

プロジェクトルートまたは`tools/api_comparison`の`.env`へ
`OPENWEATHER_API_KEY`を設定し、次のコマンドを実行します。

```powershell
python tools/api_comparison/collect_current.py
```

## Windows Task Schedulerによる自動収集

`run_current_collection.ps1`は、スクリプト自身の位置を基準にプロジェクトと
`collect_current.py`を解決します。Task Schedulerの作業ディレクトリに依存せず、
実行ごとの標準出力と標準エラーを`logs/`へ分けて保存します。

登録前にPythonの実体を確認します。

```powershell
(Get-Command python).Source
```

実行用スクリプトだけを手動確認する例です。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File tools/api_comparison/run_current_collection.ps1 `
  -PythonPath "C:\Path\To\python.exe"
```

Task Schedulerへ毎時5分・35分に登録する例です。初回を次の5分または35分に設定し、
以後30分間隔で実行します。登録スクリプトを実行すると、同名タスクは更新されます。
必要な内容を確認してから実行してください。

登録前に、`-ValidateOnly`を付けて登録直前までの設定を検証できます。この場合、
Task Schedulerへの登録・更新は行いません。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File tools/api_comparison/register_current_collection_task.ps1 `
  -PythonPath "C:\Path\To\python.exe" `
  -Minute 5 `
  -ValidateOnly
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File tools/api_comparison/register_current_collection_task.ps1 `
  -PythonPath "C:\Path\To\python.exe" `
  -Minute 5
```

既定ではログオン中のユーザーとして動作し、スリープ解除は行いません。
PCが停止していた場合は収集できません。スリープ中または一時的に実行できなかった場合は、
復帰後に可能な範囲で実行します。

スリープ中のPCを収集時刻に復帰させる場合は、検証時と登録時の両方に
`-WakeToRun`を追加します。未指定の場合はOFFです。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File tools/api_comparison/register_current_collection_task.ps1 `
  -PythonPath "C:\Path\To\python.exe" `
  -Minute 5 `
  -WakeToRun `
  -ValidateOnly
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File tools/api_comparison/register_current_collection_task.ps1 `
  -PythonPath "C:\Path\To\python.exe" `
  -Minute 5 `
  -WakeToRun
```

WakeToRunを有効にしても、PCの電源が完全に切れている場合は実行できません。
また、Windowsの電源プラン、スリープ解除タイマー、端末のファームウェア設定によっては
復帰できない場合があります。

`collect_current.py`の`target_time`はJSTの30分境界へ切り捨てます。そのため、
17:05の収集は17:00、17:35の収集は17:30として全都市・全APIで共有されます。

同じ時刻枠で再実行すると、`source + city + point_role + target_time`の一意制約により
既存レコードの上書きは行われず、対象レコードの保存は失敗としてログへ残ります。
タスクの前回実行が継続中の場合、新しい実行は開始しません。

## 今後

現在の自動収集を継続しながら、Visual CrossingとTomorrow.ioの現在値取得、
同時刻データの比較処理を順番に実装します。
