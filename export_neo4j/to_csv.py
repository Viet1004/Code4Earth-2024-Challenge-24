import json
import csv

with open("toy_kg_70b.json", "r") as file:
    data = json.load(file)
    # Convert nodes to CSV
    with open("nodes.csv", "w", newline="") as nodes_file:
        fieldnames = ["name", "label", "properties"]
        writer = csv.DictWriter(nodes_file, fieldnames=fieldnames)

        writer.writeheader()
        for node in data["nodes"]:
            properties = node["properties"]
            if not properties:
                properties = None
            writer.writerow(
                {
                    "name": node["name"],
                    "label": node["label"],
                    "properties": json.dumps(properties) if properties else None,
                }
            )

    # Convert relationships to CSV
    with open("relationships.csv", "w", newline="") as relationships_file:
        fieldnames = ["start", "end", "type", "properties"]
        writer = csv.DictWriter(relationships_file, fieldnames=fieldnames)

        writer.writeheader()
        for relationship in data["relationships"]:
            properties = relationship["properties"]
            if not properties:
                properties = None
            writer.writerow(
                {
                    "start": relationship["start"],
                    "end": relationship["end"],
                    "type": relationship["type"],
                    "properties": json.dumps(properties) if properties else None,
                }
            )
