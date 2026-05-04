"""Streamlit dashboard shell for football analytics data products."""

import streamlit as st


def main() -> None:
    """Render the dashboard scaffold."""

    st.set_page_config(page_title="Football Intelligence", layout="wide")
    st.title("Football Intelligence Platform")
    st.caption("Initial dashboard scaffold. Data-backed views will be added incrementally.")

    tabs = st.tabs(
        [
            "xG Trend",
            "Pass Types",
            "Shot Map",
            "Pressure Heatmap",
            "Market Values",
            "Squad Profile",
        ]
    )

    placeholders = [
        "xG trend over time",
        "pass type distribution",
        "shot map",
        "pressure heatmap",
        "player market value evolution",
        "squad age/value profile",
    ]

    for tab, placeholder in zip(tabs, placeholders, strict=True):
        with tab:
            st.info(f"Placeholder for {placeholder}.")


if __name__ == "__main__":
    main()
