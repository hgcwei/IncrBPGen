import sys, ast, time, csv, random, numpy as np
from collections import defaultdict, deque

# ======================================================================
# 1. 表格数据解析器 (完全对齐基准版)
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
# 2. 核心算法：基于遗传/演化思想的基路径生成 (Ghiduk 改进版)
# ======================================================================
def get_edge_vector(path, edge_idx, ne):
    v = np.zeros(ne, dtype=int)
    for i in range(len(path) - 1):
        e = (path[i], path[i+1])
        if e in edge_idx: v[edge_idx[e]] = 1
    return v

def ghiduk_ga_v2(nv, E, s, t, k, timeout=15):
    t0 = time.time()
    adj = defaultdict(list)
    for u, v in E: adj[u].append(v)
    edge_list = sorted(set(E))
    edge_idx = {e: i for i, e in enumerate(edge_list)}
    ne = len(edge_list)
    
    basis_paths, basis_mat = [], []
    
    # 引导代：通过 BFS 注入第一条可行路径
    q = deque([[s]])
    while q:
        cp = q.popleft()
        if cp[-1] == t:
            basis_paths.append(cp)
            basis_mat.append(get_edge_vector(cp, edge_idx, ne))
            break
        for nxt in adj[cp[-1]]:
            if nxt not in cp: q.append(cp + [nxt])
            
    # 演化代：基于适应度/频率惩罚的随机游走迭代搜索
    attempts = 0
    while len(basis_paths) < k and (time.time() - t0) < timeout and attempts < 1000:
        attempts += 1
        p, cur = [s], s
        vc = defaultdict(int); vc[s] = 1
        for _ in range(nv * 3):
            if cur == t: break
            nbs = adj[cur]
            if not nbs: break
            # 演化权重：优先未访问节点，对环路节点施加倒数惩罚
            ws = [5.0 if n==t else (2.0 if vc[n]==0 else 0.1/vc[n]) for n in nbs]
            if sum(ws) == 0: break
            cur = random.choices(nbs, weights=ws, k=1)[0]
            p.append(cur); vc[cur] += 1
            
        if p[-1] == t:
            v = get_edge_vector(p, edge_idx, ne)
            # 线性独立性校验 (Rank 秩评估)
            if np.linalg.matrix_rank(basis_mat + [v]) > len(basis_mat):
                basis_paths.append(p)
                basis_mat.append(v)
                
    return basis_paths, time.time() - t0

# ======================================================================
# 3. 批量评估器与全局总结面板 (已修改为路径覆盖率逻辑)
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
        
        paths, duration = ghiduk_ga_v2(g['n'], g['E'], g['s'], g['t'], target_cc)
        total_time += duration
        
        found_count = len(paths)
        total_found_paths += found_count
        
        is_ok = found_count >= target_cc
        if is_ok: success += 1
        print(f"{g['name'][:25]:<25} {target_cc:<10} {found_count:<8} {duration:<8.3f} {'SUCCESS' if is_ok else 'FAILED'}")
        
    print("-" * 65)
    print("GLOBAL SUMMARY PANEL")
    print(f"Total Graphs          : {total}")
    print(f"Success Rate          : {success/total*100:.2f}% ({success}/{total})")
    print(f"Total Execution Time  : {total_time:.3f} s")
    
    # 计算精细化的路径覆盖率
    path_coverage = (total_found_paths / total_target_paths * 100) if total_target_paths > 0 else 0.0
    print(f"Path Coverage         : {path_coverage:.2f}% ({total_found_paths}/{total_target_paths})")

if __name__ == "__main__":
    main()