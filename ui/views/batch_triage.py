import pandas as pd
import streamlit as st

from components.batch_table import render_batch_table
from utils.api_client import post_triage_batch


def render_batch_triage() -> None:
    st.subheader("Submit Messages for Triage")

    col1, col2 = st.columns(2)

    messages_to_process = []
    input_type = "single"

    with col1:
        st.markdown("### Single Message")
        message = st.text_area(
            "Enter your message:",
            height=150,
            placeholder="Type your customer message here...",
            key="single_message",
        )
        if message.strip():
            messages_to_process = [message]
            input_type = "single"

    with col2:
        st.markdown("### Batch Upload")
        uploaded_file = st.file_uploader(
            "Upload CSV or Excel File",
            type=["csv", "xlsx"],
            key="batch_upload",
        )

        if uploaded_file:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
            else:
                df = pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)

            df = df.astype(str)

            st.subheader("Preview")
            st.dataframe(df.head(), use_container_width=True)

            if "message" not in df.columns:
                st.error("File must contain a column named 'message'")
            else:
                messages_to_process = df["message"].tolist()
                input_type = "batch"

    st.divider()

    col_send, col_info = st.columns([1, 3])

    with col_send:
        send_button = st.button("Send", key="send_button", use_container_width=True)

    with col_info:
        if input_type == "batch" and messages_to_process:
            st.info(f"📦 Ready to process {len(messages_to_process)} message(s)")
        elif input_type == "single" and messages_to_process:
            st.info("📝 Ready to process single message")

    if send_button and messages_to_process:
        messages_to_process = [str(m).strip() for m in messages_to_process if str(m).strip()]
        if not messages_to_process:
            st.error("No valid messages to process")
        else:
            with st.spinner("🔄 Processing messages..."):
                try:
                    results = post_triage_batch(messages_to_process)
                    render_batch_table(results)
                except Exception as ex:
                    st.error(f"Error: {str(ex)}")
    elif send_button:
        st.error("Please enter a message or upload a file")
