import streamlit as st

from pages.batch_triage import render_batch_triage


def main() -> None:
    st.set_page_config(
        page_title="Customer Support Agent",
        layout="wide",
    )

    st.title("🧠 Customer Support Agent")
    st.markdown("*Automated message triage and analysis*")
    render_batch_triage()


if __name__ == "__main__":
    main()

