# Dataset

GraphShield uses the **Elliptic Bitcoin Transaction Dataset** as a benchmark dataset for illicit transaction detection.

The dataset represents Bitcoin transactions as a graph:

- Nodes → transactions
- Edges → Bitcoin flow between transactions
- Labels:
  - `1` → illicit transaction
  - `2` → licit transaction
  - `unknown` → unlabeled transaction

The dataset contains:

- 203,769 transaction nodes
- 234,355 transaction edges
- 166 transaction-level features


## Download Dataset

Due to dataset size and licensing limitations, the raw dataset is not included in this repository.

You can download it from Kaggle:

<div align="center">

<a href="https://www.kaggle.com/datasets/ellipticco/elliptic-data-set">
<img src="https://img.shields.io/badge/Dataset-Elliptic%20Bitcoin%20Dataset-blue?style=for-the-badge&logo=kaggle">

</a>

</div>


After downloading, place the files in this folder:
```
data/
│
├── elliptic_txs_features.csv
├── elliptic_txs_classes.csv
└── elliptic_txs_edgelist.csv
```


## Dataset Processing

The dataset is processed through the GraphShield pipeline:

1. Feature preprocessing
2. Graph construction
3. GATv2 graph representation learning
4. Traditional ML classification
5. Hybrid risk scoring
6. Explainability generation (SHAP + GNNExplainer)

