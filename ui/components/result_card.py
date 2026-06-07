import streamlit as st


def render_result_card(result: dict) -> None:
    if not result:
        return

    st.success("Analysis completed")
    st.json(result)
