import streamlit as st
from main import process_census_query
import logging

# Configuration of the page
st.set_page_config(page_title="US Census AI Agent", layout="centered")

st.title("US Census AI Agent")
st.caption(
    "Ask questions about US Census data — population, income, housing, education, and more."
)

# Session state to hold chat history and conversation context
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Render chat messages and any associated SQL or results
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sql"):
            with st.expander("View SQL"):
                st.code(msg["sql"], language="sql")
        if msg.get("results") is not None:
            with st.expander("View Data"):
                st.dataframe(msg["results"], use_container_width=True)

# Chat input for user queries
if prompt := st.chat_input(
    "Ask a question about US Census data...\nFor example: 'What is the population of California in 2020?'"
):

    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run agent
    with st.chat_message("assistant"):
        with st.spinner("Querying census data..."):
            response = process_census_query(
                prompt, conversation_history=st.session_state.conversation_history
            )

        if response["error"]:
            logging.error(
                f"[Census Agent] Query failed: {response['error']}"
            )  # log real error
            message = "Something went wrong with your query. Please try again."
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"{message}",
                    "sql": response.get("sql"),
                    "results": None,
                }
            )

        elif response["answer"] != "success":
            # Guardrail hit or no-data message
            st.markdown(response["answer"])
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response["answer"],
                    "sql": None,
                    "results": None,
                }
            )

        else:
            results = response["results"]
            sql = response["sql"]
            row_count = len(results)
            summary = f"Found {row_count} row{'s' if row_count > 1 else ''} of data."

            st.markdown(summary)
            st.dataframe(results, use_container_width=True)
            with st.expander("View SQL"):
                st.code(sql, language="sql")

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": summary,
                    "sql": sql,
                    "results": results,
                }
            )
