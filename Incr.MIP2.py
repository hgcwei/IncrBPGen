import sys
import ast
import time
import csv

try:
    import cplex
except ImportError:
    print("FATAL ERROR: CPLEX Python API is not installed.")
    print("Please run 'pip install cplex' in your terminal.")
    sys.exit("Dependency missing, program terminated.")

# ======================================================================
# 1. 表格数据解析器 (自动识别 Tab 分隔的 TSV 或 逗号分隔的 CSV)
# ======================================================================
def parse_graph_csv(filepath="60pycodeset_v2_annotated.csv"):
    """解析表格文件，提取节点数、起止点、边集及控制流图圈复杂度(cfg_cc)"""
    all_graphs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sample = f.read(4096)
            f.seek(0)
            delimiter = '\t' if '\t' in sample else ','
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            required_headers = ['function_name', 'num_nodes', 'source_node', 'sink_node', 'cfg_cc', 'edges']
            if not all(h in reader.fieldnames for h in required_headers):
                print(f"FATAL ERROR: CSV file is missing required columns. Expected: {required_headers}")
                sys.exit(1)

            for row_idx, row in enumerate(reader, 1):
                try:
                    graph_data = {
                        'name': row['function_name'].strip(),
                        'n': int(row['num_nodes']),
                        's': int(row['source_node']),
                        't': int(row['sink_node']),
                        'CC': int(row['cfg_cc']), 
                        'E': list(set(ast.literal_eval(row['edges'].strip()))) # 解析的同时完成去重
                    }
                    all_graphs.append(graph_data)
                except Exception as e:
                    print(f"Warning: Skipping row {row_idx} due to parsing error: {e}")
                    
    except FileNotFoundError:
        print(f"FATAL ERROR: The input file '{filepath}' was not found.")
        print(f"Please place the file in the same directory.")
        sys.exit(1)

    print(f"Successfully loaded {len(all_graphs)} graphs from '{filepath}'.")
    print("-" * 50 + "\n")
    return all_graphs


# ======================================================================
# 2. 核心批处理与增量求解主程序
# ======================================================================

PRIVATE_EDGE_PENALTY = 10.0
graphs_to_test = parse_graph_csv("large_scale_dataset_v3.csv")

total_graphs = len(graphs_to_test)
graphs_fully_solved = 0      
total_paths_required = 0     
total_paths_found = 0        
total_execution_time = 0     

print(f"CPLEX version: {cplex.__version__}")
print(f"Starting batch incremental solving for {total_graphs} graphs...\n")

for graph_idx, graph_info in enumerate(graphs_to_test, 1):
    name = graph_info['name']
    n = graph_info['n']
    s = graph_info['s']
    t = graph_info['t']
    E = graph_info['E']
    k = graph_info['CC']           
    
    total_paths_required += k
    print(f"[{graph_idx}/{total_graphs}] Processing Graph: {name} (nodes={n}, edges={len(E)}, target_paths={k})")
    
    graph_start_time = time.time()
    found_paths_this_graph = 0
    previously_used_edges = set()
    V = range(n)
    M = 10000  # 紧凑的大M常数，单流最大不超过 n-1

    # --- 增量式寻找当前图的 k 条路径 ---
    for i in range(1, k + 1):
        # 使用 try...finally 结构确保任何情况下 model.end() 都能执行
        model = cplex.Cplex()
        try:
            model.set_problem_name(f"{name}_path_{i}")
            
            # 关闭日志和结果输出
            model.set_log_stream(None)
            model.set_results_stream(None)
            model.set_warning_stream(None)
            model.set_error_stream(None)
            
            # 【性能优化】强制 CPLEX 使用单线程，消除多线程频繁创建/销毁的上下文开销
            model.parameters.threads.set(1)

            # 变量定义
            x_names = {(u, v): f'x_{u}_{v}' for u, v in E}
            model.variables.add(names=list(x_names.values()), types=[model.variables.type.integer] * len(E))

            use_edge_names = {(u, v): f'use_{u}_{v}' for u, v in E}
            model.variables.add(names=list(use_edge_names.values()), types=[model.variables.type.binary] * len(E))

            node_used_names = {v: f'node_used_{v}' for v in V}
            flow_names = {(u, v): f'flow_{u}_{v}' for u, v in E}
            model.variables.add(names=list(node_used_names.values()), types=[model.variables.type.binary] * len(V))
            model.variables.add(names=list(flow_names.values()), types=[model.variables.type.continuous] * len(E))

            # 目标函数
            model.objective.set_sense(model.objective.sense.minimize)
            path_length_objective = [(var_name, 1.0) for var_name in x_names.values()]
            
            private_edge_objective = []
            if i > 1:
                potential_private_edges = [e for e in E if e not in previously_used_edges]
                private_edge_vars = [use_edge_names[e] for e in potential_private_edges]
                private_edge_objective = [(var, PRIVATE_EDGE_PENALTY) for var in private_edge_vars]

            model.objective.set_linear(path_length_objective + private_edge_objective)

            # 构建约束集
            all_constraints = []
            def add_constraint(lin_expr, sense, rhs, c_name):
                all_constraints.append([lin_expr, sense, rhs, c_name])

            # a) 网络流守恒
            for v in V:
                out_edges = [x_names[u, w] for u, w in E if u == v]
                in_edges = [x_names[u, w] for u, w in E if w == v]
                rhs = 0
                if v == s: rhs = 1
                if v == t: rhs = -1
                if out_edges or in_edges:
                    add_constraint(
                        cplex.SparsePair(ind=out_edges + in_edges, val=[1.0] * len(out_edges) + [-1.0] * len(in_edges)),
                        'E', rhs, f"flow_{v}")

            # b) 建立整数流 x 与 激活边界 use_edge 的绑定
            for u, v in E:
                add_constraint(cplex.SparsePair(ind=[x_names[u, v], use_edge_names[u, v]], val=[1.0, -M]), 'L', 0.0, f"link_U_{u}_{v}")
                add_constraint(cplex.SparsePair(ind=[x_names[u, v], use_edge_names[u, v]], val=[1.0, -1.0]), 'G', 0.0, f"link_L_{u}_{v}")

            # c) 核心增量约束
            if i > 1:
                potential_private_edges = [use_edge_names[e] for e in E if e not in previously_used_edges]
                if not potential_private_edges:
                    break 
                add_constraint(cplex.SparsePair(ind=potential_private_edges, val=[1.0] * len(potential_private_edges)), 'G', 1.0, "require_private")

            # d) 单连通性破圈约束
            add_constraint(cplex.SparsePair([node_used_names[s]], [1.0]), 'E', 1.0, "s_used")
            for v in V:
                incident_edges = [use_edge_names[e] for e in E if v in e]
                if incident_edges:
                    add_constraint(cplex.SparsePair([node_used_names[v]] + incident_edges, [1.0] + [-1.0] * len(incident_edges)), 'L', 0.0, f"n_link_L_{v}")
                    add_constraint(cplex.SparsePair([node_used_names[v]] + incident_edges, [len(incident_edges)] + [-1.0] * len(incident_edges)), 'G', 0.0, f"n_link_U_{v}")
            
            source_out_flow = [flow_names[e] for e in E if e[0] == s]
            source_in_flow = [flow_names[e] for e in E if e[1] == s]
            demand_nodes = [node_used_names[v] for v in V if v != s]
            add_constraint(cplex.SparsePair(source_out_flow + source_in_flow + demand_nodes, [1.0] * len(source_out_flow) + [-1.0] * len(source_in_flow) + [-1.0] * len(demand_nodes)), 'E', 0.0, "aux_flow_s")
            
            for v in V:
                if v != s:
                    out_flow = [flow_names[e] for e in E if e[0] == v]
                    in_flow = [flow_names[e] for e in E if e[1] == v]
                    add_constraint(cplex.SparsePair(out_flow + in_flow + [node_used_names[v]], [1.0] * len(out_flow) + [-1.0] * len(in_flow) + [1.0]), 'E', 0.0, f"aux_flow_v_{v}")
            for e in E:
                add_constraint(cplex.SparsePair([flow_names[e], use_edge_names[e]], [1.0, -M]), 'L', 0.0, f"aux_cap_{e[0]}_{e[1]}")

            model.linear_constraints.add(lin_expr=[c[0] for c in all_constraints], senses=[c[1] for c in all_constraints], rhs=[c[2] for c in all_constraints], names=[c[3] for c in all_constraints])

            # 求解
            model.solve()
            status = model.solution.get_status()

            if status in [model.solution.status.optimal, model.solution.status.MIP_optimal]:
                sol_vals = {name: val for name, val in zip(model.variables.get_names(), model.solution.get_values())}
                current_edges = [e for e, name in use_edge_names.items() if sol_vals.get(name, 0.0) > 0.5]
                
                found_paths_this_graph += 1
                previously_used_edges.update(current_edges)
            else:
                break
        finally:
            # 【核心修复】显式调用 end() 释放 C 语言底层的全部内存与句柄资源
            model.end()

    graph_end_time = time.time()
    graph_duration = graph_end_time - graph_start_time
    
    total_execution_time += graph_duration
    total_paths_found += found_paths_this_graph
    if found_paths_this_graph == k:
        graphs_fully_solved += 1
        print(f"  > Result: SUCCESS. Found all {found_paths_this_graph}/{k} paths in {graph_duration:.2f}s.")
    else:
        print(f"  > Result: PARTIAL. Found {found_paths_this_graph}/{k} paths (Incomplete basis) in {graph_duration:.2f}s.")
    print("-" * 30)

# ======================================================================
# 3. 最终全局指标统计输出报告
# ======================================================================
print("\n" + "=" * 50)
print("BATCH SOLVER STATISTICAL REPORT (OPTIMIZED)")
print("=" * 50)

if total_graphs > 0 and total_paths_required > 0:
    success_rate = (graphs_fully_solved / total_graphs) * 100
    coverage_rate = (total_paths_found / total_paths_required) * 100
    avg_time = total_execution_time / total_graphs

    print(f"{'Total Graphs Evaluated':<28}: {total_graphs}")
    print(f"{'Fully Solved Graphs (100% CC)':<28}: {graphs_fully_solved}")
    print(f"{'Total Target Basis Paths':<28}: {total_paths_required}")
    print(f"{'Total Generated Paths':<28}: {total_paths_found}")
    print("-" * 50)
    print(f"{'Graph Success Rate':<28}: {success_rate:.2f}%")
    print(f"{'Basis Path Coverage Rate':<28}: {coverage_rate:.2f}%")
    print(f"{'Average Time Per Graph':<28}: {avg_time:.4f} seconds")
else:
    print("No analytical data available.")

print("=" * 50)
