import pandas as pd
import streamlit as st


def render_batch_table(results: list) -> None:
    if not results:
        st.info("No results to show yet.")
        return

    # Flatten nested triage data for tabular display
    rows = []
    for r in results:
        data = r.get("data") or {}
        rows.append({
            "review_id":      r.get("review_id"),
            "success":        r.get("success"),
            "message":        str(r.get("input_message", ""))[:80],
            "category":       data.get("category", "—"),
            "urgency":        data.get("urgency", "—"),
            "sentiment":      data.get("sentiment", "—"),
            "suggested_owner":data.get("suggested_owner", "—"),
            "confidence":     data.get("confidence", "—"),
            "abusive_flag":   data.get("abusive_flag", "—"),
            "error":          r.get("error") or "",
        })

    df = pd.DataFrame(rows)

    success_count = sum(1 for r in results if r.get("success"))
    st.subheader(f"Triage Results — {success_count}/{len(results)} processed")
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="triage_results.csv",
        mime="text/csv",
    )

    with st.expander("Full JSON Response"):
        st.json(results)
