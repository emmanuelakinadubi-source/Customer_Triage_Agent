import pandas as pd
import streamlit as st

from components.batch_table import render_batch_table
from utils.api_client import APIError, post_triage_single, post_triage_batch


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
                try:
                    df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False, encoding="utf-8")
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False, encoding="latin1")
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
        if messages_to_process:
            count = len(messages_to_process)
            label = "single message" if input_type == "single" else f"{count} message(s)"
            st.info(f"Ready to process {label}")

    if send_button and messages_to_process:
        messages_to_process = [str(m).strip() for m in messages_to_process if str(m).strip()]
        if not messages_to_process:
            st.error("No valid messages to process")
        else:
            with st.spinner("Processing..."):
                try:
                    if input_type == "single":
                        result = post_triage_single(messages_to_process[0])
                        _render_single_result(result)
                    else:
                        results = post_triage_batch(messages_to_process)
                        render_batch_table(results)
                except APIError as ex:
                    _show_api_error(ex)
                except Exception as ex:
                    st.error(f"Unexpected error — please try again. ({ex})")

    elif send_button:
        st.error("Please enter a message or upload a file")


def _show_api_error(ex: APIError) -> None:
    code = ex.status_code
    detail = ex.detail or ""
    if code == 400:
        st.error(f"Invalid message: {detail}")
    elif code == 422 and "guardrail" in detail.lower():
        st.error(
            "This message was flagged by our content safety system. "
            "Please rephrase and try again."
        )
    elif code == 422:
        st.error(f"Message could not be processed: {detail}")
    elif code == 429:
        st.warning("Too many requests — please wait a moment before trying again.")
    elif code in (502, 503):
        st.error("The AI service is temporarily unavailable. Please try again shortly.")
    else:
        st.error(
            f"Something went wrong (error {code}). Please try again or contact support."
        )


def _render_single_result(result: dict) -> None:
    st.divider()
    st.subheader("Triage Result")

    if result.get("abusive_flag"):
        st.error("Abusive content detected — flagged for human review. No draft generated.")
    else:
        st.success("Analysis complete — result saved to database")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Category", result.get("category", "—"))
    c2.metric("Urgency", result.get("urgency", "—"))
    c3.metric("Sentiment", result.get("sentiment", "—"))
    c4.metric("Confidence", result.get("confidence", "—"))

    st.markdown(f"**Suggested Owner:** {result.get('suggested_owner', '—')}")
    st.markdown(f"**Urgency Reason:** {result.get('urgency_reason', '—')}")

    draft = result.get("draft_response")
    if draft and not result.get("abusive_flag"):
        st.markdown("**Draft Response:**")
        st.info(draft)

    with st.expander("Full JSON"):
        st.json(result)
