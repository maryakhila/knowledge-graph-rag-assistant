
import streamlit as st
from neo4j import GraphDatabase

st.set_page_config(
    page_title="Knowledge Graph RAG Assistant",
    page_icon="🕸️",
    layout="wide",
)

st.title("🕸️ Knowledge Graph-Powered RAG Assistant")
st.write("Store facts, connect entities, and retrieve information from your knowledge graph.")

with st.sidebar:
    st.header("Neo4j connection")
    uri = st.text_input("Neo4j URI", placeholder="neo4j+s://your-instance.databases.neo4j.io")
    username = st.text_input("Username", value="neo4j")
    password = st.text_input("Password", type="password")
    connect = st.button("Connect to Neo4j", type="primary")

if "neo4j_driver" not in st.session_state:
    st.session_state.neo4j_driver = None

if connect:
    if not uri or not username or not password:
        st.error("Enter your Neo4j URI, username, and password.")
    else:
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            driver.verify_connectivity()
            st.session_state.neo4j_driver = driver
            st.success("Connected to Neo4j!")
        except Exception as e:
            st.session_state.neo4j_driver = None
            st.error("Connection failed. Check your connection details.")
            st.caption(str(e))

driver = st.session_state.neo4j_driver

if driver:
    st.subheader("1. Add knowledge")
    st.caption("Enter a simple fact, such as: Ada Lovelace | CREATED | Algorithm")

    with st.form("add_fact"):
        subject = st.text_input("Entity A", placeholder="Ada Lovelace")
        relation = st.text_input("Relationship", placeholder="CREATED")
        obj = st.text_input("Entity B", placeholder="Algorithm")
        submitted = st.form_submit_button("Save relationship")

    if submitted:
        if not subject.strip() or not relation.strip() or not obj.strip():
            st.warning("Fill in all three fields.")
        else:
            rel = "".join(
                c for c in relation.strip().upper()
                if c.isalnum() or c == "_"
            )
            if not rel:
                st.warning("Enter a valid relationship name.")
            else:
                try:
                    with driver.session() as session:
                        session.run(
                            """
                            MERGE (a:Entity {name: $subject})
                            MERGE (b:Entity {name: $object})
                            MERGE (a)-[r:RELATED_TO {kind: $relation}]->(b)
                            """,
                            subject=subject.strip(),
                            object=obj.strip(),
                            relation=rel,
                        )
                    st.success("Relationship saved!")
                except Exception as e:
                    st.error("Could not save the relationship.")
                    st.caption(str(e))

    st.divider()
    st.subheader("2. Search your knowledge graph")
    question = st.text_input(
        "Search for an entity",
        placeholder="Ada Lovelace",
    )

    if st.button("Search graph"):
        if not question.strip():
            st.warning("Enter an entity name.")
        else:
            try:
                with driver.session() as session:
                    result = session.run(
                        """
                        MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
                        WHERE toLower(a.name) CONTAINS toLower($q)
                           OR toLower(b.name) CONTAINS toLower($q)
                        RETURN a.name AS subject, r.kind AS relation,
                               b.name AS object
                        LIMIT 50
                        """,
                        q=question.strip(),
                    )
                    facts = [record.data() for record in result]

                if facts:
                    st.dataframe(facts, use_container_width=True)
                    st.markdown("**Facts found:**")
                    for fact in facts:
                        st.write(
                            f"{fact['subject']} — {fact['relation']} → "
                            f"{fact['object']}"
                        )
                else:
                    st.info("No matching relationships found yet.")
            except Exception as e:
                st.error("Search failed.")
                st.caption(str(e))

    st.divider()
    st.subheader("3. View graph statistics")
    if st.button("Show statistics"):
        try:
            with driver.session() as session:
                record = session.run(
                    """
                    MATCH (n:Entity)
                    OPTIONAL MATCH ()-[r:RELATED_TO]->()
                    RETURN count(DISTINCT n) AS entities,
                           count(DISTINCT r) AS relationships
                    """
                ).single()
            st.metric("Entities", record["entities"])
            st.metric("Relationships", record["relationships"])
        except Exception as e:
            st.error("Could not load statistics.")
            st.caption(str(e))
else:
    st.info(
        "Connect to your Neo4j database using the sidebar to begin. "
        "Create a database at https://console.neo4j.io/ if you haven't yet."
    )
