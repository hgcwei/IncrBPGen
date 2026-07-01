# IncrBPGen: Incremental MIP-Based Basis Path Generation

[![arXiv](https://img.shields.io/badge/arXiv-2601.05463-b31b1b.svg)](https://arxiv.org/abs/2601.05463)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

Official implementation of the paper:

> **Rethinking Basis Path Testing: Mixed Integer Programming Approach for Test Path Set Generation**
>
> Chao Wei, Xinyi Peng, Yawen Yan, Mao Luo, Ting Cai
>
> 📄 [arXiv:2601.05463](https://arxiv.org/abs/2601.05463)

---

## 📖 Overview

Basis path testing is a cornerstone of structural software testing, yet traditional automated methods relying on greedy graph-traversal algorithms (e.g., DFS/BFS) often fail to generate a complete set of linearly independent paths. This project reframes basis path generation from a procedural search task into a **declarative optimization problem** using Mixed Integer Programming (MIP).

We provide:

- **Incr. MIP2 (Novelty-Driven)** — Our proposed method that achieves **100% success rate** on both real-code and synthetic datasets.
- **Incr. MIP1 (Greedy)** — An ablation variant that minimizes only path length, demonstrating the "Greedy Trap" phenomenon.
- **GA Baseline** — A Genetic Algorithm baseline representative of Search-Based Software Testing (SBST) approaches.
- **Naive BFS Baseline** — A breadth-first search baseline for comparison.

### Key Results

| Dataset | Incr. MIP2 (Ours) | GA | Naive BFS |
|---|---|---|---|
| **Real Code** (3,048 functions) | **100.0%** | 93.6% | 37.7% |
| **Synthetic** (300 graphs) | **100.0%** | 100.0% | 0.0% |

---

## 📁 Repository Structure

```
IncrBPGen/
├── Incr.MIP2.py                    # 🔑 Our proposed method (Novelty-Driven Incremental MIP)
├── Incr.MIP1.py                    # Ablation: Greedy Incremental MIP (no novelty penalty)
├── ga_basis.py                     # Baseline: Genetic Algorithm
├── bfs_simple_basis.py             # Baseline: Naive BFS
├── synthetic_dataset_combined.csv  # Synthetic CFG dataset (300 graphs)
├── real_code_dataset.rar           # Real-code CFG dataset (3,048 functions, compressed)
└── README.md
```

---

## 🔧 Requirements

### Software Dependencies

- **Python** ≥ 3.8
- **IBM ILOG CPLEX Optimization Studio** (v12.10+ or v22.1+)
  - The CPLEX Python API (`cplex` package) is required for the MIP-based methods.
- **NumPy** — Required for the GA and BFS baselines.

### Installing CPLEX

CPLEX is a commercial solver with a free academic license. To install:

1. **Academic License**: Apply for a free academic license at [IBM Academic Initiative](https://www.ibm.com/academic).
2. **Install CPLEX**: Download and install IBM ILOG CPLEX Optimization Studio.
3. **Install Python API**:
   ```bash
   # After installing CPLEX, navigate to the CPLEX Python API directory:
   cd /path/to/cplex/python/3.x/x86-64_linux  # Adjust for your OS
   python setup.py install
   
   # Or, for newer versions:
   pip install cplex
   ```

### Installing Other Dependencies

```bash
pip install numpy
```

---

## 📊 Datasets

### Dataset Format

All datasets use CSV format with the following columns:

| Column | Description |
|---|---|
| `function_name` | Unique identifier for the function/graph |
| `num_nodes` | Number of nodes (basic blocks) in the CFG |
| `source_node` | Entry node ID (typically `0`) |
| `sink_node` | Exit node ID (typically `1`) |
| `cfg_cc` | Cyclomatic complexity (CC = \|E\| − \|V\| + 2) |
| `edges` | Edge list as a Python literal, e.g., `[(0, 2), (2, 3), ...]` |

### Synthetic CFG Dataset (`synthetic_dataset_combined.csv`)

300 randomly generated Control Flow Graphs organized into three complexity groups:

| Group | CC | Nodes (\|V\|) | Edges (\|E\|) | Count |
|---|---|---|---|---|
| Small | 10 | 9 | 17 | 100 |
| Medium | 50 | 30 | 78 | 100 |
| Large | 100 | 50 | 148 | 100 |

Each graph is generated using a structured random generator that composes realistic control flow patterns (if-else branches, local loops, diamond structures, multi-way branches) within isolated segments of a backbone chain. The segment-isolation strategy ensures localized strongly connected components (SCC ratio ≈ 4–24%), closely matching real-world CFG characteristics.

### Real-Code Dataset (`real_code_dataset.rar`)

3,048 Python functions extracted from 10 well-known open-source projects:

| Project | Functions | Description |
|---|---|---|
| CPython | 1,196 | Python language runtime |
| pandas | 648 | Data analysis library |
| Django | 445 | Web framework |
| scikit-learn | 377 | Machine learning library |
| TheAlgorithms | 180 | Algorithm collection |
| Celery | 90 | Distributed task queue |
| Rich | 56 | Terminal formatting library |
| Click | 27 | CLI framework |
| Flask | 18 | Web microframework |
| Requests | 11 | HTTP library |

- **CC range**: 2–95 (mean 13.8, median 12)
- **CFG construction**: Custom AST-based builder with correct Python boolean short-circuit evaluation semantics
- **Validation**: All CFGs verified against `radon` for CC consistency; zero dead-end nodes

To extract:
```bash
unrar x real_code_dataset.rar
# or
7z x real_code_dataset.rar
```

---

## 🚀 Quick Start

### 1. Run the Proposed Method (Incr. MIP2)

```bash
# On the synthetic dataset
python Incr.MIP2.py
```

By default, the script reads from the dataset file specified in the source code. To change the input dataset, modify the `parse_graph_csv()` call in the script:

```python
# Change this line to point to your dataset:
graphs_to_test = parse_graph_csv("synthetic_dataset_combined.csv")
```

### 2. Run Baselines

```bash
# Greedy MIP (ablation study)
python Incr.MIP1.py

# Genetic Algorithm baseline
python ga_basis.py

# Naive BFS baseline
python bfs_simple_basis.py
```

### 3. Run on Your Own CFGs

Prepare a CSV file with the required columns (see [Dataset Format](#dataset-format)) and update the file path in the script:

```python
graphs_to_test = parse_graph_csv("your_dataset.csv")
```

---

## ⚙️ Method Details

### Incr. MIP2: Novelty-Driven Incremental MIP (Our Method)

The core idea is to generate basis paths **one at a time** using an incremental MIP formulation. At each iteration *i*, the solver finds a new source-to-sink path that:

1. **Is structurally valid** — satisfies flow conservation and connectivity constraints.
2. **Is linearly independent** — contains at least one "private edge" not used by any previously generated path.
3. **Is structurally simple** — minimizes total path length.
4. **Preserves future options** — a novelty penalty discourages premature consumption of uncovered edges.

The objective function is:

$$\min \quad Z_i = \underbrace{\sum_{e \in E} x_e}_{\text{Path Length}} + \alpha \cdot \underbrace{\sum_{e \in E \setminus E_{\text{cov}}^{(i-1)}} y_e}_{\text{Novelty Penalty}}$$

where α is the novelty penalty weight (default: α = 1). Our sensitivity analysis shows that the method achieves 100% success rate for α ∈ {0.1, 1, 10, 100, 1000}, demonstrating robustness across four orders of magnitude.

### Incr. MIP1: Greedy Incremental MIP (Ablation)

Same formulation as Incr. MIP2 but **without the novelty penalty** (α = 0). This variant demonstrates the "Greedy Trap": by myopically minimizing path length, it prematurely consumes critical edges, causing success rates to drop from 99% (CC=10) to 28% (CC=100).

### Key Constraints

- **Flow Conservation**: Standard Kirchhoff balance at each node.
- **Subtour Elimination**: Single-commodity flow formulation prevents disconnected path components.
- **Private-Edge Independence**: Each path must contain at least one edge not used by any preceding path, guaranteeing linear independence.

---

## 📈 Reproducing Paper Results

To reproduce the main results from the paper:

```bash
# Table 3: Synthetic dataset results (all methods)
python Incr.MIP2.py    # Incr. MIP2 → 100% success
python Incr.MIP1.py    # Incr. MIP1 → 63% success (Greedy Trap)
python ga_basis.py      # GA → 100% success on synthetic
python bfs_simple_basis.py  # Naive BFS → 0% success

# Table 4: Real-code dataset results
# Modify each script to load the real-code dataset:
#   graphs_to_test = parse_graph_csv("real_code_dataset.csv")
```

### Expected Output Format

Each script produces per-graph results followed by a summary:

```
[1/300] Processing Graph: synthetic_cc10_v9_1 (nodes=9, edges=17, target_paths=10)
  > Result: SUCCESS. Found all 10/10 paths in 0.03s.
...
==================================================
BATCH SOLVER STATISTICAL REPORT
==================================================
Total Graphs Evaluated      : 300
Fully Solved Graphs (100% CC): 300
Graph Success Rate          : 100.00%
Basis Path Coverage Rate    : 100.00%
Average Time Per Graph      : 17.0299 seconds
==================================================
```

---

## 📋 Citation

If you find this work useful, please cite our paper:

```bibtex
@article{wei2025rethinking,
  title={Rethinking Basis Path Testing: Mixed Integer Programming Approach for Test Path Set Generation},
  author={Wei, Chao and Peng, Xinyi and Yan, Yawen and Luo, Mao and Cai, Ting},
  journal={arXiv preprint arXiv:2601.05463},
  year={2025}
}
```

---

## 📄 License

This project is released under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- [IBM CPLEX](https://www.ibm.com/products/ilog-cplex-optimization-studio) — Commercial MIP solver used in this work.
- The open-source projects whose code was used to construct the real-code dataset: [CPython](https://github.com/python/cpython), [pandas](https://github.com/pandas-dev/pandas), [Django](https://github.com/django/django), [scikit-learn](https://github.com/scikit-learn/scikit-learn), [TheAlgorithms](https://github.com/TheAlgorithms/Python), [Celery](https://github.com/celery/celery), [Rich](https://github.com/Textualize/rich), [Click](https://github.com/pallets/click), [Flask](https://github.com/pallets/flask), [Requests](https://github.com/psf/requests).
