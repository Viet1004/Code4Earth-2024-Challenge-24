import csv
from neo4j import GraphDatabase
import json
import dotenv
import os


def read_csv(file_path):
    with open(file_path, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        return [row for row in reader]


def create_nodes(tx, nodes):
    for node in nodes:
        name = node["name"]
        print(name)
        label = node["label"]
        properties = node["properties"]
        if properties:
            properties = json.loads(properties)
            tx.run(
                f"""CREATE (n:`{label}` {{name: "{name}", {', '.join([f'{k}: ${k}' for k in properties.keys()])}}})""",
                name=name,
                **properties,
            )
        else:
            properties = {}
            tx.run(f"""CREATE (n:`{label}` {{name: "{name}"}}) """, name=name)


def create_relationships(tx, relationships):
    for relationship in relationships:
        start = relationship["start"]
        end = relationship["end"]
        type = relationship["type"]
        properties = relationship["properties"]
        if properties:
            properties = json.loads(properties)
            tx.run(
                f"""
                MATCH (a {{name: $start}}), (b {{name: $end}})
                CREATE (a)-[r:`{type}` {{ {', '.join([f'{k}: ${k}' for k in properties.keys()])} }}]->(b)
            """,
                start=start,
                end=end,
                **properties,
            )

        else:
            tx.run(
                f"""
                MATCH (a {{name: $start}}), (b {{name: $end}})
                CREATE (a)-[r:`{type}`]->(b)
            """,
                start=start,
                end=end,
            )
            properties = {}


def upload_to_neo4j(uri, username, password, nodes_file, relationships_file):
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        nodes = read_csv(nodes_file)
        relationships = read_csv(relationships_file)

        with driver.session() as session:
            session.execute_write(create_nodes, nodes)
            session.execute_write(create_relationships, relationships)


if __name__ == "__main__":
    load_status = dotenv.load_dotenv("Neo4j-a71aea6b-Created-2024-06-09.txt")
    if load_status is False:
        raise RuntimeError("Environment variables not loaded.")

    URI = os.getenv("NEO4J_URI")
    AUTH = (os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))

    username = AUTH[0]
    password = AUTH[1]
    nodes_file = "nodes.csv"
    relationships_file = "relationships.csv"

    upload_to_neo4j(URI, username, password, nodes_file, relationships_file)
