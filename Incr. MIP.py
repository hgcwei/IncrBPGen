# ======================================================================
# INCREMENTAL VERSION - Solves for k paths one by one for higher efficiency
# ======================================================================

import cplex
import sys

print(f"CPLEX version: {cplex.__version__}")
print("-" * 30)

# ==== 1. Parameters ====
k = 9
n = 10
s = 0
t = 9

E = [
    (0, 1), (1, 2), (1, 3), (2, 9), (2, 1), (3, 4),
    (3, 5), (3, 8), (4, 3), (4, 9), (5, 7), (5, 6),
    (6, 3), (6, 9), (7, 5), (8, 3), (8, 9)
]
V = range(n)

# ==== 2. Incremental Solving Loop ====
found_paths = []
previously_used_edges = set()

print(f"Starting incremental search for {k} private paths...")

for i in range(1, k + 1):
    print(f"\n--- Solving for Path {i} ---")

    # --- 2.1 Model and Variable Setup for the CURRENT path ---
    model = cplex.Cplex()
    model.set_problem_name(f"Find_Path_{i}")
    model.set_log_stream(None)
    model.set_results_stream(None)

    # Binary variable: 1 if edge e is used in the current path, 0 otherwise
    use_edge_names = {(u, v): f'use_{u}_{v}' for u, v in E}
    model.variables.add(names=list(use_edge_names.values()), types=[model.variables.type.binary] * len(E))

    # --- 2.2 Single-Connectivity (Anti-Subtour) Variables ---
    node_used_names = {v: f'node_used_{v}' for v in V}
    flow_names = {(u, v): f'flow_{u}_{v}' for u, v in E}

    model.variables.add(names=list(node_used_names.values()), types=[model.variables.type.binary] * len(V))
    model.variables.add(names=list(flow_names.values()), types=[model.variables.type.continuous] * len(E))

    # --- 2.3 Objective Function: Minimize path length ---
    model.objective.set_sense(model.objective.sense.minimize)
    objective_pairs = [(var_name, 1.0) for var_name in use_edge_names.values()]
    model.objective.set_linear(objective_pairs)

    # --- 2.4 Constraints for the CURRENT path ---
    all_constraints = []


    def add_constraint(lin_expr, sense, rhs, name):
        all_constraints.append([lin_expr, sense, rhs, name])


    # a) Standard Path Flow Conservation
    for v in V:
        out_edges = [use_edge_names[u, w] for u, w in E if u == v]
        in_edges = [use_edge_names[u, w] for u, w in E if w == v]
        rhs = 0
        if v == s: rhs = 1
        if v == t: rhs = -1
        if out_edges or in_edges:
            add_constraint(
                cplex.SparsePair(ind=out_edges + in_edges, val=[1.0] * len(out_edges) + [-1.0] * len(in_edges)),
                'E', rhs, f"path_flow_{v}")

    # b) THE CORE LOGIC: Private Edge Constraint
    if i > 1:
        potential_private_edges = [use_edge_names[e] for e in E if e not in previously_used_edges]
        if not potential_private_edges:
            print(f"WARNING: No more available private edges. Cannot find path {i}.")
            break
        add_constraint(cplex.SparsePair(ind=potential_private_edges, val=[1.0] * len(potential_private_edges)),
                       'G', 1.0, "private_edge_requirement")

    # c) Connectivity Constraints
    add_constraint(cplex.SparsePair([node_used_names[s]], [1.0]), 'E', 1.0, "s_is_used")
    for v in V:
        incident_edges = [use_edge_names[e] for e in E if v in e]
        if incident_edges:
            add_constraint(
                cplex.SparsePair([node_used_names[v]] + incident_edges, [1.0] + [-1.0] * len(incident_edges)),
                'L', 0.0, f"node_use_link_L_{v}")
            add_constraint(cplex.SparsePair([node_used_names[v]] + incident_edges,
                                            [len(incident_edges)] + [-1.0] * len(incident_edges)),
                           'G', 0.0, f"node_use_link_U_{v}")

    source_out_flow = [flow_names[e] for e in E if e[0] == s]
    source_in_flow = [flow_names[e] for e in E if e[1] == s]
    demand_nodes = [node_used_names[v] for v in V if v != s]
    add_constraint(cplex.SparsePair(source_out_flow + source_in_flow + demand_nodes,
                                    [1.0] * len(source_out_flow) + [-1.0] * len(source_in_flow) + [-1.0] * len(
                                        demand_nodes)),
                   'E', 0.0, "aux_flow_source")

    for v in V:
        if v != s:
            out_flow = [flow_names[e] for e in E if e[0] == v]
            in_flow = [flow_names[e] for e in E if e[1] == v]
            add_constraint(cplex.SparsePair(out_flow + in_flow + [node_used_names[v]],
                                            [1.0] * len(out_flow) + [-1.0] * len(in_flow) + [1.0]),
                           'E', 0.0, f"aux_flow_demand_{v}")

    for e in E:
        add_constraint(cplex.SparsePair([flow_names[e], use_edge_names[e]], [1.0, -(n - 1)]),
                       'L', 0.0, f"flow_capacity_{e[0]}_{e[1]}")

    model.linear_constraints.add(lin_expr=[c[0] for c in all_constraints],
                                 senses=[c[1] for c in all_constraints],
                                 rhs=[c[2] for c in all_constraints],
                                 names=[c[3] for c in all_constraints])

    # --- 2.5 Solve and Process Results ---
    model.solve()
    solution = model.solution
    status_code = solution.get_status()

    if status_code in [solution.status.optimal, solution.status.MIP_optimal]:
        print(f"  > Path {i} found successfully.")
        solution_values = {name: val for name, val in zip(model.variables.get_names(), solution.get_values())}

        # Extract edges strictly
        current_path_edges = [e for e, name in use_edge_names.items() if solution_values.get(name, 0.0) > 0.5]

        private_edges_this_path = [e for e in current_path_edges if e not in previously_used_edges]

        found_paths.append({
            "id": i,
            "edges": current_path_edges,
            "private_edges": private_edges_this_path
        })
        previously_used_edges.update(current_path_edges)

    else:
        print(f"  > Could not find a valid path {i} (Status: {solution.get_status_string(status_code)}).")
        break

# ==== 3. Final Results Display (FIXED LOGIC) ====
print("\n" + "=" * 40)
print("INCREMENTAL SOLVE COMPLETED")
print("=" * 40)


# Helper function to reconstruct path using ALL edges (handling loops correctly)
def reconstruct_full_path(current_node, target_node, available_edges):
    # Base case: if no edges left and we are at target, we are done
    if not available_edges:
        if current_node == target_node:
            return []
        else:
            return None  # Stuck

    # Try all outgoing edges matching current_node
    candidates = [e for e in available_edges if e[0] == current_node]

    for edge in candidates:
        # Create new list without this edge (backtracking safe)
        next_edges = list(available_edges)
        next_edges.remove(edge)

        # Recurse
        res = reconstruct_full_path(edge[1], target_node, next_edges)
        if res is not None:
            return [edge] + res

    return None


if not found_paths:
    print("No paths were found.")
else:
    print(f"Found {len(found_paths)} paths out of the requested {k}:\n")
    for path_info in found_paths:
        path_edges = path_info["edges"]

        # Use the new recursive DFS function to arrange edges correctly
        ordered_edges = reconstruct_full_path(s, t, path_edges)

        if ordered_edges:
            # Construct the node sequence string
            node_seq = [s] + [e[1] for e in ordered_edges]
            path_str = " -> ".join(map(str, node_seq))
            path_len = len(ordered_edges)
        else:
            path_str = "Error reconstructing path (graph might be disconnected)"
            path_len = "N/A"

        print(f"Path {path_info['id']}:")
        print(f"  Route: {path_str}")
        print(f"  Len:   {path_len}")
        print(f"  Edges: {path_edges}")
        print(f"  Private Edge(s): {path_info['private_edges']}")
        print("-" * 25)
