import streamlit as st
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import logging
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components


logging.basicConfig(level=logging.INFO)


_ = load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
URI = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")
password = os.getenv("NEO4J_PASSWORD")


def get_response(user_query, contexts, chat_history):
    template = """
    You are a helpful assistant. Answer the following questions considering the history of the conversation:

    Chat history: {chat_history}

    Contexts: {contexts}

    User question: {user_question}
    """

    prompt = ChatPromptTemplate.from_template(template)

    llm = ChatOpenAI()

    chain = prompt | llm | StrOutputParser()

    return chain.stream(
        {
            "chat_history": chat_history,
            "contexts": contexts,
            "user_question": user_query,
        }
    )


def get_answer_neo4j(driver, question):
    contexts = []
    chunkIds = []
    with driver.session() as session:
        query = """
                WITH genai.vector.encode(
                    $question,
                    "OpenAI",
                    {
                    token: $openAiApiKey
                    }) AS question_embedding
                CALL db.index.vector.queryNodes(
                    'chunk_content_embeddings',
                    $top_k,
                    question_embedding
                    ) YIELD node AS chunk, score
                RETURN chunk.name, chunk.content, score
            """

        result = session.run(
            query, {"question": question, "openAiApiKey": OPENAI_API_KEY, "top_k": 5}
        )
        for record in result:
            name = record["chunk.name"]
            score = record["score"]
            chunkIds.append(name)
            contexts.append(record["chunk.content"])
            print("Name:", name)
            print(score)

    return contexts, chunkIds, score


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
    col1, col2, col3 = st.columns([3, 2, 5], gap="small")  # Adjusted column widths

    if "count" not in st.session_state:
        st.session_state.count = 0
    
    graph_path = "./graphs"
    if not os.path.exists(graph_path):
    # Create the directory
        os.makedirs(graph_path)

    # Left Column: Chat Window
    with col1:
        st.subheader("Chat window")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = [
                AIMessage(content="Hello, I am a bot. How can I help you?"),
            ]

        # Display conversation
        for message in st.session_state.chat_history:
            if isinstance(message, AIMessage):
                with st.chat_message("AI"):
                    st.write(message.content)
            elif isinstance(message, HumanMessage):
                with st.chat_message("Human"):
                    st.write(message.content)

        # User input
        user_query = st.chat_input("Type your message here...")

        if user_query is not None and user_query != "":
            st.session_state.count += 1
            contexts, chunkIds, score = get_answer_neo4j(driver, user_query)
            contexts_string = "\n".join(contexts)
            print(contexts)
            subgraph = query_subgraph(driver, chunkIds)
            net = process_subgraph_to_pyvis(subgraph)
            html_file_path = f"graphs/graph_{st.session_state.count}.html"
            net.save_graph(html_file_path)

            st.session_state.chat_history.append(HumanMessage(content=user_query))

            with st.chat_message("Human"):
                st.markdown(user_query)

            with st.chat_message("AI"):
                response = st.write_stream(
                    get_response(
                        user_query, contexts_string, st.session_state.chat_history
                    )
                )
            st.session_state.chat_history.append(AIMessage(content=response))
            # logging.info(st.session_state.chat_history)

    # Middle Column: List of HTML Files
    with col2:
        st.subheader("Graph History")
        dir = "graphs/"
        html_files = [file for file in os.listdir(dir) if file.endswith(".html")]
        if "selected_html" not in st.session_state:
            st.session_state.selected_html = None

        for file in html_files:
            if st.button(file):
                st.session_state.selected_html = file

    # Right Column: Graph Visualization and Node Information
    with col3:
        st.subheader("Graph Visualization")

        if st.session_state.selected_html:
            file_path = os.path.join(dir, st.session_state.selected_html)
            
            # Top Row: Interactive Graph Visualization
            with st.container():
                # st.subheader("Interactive Graph")
                
                # add JavaScript to index.html for makING the graph interactive 
                with open(file_path, "r", encoding="utf-8") as file:
                    graph_content = file.read()

                # Inject JavaScript for click detection
                script = """
                <script>
                // ----------------------------------------------------
                // Just copy/paste these functions as-is:

                function sendMessageToStreamlitClient(type, data) {
                    var outData = Object.assign({
                    isStreamlitMessage: true,
                    type: type,
                    }, data);
                    window.parent.postMessage(outData, "*");
                }

                function init() {
                    sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1});
                }

                function setFrameHeight(height) {
                    sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height});
                }

                // The `data` argument can be any JSON-serializable value.
                function sendDataToPython(data) {
                    sendMessageToStreamlitClient("streamlit:setComponentValue", data);
                }

                // -------------- Receive info from Graph -----------------------

                function onClick(event) {
                        const nodeId = event.nodes[0];
                        if (nodeId) {
                        var clickedNode = allNodes[nodeId]
                            
                            sendDataToPython({
                            value: clickedNode,
                            dataType: "json",
                            });
                        }
                    }

                    network.on('click', onClick);

                // ----------------------------------------------------
                // Now modify this part of the code to fit your needs:

                // Hook things up!
                init();

                // Hack to autoset the iframe height.
                // window.addEventListener("load", function() {
                //     window.setTimeout(function() {
                //     setFrameHeight(document.documentElement.clientHeight)
                //     }, 0);
                // });

                // Optionally, if the automatic height computation fails you, give this component a height manually
                // by commenting out below:
                setFrameHeight(500);
                </script>

                """
                index_content = graph_content + script

                # copy from graph_1 to ./index.html
                index_path = "./index.html"
                with open(index_path, "w", encoding="utf-8") as file:
                    file.write(index_content)

                # Create a new component which read from ./index.html
                mycomponent = components.declare_component(
                    name=os.path.basename(file_path),
                    path=".",
                )
                node_info = mycomponent()

            # Bottom Row: Node Information
            with st.container():
                st.subheader("Node Information")
                # st.write(node_info)
                if node_info is not None:
                    information = eval(node_info['title'])
                    information.pop('contentEmbedding', None)
                    st.write(information)

    driver.close()


if __name__ == "__main__":
    main()
