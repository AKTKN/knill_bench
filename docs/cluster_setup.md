# Conda 環境とクラスターマシンへの配布

研究用環境は **knill_system**、Python は **3.12.15** です。数値・解析・
作図・ノートブック関連は pip でインストールします。従来の `.venv` は使用しません。

## ローカル環境の再作成

リポジトリ直下で実行します。

```bash
bash scripts/bootstrap.sh
conda activate knill_system
python -m pip check
python -m pytest -q
```

bootstrap は environments.yaml に従って環境を作成または更新し、指定 SHA の
Hex / lomatching / surface-sim と knill-bench を editable install します。
既存の checkout が異なる SHA の場合は停止し、reset しません。

環境だけを用意する場合は次のように分けられます。

```bash
conda env create -f environments.yaml
conda activate knill_system
# 指定された三つの checkout を用意した後:
python -m pip install --no-deps --no-build-isolation \
  -e external/Hex -e external/lomatching -e external/surface-sim -e '.[research,dev]'
```

- requirements.lock: 既存実験の数値依存を固定。Stim 1.16.0、LDPC 2.4.1、
  NumPy 2.5.3、SciPy 1.18.1、PyMatching 2.4.0 など。
- requirements-research.lock: JupyterLab、ipykernel、ipywidgets、pandas/xarray、
  seaborn、Plotly、statsmodels、SymPy、h5py、joblib、Dask/distributed、
  psutil、rich、ビルド・テストツールと追加の推移依存を固定。
- environments.yaml: Conda の Python/pip と上記二つの pip lock を指定。
  個人の絶対パス/prefix を含みません。
- conda-linux-64.explicit.txt: この環境の Conda ネイティブパッケージを
  build/URL まで固定した Linux x86_64 用の記録です。pip パッケージは別の lock で管理します。

Jupyter カーネルは環境内に登録済みです。別マシンでは次を実行できます。

```bash
python -m ipykernel install --sys-prefix --name knill_system --display-name 'Python (knill_system)'
jupyter lab
```

## Hex と bench の wheel 化

Hex H5 の素の wheel には必要な `.mtx` 行列が含まれません。また、従来の
出典記録は Git checkout を必要としました。そのため、次の専用ビルダーを使います。

```bash
conda activate knill_system
python scripts/build_cluster_bundle.py --download-deps --output results/cluster_bundle
```

出力先は新しいディレクトリを指定します。既存配布物は上書きしません。
`--download-deps` を省くと研究用四パッケージの wheel だけを作成し、対象側で
通常の pip ダウンロードが必要になります。

ビルダーは固定 SHA の clean な依存 checkout を検証し、一時コピー上で
packaging 設定を補います。**Hex や他の依存リポジトリ本体は変更しません**。
Hex の全 Python/行列リソース、各パッケージの出典 manifest、bench の CLI を
含む wheel を作成し、元の Python/行列ファイルとの SHA256 一致を検証します。
Git URL を持つ依存を wheel metadata に残さず、ローカル wheel だけで依存を解決できます。
依存ソースの URL/SHA は pyproject.toml の tool.knill-bench.sources に保持します。

配布ディレクトリには次が入ります。

```text
wheels/                     # 四パッケージと、指定時は全 pip 依存の wheel
manifest.json               # ソース SHA、dirty、リソース hash、wheel checksum
install.py                  # checksum 確認後に pip install
requirements.lock
requirements-research.lock
environments.yaml
GETTING_STARTED.md
configs/                    # 設定例・テンプレート
```

ソース配布しかない固定依存（例: sinter 1.16.0）はビルド側で wheel に変換します。
計算ノードではソースビルドも Git 接続も不要です。ビルド側の bench に未コミットの
変更があれば dirty:true として記録され、実際に同梱したコードの hash も記録されます。
これは署名付きパッケージ認証ではなく、配布したソース・リソースの整合性確認です。

## クラスター側のセットアップ

このマシンで作るバイナリ依存 wheel は **CPython 3.12 / Linux x86_64** 用です。
現在の固定 wheel 群には glibc 2.28 以降が必要です。異なる OS/CPU や古い Linux では、
対応するログインノード上で配布セットを作成してください。クラスターマシン自体での
実行検証は別途必要です。

まず Conda の Python/pip をログインノードで用意します。

```bash
conda create -n knill_system -c conda-forge --override-channels python=3.12.15 pip=26.2.1 -y
conda activate knill_system
# 転送した配布ディレクトリ内:
python install.py
python -m pip check
knill-bench-v2 validate-config configs/templates/logical_zero_factory.yaml
```

`--download-deps` 付きの配布物なら install.py の pip 処理は `--no-index` で
ローカル wheel のみを使います。**Conda 自体と Python の配布は別途用意**してください。
同一 Linux 環境の native パッケージを厳密に再現する場合は、リポジトリ内の
conda-linux-64.explicit.txt を使って `conda create -n knill_system --file ...` とできます。

実行例:

```bash
conda run --no-capture-output -n knill_system knill-bench-v2 run configs/templates/logical_zero_factory.yaml
conda run --no-capture-output -n knill_system knill-bench-v2 analyze-factory RUN_DIRECTORY \
  --settings configs/templates/factory_analysis.yaml --output report.md
```

SLURM 等からは割当 CPU 数に合わせて config の workers を設定します。数値ライブラリの
スレッド数も明示すると過剰な並列化を避けられます。

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
conda run --no-capture-output -n knill_system knill-bench-v2 run my_factory.yaml
```

単一マシンの複数プロセスが現在の実装範囲です。workers は複数ノードへの自動配分や
MPI ジョブではありません。複数のジョブで一つの run に同時書込みしないでください。
wheel インストールでもソース/行列 hash、Hex H5、型/API の検証と出典記録を保ちます。
環境の変更前に作成した run の resume は、既存の厳密な互換性チェックで拒否され得ます。

設定・実験・解析の説明は [Getting started](../GETTING_STARTED.md) を参照してください。

設定形式の参考: [Conda の環境管理](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html)、
[Setuptools の package data](https://setuptools.pypa.io/en/latest/userguide/datafiles.html)。

## GitHub clone から PBS ジョブを実行する

ログインノードで fork を含む環境を構築します。次の bootstrap は
knill_system を作成し、既存環境があれば同名環境を更新します。

```bash
git clone --branch auxiliary-system https://github.com/AKTKN/knill_bench.git
cd knill_bench
# 必要ならサイト指定の Anaconda module をここで load する。
bash scripts/bootstrap.sh
conda activate knill_system
python -m pip check
cp configs/templates/logical_zero_factory.yaml configs/cluster_factory.yaml
# configs/cluster_factory.yaml の d/p/T/shots、buffer_shot、出力先を編集。
# 自動調整: batch_size: auto、target_chunk_seconds: 1.0
python -m knill_bench.experiments.cli validate-config configs/cluster_factory.yaml
```

別の環境名にする場合は environments.yaml をコピーして name を変更するか、
`conda env create -n my_knill_cluster -f environments.yaml` で作成し、上記の
指定 SHA の依存 checkout と四パッケージの editable install を行ってください。
bootstrap 自体の環境名は knill_system です。異なる環境を更新する操作は不要です。

`scripts/cluster_run_simualtion.sh` はユーザー提供のファイル名を維持した
PBS 用スクリプトです。先頭の select/ncpus/walltime/ログ出力先をクラスタの
規約に合わせて編集し、リポジトリ直下から送信します。nodefile の fallback を
使うため、例では mpiprocs と ncpus を同じ 96 にしています（MPI は起動しません）。

```bash
mkdir -p logs
qsub -v CONFIG_FILE=configs/cluster_factory.yaml,KNILL_CONDA_ENV=knill_system \
  scripts/cluster_run_simualtion.sh
# 割当より少ない worker に制限する例:
qsub -v CONFIG_FILE=configs/cluster_factory.yaml,WORKERS=8 \
  scripts/cluster_run_simualtion.sh
# 失敗・中断 run の再開（保存済み workers を収容できる CPU 割当が必要）:
qsub -v RESUME_RUN=results/RUN_DIRECTORY scripts/cluster_run_simualtion.sh
```

CONFIG_FILE の既定値は小さな factory テンプレートです。Fig.4(d) YAML にも
差し替えられます。実験予算を確認してから送信してください。PBS_NCPUS、未設定なら
PBS_NODEFILE の行数を CPU 割当として読み取り、--workers で実効設定に保存します。
両方が無ければ 1 worker です。WORKERS が割当を超えた場合、または nodefile が
複数ノードを含む場合は停止します。単一ノードの process pool で、MPI ではありません。
数値ライブラリのスレッド数は 1 に固定し、PBS_O_WORKDIR に移動してから実行します。

非対話シェルで conda が見つからない場合は `CONDA_BASE=/path/to/anaconda3` を
qsub -v で渡すか、サイトの Anaconda module をロードしてください。
ジョブ内では環境作成・依存ダウンロードを行いません。保存用 buffer_shot と計算用
チャンクは独立です。詳細・seed の再現性の限界は
[並列実行仕様](parallel_execution.md)を参照してください。
ローカルの模擬 PBS 環境で検証していますが、実クラスタでの qsub は未実施です。

The same PBS script also accepts ordinary SE memory configurations. Copy
configs/templates/se_memory.yaml, edit rounds/d/p/shots/get_logicalgap and pass
that file as CONFIG_FILE. No environment/dependency change is required.
See [memory configuration and output](se_memory.md).
