"""BDU Student Union complaints dashboard — deploy this file on Streamlit Community Cloud."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from config import CAMPUSES, CATEGORIES, PRIORITIES, SHEET_NAME, STATUSES

st.set_page_config(
    page_title="BDU Student Union Dashboard",
    page_icon="🎓",
    layout="wide",
)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "Ticket ID",
            "Timestamp",
            "Campus",
            "Category",
            "Description",
            "Location",
            "Photo URL",
            "Anonymous",
            "Name",
            "Phone",
            "Department",
            "Status",
            "Priority",
            "Telegram User ID",
        ]
    )


@st.cache_data(ttl=30)
def load_from_google_sheets() -> pd.DataFrame:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes,
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["SHEET_ID"]).worksheet(SHEET_NAME)
    rows = sheet.get_all_records()
    if not rows:
        return _empty_frame()
    return pd.DataFrame(rows)


def load_data() -> tuple[pd.DataFrame, str]:
    if "gcp_service_account" in st.secrets and st.secrets.get("SHEET_ID"):
        try:
            return load_from_google_sheets(), "Google Sheets (live)"
        except Exception as exc:
            st.warning(f"Could not read Google Sheets ({exc}). Showing sample data.")
    sample = pd.read_csv("sample_complaints.csv")
    return sample, "sample_complaints.csv (demo)"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    for col in ["Campus", "Category", "Status", "Priority", "Ticket ID"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def save_status(ticket_id: str, status: str, priority: str) -> bool:
    if "gcp_service_account" not in st.secrets:
        return False
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=scopes,
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(st.secrets["SHEET_ID"]).worksheet(SHEET_NAME)
    cell = ws.find(ticket_id)
    if not cell:
        return False
    headers = ws.row_values(1)
    status_col = headers.index("Status") + 1
    priority_col = headers.index("Priority") + 1
    ws.update_cell(cell.row, status_col, status)
    ws.update_cell(cell.row, priority_col, priority)
    return True


st.title("🎓 Bahir Dar University Student Union")
st.caption("Data-driven complaint tracking for all campuses, including Fashion Technology (Selam) and Yibab.")

raw, source = load_data()
df = prepare(raw)

st.sidebar.header("Filters")
st.sidebar.write(f"**Data source:** {source}")
if st.sidebar.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()

campus_filter = st.sidebar.multiselect("Campus", CAMPUSES, default=CAMPUSES)
category_filter = st.sidebar.multiselect("Category", CATEGORIES, default=CATEGORIES)
status_filter = st.sidebar.multiselect("Status", STATUSES, default=STATUSES)

if df.empty:
    filtered = df
else:
    filtered = df[
        df["Campus"].isin(campus_filter)
        & df["Category"].isin(category_filter)
        & df["Status"].isin(status_filter)
    ]

c1, c2, c3, c4 = st.columns(4)
total = len(filtered)
resolved = int((filtered["Status"] == "Resolved").sum()) if not filtered.empty else 0
progress = int((filtered["Status"] == "In Progress").sum()) if not filtered.empty else 0
high = int((filtered["Priority"] == "High").sum()) if not filtered.empty else 0
c1.metric("Total complaints", total)
c2.metric("Resolved", resolved)
c3.metric("In progress", progress)
c4.metric("High priority", high)

tab_charts, tab_table, tab_action = st.tabs(["Charts", "Tickets", "Update ticket"])

with tab_charts:
    if filtered.empty:
        st.info("No complaints match the current filters.")
    else:
        left, right = st.columns(2)
        campus_counts = (
            filtered.groupby("Campus").size().reset_index(name="Complaints")
        )
        fig_bar = px.bar(
            campus_counts,
            x="Campus",
            y="Complaints",
            title="Complaints by campus",
            color="Campus",
        )
        fig_bar.update_layout(showlegend=False, xaxis_tickangle=-25)
        left.plotly_chart(fig_bar, use_container_width=True)

        cat_counts = filtered.groupby("Category").size().reset_index(name="Complaints")
        fig_pie = px.pie(
            cat_counts,
            names="Category",
            values="Complaints",
            title="Complaints by category",
            hole=0.4,
        )
        right.plotly_chart(fig_pie, use_container_width=True)

        trend = filtered.dropna(subset=["Timestamp"]).copy()
        if not trend.empty:
            trend["Date"] = trend["Timestamp"].dt.date
            daily = trend.groupby("Date").size().reset_index(name="Complaints")
            fig_line = px.line(
                daily,
                x="Date",
                y="Complaints",
                markers=True,
                title="Complaints over time",
            )
            st.plotly_chart(fig_line, use_container_width=True)

with tab_table:
    show_cols = [
        "Ticket ID",
        "Timestamp",
        "Campus",
        "Category",
        "Description",
        "Location",
        "Status",
        "Priority",
        "Anonymous",
    ]
    present = [c for c in show_cols if c in filtered.columns]
    st.dataframe(
        filtered[present].sort_values("Timestamp", ascending=False)
        if not filtered.empty and "Timestamp" in filtered.columns
        else filtered[present],
        use_container_width=True,
        hide_index=True,
    )

with tab_action:
    st.subheader("Change status (Google Sheets only)")
    st.write(
        "This writes back to the same sheet the Telegram bot uses. "
        "It will not work while the app is on sample CSV only."
    )
    if filtered.empty:
        st.info("No tickets to update.")
    else:
        ticket = st.selectbox("Ticket", filtered["Ticket ID"].tolist())
        row = filtered[filtered["Ticket ID"] == ticket].iloc[0]
        st.write(f"**Campus:** {row.get('Campus', '')}  |  **Category:** {row.get('Category', '')}")
        st.write(row.get("Description", ""))
        new_status = st.selectbox("New status", STATUSES, index=STATUSES.index(str(row.get("Status", "Open"))) if str(row.get("Status", "Open")) in STATUSES else 0)
        new_priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(str(row.get("Priority", "Medium"))) if str(row.get("Priority", "Medium")) in PRIORITIES else 1)
        if st.button("Save update"):
            if save_status(ticket, new_status, new_priority):
                st.cache_data.clear()
                st.success(f"Updated {ticket}")
                st.rerun()
            else:
                st.error("Update failed. Connect Google Sheets secrets on Streamlit Cloud to enable this.")

st.sidebar.markdown("---")
st.sidebar.caption(f"Last loaded {datetime.now().strftime('%Y-%m-%d %H:%M')}")
