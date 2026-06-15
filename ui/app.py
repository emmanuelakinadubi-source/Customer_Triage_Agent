import pandas as pd
import streamlit as st
from pathlib import Path

from components.triage_form import render_batch_triage
from utils.api_client import APIError, get_triage_history

RAGAS_RESULTS_PATH = Path("evals/experiments/policy_rag_ragas.csv")

def render_history_tab() -> None:
    st.subheader("Triage History")
    st.caption("Records are saved automatically after each triage call.")

    col_limit, col_btn = st.columns([2, 1])
    with col_limit:
        limit = st.slider("Records to load", min_value=10, max_value=200, value=50, step=10)
    with col_btn:
        st.write("")  # vertical alignment spacer
        refresh = st.button("Load / Refresh", use_container_width=True)

    if refresh:
        try:
            records = get_triage_history(limit)
        except APIError as exc:
            if exc.status_code in (502, 503):
                st.error("The AI service is temporarily unavailable. Please try again shortly.")
            else:
                st.error(f"Could not load history (error {exc.status_code}): {exc.detail}")
            return
        except Exception as exc:
            st.error(f"Could not reach the API — check that the backend is running. ({exc})")
            return

        if not records:
            st.info("No triage records found yet. Submit a message to get started.")
            return

        df = pd.DataFrame(records)

        # Summary metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Records", len(df))
        if "abusive_flag" in df.columns:
            m2.metric("Abusive Flagged", int(df["abusive_flag"].sum()))
        if "guardrail_passed" in df.columns:
            m3.metric("Guardrail Passed", int(df["guardrail_passed"].sum()))

        st.divider()

        # Display table (drop verbose columns)
        display_cols = [
            "id", "created_at", "category", "urgency", "sentiment",
            "suggested_owner", "confidence", "abusive_flag", "guardrail_passed",
        ]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True)

        # Full message viewer
        if "id" in df.columns and "message" in df.columns:
            with st.expander("View full messages"):
                for _, row in df[["id", "message", "draft_response"]].iterrows():
                    st.markdown(f"**[{row['id']}]** {row['message']}")
                    if row.get("draft_response"):
                        st.info(row["draft_response"])
                    st.divider()

        # Download
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download History CSV",
            data=csv_bytes,
            file_name="triage_history.csv",
            mime="text/csv",
        )


def render_ragas_tab() -> None:
    st.subheader("Ragas Evaluation")
    st.caption("Latest saved Ragas scores for the policy RAG evaluation dataset.")

    if not RAGAS_RESULTS_PATH.exists():
        st.info(
            "No Ragas results found yet. Run the evaluation from VS Code PowerShell, "
            "then refresh this tab."
        )
        st.code(
            "docker run --rm -v C:\\My_projects\\customerReviews:/workspace "
            "-w /workspace customerreviews-api python scripts/evaluate_ragas.py",
            language="powershell",
        )
        return

    df = pd.read_csv(RAGAS_RESULTS_PATH)
    metric_cols = [
        "faithfulness",
        "answer_relevancy",
        "llm_context_precision_with_reference",
        "context_recall",
    ]
    available_metrics = [col for col in metric_cols if col in df.columns]

    if available_metrics:
        metric_labels = {
            "faithfulness": "Faithfulness",
            "answer_relevancy": "Relevancy",
            "llm_context_precision_with_reference": "Context Precision",
            "context_recall": "Context Recall",
        }
        cols = st.columns(len(available_metrics))
        for col, metric in zip(cols, available_metrics):
            value = pd.to_numeric(df[metric], errors="coerce").mean()
            display_value = "N/A" if pd.isna(value) else f"{value:.3f}"
            col.metric(metric_labels.get(metric, metric), display_value)

    st.divider()
    st.dataframe(df, use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Ragas CSV",
        data=csv_bytes,
        file_name="policy_rag_ragas.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(
        page_title="Customer Support Triage Agent",
        page_icon="🧠",
        layout="wide",
    )

    with st.sidebar:
        st.title("Triage Agent")
        st.divider()
        st.markdown("### External Tools")
        st.link_button("API Docs (Swagger)", "http://localhost:8000/docs")
        st.divider()
        st.caption("Re-engineered by Syed, Madhavi & Harshasree")

    st.title("🧠 Customer Support Triage Agent")
    st.markdown("*Automated classification, routing, and draft response — saved to database*")

    tab_triage, tab_history, tab_ragas = st.tabs(["Triage", "History", "Ragas"])

    with tab_triage:
        render_batch_triage()

    with tab_history:
        render_history_tab()

    with tab_ragas:
        render_ragas_tab()


if __name__ == "__main__":
    main()
