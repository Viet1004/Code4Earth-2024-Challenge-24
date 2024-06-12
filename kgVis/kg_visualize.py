import json
from pyvis.network import Network

file = "../assets/toy_kg_70b.json"


def get_data_from_file(kg_file):
    with open(kg_file, "r") as f:
        data = json.load(f)
        return data["nodes"]


def kg_visualise(data, name_color, label_color, edge_color, name_shape, lable_shape):
    g = Network(height="1500px", width="100%", bgcolor="#222222", font_color="white")
    for node in data:
        titre = ""
        for key, value in node["properties"].items():
            titre += f"{key} : {value}\n"
        name = node["name"]
        label = node["label"]
        g.add_node(name, color=name_color, shape=name_shape, title=titre)
        g.add_node(label, color=label_color, shape=lable_shape)
        g.add_edge(name, label, color=edge_color)
    g.barnes_hut(gravity=-5000, damping=1, spring_strength=1)
    g.show_buttons(filter_="physics")
    g.show("test.html", notebook=False)


kg_data = get_data_from_file(file)
name_color = "#03DAC6"
label_color = "#da03b3"
edge_color = "#018786"
name_shape = "circle"
lable_shape = "ellipse"

kg_visualise(kg_data, name_color, label_color, edge_color, name_shape, lable_shape)
