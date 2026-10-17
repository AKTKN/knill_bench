# Factory wall-time 調査と局所 DEM 改修（2026-10-16）

最新の実装変更は **[検証省略オプション・準備 frame 最適化](factory_frame_optimization.md)**
を参照してください。以下の既存計測は、その最適化前の数値です。

追加調査：**[d=7 固定・T=1,2,4,8 の1 shotあたり時間とグラフ](factory_T_scaling_report.md)**。
構築後の sampling/decode と、初期化・保存込みの償却時間を分けて測定しています。
さらに **[T=3 固定・d=3,5,7,9,11 の距離 sweep と考察](factory_distance_scaling_report.md)**
で、準備深さ=d とした距離依存を比較しています。

## 改修後の結論

**旧方式の準備履歴を通す単一 fault 投影と Python の大量イベント統合は、
現在の factory True 経路から除去されました。** `create_codecapacity_dem: true`
は `module_local_stim_dem` を使います。d=3/5/7 の選択点はいずれも完了し、
旧 `merge_independent_events` / `_propagate_faults` は呼ばれていません。

これは **推論モデルの変更を伴う改修**です。準備・以前の stage の残留エラーを
prior から除外していますが、物理回路には noisy preparation と実際の残留
エラーが残ります。旧 prior と等価な高速化、誤り率改善、posterior の正確さを
主張するものではありません。Hex H5 のソース・回路・準備復号・因果的 frame
更新・終端 oracle 評価は変更せず、bench の
[専用アダプタ](../src/knill_bench/adapters/hex_factory.py) を追加しました。

DEM 解析は、理想符号化入力（全 CSS stabilizer sign=+1）、局所 noise/CNOT/
noisy destructive Z readout、局所 detector の順です。入力の Z_L(A) Z_L(B)
と出力の logical Z record parity を同じ Pauli-target OBSERVABLE_INCLUDE で
結び、ランダムな byproduct の値ではなく noise による反転を追います。
この理想入力・注釈は物理回路に追加しません。H5 の準備出口と CNOT の間には
独立した追加 noise channel がないため、仮想的な idle/boundary noise も追加
していません。最後の SE gate の noise は準備側として prior から除外します。
詳細は [factory guide](logical_zero_factory.md) に記載しています。

## 同条件の選択点での再測定

前回と同じ config snapshot / config hash、p=.003、r_0=r_plus=d、T=2、
master seed を使用。Conda knill_system、Stim 1.16.0 / PyMatching 2.4.0、
OMP/OpenBLAS/MKL 各1 thread。テストや他の本調査プロファイルとは重ねず、
単独 worker で順番に測定しました。各回、物理 sampler を同じ point seed で
新規に作成し、固定 batch の全 trajectory を生成・復号・一時 Parquet 保存。
実験の全9点 sweep、既存 run の resume、既存データの変更は行っていません。

| d | shots / batch | 旧 True | 新 True・初回 | 新 True・同一 process の2回目 |
| --- | --- | ---: | ---: | ---: |
| 3 | 7 / 7 | **10.480 秒**（今回の H5 再計測） | **0.875 秒** | 0.394 秒 |
| 5 | 7 / 7 | 240.028 秒で打切り（前回、未完了） | **2.507 秒** | 2.045 秒 |
| 7 | 7 / 7 | 60.023 秒で打切り（前回、未完了） | **10.830 秒** | 10.089 秒 |
| 3 | 100 / 100 | 9.651 秒（前回、完了） | **0.896 秒** | 未計測 |

時間は `_run_point` の wall time で、初期化・sampling・decode・書込み・
commit 検証を含みます。Conda 起動、import、親 provenance、spawn pool 起動は
含みません。今回の import は約0.93–1.15秒、provenance は約0.08–0.10秒でした。
各値は単回の診断で、統計的な性能推定や本番並列 throughput ではありません。
d5/d7 の旧値は完了時間ではないため、厳密な speedup 倍率に換算しません。

d3 の旧/新は物理 circuit hash と point seed が一致し、d3/5/7 とも前回の
Hamming 診断とも一致しました。物理サンプルの一致は別途回帰テストでも確認。
各新方式の初回/2回目は、保存した両 Parquet の SHA256 まで一致しました。
これは sampler を再利用した結果ではなく、同じ seed から新規に開始した結果です。

## 消えた処理とキャッシュの実測

| 処理（初回） | d3 | d5 | d7 |
| --- | ---: | ---: | ---: |
| 局所 prior 構築全体（encoder、DEM、gap graph 等） | 0.00819 秒 | 0.01855 秒 | 0.06158 秒 |
| 上記のうち Stim DEM 抽出 | 0.000156 秒 | 0.000278 秒 | 0.000605 秒 |
| 7 shots の物理 sampling | 0.000137 秒 | 0.000309 秒 | 0.000816 秒 |
| 7 shots の準備復号・gap・終端評価 | 0.01104 秒 | 0.01176 秒 | 0.03204 秒 |
| native bundle 完全検証 | 0.11924 秒 | 1.18425 秒 | 7.52218 秒 |

表の親処理・子処理は包含関係があり、加算しません。旧 d3 の再計測では
イベント統合2回に8.883秒を使っていました。新方式では旧投影・統合は0回で、
T=2 の二つの stage は同じ局所 DEM / matching graph を共有しました。
`--repeat 2` 全体の cache 統計は全距離で **miss=1、hit=3、保持=1**。
2回目の局所 prior / Stim DEM 構築回数は0です。

cache は完全な canonical module の回路文字列（noise 引数を含む）と code
supports をキーにする worker 内の16-entry LRU。解析用 encoder 文字列は
8-entry LRU。T、準備深さ、seed、shots、theta はこの prior を変えません。
距離・noise・局所回路が変われば別モデルです。sampler / RNG は共有しません。
並列 worker 間や別 process には cache を共有しません。

2回目の全体短縮を cache だけの効果とはしていません。例えば d3 の初回
書込み0.467秒には Arrow/Pandas の lazy import が含まれ、2回目は0.00116秒
でした。cache 効果は独立した生成回数・処理時間で確認しています。

冗長だった完全 bundle 検証は旧 True の **3回から1回** に削減しました。
省略したのは同じ fresh bundle の重複検証です。native builder の全 signed
flow / ledger / strict DEM 検証は毎回実施し、検証済み bundle を直ちに
H5 decoder の初期化へ渡します。単なる circuit hash による検証免除ではなく、
外部の未検証 bundle を受け入れる経路も設けていません。H5 の初期化 slot に
依存する小さな binding は明示し、実際の decode method は継承しています。

現在の d7 初回では **bundle.validate が7.522秒 / 全体10.830秒（約69%）**。
局所 prior は0.062秒なので、残る主な費用は native 回路/準備構築と完全検証
です。Hex 内の signed-flow 検証そのものは変更していません。以前の line
profile はこの検証内の `has_all_flows` を主因と特定していますが、今回の表は
関数境界の直接測定であり、その line 計測と時間を混ぜてはいません。

## 再現と成果物

リポジトリ直下で、出力名は未使用のものを指定します。

```bash
# 同一 process の初回と warm cache。d=3/5/7 を1点ずつ。
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
bash scripts/python.sh scripts/profile_factory.py \
  results/factory_local_dem_profile/config.snapshot.yaml \
  --distance 3 --p .003 --shots 7 --batch-size 7 --repeat 2 \
  --max-wall-seconds 120 --output results/factory_local_dem_profile/recheck_d3.json

# 固定 H5 の旧 True を明示的に再生する診断専用モード。
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
bash scripts/python.sh scripts/profile_factory.py \
  results/factory_local_dem_profile/config.snapshot.yaml \
  --distance 3 --p .003 --shots 7 --batch-size 7 --prior legacy-projected \
  --max-wall-seconds 60 --output results/factory_local_dem_profile/recheck_legacy_d3.json
```

[新旧 JSON と設定 snapshot](../results/factory_local_dem_profile/) と
[attempt ごとの処理別 CSV](../results/factory_local_dem_profile/summary.csv) を保存。
JSON は source hash、policy、seed、物理 circuit hash、局所 model hash、
cache 統計、初回/2回目の inclusive/exclusive wall/CPU 時間を持ちます。
`legacy-projected` は診断プロセス内だけで旧 compile 経路を呼び、設定や
依存ソースを変更しません。通常の run に旧方式へ戻る隠れた fallback はありません。

全 bench gate は255 tests passed。詳細な小規模物理検証、並列/再開検証と
read-only Hex gate は [TEST.md](../TEST.md) を参照してください。
旧方式の run へ新モデルで resume はできません。保存済み解析は旧 policy
のまま可能です。新旧 gap の尺度を同じ品質の校正値として混在させないでください。

---

## 以下は改修前の調査記録（保持）

主因は `create_codecapacity_dem: true` の事前モデル構築にある
**故障イベント統合の繰り返し検証**です。物理サンプリングや通常の
PyMatching 復号は、今回の長時間実行の主因ではありません。

対象は現在の `configs/logical_zero_factory_v2_example.yaml`。
d=3/5/7、p=.005/.003/.001、r_0=r_plus=d、T=2、100 shots/点、
batch_size=100、workers=6、projected prior=True。設定 SHA256 は
`c4d64bbb006cbcc5c7fd962c6e3b0d554250720ccc8a2e0d6d45f59a87a4e3de`。
環境は WSL2/Linux、Python 3.12.15、Stim 1.16.0、PyMatching 2.4.0、
論理 CPU 20、RAM 約 8.23 GB。Hex は H5 `4278d29` の clean な checkout です。

既存 run `20261016181159_c4d64bbb_factory_v2_example` は日本時間
18:11:59–18:34:53、約 1,373.85 秒後に KeyboardInterrupt で終了していました。
調査開始時、その実験プロセスは存在しませんでした。

| 距離 | 既存並列実験の点 wall time | 結果 |
| --- | ---: | --- |
| 3 | 15.70–15.79 秒 | 各 p で 100 shots 完了 |
| 5 | 302.99–309.19 秒 | 各 p で 100 shots 完了 |
| 7 | 約 1,358.03–1,358.10 秒で中断 | 完了マーカーの確定 shots は 0 |

点時間は初期化・処理・保存・コーディネータ待ちなどを含みます。並列点の時間を
足して全体 wall time とはできません。確定 shots=0 という記録だけでは、中断時の
内部処理位置までは判定できません。

追加測定は **p=.003 の点を単独プロセスで順番に実行**しました。
通常は 7 shots、物理 batch_size=7、BLAS/OMP/MKL 各 1 スレッドです。
実際の `_run_point` と unchanged Hex に runtime-only wrapper を付けて計測し、
一時的な物理出力は削除しました。ユーザー設定や既存データを変更せず、
新しい 9 点の全 sweep も実行していません。

| モード | d | 診断 shots | 点 wall time | 状態 |
| --- | ---: | ---: | ---: | --- |
| Projected=True | 3 | 7 | 9.738 秒 | 完了 |
| Projected=True | 3 | 100 | 9.651 秒 | 完了 |
| Projected=True | 5 | 7 | 240.028 秒で打切り | stage 1 のモデル統合中。物理サンプリング未到達 |
| Projected=True | 7 | 7 | 60.023 秒で打切り | stage 0 のモデル統合中。物理サンプリング未到達 |
| Hamming=False | 3 | 7 | 0.937 秒 | 完了 |
| Hamming=False | 5 | 7 | 3.738 秒 | 完了 |
| Hamming=False | 7 | 7 | 16.539 秒 | 完了 |

打切り値は完了時間の下限であり、完了所要時間の推定ではありません。
上表は単独 worker の時間で、Conda 起動・import・親 provenance・pool 起動を
含む CLI 全体時間ではありません。別途記録した import は約 0.95–1.12 秒、
provenance は約 0.08–0.11 秒。pool 起動単独は測っていません。
Hamming と Projected は推論・gap 単位が異なるため、同じ推論の高速化として
比較しないでください。完了した d3 比較で物理回路 hash と seed の一致を確認済みです。
この診断では誤り率を比較していません。

d3、True、100 shots の内訳です。親子の時間を含むため、行を加算しないでください。

| 処理 | wall time |
| --- | ---: |
| 点全体 | 9.651 秒 |
| geometry 読込み | 0.0556 秒 |
| 回路・準備モジュール構築（内部検証を含む） | 0.2725 秒 |
| stage 0 の projected model 構築 | 2.5129 秒 |
| stage 1 の projected model 構築 | 6.0220 秒 |
| 上記モデル構築中のイベント統合、計 2 回 | **8.0211 秒** |
| bundle 検証、計 3 回（他の構築処理と重複） | 0.3102 秒 |
| 100 shots の Stim サンプリング | **0.000242 秒** |
| 100 shots の準備復号・gap・終端評価 | **0.008989 秒** |
| Parquet open / write / commit・検証 | 0.0092 / 0.3979 / 0.0196 秒 |

7 shots と 100 shots でほぼ同じ時間なのは固定の初期化費用が支配的だからです。
物理 `batch_size` と、モデル構築内部の故障 batch（現在 1,024 mechanisms）は
別です。shots/batch_size の調整では、この統合処理を解消できません。
初回の Arrow/Pandas 関連 lazy import は write の時間に含まれます。

d5 の 240 秒計測では、`merge_independent_events` が **230.594 秒
（約 96.1%）**を占めました。その間の PyMatching.decode_batch 呼出し合計は
**0.0946 秒**で、投影用の制御故障に対する復号も含む値です。

原因は [codecapacity_dem.py](../external/Hex/src/hex_qec/decoders/codecapacity_dem.py)
の `merge_independent_events` と `ProjectedEvent.__post_init__` です。
`DEPOLARIZE2` などを個々の Pauli 故障へ展開し、完全な detector/logical
signature ごとに統合します。故障を 1 個追加するたび、蓄積済み ID tuple の
結合・並べ替え・集合化・全 ID の型検証を繰り返しています。

| d / stage | mechanism 数 | 最大の同一 signature グループ | 統合完了までの反復 ID 検証量の見積り |
| --- | ---: | ---: | ---: |
| 3 / 0 | 2,418 | 1,993 | 2,003,352 |
| 3 / 1 | 3,699 | 3,202 | 5,149,882 |
| 5 / 0 | 12,930 | 11,849 | 70,245,418 |
| 5 / 1 | 19,595 | 18,314 | 167,764,128 |
| 7 / 0 | 37,506 | 35,505 | 630,388,608 |

最後の列は実測したグループ数から計算した `sum(n_g*(n_g+1)//2)`。
打切り時点で全量を処理済みという意味ではありません。入力の初回検証等は別途です。
d3 の cProfile では、ID 型検証 generator の呼出しが約 717 万回ありました。
故障数が増えると、この Python 処理が二次的に増えます。

二次的なボトルネックは
[FactoryCircuitBundle.validate](../external/Hex/src/hex_qec/protocols/logical_zero_factory.py)
です。Hamming d7 の全 16.539 秒中、**13.412 秒**が 2 回の検証でした。
True の初期化経路は内部の既定 decoder 構築も含め 3 回検証しています。
別の行トレース計測では、検証 6.982 秒中 **6.383 秒（約 91.4%）**が
113 行目の `self.circuit[:stop].has_all_flows(...)` に集中しました。
この行の実行は 2 回の検証で計 **1,972 回**。prefix の measurement 数取得は
0.303 秒、厳密 DEM 検証は 0.169 秒でした。
行トレース時の点全体は 9.176 秒でしたが、別実行の診断値であり高速化の結果では
ありません。単回計測・計測器・マシン状態の差があるため、精密な速度比較には
使っていません。

NumPy の OpenBLAS は未指定時 20 スレッドでした。d3 True/7 shots は既定で
9.517 秒、1 スレッド指定で 9.738 秒。各 1 回の比較でスレッド制限による改善の
証拠はなく、今回の主因は BLAS ではありません。統合の CPU time は wall time に
近く、Python 計算に時間を使っています。workers を増やしても、1 点内のこの
逐次処理は分割されません。

改善の優先順位:

1. signature ごとに ID を蓄積し、最終イベント生成・全 ID 検証・ソートを
   グループごとに一度にする。確率の XOR 統合順序、全 mechanism ID、no-op
   イベント、例外条件を保ち、既存実装との一致を検証する。
2. bundle/flow 検証の重複と prefix の再構築を見直す。flow/ledger 等まで検証する
   条件を維持し、回路 hash だけで他の入力も同一とはみなさない。
3. 初期化中の stage/点の進捗を stderr に表示する。現在の通常 CLI は完了後に
   run path を出すため、`FACTORY_RUN=$(...)` は長時間無表示になります。

今回は計測・報告だけを行い、最適化を pinned Hex へ適用していません。
False は動作確認の比較に使えますが、True の推論を保つ最適化ではありません。

再計測は knill_system 環境・リポジトリ直下で行います。snapshot は今回の設定です。
出力は既存ファイルと重ならない名前を指定してください。

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python scripts/profile_factory.py results/factory_wall_profile/config.snapshot.yaml \
  --distance 3 --p .003 --shots 100 --batch-size 100 \
  --output results/factory_wall_profile/recheck_d3.json
```

`--prior hamming` は比較用、`--cprofile` は関数別統計、`--trace-validation` は
検証の行別計測です。`--max-wall-seconds` は点の上限（既定 180 秒）。打切り時は
partial timing と timeout status を保存し終了コード 2。既存 run は resume しません。

cProfile ありの d3 は点全体が約 40 秒になり、通常の約 9.5 秒に比べ大きな
計測負荷がありました。関数別集計だけで全 wall time を説明できないケースもあり、
主たる数値は `perf_counter` の直接計測です。JSON は inclusive と self time を
保存しています。単回のローカル診断であり、本番スループット・誤り率・信頼区間の
測定ではありません。d5/d7 True の完了時間は今回の制限内では測っていません。

[JSON・pstats・設定 snapshot](../results/factory_wall_profile/) と
[処理別 CSV](../results/factory_wall_profile/summary.csv) に生の結果があります。
[計測スクリプト](../scripts/profile_factory.py)、[検証記録](../TEST.md) も参照してください。
