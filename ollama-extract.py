import fitz
import ollama
import tabula
import os
from tabula.io import read_pdf

# extract texts
doc = fitz.open("example.pdf")
for pageNumber, page in enumerate(doc.pages(), start=1):
    if pageNumber > 2 and pageNumber < 10:
        text = page.get_text().encode("utf8")
        with open(f"texts/output_{pageNumber}.txt", "wb") as out:
            out.write(text)  # write text of page
            out.write(bytes((12,)))  # write page delimiter (form feed 0x0C)

# extract tables
tables = read_pdf("example.pdf", pages="all")# read PDF file
os.makedirs('tables', exist_ok = True) 
for table_idx, table in enumerate(tables):
    table.to_csv(f"tables/output_{table_idx}.csv")


system_promt = "You are a helpful Natural Language Processing expert who extracts relevant information and store them on a Knowledge Graph. No yapping."

user_promt = """You are a data scientist working for a company that is building a graph database. Your task is to extract information from data and convert it into a graph database.
Provide a set of Nodes in the form [ENTITY_ID, TYPE, PROPERTIES] and a set of relationships in the form [ENTITY_ID_1, RELATIONSHIP, ENTITY_ID_2, PROPERTIES].
It is important that the ENTITY_ID_1 and ENTITY_ID_2 exists as nodes with a matching ENTITY_ID. If you can't pair a relationship with a pair of nodes don't add it.
When you find a node or relationship you want to add try to create a generic TYPE for it that  describes the entity you can also think of it as a label.
You will be given a list of types that you should try to use when creating the TYPE for a node. If you can't find a type that fits the node you can create a new one.
Return the final results in JSON without yapping.
"""

for page in range(3, 10):
    with open(f"texts/output_{page}.txt", "r", encoding="utf-8") as f:
        text = f.readlines()
        text = " ".join(text)
        text = text.replace("/n", "")
        stream = ollama.chat(
            model="llama3",
            messages=[
                {"role": "system", "content": system_promt + user_promt},
                {"role": "user", "content": text},
            ],
            stream=True,
        )
        # for chunk in stream:
        #     print(chunk["message"]["content"], end="", flush=True)
stream = ollama.chat(
    model="llama3",
    messages=[
        {"role": "user", "content": "Print all results you have found in JSON only."},
    ],
    stream=True,
)
for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)

