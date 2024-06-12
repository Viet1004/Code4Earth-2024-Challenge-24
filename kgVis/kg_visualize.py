import json
import sys

from pyvis.network import Network

file = "../assets/toy_kg_cleaned.json"

def get_data_from_file(kg_file) :
    with open(kg_file, 'r') as f :
        data = json.load(f)
        nodes = data['nodes']
        edges = data['relationships']
        return (nodes, edges)

def kg_build_kg(nodes, edges, node_color, node_shape, edge_color, cluster_color, cluster_shape) :
    g = Network(height='1500px', width='100%', bgcolor='#222222', font_color='white', directed=True)
    kg_build_nodes(g, nodes, node_color, node_shape)
    kg_build_edges(g, edges, edge_color, cluster_color, cluster_shape)
    g.barnes_hut(gravity=-5000, damping=1, spring_strength=1)
    g.show_buttons(filter_='physics')
    g.show("test.html", notebook=False)

def kg_build_nodes(graph, nodes, node_color, node_shape) :
    for node in nodes :
        titre = f"label : {node['label']}\n"
        for key, value in node['properties'].items() :
            titre += f"{key} : {value}\n"
        name = node['name']
        graph.add_node(name, color=node_color, shape=node_shape, title=titre)

def kg_build_edges(graph, edges, edge_color, cluster_color, cluster_shape) :
    for edge in edges:
        start_name = edge['start']
        end_name = edge['end']
        if id_exist_in_kg(graph, start_name) and id_exist_in_kg(graph, end_name) :
            start = graph.get_node(edge['start'])
            end = graph.get_node(edge['end'])
            end['color'] = cluster_color
            end['shape'] = cluster_shape
            titre = ""
            for key, value in edge['properties'].items():
                titre += f"{key} : {value}\n"
            labl = edge['type']
            graph.add_edge(start['id'], end['id'], color=edge_color, title=titre, label=labl)

def id_exist_in_kg(graph, node_id) :
    return any(node == node_id for node in graph.get_nodes())

kg_data = get_data_from_file(file)
kg_nodes = kg_data[0]
kg_edges = kg_data[1]

if not kg_nodes:
    print("Node list empty !")
    sys.exit()
elif not kg_edges:
    print("Edge list empty !")
    sys.exit()
else:
    node_color = "#03DAC6"
    cluster_color = "#da03b3"
    edge_color = "#FFFF00"
    node_shape = "circle"
    cluster_shape = "ellipse"
    kg_build_kg(kg_nodes, kg_edges, node_color, node_shape, edge_color, cluster_color, cluster_shape)
