import pandas as pd
import streamlit as st


def render_batch_table(results: list[dict]) -> None:
    if not results:
        st.info("No results to show yet.")
        return

    df = pd.DataFrame(results).astype(str)
    st.subheader("Triage Results")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Results CSV",
        data=csv,
        file_name="triage_results.csv",
        mime="text/csv",
    )
