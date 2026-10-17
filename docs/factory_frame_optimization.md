# Factory の検証省略・準備 frame 最適化（2026-10-17）

factory schema-v2 YAML に以下を指定できます。

```yaml
skip_circuit_validation: true
```

**true は完全検証を省略、false／省略時は完全検証あり**です。
`create_codecapacity_dem` の true/false 両方に適用します。Fig.4(d) と v1
の数値処理、Hex H5 のソースには変更していません。実装と API の詳細は
[factory guide](logical_zero_factory.md) を参照してください。

## 何を省略するか

構築時の `FactoryCircuitBundle.validate()` を省略します。この関数が行う
measurement ledger、因果境界／oracle 分離、各 prefix の signed flow、
operational circuit の厳密 DEM 検証が対象です。省略しない場合は両 prior
モードとも一度だけ実行します。構築自体の整合性チェック、回路 hash、局所
DEM の構造チェック、復号後の sign 整合性、gap／保存データのチェックは残ります。

このオプションは検証済み回路の保存・読み込みではありません。物理回路は毎回
native builder で構築し、sampler は点ごとの seed で新しく作ります。依存の H5
には検証引数がないため、元の builder 関数を private な globals 辞書で実行し、
構築中だけ bundle の validate を no-op とする型を渡します。返却時は通常の
native bundle に戻すので、明示的な `bundle.validate()` は引き続き動作します。
依存ソースや共有 module globals の書き換えはありません。

## frame の計算変更

準備 module の二つの circuit-level matching と二つの code-capacity
matching はそのままです。pure error の選び方、重み、tie-breaking、論理
class の規約を変えていません。準備部分の測定記録も従来どおり復号に使います。

変更したのは補正決定後の線形演算です。c を circuit-level 補正、A をその
補正から **最終** stabilizer 測定への写像、B を出口 frame への写像とすると、
必要なのは `s_final = raw_final XOR cA` と `frame = cB XOR repair(s_final)`
です。全時刻の corrected history を作らず、A/B の必要な列を事前にまとめます。

- X/Z sector を出口 X frame・Z frame・最終 check 値の同じ packed 出力へ写像。
- 入力8 bit ごとの XOR lookup table を準備 template ごとに一度構築し、batch
  では bit-packed XOR で評価。出力を合わせてから unpack します。
- 最終 sign の capacity repair は出口 frame に直接 XOR。大きな correction
  vector の連結、batch ごとの CSR 構築と corrected history の dense 化を除去。
- A/B 支持・準備基底・深さごとの native template に対応する写像を再利用。
  1回の gather は入力32 byte 分に制限します。

lookup table 分の常駐メモリは増えます。1写像あたり
`256 × ceil(input_bits/8) × ceil(output_bits/8)` byte で、shot 数とは独立です。
元の public `PreparationFramePlan` とその全履歴を含む返却値は維持し、compiled
factory 内だけ出口 frame 用の実装を使います。

今回の frame 最適化は同じ推論結果を求める演算変更です。以前導入した局所
DEM は引き続き **準備・前段の残留エラーを prior から除外するモデル**であり、
それらのエラーは物理サンプルに残ります。今回 prior のモデルは変更していません。

## 検証と計測条件

小規模 d3/5・各7 shots以下で元の全履歴実装と出口 frame および全 decode
フィールドを比較し、一致を確認しました。検証の有無でも回路・cache key・
同一 seed の測定記録・復号結果は一致します。serial/spawn、saved metadata、
config hash と物理 seed の独立性もテスト対象です。
全 bench は **272 passed**、Hex 既存テストの read-only 実行は **128 passed**。
修正したテスト上の仮定、警告数、実行コマンドは [TEST.md](../TEST.md) に記録しました。

速度比較は別の選択点診断で d=7、T=3、p=.003、r_0=r_plus=7、seed=917、
1,024 shots、batch=128 としました。Conda knill_system、OMP/OpenBLAS/MKL
各1 thread、他の本作業のテストとは重ねずに実行。構築は検証あり／なしを
交互順で各3回測定し、毎回 local prior cache を消去しました。
復号比較は同じ物理 bundle・同じ局所 DEM/gap graph・同じ1,024測定記録を
使い、準備 plan の算術だけを native／packed に切り替えます。全フィールドを
事前比較してからウォームアップ後の7反復を交互順で計測しています。
I/O と sampling は復号時間に含みません。

再現コマンドと生データ:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  bash scripts/python.sh results/factory_frame_optimization/compare.py
```

[診断スクリプト](../results/factory_frame_optimization/compare.py)、
[JSON](../results/factory_frame_optimization/comparison.json)、
[ログ](../results/factory_frame_optimization/compare.log) は ignored results 下です。

## 計測結果

| 対象 | 従来の算術／検証あり | 最適化後／検証省略 | 時間短縮 |
| --- | ---: | ---: | ---: |
| 構築時間・中央値 | 14.1798 s | 3.21248 s | 77.3% |
| 準備復号＋frame、1,024 shots | 0.280835 s | 0.222392 s | 20.8% |
| 復号全体、1,024 shots | 0.348699 s | 0.289702 s | 16.9% |
| 準備復号＋frame、1 shot 償却 | 0.274253 ms | 0.217180 ms | 20.8% |
| 復号全体、1 shot 償却 | 0.340526 ms | 0.282912 ms | 16.9% |

構築比較は両方とも今回の packed 算術を備え、検証フラグだけが異なります。
復号比較はその逆で、同じ構築済みデータに対する算術だけが異なります。
準備復号の時間には T+1=4 preparations の全 matching と frame 計算が含まれます。
構築時間には setup／DEM／sampler を含みますが、import と provenance 収集、
sampling、保存は含みません。

7反復の最小–最大は、準備 frame が従来0.270392–0.303042 s、新0.214430–
0.237844 s、復号全体が従来0.337710–0.380920 s、新0.266566–0.310605 s。
構築3反復は検証あり13.4944–14.1948 s、省略3.09238–3.34202 s でした。
これらは反復範囲であり信頼区間ではありません。今回の lookup table 合計は
2.615 MiB です（その他の native map／matching graph のメモリを除く）。

完全検証が setup の主要コストであるという以前の診断と整合します。算術の
最適化も効果がありましたが、matching を4回行う必要は残ります。この測定は
batch throughput からの償却値であり、1 module の到着から応答までの最大
latency、ハードウェア上のリアルタイム性を示すものではありません。d11 の
改善率もこの d7 の測定からは推定していません。以前の距離／T sweep は別の
時間帯・実装での計測なので、上表の直接比較には混ぜていません。
