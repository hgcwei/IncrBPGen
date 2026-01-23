# Rethinking Basis Path Testing: A Mixed Integer Programming Approach

[![arXiv](https://img.shields.io/badge/arXiv-2601.05463-b31b1b.svg)](https://arxiv.org/abs/2601.05463)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains the official implementation for the paper: **"Rethinking Basis Path Testing: Mixed Integer Programming Approach for Test Path Set Generation"**.

Our work reframes the classical problem of basis path generation from a procedural, graph-traversal task into a declarative optimization problem. We leverage Mixed Integer Programming (MIP) to generate a complete basis path set that is globally optimal in its structural simplicity, overcoming the limitations of traditional greedy algorithms like DFS/BFS.

## Abstract

Basis path testing is a cornerstone of structured testing, yet conventional automated methods (e.g., DFS/BFS) often produce suboptimal paths, which hinders downstream test data generation and increases the cognitive load on engineers. This paper reframes basis path generation from a procedural search task into a declarative optimization problem. We introduce a Mixed Integer Programming (MIP) framework designed to generate a complete basis path set that is globally optimal in terms of structural simplicity.

The framework comprises two complementary strategies:
1.  **A Holistic MIP Model**: Guarantees a theoretically optimal path set.
2.  **An Incremental MIP Strategy**: Provides a scalable solution for large, complex topologies. This strategy employs an innovative multi-objective function that ensures a 100% success rate in generation while maintaining computational efficiency.

Our experimental evaluation on real-world code and large-scale synthetic Control Flow Graphs (CFGs) demonstrates that our incremental MIP strategy achieves a 100% success rate in generating complete basis path sets, providing a high-quality structural "scaffold" for subsequent test generation efforts.

## Core Contributions

1.  **Paradigm Shift**: We are the first to formulate basis path generation as a declarative optimization problem, focusing on *what* constitutes an optimal path set rather than *how* to find it.
2.  **Globally Optimal Model**: We propose a holistic MIP model that guarantees finding the simplest path set that satisfies both coverage and independence criteria.
3.  **Scalable Incremental Strategy**: To address scalability, we designed an incremental MIP strategy with a "novelty penalty" mechanism, which effectively avoids the "greedy traps" inherent in traditional algorithms.
4.  **Exceptional Robustness**: Our experiments show that the incremental MIP approach achieves a **100% success rate** across a wide range of complex topologies, a feat unattainable by traditional procedural baselines.

## Framework Overview

Our approach aims to generate a basis path set of size `k` (the cyclomatic complexity) from a given Control Flow Graph (CFG).

### 1. Holistic MIP Model

This model solves the entire problem at once, coupling the generation of all `k` paths into a single, large optimization model.
- **Objective**: Minimize the total length of all paths.
- **Constraints**:
  - Path validity and connectivity (based on network flow).
  - Path set completeness (covering all edges).
  - Path linear independence (via a "private edge" constraint).
- **Pros**: Theoretically guarantees a globally optimal solution.
- **Cons**: Faces scalability challenges on large graphs.

### 2. Incremental MIP Model

This model decomposes the problem into `k` sequential, smaller optimization subproblems, generating one new, linearly independent path at each iteration.
- **Objective**: An innovative multi-objective function that simultaneously minimizes **Path Length** and maximizes **Novelty** (by minimizing the number of newly covered edges).
  ```
  min Z = (Path Length) + (Novelty Penalty)
  ```
- **Key Mechanism**: The "novelty penalty" incentivizes the model to reuse already covered edges whenever possible, only "conservatively" exploring new edges when required to satisfy linear independence. This prevents the premature exhaustion of simple paths and avoids getting stuck.
- **Pros**: Highly scalable and extremely robust in practice (100% success rate).
- **Cons**: Does not theoretically guarantee global optimality, but empirically generates very high-quality path sets.

## Key Results

Our incremental MIP strategy (Incr. MIP2) demonstrates superior performance across all test scenarios:

| Dataset | Method | Success Rate (%) | Avg. Time (s) |
| :--- | :--- | :---: | :---: |
| **Real-world Code (50 Python fns)** | BFS | 90.0 | **0.0001** |
| (k ∈ [1, 8]) | **Incr. MIP2** | **100.0** | 0.0312 |
| **Large-scale Synthetic Data** | BFS | 12.3 | **0.0023** |
| (k=100, |V|=50) | Incr. MIP1 (Greedy) | 14.7 | 15.32 |
| | **Incr. MIP2 (Novelty)**| **100.0** | 17.76 |

**Conclusion**: The incremental MIP2 is the only method that both guarantees 100% success in generating a complete basis path set and maintains practical computational efficiency on complex systems.

## Setup & Installation

This project is implemented in Python and relies on the IBM ILOG CPLEX Optimizer for solving MIP models.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create a Python virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: `requirements.txt` should include `cplex` and other necessary libraries.*

4.  **Install CPLEX**:
    You need to have IBM ILOG CPLEX Optimization Studio installed. Students and academics can get a free license via the [IBM Academic Initiative](https://www.ibm.com/academic/home). After installation, ensure its Python API is correctly configured in your environment.

## How to Use

*(Please add specific instructions for your code here. The following is an example template—please adapt it to your actual code structure.)*

### 1. Input Format

Our script accepts an input file representing the Control Flow Graph (CFG) in an adjacency list format. For example, `graph.txt`:
```
# Format: node_id neighbor1 neighbor2 ...
# s=0, t=6
0 1 2
1 3
2 3
3 4 5
4 6
5 6
6
```

### 2. Running an Example

To generate a basis path set for `graph.txt` using the incremental MIP model:
```bash
python generate_paths.py --graph_file path/to/graph.txt --model incremental --source 0 --sink 6
```

To see all available options:
```bash
python generate_paths.py --help
```

## Citation

If you use our code or methods in your research, please cite our paper:

```bibtex
@misc{wei2026rethinking,
      title={Rethinking Basis Path Testing: Mixed Integer Programming Approach for Test Path Set Generation}, 
      author={Chao Wei and Xinyi Peng and Yawen Yan and Mao Luo and Ting Cai},
      year={2026},
      eprint={2601.05463},
      archivePrefix={arXiv},
      primaryClass={cs.SE}
}
```

## Contact

-   Chao Wei: `weichao.2022@hbut.edu.cn`
-   Mao Luo (Corresponding Author): `luomao@hbut.edu.cn`

Feel free to reach out with any questions, suggestions, or for potential collaborations!
