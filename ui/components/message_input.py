import streamlit as st


def render_message_input(default_text: str = "") -> str:
    return st.text_area("Customer Message", value=default_text, height=200)
