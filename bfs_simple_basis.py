import sys, ast, time, csv, numpy as np
from collections import defaultdict, deque

# ======================================================================
# 1. 表格数据解析器 (与 GA 版完全一致)
# ======================================================================
def parse_graph_csv(filepath="synthetic_dataset_combined.csv"):
    graphs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sample = f.read(1024); f.seek(0)
            delim = '\t' if '\t' in sample else ','
            reader = csv.DictReader(f, delimiter=delim)
            for row in reader:
                graphs.append({
                    'name': row['function_name'].strip(),
                    'n': int(row['num_nodes']),
                    's': int(row['source_node']),
                    't': int(row['sink_node']),
                    'CC': int(row['cfg_cc']), 
                    'E': list(set(map(tuple, ast.literal_eval(row['edges'].strip()))))
                })
    except Exception as e:
        print(f"FATAL ERROR: {e}"); sys.exit(1)
    print(f"Successfully loaded {len(graphs)} graphs.\n" + "-"*65)
    return graphs

# ======================================================================
# 2. 对照组算法：朴素路径 BFS 基路径求解器
# ======================================================================
def get_edge_vector(path, edge_idx, ne):
    v = np.zeros(ne, dtype=int)
    for i in range(len(path) - 1):
        e = (path[i], path[i+1])
        if e in edge_idx: v[edge_idx[e]] = 1
    return v

def naive_bfs_basis(nv, E, s, t, k, timeout=15):
    t0 = time.time()
    adj = defaultdict(list)
    for u, v in E: adj[u].append(v)
    edge_list = sorted(set(E))
    edge_idx = {e: i for i, e in enumerate(edge_list)}
    ne = len(edge_list)
    
    basis_paths, basis_mat = [], []
    
    # 队列中存储的是完整的路径列表
    q = deque([[s]])
    
    # 标准 BFS 路径空间搜索
    while q and len(basis_paths) < k and (time.time() - t0) < timeout:
        cp = q.popleft()
        curr = cp[-1]
        
        # 到达终点，触发线性独立性检查
        if curr == t:
            v = get_edge_vector(cp, edge_idx, ne)
            if len(basis_mat) == 0:
                basis_paths.append(cp)
                basis_mat.append(v)
            elif np.linalg.matrix_rank(basis_mat + [v]) > len(basis_mat):
                basis_paths.append(cp)
                basis_mat.append(v)
            continue
            
        # 朴素扩展：遍历邻居，避免单条路径内成环 (nxt not in cp)
        for nxt in adj[curr]:
            if nxt not in cp:
                q.append(cp + [nxt])
                
    return basis_paths, time.time() - t0

# ======================================================================
# 3. 批量评估器与全局总结面板 (统一采用路径覆盖率)
# ======================================================================
def main():
    graphs = parse_graph_csv()
    total, success, total_time = 0, 0, 0.0
    total_target_paths = 0
    total_found_paths = 0
    
    print(f"{'Function':<25} {'Target(CC)':<10} {'Found':<8} {'Time(s)':<8} {'Status':<10}")
    print("-" * 65)
    
    for g in graphs:
        total += 1
        target_cc = g['CC']
        total_target_paths += target_cc
        
        # 调用朴素 BFS 求解器
        paths, duration = naive_bfs_basis(g['n'], g['E'], g['s'], g['t'], target_cc)
        total_time += duration
        
        found_count = len(paths)
        total_found_paths += found_count
        
        is_ok = found_count >= target_cc
        if is_ok: success += 1
        print(f"{g['name'][:25]:<25} {target_cc:<10} {found_count:<8} {duration:<8.3f} {'SUCCESS' if is_ok else 'FAILED'}")
        
    print("-" * 65)
    print("GLOBAL SUMMARY PANEL (NAIVE BFS BASELINE)")
    print(f"Total Graphs          : {total}")
    print(f"Success Rate          : {success/total*100:.2f}% ({success}/{total})")
    print(f"Total Execution Time  : {total_time:.3f} s")
    
    path_coverage = (total_found_paths / total_target_paths * 100) if total_target_paths > 0 else 0.0
    print(f"Path Coverage         : {path_coverage:.2f}% ({total_found_paths}/{total_target_paths})")

if __name__ == "__main__":
    main()
