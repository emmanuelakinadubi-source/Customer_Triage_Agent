import pandas as pd
import streamlit as st

from components.batch_table import render_batch_table
from utils.api_client import APIError, post_triage_single, post_triage_batch

MAX_CONTEXT_CHARS = 4_500
MAX_CONTEXT_TURNS = 4


def render_batch_triage() -> None:
    st.subheader("Customer Triage Chat")

    _render_chat_triage()

    st.divider()
    _render_batch_upload()


def _render_chat_triage() -> None:
    if "triage_chat_messages" not in st.session_state:
        st.session_state.triage_chat_messages = []

    col_title, col_clear = st.columns([4, 1])
    with col_title:
        st.caption("Send customer messages one after another. Recent turns are used as context.")
    with col_clear:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.triage_chat_messages = []
            st.rerun()

    if not st.session_state.triage_chat_messages:
        with st.chat_message("assistant"):
            st.markdown("Paste a customer message and I will classify it, route it, and draft a reply.")

    for item in st.session_state.triage_chat_messages:
        with st.chat_message(item["role"]):
            if item["role"] == "user":
                st.markdown(item["content"])
            elif item.get("type") == "error":
                st.error(item["content"])
            else:
                _render_chat_result(item["content"])

    prompt = st.chat_input("Type a customer message...")
    if not prompt:
        return

    message = prompt.strip()
    if not message:
        return

    st.session_state.triage_chat_messages.append(
        {"role": "user", "content": message}
    )

    with st.chat_message("user"):
        st.markdown(message)

    with st.chat_message("assistant"):
        with st.spinner("Triaging..."):
            try:
                api_message = _build_contextual_message(
                    current_message=message,
                    chat_messages=st.session_state.triage_chat_messages,
                )
                result = post_triage_single(api_message)
                _render_chat_result(result)
                st.session_state.triage_chat_messages.append(
                    {"role": "assistant", "content": result}
                )
            except APIError as ex:
                error_message = _format_api_error(ex)
                st.error(error_message)
                st.session_state.triage_chat_messages.append(
                    {"role": "assistant", "type": "error", "content": error_message}
                )
            except Exception as ex:
                error_message = f"Unexpected error — please try again. ({ex})"
                st.error(error_message)
                st.session_state.triage_chat_messages.append(
                    {"role": "assistant", "type": "error", "content": error_message}
                )


def _render_batch_upload() -> None:
    st.subheader("Batch Upload")

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel File",
        type=["csv", "xlsx"],
        key="batch_upload",
    )

    if not uploaded_file:
        return

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
        return

    messages_to_process = df["message"].tolist()
    count = len(messages_to_process)

    col_send, col_info = st.columns([1, 3])
    with col_send:
        send_button = st.button("Send batch", key="send_batch_button", use_container_width=True)
    with col_info:
        st.info(f"Ready to process {count} message(s)")

    if not send_button:
        return

    messages_to_process = [str(m).strip() for m in messages_to_process if str(m).strip()]
    if not messages_to_process:
        st.error("No valid messages to process")
        return

    with st.spinner("Processing batch..."):
        try:
            results = post_triage_batch(messages_to_process)
            render_batch_table(results)
        except APIError as ex:
            _show_api_error(ex)
        except Exception as ex:
            st.error(f"Unexpected error — please try again. ({ex})")


def _build_contextual_message(current_message: str, chat_messages: list[dict]) -> str:
    context_items = []
    prior_messages = chat_messages[:-1]

    for item in prior_messages[-(MAX_CONTEXT_TURNS * 2):]:
        if item["role"] == "user":
            context_items.append(f"Customer: {item['content']}")
        elif item.get("type") == "error":
            continue
        else:
            result = item.get("content", {})
            if isinstance(result, dict):
                draft = result.get("draft_response") or ""
                category = result.get("category") or "Unknown"
                owner = result.get("suggested_owner") or "Unknown"
                if draft:
                    context_items.append(
                        f"Assistant draft ({category}, {owner}): {draft}"
                    )

    if not context_items:
        return current_message

    context = "\n".join(context_items)
    combined = f"""Conversation context for reference only:
\"\"\"
{context}
\"\"\"

Latest customer message to triage:
\"\"\"
{current_message}
\"\"\"
"""
    if len(combined) <= MAX_CONTEXT_CHARS:
        return combined

    return combined[-MAX_CONTEXT_CHARS:]


def _render_chat_result(result: dict) -> None:
    if result.get("abusive_flag"):
        st.error("Abusive content detected — flagged for human review. No draft generated.")
    else:
        st.success("Analysis complete — result saved to database")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Category", result.get("category", "-"))
    c2.metric("Urgency", result.get("urgency", "-"))
    c3.metric("Sentiment", result.get("sentiment", "-"))
    c4.metric("Confidence", result.get("confidence", "-"))

    st.markdown(f"**Suggested Owner:** {result.get('suggested_owner', '-')}")
    st.markdown(f"**Urgency Reason:** {result.get('urgency_reason', '-')}")

    draft = result.get("draft_response")
    if draft and not result.get("abusive_flag"):
        st.markdown("**Draft Response:**")
        st.info(draft)

    with st.expander("Full JSON"):
        st.json(result)


def _format_api_error(ex: APIError) -> str:
    code = ex.status_code
    detail = ex.detail or ""
    if code == 400:
        return f"Invalid message: {detail}"
    if code == 422 and "guardrail" in detail.lower():
        return f"The response did not pass validation: {detail}"
    if code == 422:
        return f"Message could not be processed: {detail}"
    if code == 429:
        return "Too many requests — please wait a moment before trying again."
    if code in (502, 503):
        return "The AI service is temporarily unavailable. Please try again shortly."
    return f"Something went wrong (error {code}). Please try again or contact support."


def _show_api_error(ex: APIError) -> None:
    st.error(_format_api_error(ex))


def _render_single_result(result: dict) -> None:
    _render_chat_result(result)
