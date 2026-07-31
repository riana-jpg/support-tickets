"""
Encounter Dashboard — Demo
Run with:  streamlit run encounter_dashboard.py

This is a self-contained demo. It generates realistic synthetic
encounter data on the fly (no external files or DB needed), so it
runs anywhere `streamlit` is installed.
"""

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Encounter Dashboard",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Synthetic data generation (cached so it's stable across reruns/filters)
# ---------------------------------------------------------------------------
@st.cache_data
def generate_encounters(n=2500, seed=42):
    rng = np.random.default_rng(seed)

    providers = [
        "Dr. A. Nguyen", "Dr. B. Alvarez", "Dr. C. Whitfield",
        "Dr. D. Osei", "NP E. Ramirez", "PA F. Chen",
    ]
    departments = ["Primary Care", "Behavioral Health", "Pediatrics", "Dental", "Urgent Care"]
    encounter_types = ["Office Visit", "Telehealth", "Mobile Clinic", "Follow-up", "Annual Wellness"]
    payers = ["Medicaid", "Medicare", "Commercial", "Self-Pay", "Sliding Scale"]
    statuses = ["Completed", "No-Show", "Cancelled", "Scheduled"]
    status_p = [0.78, 0.10, 0.07, 0.05]

    start = datetime.today() - timedelta(days=180)
    dates = [start + timedelta(days=int(d)) for d in rng.integers(0, 180, size=n)]

    df = pd.DataFrame({
        "encounter_id": [f"ENC-{100000+i}" for i in range(n)],
        "date": dates,
        "provider": rng.choice(providers, size=n, p=[0.22, 0.2, 0.18, 0.15, 0.15, 0.10]),
        "department": rng.choice(departments, size=n, p=[0.40, 0.15, 0.20, 0.10, 0.15]),
        "encounter_type": rng.choice(encounter_types, size=n, p=[0.45, 0.20, 0.15, 0.15, 0.05]),
        "payer": rng.choice(payers, size=n, p=[0.45, 0.20, 0.20, 0.10, 0.05]),
        "status": rng.choice(statuses, size=n, p=status_p),
        "patient_age": rng.integers(1, 90, size=n),
        "duration_min": rng.integers(10, 60, size=n),
        "charge_amount": np.round(rng.normal(180, 60, size=n).clip(40, 500), 2),
    })
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["weekday"] = df["date"].dt.day_name()
    return df


df = generate_encounters()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("🩺 Filters")
st.sidebar.caption("Demo data — synthetic, generated on load")

min_date, max_date = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

departments_sel = st.sidebar.multiselect(
    "Department", sorted(df["department"].unique()), default=sorted(df["department"].unique())
)
providers_sel = st.sidebar.multiselect(
    "Provider", sorted(df["provider"].unique()), default=sorted(df["provider"].unique())
)
status_sel = st.sidebar.multiselect(
    "Status", sorted(df["status"].unique()), default=sorted(df["status"].unique())
)
payer_sel = st.sidebar.multiselect(
    "Payer", sorted(df["payer"].unique()), default=sorted(df["payer"].unique())
)

mask = (
    (df["date"].dt.date >= start_date)
    & (df["date"].dt.date <= end_date)
    & (df["department"].isin(departments_sel))
    & (df["provider"].isin(providers_sel))
    & (df["status"].isin(status_sel))
    & (df["payer"].isin(payer_sel))
)
fdf = df[mask].copy()

st.sidebar.divider()
st.sidebar.metric("Rows in view", f"{len(fdf):,}")

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.title("Encounter Dashboard")
st.caption(f"Showing {start_date:%b %d, %Y} – {end_date:%b %d, %Y}  ·  demo / synthetic data")

completed = fdf[fdf["status"] == "Completed"]
no_show_rate = (fdf["status"] == "No-Show").mean() * 100 if len(fdf) else 0
cancel_rate = (fdf["status"] == "Cancelled").mean() * 100 if len(fdf) else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Encounters", f"{len(fdf):,}")
k2.metric("Completed", f"{len(completed):,}")
k3.metric("No-Show Rate", f"{no_show_rate:.1f}%")
k4.metric("Cancellation Rate", f"{cancel_rate:.1f}%")
k5.metric("Avg. Charge (Completed)", f"${completed['charge_amount'].mean():,.0f}" if len(completed) else "—")

st.divider()

# ---------------------------------------------------------------------------
# Charts row 1: volume over time + status mix
# ---------------------------------------------------------------------------
c1, c2 = st.columns((2, 1))

with c1:
    st.subheader("Encounter Volume Over Time")
    daily = fdf.groupby("date").size().reset_index(name="encounters")
    chart = (
        alt.Chart(daily)
        .mark_area(opacity=0.4, interpolate="monotone")
        .encode(x=alt.X("date:T", title=None), y=alt.Y("encounters:Q", title="Encounters"))
        + alt.Chart(daily)
        .mark_line(interpolate="monotone")
        .encode(x="date:T", y="encounters:Q")
    )
    st.altair_chart(chart, use_container_width=True)

with c2:
    st.subheader("Status Mix")
    status_counts = fdf["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    pie = (
        alt.Chart(status_counts)
        .mark_arc(innerRadius=60)
        .encode(theta="count:Q", color="status:N", tooltip=["status", "count"])
    )
    st.altair_chart(pie, use_container_width=True)

# ---------------------------------------------------------------------------
# Charts row 2: department + provider breakdown
# ---------------------------------------------------------------------------
c3, c4 = st.columns(2)

with c3:
    st.subheader("Encounters by Department")
    dept = fdf.groupby("department").size().reset_index(name="encounters").sort_values("encounters", ascending=True)
    bar = (
        alt.Chart(dept)
        .mark_bar()
        .encode(x="encounters:Q", y=alt.Y("department:N", sort="-x", title=None))
    )
    st.altair_chart(bar, use_container_width=True)

with c4:
    st.subheader("Encounters by Provider")
    prov = fdf.groupby("provider").size().reset_index(name="encounters").sort_values("encounters", ascending=True)
    bar2 = (
        alt.Chart(prov)
        .mark_bar()
        .encode(x="encounters:Q", y=alt.Y("provider:N", sort="-x", title=None))
    )
    st.altair_chart(bar2, use_container_width=True)

# ---------------------------------------------------------------------------
# Charts row 3: payer mix + weekday pattern
# ---------------------------------------------------------------------------
c5, c6 = st.columns(2)

with c5:
    st.subheader("Payer Mix")
    payer = fdf.groupby("payer").size().reset_index(name="encounters")
    bar3 = alt.Chart(payer).mark_bar().encode(
        x=alt.X("payer:N", sort="-y", title=None), y="encounters:Q"
    )
    st.altair_chart(bar3, use_container_width=True)

with c6:
    st.subheader("Encounters by Day of Week")
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd = fdf.groupby("weekday").size().reindex(order).fillna(0).reset_index()
    wd.columns = ["weekday", "encounters"]
    bar4 = alt.Chart(wd).mark_bar().encode(
        x=alt.X("weekday:N", sort=order, title=None), y="encounters:Q"
    )
    st.altair_chart(bar4, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Detail table
# ---------------------------------------------------------------------------
st.subheader("Encounter Detail")
st.dataframe(
    fdf.sort_values("date", ascending=False)[
        ["encounter_id", "date", "provider", "department", "encounter_type",
         "payer", "status", "patient_age", "duration_min", "charge_amount"]
    ],
    use_container_width=True,
    hide_index=True,
)

csv = fdf.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data as CSV", csv, "encounters_filtered.csv", "text/csv")
