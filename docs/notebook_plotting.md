# Notebookから保存データを作図する

`knill_bench.analysis` の `RunRegistry`, `NotebookPlots`, `FigureStyle` を使う。
対象は schema-v2 の Fig.4(d)、ordinary SE memory、logical-zero factory。
保存ファイルを読むだけで、回路構築・デコード・シミュレーション・resume は行わない。
実行例は [notebooks/saved_figures.ipynb](../notebooks/saved_figures.ipynb)。
既存のv1 plotting APIとv2 CLI/B3解析は変更しない。

## 環境と体裁

Notebook kernelはConda `knill_system` を選ぶ。ユーザー所有のスタイルpackageは
次のコマンドでインストールできる（数値依存関係やfork sourceは変更しない）。

```bash
bash scripts/python.sh -m pip install --no-deps --no-build-isolation -e external/plotting_lib
bash scripts/python.sh -m pip check
```

この環境ではインストール済み。使用した `plotting_lib` は version 0.1.0、
checkout `f0837a9d2f7f20268ebf705a00731a10c648ad3c`。
任意のNotebook用依存なのでsimulation用lock/wheel bundleには追加しない。
別環境では上のローカルpackageのインストールが必要。

```python
from knill_bench.analysis import RunRegistry, NotebookPlots, FigureStyle, WilsonInterval

style = FigureStyle(dpi=300)
# 添付図に近い既定値: figsize=(6, 3.6), 軸ラベル14pt, 目盛13pt, 凡例12pt
# style.settings = {"axes.labelsize": 16, "xtick.labelsize": 14, "ytick.labelsize": 14}
# style.figsize = (6.75, 4.0)
```

`FigureStyle` は `plotting_lib.update_settings(style="aps")` を基礎に、添付図に
近いserif体・文字と目盛サイズ・内向きの長短目盛・枠付き凡例を共通設定する。
画面・保存ともデフォルト300 dpi。rc設定はcontext内で適用し、Notebook全体を変更しない。
全作図APIはタイトルなしのMatplotlib `(fig, ax)` を返す。
`ax=` で既存Axesへ描く場合、そのFigureのサイズ・dpiは呼び出し元が管理する。
frequencyは `return_unique=True`、lifetimeは `return_summary=True` で
3番目の戻り値を追加できる。

### LaTeX / MathTextラベル

標準の `usetex=False, math_fontset="cm"` でComputer Modern数式を使う。
`$...$` で囲んだ `\mathrm{...}`（roman）、`\mathsf{...}`（sans serif）が使用可能。
`labels` に既定ラベル文字列から任意の表記への対応を設定すれば、全作図へ適用できる。

```python
style = FigureStyle(labels={
    "Physical error rate": r"$\mathrm{Physical\ Error\ Rate}$",
    "logical error rate": r"$p_{\mathrm{L}}$",
    "Logical gap": r"$\mathsf{Logical\ gap}$",
})
# 図ごとの編集も可能: ax.set_ylabel(r"$p_{\mathrm{L}}$")
```

実際のLaTeXで描画する場合は `FigureStyle(usetex=True,
latex_preamble=r"\usepackage{amsmath}", labels=...)`。
latex/dvipngと必要なTeX packageがある環境が必要。この環境ではPNG/PDF保存まで確認済み。
既定preambleはamsmathのみで、plotting_libの追加package群を要求しない。
TeXの追加macro/packageは `latex_preamble` で指定できる。
自動生成する凡例中の `_` などは実TeXモードではescapeする。
明示した `labels` の値はそのまま使用するため、raw文字列と `$...$` を使用すること。

### 95% Wilson信頼区間のshade

**積み上げlifetime図を除く5種類の図**には、既定で95%のpointwise区間を
同じ曲線色のshadeとして付加する。lifetime図は右軸の平均も含めて対象外。
共通クラス `WilsonInterval` が計算し、`FigureStyle.shade_alpha`（既定0.18）が透明度を決める。
既存の作図呼び出しに引数を追加する必要はない。

```python
interval = WilsonInterval()  # confidence=0.95
lower, upper = interval.bounds(3, 7)  # successes, trials
style.shade_alpha = .18
# data登録後に必要なら明示する（省略しても同じ既定値）:
# plots = NotebookPlots(data, style=style, interval=interval)
```

比率k/nの区間は連続性補正なしのWilson score法。
`z=Φ⁻¹(1−α/2)`, `c=(k+z²/2)/(n+z²)`,
`h=z*sqrt((k/n)*(n−k)+z²/4)/(n+z²)` として、`[c−h,c+h]` を0..1に収める。
式は [NISTのWilson法](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm) に対応する。
0エラーでも上限は正、全エラーでも下限は1未満。n=0では両端をNaNとし、帯を描かない。
per-round換算時は上下限にも同じ単調な `1−(1−p)**(1/r)` を適用する。

| 図 | k / nと表示する区間 |
|---|---|
| 未選別LER | errors / shots |
| gap frequency | 当該gap値の出現数 / shots。count表示では上下限をshots倍 |
| abort | rejected / shots |
| 選別後LER | accepted_errors / accepted（全shotsではない） |
| LER低減率 | 下記のpaired-count変換によるWilson由来の区間 |

count表示のfrequency帯は `N*P(gap=x)`（期待度数）の区間であり、将来の実現度数に対する
予測区間ではない。各categoryの区間は周辺の二項比率の区間で、category間で独立とは仮定しない。

**低減率の区間:** `1−LER_selected/LER_raw` は二項比率そのものではないため、
これに直接Wilson式を使わない。採択イベントA、エラーEとして
`a=P(A)`, `b=P(A|E)` と置くと `LER_selected/LER_raw=b/a`。
同じshot集合から `a=accepted/shots`, `b=accepted_errors/errors` を求める。
2区間を [Bonferroni法](https://www.itl.nist.gov/div898/handbook/prc/section4/prc463.htm) で調整
（既定では各97.5% Wilson）し、`[1−b_upper/a_lower, 1−b_lower/a_upper]` を返す。
この比への変換は本モジュールでの導出で、2比率の独立性を仮定しない保守的な組合せ。
Wilson自体は近似なので、有限標本で厳密に95%を保証する区間ではない。

採択ゼロ・元のエラーゼロでは低減率の帯は未定義。構造的に選別なしの負の閾値では、
定義された低減率も上下限も0。有限のcutでたまたま全shotが通った場合とは区別する。
負の低減率・負の下限を0に切り詰めない。

どの帯も**固定した点/category/cutごとの区間**。全距離・全gap値・全閾値に対する同時区間や、
dataを見て選んだ閾値に対するcoverageを主張しない。対数軸上では0以下の部分は表示範囲に入らない。
帯を点の間で結ぶ描画は、未観測の連続領域について信頼区間を推論するものではない。
旧v1/B3/CLIのWilson・Agresti–Coull計算と保存schemaは変更しない。

```python
# fig, ax = plots.plot_...(...)
# ax.set_ylim(1e-5, 1)
# ax.legend(loc="best")
# style.save(fig, "figure.pdf")  # ベクタ形式。PNGも300 dpi
# with style.context():
#     ax.text(...)              # 後から足すartistにも同じスタイル
```

## パス登録と条件指定

```python
from pathlib import Path
root = Path("/home/quantum_teresheys/workspace/knilll_bench/results/cluster/results")
data = RunRegistry({
    "fig4d": root / "20261017224016_27f982ab_fig4d",
    "memory": root / "20261017224951_8501f871_my_se_memory",
    "factory": root / "20261021061441_97825404_logical_zero_factory",
})
# data.register("another_key", "/path/to/another/run")
plots = NotebookPlots(data, style=style, batch_size=65536, round_digit=None)
```

**登録時とNotebookPlotsの生成時はファイルを開かない**。作図呼び出しごとに
config/metadataを読み、選択したpointのParquetだけをバッチ処理する。
`filter_by={"key": "factory"}` なら他のkeyのパスも開かない。
`filter_by` のスカラーは完全一致、list/tuple/setは候補への一致。
`group_by` はフィールド名1つ、またはそのlist/tuple。
凡例にはgroup条件を表示する。未知フィールド、空選択、重複keyはエラー。

主な条件は `key`, `kind`, `name`, `d`, `p`, `T`, `r_0`, `r_plus`, `rounds`,
`noise`, `decoder`, `create_codecapacity_dem`, `prior_policy`, `gap_units`,
`final_readout`, `shots`, `config_hash`, `case_id`。
`distance=d`, `T_tel=T`, `r_+=r_plus`, `noisemodel=noise` のaliasも使える。
`r_0`, `r_plus`, `rounds` はdの式を評価した実際の整数。
`noise_parameters` はnoise設定のcanonical JSON文字列で、custom noiseの区別に使える。
その他configのトップレベル固定フィールドも使用できる。

1本のp曲線は、p以外の物理条件・key・priorが同じである必要がある。
それ以外の図は、各groupに物理pointが1つになるよう指定する。
複数pointを暗黙に平均・poolしない。key間比較ではkeyもgroupに加える。

未完了runでも**completeとして公開されたpoint**は使える。
選択条件に含まれる未完了pointは警告して除外する。complete pointの欠損、
config変更、schema/ID/shot/error数の不一致、null/NaN/inf/負のgapはエラー。
既存gapファイルはLERのみの図でもpair検証する。データやmetadataは変更しない。

## Gap値の共通丸めオプション

```python
plots = NotebookPlots(data, style=style, round_digit=6)  # 小数点以下6桁に四捨五入
# 個別のgap図でも上書き可能:
# plots.plot_abort(..., round_digit=2)
# plots.plot_abort(..., round_digit=None)  # この図だけ丸めを解除
```

既定 `None` は元のgap値をそのまま使う。整数指定は、元のfloatの最短十進表記を
Decimalに変換し、**ROUND_HALF_UPの四捨五入**を行う（例: 1.25→1.3、
2.675→2.68）。偶数丸めではない。0は整数、負の桁数は10/100…単位の丸め。
対応範囲は-308〜308、bool/文字列/非整数はエラー。

表示するx値だけでなく、**全段のgapを最初に丸めたうえで**frequency、unique値、
自動閾値グリッド、AND採択、abort、lifetime、選別後LERと低減率をすべて計算する。
明示した `gap_threshold` 自体は丸めない。丸めによりgapが閾値と等しくなれば
`<=` の規則で棄却される。lifetimeの2回目の読み込みにも同じ丸めを適用する。
未選別LERには影響しない。rawのnull/nonfinite/負値検証は丸め前に行うため、
丸めで壊れたデータを隠さない。保存済みParquet/B3の計算は変更しない。

## 1. 物理エラー率と論理エラー率

```python
fig, ax = plots.plot_logical_error_rate(
    filter_by={"key": ["fig4d", "memory"]}, group_by=["key", "d"],
    per_rounds=True,
)
```

yは対数。未選別LERは `errors/shots`。
`per_rounds=True` では `1 - (1 - LER)**(1/r)`、memoryでは `r=rounds`、
Knill/factoryでは `r=T`。これは独立round仮定を証明するものではなく、表示の換算規約。
計算はlog1p/expm1で行う。デフォルトFalse。
ゼロ観測エラーを擬似カウントで置き換えないので、0は対数軸では表示されない。

## 2. Logical gapのfrequency

```python
fig, ax = plots.plot_gap_frequency(
    filter_by={"key": "factory", "p": .001}, group_by="d", T_idx=1,
)
```

gapファイルが必要。`T_idx` は1始まりでデフォルト1。
共通/個別 `round_digit` を適用後、同じgap値の出現数をscatter表示する。
bin化は行わず、`round_digit=None` の場合は元のexact値を区別する。
`normalize=True` なら各pointのshot数で割った相対frequency。
memoryのgapは全memory実験に対する1値なので `T_idx=1` のみ。

`return_unique=True` を指定すると、**各group・全判定段**のunique値リストを
3番目の戻り値として返す。図は指定した `T_idx` のみを表示する。

```python
fig, ax, unique_gaps = plots.plot_gap_frequency(
    filter_by={"key": "factory", "p": .001}, group_by="d", T_idx=1,
    return_unique=True, round_digit=6,
)
unique_gaps[(5,)][1]  # group_by=dのd5、最初の判定。昇順のfloatリスト
# unique_gaps[(5,)][2]  # 2段目
# unique_gaps           # Notebookで全group・全段のリストを表示
```

辞書のgroup keyは `group_by` の値を順に並べたtuple。group_byが空なら `()`。
`return_unique=False`（既定）は従来どおり `(fig, ax)` のみ。

## 3. 閾値とabort probability

```python
fig, ax = plots.plot_abort(
    filter_by={"key": "factory", "p": .001}, group_by="d",
)
```

いずれかの段のgapが **閾値以下 (`<=`)** なら棄却する。
従って採択は `AND_t(gap_t > threshold)`、abortは `1 - accepted/shots`。
デフォルトのx値は丸め設定適用後の全段のgapのunique値の和集合（binなし）。
点を線で結ぶ。`gap_threshold=[...]` で指定値にもできる。
`-inf` は選別なし、`+inf` は全棄却（端点表示には有限閾値が適する）。

**境界の注意:** 既存B3 `analyze-factory` は `gap >= theta` を採択する。
今回のNotebook APIはユーザー指定の `gap > threshold` を採択するため、
等号を含むデータではB3と結果が異なる。既存B3の定義は変更していない。

## 4. 閾値とlifetimeの積み上げ割合・平均

```python
fig, ax, lifetime_summary = plots.plot_lifetime(
    filter_by={"key": "factory", "p": .001}, group_by="d",
    gap_threshold=[0, 6, 8], return_summary=True,
)
# d5の閾値ごとの平均lifetime:
lifetime_summary[(5,)]["mean_lifetime"]
```

factory専用。最初に棄却される段がkならlifetimeはk-1。
全段を通過したshotはT。全shotを使い、採択shotだけに条件づけない。
Tは観測上限であり、T以降の寿命や動的retryは推定しない。
**左軸**は全shotに対する割合。lifetime=0,1,…,Tの割合を色で分け、
1本の棒が合計100%になるように積み上げる。複数groupは横に並べ、
棒のハッチ模様で区別する。上の凡例はlifetimeの色、下の凡例はgroupを表す。

**右軸の破線・marker**は、棄却shotを含む全shotの平均lifetime。
整数histogram `n_l` と全shot数Nから `sum(l*n_l)/N` を計算する。
平均の小さな変化も読み取れるよう、右軸は左の割合軸とは独立に自動スケールする。
全範囲を表示したい場合は `fig.axes[-1].set_ylim(0, T)` とする。
`show_mean=False` で右軸・破線を非表示にできる。

この平均は **Tで打ち切った観測範囲0..Tの平均**。ほぼ全shotがTまで残る場合は
平均もTに近くなる。T以降の未観測の寿命や無制限のretry寿命を推定するものではない。
指数分布などの分布形は仮定せず、保存されたshotをそのまま集計する。

`return_summary=True` は `{group_tuple: summary}` を3番目に返す。
summaryには昇順 `thresholds`、`T`、`shots`、整数 `counts`、`fractions`、
`mean_lifetime` が入る。counts/fractionsは `(閾値数, T+1)` で、列がlifetime=0..T。
既定の戻り値は従来どおり `(fig, ax)`。axは左の割合軸、平均軸は `fig.axes[-1]`
（`show_mean=True` の場合）。
色とgroupの凡例は `fig.legends` から編集できる。

デフォルトは丸め設定適用後の全gapのunique値。ただし**11種類以上ならエラー**となるので、
上のようにlist/setで `gap_threshold` を明示する。
x座標は等間隔のカテゴリで、tick labelが実際の閾値。

## 5. 選別によるLER低減率

```python
fig, ax = plots.plot_ler_reduction(
    filter_by={"key": "factory", "p": .001}, group_by="d",
)
```

低減率は `1 - LER_selected / LER_unselected`。
1が完全な低減、0が同等、負は悪化。factor（何倍）ではない。
pまたはdの少なくとも一方を、`filter_by` で1値に固定する必要がある。
閾値・採択規約は3と同じ。採択ゼロ、または未選別エラーゼロなら低減率は
未定義（NaN）として線を切る。ゼロや無限の低減と解釈しない。

## 6. 複数閾値の選別後LERと物理エラー率

```python
fig, ax = plots.plot_postselected_logical_error_rate(
    filter_by={"key": "factory"}, group_by="d",
    gap_threshold=[0, 2, 4],
)
```

`group_by` はちょうど1フィールド（デフォルトd）。groupを色で、閾値をmarkerと
線種の両方で区別する。2種類の凡例を同じlegendに表示。
区別可能な12閾値まで。各pで全段のgap選別後の `accepted_errors/accepted` を描く。
yは対数。**per-round換算は行わない**。採択ゼロは未定義。

この図の横軸は1/2/5系の間隔で主目盛を約5区間に整理し、不要な末尾0を減らす。
例えばp=.001〜.005の図は `0.001, 0.002, 0.003, 0.004, 0.005` となり、
13ptの共通目盛サイズを保ったままラベル間隔を確保する。非常に小さい/大きい値は
科学表記に切り替え、加算offsetは使わない。描画後の `ax.xaxis` から個別編集も可能。

## 科学的解釈と処理量

factoryのLERは常に**terminal evaluation-oracle labelの条件付きエラー率**で、
online data-Knill LERではない。ラベルをgap選別やlifetime算出に使わない。
異なるgap units/priorは同じ閾値の意味が異なるため、比較対象のkey/priorを明示する。
新APIは観測比率と上記のpointwise Wilson shadeを描く（積み上げlifetime図を除く）。
dataを見て選んだ閾値の同時coverageや、ゼロ観測エラーに基づく無誤りの保証はない。

Parquetのread batch境界とrow group境界は一致不要。
shot全件のDataFrameやtrajectory配列は保持せず、exact frequency/minimum-gap
集計に必要なunique値数に比例したメモリを使う。unique値が多い場合、
丸めない既定のscatterも大きくなる。必要なら `round_digit` で数値精度を指定する。
丸めは各bounded batchのunique値のみで処理し、変換cacheも4096件まで。
lifetimeはunique-grid集計後にもう一度
bounded readして、指定閾値ごとの0..Tのhistogramを作る。
`data.select(filter_by)` は必要時だけconfig/metadataを読む低レベルAPI、
`saved_data.SavedPoint.batches` は検証付きiterator。
`notebook_plotting.summarize_point` / `cut_statistics` で集計値も取り出せる。
iteratorは最後まで消費してshot/error count検証を完了させること。
