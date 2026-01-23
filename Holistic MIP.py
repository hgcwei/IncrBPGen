# ======================================================================
# FINAL CORRECTED VERSION - Ensures X values for all private edges are shown
# ======================================================================

try:
    import cplex
    import sys
except ImportError:
    print("FATAL ERROR: CPLEX Python API is not installed.")
    print("Please run 'pip install cplex' in your terminal.")
    sys.exit("Dependency missing, program terminated.")

print(f"CPLEX version: {cplex.__version__}")
print("-" * 30)

# ==== 1. Parameters ====
k = 3
n = 10
s = 0
t = 9

E = [
    (0, 1), (1, 2), (1, 3), (2, 9), (2, 1), (3, 4),
    (3, 5), (3, 8), (4, 3), (4, 9), (5, 7), (5, 6),
    (6, 3), (6, 9), (7, 5), (8, 3), (8, 9)
]

V = range(n)
path_range = range(1, k + 1)
M = n
M_private = 1000

# ==== 2. Model and Variables ====
model = cplex.Cplex()
model.set_problem_name("MultiPathPrivateEdges")

# Variable Generation
x_names = {(i, e[0], e[1]): f'x_{i}_{e[0]}_{e[1]}' for i in path_range for e in E}
z_names = {(i, e[0], e[1]): f'z_{i}_{e[0]}_{e[1]}' for i in path_range for e in E}
use_edge_names = {(i, e[0], e[1]): f'use_{i}_{e[0]}_{e[1]}' for i in path_range for e in E}
is_node_used_names = {(i, v): f'node_used_{i}_{v}' for i in path_range for v in V}
flow_names = {(i, e[0], e[1]): f'flow_{i}_{e[0]}_{e[1]}' for i in path_range for e in E}

# Add Variables in Batches
model.variables.add(names=list(x_names.values()), types=[model.variables.type.integer] * len(x_names))
model.variables.add(names=list(z_names.values()), types=[model.variables.type.binary] * len(z_names))
model.variables.add(names=list(use_edge_names.values()), types=[model.variables.type.binary] * len(use_edge_names))
model.variables.add(names=list(is_node_used_names.values()), types=[model.variables.type.binary] * len(is_node_used_names))
model.variables.add(names=list(flow_names.values()), types=[model.variables.type.continuous] * len(flow_names))
print(f"Model created with {model.variables.get_num()} variables.")

# ==== 3. Objective Function ====
model.objective.set_sense(model.objective.sense.minimize)
objective_pairs = [(var_name, 1.0) for var_name in x_names.values()]
model.objective.set_linear(objective_pairs)

# ==== 4. Constraints ====
print("Building constraints...")
all_constraints = []
def add_constraint(lin_expr, sense, rhs, name):
    all_constraints.append([lin_expr, sense, rhs, name])

# Constraints logic (unchanged from your version)
for i in path_range:
    ind_s, val_s = ([x_names[i,e[0],e[1]] for e in E if e[0]==s], [1.0]*len([e for e in E if e[0]==s])); ind_s += ([x_names[i,e[0],e[1]] for e in E if e[1]==s], [-1.0]*len([e for e in E if e[1]==s]))[0]; val_s += [-1.0]*len([e for e in E if e[1]==s])
    add_constraint(cplex.SparsePair(ind=ind_s, val=val_s), 'E', 1.0, f"flow_s_{i}")
    ind_t, val_t = ([x_names[i,e[0],e[1]] for e in E if e[0]==t], [1.0]*len([e for e in E if e[0]==t])); ind_t += ([x_names[i,e[0],e[1]] for e in E if e[1]==t], [-1.0]*len([e for e in E if e[1]==t]))[0]; val_t += [-1.0]*len([e for e in E if e[1]==t])
    add_constraint(cplex.SparsePair(ind=ind_t, val=val_t), 'E', -1.0, f"flow_t_{i}")
    for v in V:
        if v not in [s, t]:
            ind_v, val_v = ([x_names[i,e[0],e[1]] for e in E if e[0]==v], [1.0]*len([e for e in E if e[0]==v])); ind_v += ([x_names[i,e[0],e[1]] for e in E if e[1]==v], [-1.0]*len([e for e in E if e[1]==v]))[0]; val_v += [-1.0]*len([e for e in E if e[1]==v])
            if ind_v: add_constraint(cplex.SparsePair(ind=ind_v, val=val_v), 'E', 0.0, f"flow_v_{i}_{v}")
    for e in E: add_constraint(cplex.SparsePair([x_names[i,e[0],e[1]], use_edge_names[i,e[0],e[1]]], [1.0, -M]), 'L', 0.0, f"link_x_use_U_{i}_{e[0]}_{e[1]}"); add_constraint(cplex.SparsePair([x_names[i,e[0],e[1]], use_edge_names[i,e[0],e[1]]], [1.0, -1.0]), 'G', 0.0, f"link_x_use_L_{i}_{e[0]}_{e[1]}")
    add_constraint(cplex.SparsePair([is_node_used_names[i,s]], [1.0]), 'E', 1.0, f"s_is_used_{i}")
    for v in V:
        if v!=s:
            uvars = [use_edge_names[i,e[0],e[1]] for e in E if v in e]; add_constraint(cplex.SparsePair(uvars+[is_node_used_names[i,v]], [1.0]*len(uvars)+[-M]), 'L', 0.0, f"link_unode_U_{i}_{v}"); add_constraint(cplex.SparsePair([is_node_used_names[i,v]]+uvars, [1.0]+[-1.0]*len(uvars)), 'L', 0.0, f"link_unode_L_{i}_{v}")
    f_ind_s, f_val_s = ([flow_names[i,e[0],e[1]] for e in E if e[0]==s], [1.0]*len([e for e in E if e[0]==s])); f_ind_s += ([flow_names[i,e[0],e[1]] for e in E if e[1]==s], [-1.0]*len([e for e in E if e[1]==s]))[0]; f_val_s += [-1.0]*len([e for e in E if e[1]==s])
    dem_vars = [is_node_used_names[i,v] for v in V if v!=s]; add_constraint(cplex.SparsePair(f_ind_s+dem_vars, f_val_s+[-1.0]*len(dem_vars)), 'E', 0.0, f"aux_flow_s_{i}")
    for v in V:
        if v!=s:
            f_ind_v, f_val_v = ([flow_names[i,e[0],e[1]] for e in E if e[0]==v], [1.0]*len([e for e in E if e[0]==v])); f_ind_v += ([flow_names[i,e[0],e[1]] for e in E if e[1]==v], [-1.0]*len([e for e in E if e[1]==v]))[0]; f_val_v += [-1.0]*len([e for e in E if e[1]==v])
            add_constraint(cplex.SparsePair(f_ind_v+[is_node_used_names[i,v]], f_val_v+[1.0]), 'E', 0.0, f"aux_flow_v_{i}_{v}")
    for e in E: add_constraint(cplex.SparsePair([flow_names[i,e[0],e[1]], use_edge_names[i,e[0],e[1]]], [1.0, -(n-1)]), 'L', 0.0, f"aux_flow_cap_{i}_{e[0]}_{e[1]}")
    add_constraint(cplex.SparsePair([z_names[i,e[0],e[1]] for e in E], [1.0]*len(E)), 'G', 1.0, f"private_exists_{i}")
    for e in E: add_constraint(cplex.SparsePair([z_names[i,e[0],e[1]], use_edge_names[i,e[0],e[1]]], [1.0, -1.0]), 'L', 0.0, f"z_implies_use_{i}_{e[0]}_{e[1]}")
for i in range(2, k+1):
    for e in E:
        p_use = [use_edge_names[j,e[0],e[1]] for j in range(1,i)]; add_constraint(cplex.SparsePair(p_use+[z_names[i,e[0],e[1]]], [1.0]*len(p_use)+[M_private]), 'L', M_private, f"private_def_{i}_{e[0]}_{e[1]}")
        p_z = [z_names[j,e[0],e[1]] for j in range(1,i)]; add_constraint(cplex.SparsePair([z_names[i,e[0],e[1]]]+p_z, [1.0]*(len(p_z)+1)), 'L', 1.0, f"z_is_unique_{i}_{e[0]}_{e[1]}")

model.linear_constraints.add(lin_expr=[c[0] for c in all_constraints], senses=[c[1] for c in all_constraints], rhs=[c[2] for c in all_constraints], names=[c[3] for c in all_constraints])
print(f"Model built with {model.linear_constraints.get_num()} constraints.")

# ==== 5. Solve and Display Results ====
print(f"\nSolving for k = {k} paths. This may take a moment...")
model.set_log_stream(None)
model.set_results_stream(None)
model.solve()
solution = model.solution

status_code = solution.get_status()
status_string = solution.get_status_string(status_code)

print("\n" + "="*30)
print(f"SOLVE COMPLETED. CPLEX STATUS: {status_code} ({status_string})")
print("="*30 + "\n")

if status_code in [solution.status.optimal, solution.status.MIP_optimal]:
    print(f"OPTIMAL SOLUTION FOUND! Objective value: {solution.get_objective_value():.2f}\n")
    solution_values = {name: val for name, val in zip(model.variables.get_names(), solution.get_values())}
    for i in path_range:
        path_edges_original = [e for e in E if solution_values.get(use_edge_names.get((i, *e)), 0.0) > 0.5]
        private_edges = [e for e in E if solution_values.get(z_names.get((i, *e)), 0.0) > 0.5]
        
        if path_edges_original:
            sorted_path, q = [], [s]
            path_edges_copy = path_edges_original[:] 
            
            while q:
                u = q.pop(0)
                for edge in list(path_edges_copy):
                    if edge[0] == u:
                        sorted_path.append(edge)
                        if edge[1] != t:
                             q.append(edge[1])
                        path_edges_copy.remove(edge)
                        break
            
            # --- START OF MODIFICATION ---
            # 1. Get x values for the edges in the sorted path
            x_values_for_path = {}
            for edge in sorted_path:
                var_name = x_names.get((i, *edge))
                if var_name:
                    value = solution_values.get(var_name, 0.0)
                    x_values_for_path[edge] = int(round(value))
            
            # 2. **NEW**: Also get x values for any private edges not already included
            for private_edge in private_edges:
                if private_edge not in x_values_for_path:
                    var_name = x_names.get((i, *private_edge))
                    if var_name:
                        value = solution_values.get(var_name, 0.0)
                        x_values_for_path[private_edge] = int(round(value))
            # --- END OF MODIFICATION ---
            
            path_str = " -> ".join(map(str, [s] + [e[1] for e in sorted_path]))
            print(f"Path {i}:")
            print(f"  Route: {path_str}")
            print(f"  Edges: {sorted_path}")
            print(f"  X Values: {x_values_for_path}")
            print(f"  Private Edge(s): {private_edges}")
            print("-" * 20)
else:
    print("NO OPTIMAL SOLUTION WAS FOUND.")
    print("This indicates the model is either Infeasible, Unbounded, or another issue occurred.")
    print(f"For this graph, if k is too large (e.g., k > 4), the model becomes INFEASIBLE.")
    print(f"Please double-check that you are running with a small k (current value: k={k}).")



