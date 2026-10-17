# Factory：T=3 固定での符号距離と処理時間（2026-10-16〜17）

以下は検証省略・frame 最適化前の測定です。最新の実装と d7 での比較値は
[追加レポート](factory_frame_optimization.md)を参照してください。

**d=3→11 で、構築後の sampling＋decode は0.130→1.388 ms/shot、
初期化・保存込みの償却値は0.608→145.194 ms/shotでした。**
前者は約10.7倍、後者は約239倍です。d=11 の完全検証は約127秒、全体の
約86%を占めます。局所 DEM は各距離の初回1回だけ生成され、旧 fault 投影・
イベント統合は全距離で呼ばれませんでした。全20試行が打切りなしで完了しました。

## 測定結果とグラフ

T=3、p=.003、r_0=r_plus=d、True local prior。1試行は1,024 shots、batch=128。
主値は初回を除く3試行の中央値、括弧内は最小–最大です。初回は別列に示します。

| d | sampling＋decode（ms/shot） | 初期化・保存込み（ms/shot） | 初回の全体（ms/shot、単回） |
| ---: | ---: | ---: | ---: |
| 3 | **0.130**（0.119–0.134） | **0.608**（0.603–0.618） | 1.134 |
| 5 | **0.213**（0.191–0.230） | **2.968**（2.950–3.332） | 3.419 |
| 7 | **0.396**（0.156–0.429） | **14.186**（12.639–14.744） | 14.440 |
| 9 | **0.757**（0.732–0.797） | **48.493**（48.367–49.239） | 56.902 |
| 11 | **1.388**（1.385–1.444） | **145.194**（144.328–145.585） | 181.801 |

![距離に対する1 shotあたり時間。左は構築後、右は初期化・保存込みで縦軸対数。](../results/factory_distance_scaling_T3/runtime_per_shot.png)

**d=7 のwarm 3試行は0.429/0.396/0.156 ms/shotと、ばらつきが大きい**点に
注意してください。最後の値を除外せず、中央値と全範囲をそのまま示しています。
保存データのハッシュは一致し、CPU timeも同様に短くなっていますが、この計測
だけでは原因を特定できません。cache の効果や物理的な性能改善に帰属させません。
距離ごとの中央値は増加していますが、この5点から精密なべき指数や漸近的な
計算量を推定することは避けます。

## ボトルネックの内訳と考察

![距離に対する初期化・bundle構築・完全検証。縦軸対数で、包含関係のある時間を表示。](../results/factory_distance_scaling_T3/setup_scaling.png)

| d | 物理 bundle 構築（秒、検証込み） | 完全検証（秒） | 検証/全体 | 初回局所 prior 全体（秒） | そのうち Stim DEM 抽出（ms） |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 0.407 | 0.186 | 30.1% | 0.0130 | 0.117 |
| 5 | 2.724 | 1.899 | 61.9% | 0.0196 | 0.284 |
| 7 | 13.962 | 11.020 | 76.0% | 0.0610 | 0.970 |
| 9 | 48.626 | 40.731 | 82.2% | 0.2236 | 1.226 |
| 11 | 146.790 | 127.267 | 85.6% | 0.3837 | 1.500 |

物理構築・検証・割合は各warm試行の中央値、局所 prior は初回単回です。
親子の包含時間は加算しません。割合も試行ごとに求めた中央値です。

**短い診断 run の主因は、局所 prior 生成から物理回路の完全検証へ移っています。**
d=3→11 で完全検証は約684倍です。d=11 でも初回局所 prior 全体は約0.384秒、
Stim DEM 抽出は約0.00150秒なので、これをさらに最適化しても現在の初期化費用
の大部分は残ります。Hex の `validate()` は各境界までの回路 prefix に対して
signed-flow 確認などを実行します。今回の関数境界計測は検証全体の費用を示す
もので、内部処理の時間配分や次数を直接測定したものではありません。

構築後については、物理 sampling より準備復号・frame 解決の費用が大きくなります。

| d | sampling（ms/shot） | 復号全体（ms/shot） | うち準備復号・frame解決（ms/shot） | うち局所 homology gap（ms/shot） |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 0.0023 | 0.1280 | 0.0814 | 0.0310 |
| 5 | 0.0070 | 0.2059 | 0.1494 | 0.0383 |
| 7 | 0.0185 | 0.3776 | 0.3035 | 0.0505 |
| 9 | 0.0362 | 0.7209 | 0.5975 | 0.0866 |
| 11 | 0.0683 | 1.3210 | 1.1459 | 0.1314 |

各列は独立に求めた中央値です。復号全体には右2列のほか stage frame 更新、
終端評価、入力確認なども含みます。d=11 では準備復号・frame 解決が復号時間の
約86%です。これは `PreparationFramePlan.resolve` 全体の計測であり、matching
だけでなく measurement→detector 変換、sparse correction map、sign確認等を
含みます。大量 shots の継続 throughput を改善する場合はこちらの内訳や
batch size の効果が検討対象になりますが、今回それらの変更・追加比較はしていません。

局所 prior の cache と計測の整合性は以下を確認しました。

- 各距離の4試行全体で局所 Stim DEM は **1回**、後続3試行での再生成は **0回**。
  最終 cache は全距離で **miss=1、hit=11、保持=1**。
- 同距離の3 stagesで prior configuration hash が一致し、5距離では5種類に分かれます。
  距離ごとに別プロセスなので、距離間の cache 共有はしていません。
- 旧 `_propagate_faults` / `merge_independent_events` は **0回**。
- 各試行で完全検証1回、sampling/decode各8回。各距離内の4試行は保存した
  error/gap の両 Parquet の SHA256 が一致。全20試行の完了・cache・回路規模を
  保存済み JSON の assertion で検証しました。

## 距離比較で変わる回路規模

T=3 では、初期 zero 準備1回と plus 準備3回、消費 block の destructive
readout 3回と終端 oracle 1回があります。各 support は data d²個と check
ancilla d²−1個を持ち、二つの support を再利用します。準備深さ=d のため、
測定 record 数は `4 × [d(d²−1) + d²]`、simulator qubits は `4d²−2` です。

| d | 各準備の SE rounds | simulator qubits | 測定 records / shot |
| ---: | ---: | ---: | ---: |
| 3 | 3 | 34 | 132 |
| 5 | 5 | 98 | 580 |
| 7 | 7 | 194 | 1,540 |
| 9 | 9 | 322 | 3,204 |
| 11 | 11 | 482 | 5,764 |

準備履歴のサイズはこの規則では約 d³ に増えます。ただし record 数の増加と
sampling・matching・完全検証の計算時間は同じ量ではなく、同じ次数になると
は限りません。小さい距離では batch 呼出し等の固定費も相対的に大きくなります。

同じ物理エラー率 p でも、準備回路が長くなると1 shot中の noise channel 数は
増えます。したがって matching の時間には、graph サイズに加えて実際に生じる
syndrome の量も影響し得ます。この測定を「p と総 fault 数をともに固定した
decoder サイズだけの比較」とは解釈しません。

## 初期化費用と継続処理を区別する理由

通常 runner は1点につき1回だけ compile し、全 batchesで sampler/decoderを
継続利用します。この計測の反復で bundle を再構築するのは、点全体の初期化
費用とそのばらつきを測るためです。各 batchや各 shotで完全検証・DEM生成を
繰り返しているわけではありません。

全体時間を1,024で割った値が大きくても、それが大量 shots の継続処理速度を
直接表すとは限りません。概念的には
`全体時間/shot ≈ 初期化費用/N + 継続処理/shot + 保存費用/shot` です。
N を増やせば初期化の償却は小さくなりますが、batch sizeや
並列 worker 数を変えた throughput は今回測定していません。回路が異なる
d/p/T/準備深さの点へ、完全検証済みという結果を無条件に流用することもできません。

初期化をさらに改善するなら、残る費用を占める箇所の検証方法や安全な再利用の
範囲を検討すべきです。単に完全検証を消すことや、準備ノイズを物理回路から
除くことは、この性能比較の対処として行っていません。

DEM cache の回数は **teleportation 用の局所 prior 抽出**を指します。
native preparation が使う DEM や、`bundle.validate()` 内の構造確認用
`operational_circuit.detector_error_model()` を含む全 Stim 呼出しの総数では
ありません。物理 bundle の完全検証はこの構造確認も含めて維持しています。

## 条件と測定方法

局所 DEM 改修後の factory を **T=3、p=.003、create_codecapacity_dem=true**
に固定し、**d=3,5,7,9,11** を測定しました。準備深さは前回と同じ規則
**r_0=r_plus=d**。したがって距離だけでなく準備の時間方向の長さも増やす
比較です。準備深さを固定した純粋な空間サイズ比較ではありません。

1試行は **1,024 shots、batch=128（8 batches）**。実 worker の `_run_point`
による回路構築、sampling、準備復号、frame 更新、gap、終端評価、両 Parquet
の一時保存・commit 検証まで計測しました。1 shot は3段全体を通した trajectory
です。途中の gap による打切り・再試行・trajectory 選別はありません。

距離ごとに別プロセスを使い、昇順に実行しました。同一プロセスで初回＋3回を
測定し、初回を別表示、後続3回の **中央値と最小–最大** を主値とします。
各試行は物理 bundle と sampler を作り直し、同じ point seed から開始。
後続3回は局所 DEM/gap cache と lazy import が warm ですが、物理回路の構築・
完全検証は毎回行います。通常の1点実行中は構築済み sampler/decoder を全8
batchesで継続使用します。距離ごとの4試行全体に2,400秒の上限を設定しました。

- **構築後の処理 ms/shot**：`(sampling.physical_shots + decode.physical_shots) / 1024 × 1000`。
  準備復号、frame 更新、局所 gap、終端 oracle 評価を含み、初期化・保存を除きます。
- **全体の償却 ms/shot**：`point.total / 1024 × 1000`。
  回路・decoder・sampler 初期化、完全検証、sampling、復号、保存・commit検証を含みます。

いずれも batch 時間を shot 数で割った throughput 指標で、1 shotずつ API
を呼び出す latency ではありません。Conda/Python 起動、import、親 provenance、
spawn pool 起動は `point.total` に含みません。初回とwarmの差を DEM cache
だけの効果とは解釈しません。初回の Parquet 書込みには lazy import も含まれます。

環境は前回と同じ Conda knill_system、Python 3.12.15、Stim 1.16.0、
PyMatching 2.4.0、Linux/WSL2、Intel Core i7-13700H。単独 worker、
OMP/OpenBLAS/MKL 各1 thread（OpenBLAS 実値も保存）。本調査の別 simulation
やテストとは同時実行せず、ユーザーの他プロセスは変更・停止していません。
CPU affinity/周波数は固定していません。

master seed=12345。距離は sampling identity に含まれるため距離間の point
seed は異なり、同距離の反復は同じデータの timing 再測定です。誤差棒は3回の
観測範囲で、95% CI ではありません。測定順・OS scheduling・熱状態の影響は
除去していません。関数境界の timing wrapper の overhead を含み、cProfile
と行単位 tracing は無効です。

## 科学モデルの範囲

この True prior は **準備由来・以前の stage 由来の残留エラーを prior から
除外するモデル**です。物理回路の noisy preparation と残留エラー、native
frame 処理は維持しています。大きな距離で処理が完了することは、prior の
厳密さ・論理誤り率改善・しきい値を実証するものではありません。
今回の反復は性能測定用であり、誤り率の科学的評価には使用しません。
Hex H5 の依存ソース、decoder policy、検証内容は変更していません。

## 再現と成果物

[設定 snapshot](../results/factory_distance_scaling_T3/config.snapshot.yaml) は
この診断専用です。ユーザーの example YAML、既存 run は変更していません。
通常 runner で config 全体を起動する代わりに、以下の計測器で1距離ずつ実行します。

```bash
# リポジトリ直下。既存 JSON を上書きしないため再測定は新しい出力先を指定。
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
bash scripts/python.sh scripts/profile_factory.py \
  results/factory_distance_scaling_T3/config.snapshot.yaml --distance 11 --p .003 \
  --shots 1024 --batch-size 128 --repeat 4 --max-wall-seconds 2400 \
  --output results/factory_distance_scaling_T3/d11_recheck.json

# 保存された d3/d5/d7/d9/d11.json の検証・集計・描画のみ。
bash scripts/python.sh results/factory_distance_scaling_T3/summarize.py
```

[全距離の測定コマンド](../results/factory_distance_scaling_T3/measure.sh)、
[集計・描画コード](../results/factory_distance_scaling_T3/summarize.py)、
[試行ごとの CSV](../results/factory_distance_scaling_T3/attempts.csv)、
[中央値・範囲の JSON](../results/factory_distance_scaling_T3/summary.json) を保存。
各距離の raw JSON には inclusive/exclusive wall/CPU 時間、source hash、
seed、circuit/prior configuration hash、cache 統計、出力 hash、RSS を記録します。
実際の shot Parquet は計測後に削除され、診断成果物は ignored results/ に置きます。
グラフは PNG/SVG/PDF を保存しました。

関連資料：[d=7 固定の T 比較](factory_T_scaling_report.md)、
[局所 DEM 改修と旧方式の性能調査](factory_performance_report.md)。
