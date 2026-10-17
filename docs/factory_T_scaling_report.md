# Factory：符号距離固定での T と1 shotあたり処理時間（2026-10-16）

以下は検証省略・frame 最適化前の測定です。最新の実装と比較値は
[追加レポート](factory_frame_optimization.md)を参照してください。

距離方向の追加調査は **[T=3 固定・d=3〜11 の計測と考察](factory_distance_scaling_report.md)**
を参照してください。

**d=7 固定で T=1→8 にすると、構築後の sampling＋decode は
0.193→0.893 ms/shot、初期化・保存込みの償却値は5.86→43.29 ms/shotでした。**
局所 DEM の再生成は各プロセスの初回1回だけです。現在の全体時間を支配するのは
物理回路の構築・完全検証で、T=8 では検証だけで約39秒、全体の約89%です。

## 結果とグラフ

次表は初回を除いた3試行の中央値。括弧内は最小–最大です。
全体時間の償却は **1,024 shots** に対する値なので、shot 数を変えれば変わります。

| T | sampling＋decode（ms/shot） | 初期化・保存込み（ms/shot） | 初回の全体（ms/shot、単回） |
| ---: | ---: | ---: | ---: |
| 1 | **0.193**（0.176–0.199） | **5.861**（5.488–5.903） | 6.724 |
| 2 | **0.289**（0.281–0.328） | **10.008**（9.854–10.045） | 10.878 |
| 4 | **0.510**（0.437–0.521） | **18.475**（18.177–18.754） | 19.461 |
| 8 | **0.893**（0.769–0.895） | **43.290**（43.182–46.472） | 47.775 |

![Tに対する1 shotあたり時間。左は構築後、右は初期化・保存込み。](../results/factory_T_scaling_d7/runtime_per_shot.png)

構築後の時間は、今回の中央値では1 stage追加あたり約0.10 ms/shot
（各区間で0.096–0.111 ms/shot）増えています。T=1→8 の倍率は約4.64倍です。
初期準備と終端評価が共通に含まれるため、T に厳密に比例するとは限りません。
4点・この距離/ノイズ/バッチ条件での観測であり、大きな T の計算量保証ではありません。

構築後の内訳は次のとおりで、約95%以上を復号・frame/gap/終端処理が占めます。
各列を独立に中央値にしているため、上表との和は必ずしも一致しません。

| T | 物理 sampling（ms/shot） | 復号・frame・gap・終端評価（ms/shot） |
| ---: | ---: | ---: |
| 1 | 0.0085 | 0.1841 |
| 2 | 0.0130 | 0.2756 |
| 4 | 0.0211 | 0.4892 |
| 8 | 0.0387 | 0.8527 |

## 初期化の増加と DEM cache

![Tに対する初期化・物理回路構築・完全検証の時間。包含関係があるため加算しない。](../results/factory_T_scaling_d7/setup_scaling.png)

| T | 物理 bundle 構築（秒、検証を含む） | 完全検証（秒） | 初回局所 prior 構築（秒） | そのうち Stim DEM 抽出（ms） |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 5.674 | 3.696 | 0.0640 | 0.605 |
| 2 | 9.767 | 7.029 | 0.0674 | 0.828 |
| 4 | 18.220 | 15.289 | 0.0600 | 0.532 |
| 8 | 43.193 | 39.270 | 0.0614 | 0.562 |

前2列はwarm 3試行の中央値、後2列は初回単回。親・子処理は包含関係があり、
加算できません。Hex の完全検証は各境界までの回路 prefix に対する signed
flow 確認などを行います。検証は T=1→8 で約10.6倍になり、全体の増加を
強く左右しています。関数境界の今回の測定だけから、検証内部の個々の処理の
時間や漸近的な次数までは特定しません。依存ソースの変更・検証の省略はしていません。

全16試行で以下を確認しました。

- 各 T の4試行全体で局所 Stim DEM 構築は **1回**。後続3試行は **0回**。
  最終 cache は miss=1、保持=1、hit は T=1/2/4/8 順に **3/7/15/31**。
- 全 stage・全 T で局所 prior の configuration hash が一致。
  T 間は別プロセスなので cache 自体を共有した測定ではありません。
- 旧 `_propagate_faults` と `merge_independent_events` は **0回**。
- 各試行で完全 bundle 検証1回、sampling/decode 各8回。
  各 T 内の4試行は両 Parquet の SHA256 まで一致し、保存時の検証も完了。
- simulator qubits は全 T で194。測定 record 数は順に770/1155/1925/3465。
  T とともに履歴が長くなり、二つの support の再利用は維持されています。

全体時間は T=1→8 で約7.39倍でした。特に少ない shot 数では、DEM cache の
有無より1点1回の物理回路構築・検証の償却が支配的です。今回の1,024 shotsでは
T=8 の sampling＋decode 全体は約0.915秒で、完全検証の約39.27秒より小さい値です。
shot 数を増やせば初期化費用はより多くの shot に分配されますが、その条件や
並列 worker 数を変えた throughput は今回測定していません。

## 測定条件と時間の定義

局所 DEM 改修後の factory を **d=7、p=.003、r_0=r_plus=7、
create_codecapacity_dem=true** に固定し、**T=1,2,4,8** を測定しました。
各 T は独立した固定値 YAML です。通常の simulation config に T sweep 軸を
追加していません。ユーザーの example YAML や既存 run は変更していません。

1試行は **1,024 shots、batch=128（8 batches）**。実 worker の `_run_point`
を使い、物理回路を構築して、全 T 段を含む trajectory を sampling・復号し、
error/gap の両 Parquet を一時保存・検証します。1 shot は T 段全体を通した
1 trajectory で、途中の gap による打切り・再試行はありません。

各 T を別プロセスで順番に実行し、同一プロセス内では初回＋3回を計測。
後続3回の **中央値と最小–最大** を主値とし、初回は別表示します。
各試行は新しい物理 bundle と同じ seed の sampler を作り直します。
後続試行は局所 DEM/gap cache と Python の lazy import が warm な状態ですが、
物理回路構築・完全検証は省略しません。通常の1点実行中は、構築済み sampler/
decoder を8 batchesで継続使用します。

比較する時間は次の2種類です。

- **構築後の処理 ms/shot** = `(sampling.physical_shots + decode.physical_shots) / 1024 × 1000`。
  準備復号、frame 更新、局所 gap、終端 oracle 評価を含み、初期化・保存を除きます。
- **全体の償却 ms/shot** = `point.total / 1024 × 1000`。
  回路・decoder・sampler 初期化、検証、sampling、復号、Parquet 保存・commit検証を含みます。

どちらも **batch 処理時間を shot 数で割った throughput の指標**です。
1 shotずつ API を呼んだときの latency ではありません。全体の値には
Conda/Python 起動、import、親 provenance、spawn pool 起動を含めません。
初期化を除いた指標には、最初の sampling/decode 呼出しの負担も含めています。

## 実行環境と解釈の範囲

Conda `knill_system`、Python 3.12.15、Stim 1.16.0、PyMatching 2.4.0、
Linux/WSL2、Intel Core i7-13700H。単独 worker、OMP/OpenBLAS/MKL は各1 thread
（OpenBLAS の実値も JSON に記録）。同時に別の本調査 simulation やテストは
実行していません。デスクトップの通常プロセスは動作しており、CPU affinity
や周波数を固定した専用 benchmark machine ではありません。

同一 T 内は master seed=12345 から導く同じ point seed・batch 分割で反復。
T は sampling identity に含まれるため、T 間で point seed は異なります。
反復は同一データの timing 再測定で、独立した物理サンプルによる統計評価では
ありません。誤差棒は3回の観測範囲であり、95% CI ではありません。
T は昇順に測定し、測定順・OS scheduling・熱状態の影響は除去していません。
関数境界の timing wrapper による小さな overhead を含みます。
`cProfile` と行単位 tracing は無効です。

この prior は **準備由来・以前の stage 由来の残留エラーを除外するモデル**
です。それらのエラーは実際の noisy preparation・物理 simulation・frame
処理には残ります。今回の測定は処理時間の評価で、prior の統計的正確さや
論理誤り率改善を主張しません。設計と旧方式の比較は
[改修・性能レポート](factory_performance_report.md)を参照してください。

## 再現と保存データ

測定時の正確な YAML、各試行の inclusive/exclusive wall/CPU 時間、
source hash、seed、circuit/model hash、cache 統計、出力 hash、RSS を
[results/factory_T_scaling_d7](../results/factory_T_scaling_d7/) に保存しました。
実際の shot Parquet は計測終了後に削除され、診断成果物は Git 対象外です。

```bash
# リポジトリ直下。各 T ごとの4試行全体に600秒の上限。
# 既存 T*.json の上書きを拒否するため、再測定時は新しい出力先を指定。
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
bash scripts/python.sh scripts/profile_factory.py \
  results/factory_T_scaling_d7/T8.yaml --distance 7 --p .003 \
  --shots 1024 --batch-size 128 --repeat 4 --max-wall-seconds 600 \
  --output results/factory_T_scaling_d7/T8_recheck.json

# 保存済みの T1/T2/T4/T8.json を検証・集計・描画。再 simulation はしない。
bash scripts/python.sh results/factory_T_scaling_d7/summarize.py
```

全4点の測定コマンドは [measure.sh](../results/factory_T_scaling_d7/measure.sh)、
集計コードは [summarize.py](../results/factory_T_scaling_d7/summarize.py)。
[attempts.csv](../results/factory_T_scaling_d7/attempts.csv) は16試行の値、
[summary.json](../results/factory_T_scaling_d7/summary.json) は初回値とwarm統計です。
グラフは PNG に加え、同じディレクトリに SVG/PDF でも保存しています。
