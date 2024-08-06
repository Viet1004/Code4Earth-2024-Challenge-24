import os
import time
import openai
import logging
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, HumanMessage

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Set up OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY,)

# Neo4j configuration
URI = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(user, password))

def run_neo4j_query(query, parameters=None):
    with driver.session() as session:
        result = session.run(query, parameters)
        return [record for record in result]

def encode_question(question):
    retry_attempts = 5
    for attempt in range(retry_attempts):
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=question
            )
            return response.data[0].embedding
        except client.RateLimitError as e:
            if attempt < retry_attempts - 1:
                st.write(f"Rate limit exceeded. Retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
            else:
                st.write("Failed to get embedding from OpenAI due to rate limit.")
                raise e

def get_response(user_query, contexts, chat_history):
    template = """
    You are a helpful assistant. Answer the following questions considering the history of the conversation:

    Chat history: {chat_history}

    Contexts: {contexts}

    User question: {user_question}
    """

    prompt = ChatPromptTemplate.from_template(template)
    llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)
    chain = LLMChain(prompt=prompt, llm=llm, output_parser=StrOutputParser())

    return chain.run(
        {
            "chat_history": chat_history,
            "contexts": contexts,
            "user_question": user_query,
        }
    )


def get_answer_neo4j(driver, question):
    contexts = []
    chunkIds = []

    # Encode question using OpenAI
    question_embedding = encode_question(question)

    # Generate and run the Cypher query
    query = """
    WITH $question_embedding AS question_embedding
    CALL db.index.vector.queryNodes(
        'chunk_content_embeddings',
        $top_k,
        question_embedding
    ) YIELD node AS chunk, score
    RETURN chunk.name, chunk.content, score
    """
    parameters = {
        'question_embedding': question_embedding,
        'top_k': 5  # Set the number of top results you want to retrieve
    }
    neo4j_result = run_neo4j_query(query, parameters)

    if neo4j_result:
        for record in neo4j_result:
            name = record["chunk.name"]
            score = record["score"]
            chunkIds.append(name)
            contexts.append(record["chunk.content"])
            print("Name:", name)
            print(score)
        return contexts, chunkIds, score
    else : 
        st.session_state.chat_history.append(AIMessage(content="No relevant results found in the database."))


def query_subgraph(driver, chunkIds):
    query = """
    WITH $chunkIds AS names
    MATCH (n)
    WHERE n.name IN names
    OPTIONAL MATCH (n)-[r]-(neighbor)
    RETURN
    {name: n.name, properties: apoc.map.fromLists(keys(n), [p in keys(n) | n[p]])} AS node,
    collect({
          neighbor: {name: neighbor.name, properties: apoc.map.fromLists(keys(neighbor), [p in keys(neighbor) | neighbor[p]])},
          relationship: {label: type(r), properties: apoc.map.fromLists(keys(r), [p in keys(r) | r[p]])}
  }) AS neighbors
    """

    records = []

    with driver.session() as session:
        for record in session.run(query, {"chunkIds": chunkIds}):
            records.append(record)
    return records


def process_subgraph_to_pyvis(subgraph):
    net = Network(height="750px", width="100%", notebook=True)
    for record in subgraph:
        node = record["node"]
        neighbors = record["neighbors"]
        node_id = node["name"]
        node_properties = node["properties"]
        net.add_node(node_id, label=node_id, title=str(node_properties), color="red")

        for neighbor_info in neighbors:
            neighbor = neighbor_info["neighbor"]
            relationship = neighbor_info["relationship"]

            if neighbor:
                neighbor_id = neighbor["name"]
                neighbor_properties = neighbor["properties"]
                net.add_node(
                    neighbor_id,
                    label=neighbor_id,
                    title=str(neighbor_properties),
                    color="blue",
                )

                if relationship:
                    relationship_label = relationship["label"]
                    relationship_properties = relationship["properties"]
                    net.add_edge(
                        node_id,
                        neighbor_id,
                        label=relationship_label,
                        title=str(relationship_properties),
                    )

    return net


def main():
    st.set_page_config(page_title="Study with me", page_icon=":books:", layout="wide")
    driver = GraphDatabase.driver(URI, auth=(user, password))
    col1, col2 = st.columns([10, 10], gap="small")

    if "count" not in st.session_state:
        st.session_state.count = 0

    with col1:
        st.subheader("Chat window")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                AIMessage(content="Hello, I am a bot. How can I help you?"),
            ]

        # conversation
        for message in st.session_state.chat_history:
            if isinstance(message, AIMessage):
                with st.chat_message("AI"):
                    st.write(message.content)
            elif isinstance(message, HumanMessage):
                with st.chat_message("Human"):
                    st.write(message.content)

        # user input
        user_query = st.chat_input("Type your message here...")

        if user_query is not None and user_query != "":
            st.session_state.count += 1
            contexts, chunkIds, score = get_answer_neo4j(driver, user_query)
            contexts_string = "\n".join(contexts)
            print(contexts)
            subgraph = query_subgraph(driver, chunkIds)
            net = process_subgraph_to_pyvis(subgraph)
            net.show(f"graphs/graph_{st.session_state.count}.html")

            st.session_state.chat_history.append(HumanMessage(content=user_query))

            with st.chat_message("Human"):
                st.markdown(user_query)

            with st.chat_message("AI"):
                response = get_response(
                        user_query, contexts_string, st.session_state.chat_history
                    )
                st.write(response)
            st.session_state.chat_history.append(AIMessage(content=response))
            # logging.info(st.session_state.chat_history)
    with col2:
        st.subheader("Visualization window")
        dir = "graphs/"
        html_files = [file for file in os.listdir(dir) if file.endswith(".html")]
        for file in html_files:
            with st.expander(file):
                HtmlFile = open(os.path.join(dir, file), "r", encoding="utf-8")
                source_code = HtmlFile.read()
                components.html(source_code, height=500, width=500)
    driver.close()


if __name__ == "__main__":
    main()