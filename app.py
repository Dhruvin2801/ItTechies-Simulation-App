import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="ItTechies Supply Chain Sim", layout="wide", page_icon="⚙️")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Reads the data sheet from your uploaded Excel file
    # Note: Ensure the file is in the same GitHub repo folder
    file_path = "ItTechies_285Centers_6Graphs_Simulation.xlsx"
    df = pd.read_excel(file_path, sheet_name="Simulation_Data")
    return df

df_base = load_data()

# --- SIDEBAR: INTERACTIVE CONTROLS ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3061/3061341.png", width=50) # Generic supply chain icon
st.sidebar.title("Simulation Controls")
st.sidebar.markdown("Adjust base buffer levels to simulate impact on the 285-center network.")

buffer_A = st.sidebar.slider("Class A Buffer Size", min_value=0, max_value=10, value=4, step=1)
buffer_B = st.sidebar.slider("Class B Buffer Size", min_value=0, max_value=10, value=2, step=1)
buffer_C = st.sidebar.slider("Class C Buffer Size", min_value=0, max_value=10, value=0, step=1)

# --- SIMULATION ENGINE (Live Recalculation) ---
# We recalculate the target columns dynamically based on sidebar inputs!
df = df_base.copy()

# 1. Map Base Buffers
buffer_map = {'A': buffer_A, 'B': buffer_B, 'C': buffer_C}
df['Live_Base_Buffer'] = df['ABC_Class'].map(buffer_map)

# 2. Seasonality Trigger (+2 units for May/Jun Batteries & Aug Displays)
condition_battery = (df['Category'] == 'Battery') & (df['Month'].isin([5, 6]))
condition_display = (df['Category'] == 'Display') & (df['Month'] == 8)
df['Season_Trigger'] = np.where(condition_battery | condition_display, 2, 0)

# 3. Final Proposed Buffer
df['Live_Proposed_Buffer'] = df['Live_Base_Buffer'] + df['Season_Trigger']

# 4. Turnaround Time (TAT) Logic
df['Live_Proposed_TAT'] = np.where(df['Qty'] <= df['Live_Proposed_Buffer'], 0.1, df['Stochastic_Lead_Time'])

# 5. Financials
df['Total_Value'] = df['Qty'] * df['Unit_Cost']
df['Lost_Rev_Current'] = np.where(df['Stochastic_Lead_Time'] > 3, 0.15 * df['Total_Value'], 0)
df['Lost_Rev_Proposed'] = np.where(df['Live_Proposed_TAT'] > 3, 0.15 * df['Total_Value'], 0)
df['Net_Rev_Saved'] = df['Lost_Rev_Current'] - df['Lost_Rev_Proposed']
df['Express_Upside'] = np.where(df['Live_Proposed_TAT'] <= 0.1, 200 * df['Qty'], 0)

# --- DASHBOARD UI ---
st.title("📊 ItTechies: 100k-Row Stochastic Inventory Simulation")
st.markdown("Comparing a Reactive Pull System vs. a Proactive Consignment Push System.")

# TOP ROW: KPI METRICS
st.subheader("System Performance KPIs")
col1, col2, col3, col4 = st.columns(4)

current_tat = df['Stochastic_Lead_Time'].mean()
proposed_tat = df['Live_Proposed_TAT'].mean()
tat_delta = proposed_tat - current_tat

total_rev_saved = df['Net_Rev_Saved'].sum()
total_express = df['Express_Upside'].sum()

col1.metric("Current Avg TAT", f"{current_tat:.2f} Days")
col2.metric("Proposed Avg TAT", f"{proposed_tat:.2f} Days", f"{tat_delta:.2f} Days", delta_color="inverse")
col3.metric("Net Revenue Saved", f"₹{total_rev_saved:,.0f}")
col4.metric("New Express Upside", f"₹{total_express:,.0f}")

st.divider()

# MIDDLE ROW: GRAPHS
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Wait Time Shift")
    # Categorize wait times
    def categorize(tat):
        if tat <= 0.1: return "Instant (<1 Day)"
        elif tat <= 3: return "Standard (1-3 Days)"
        else: return "Delayed (>3 Days)"
    
    df['Current_Cat'] = df['Stochastic_Lead_Time'].apply(categorize)
    df['Proposed_Cat'] = df['Live_Proposed_TAT'].apply(categorize)
    
    current_counts = df['Current_Cat'].value_counts().rename("Current System")
    proposed_counts = df['Proposed_Cat'].value_counts().rename("Proposed System")
    df_shift = pd.concat([current_counts, proposed_counts], axis=1).fillna(0).reset_index()
    
    fig_shift = px.bar(df_shift, x='index', y=['Current System', 'Proposed System'], barmode='group',
                       labels={'index': 'Wait Time', 'value': 'Number of Repairs'},
                       color_discrete_sequence=['#ff9999', '#99cc99'])
    st.plotly_chart(fig_shift, use_container_width=True)

with col_g2:
    st.subheader("Instant Repair Service Level by ABC Class")
    df_instant = df[df['Live_Proposed_TAT'] <= 0.1]
    instant_counts = df_instant['ABC_Class'].value_counts().reset_index()
    instant_counts.columns = ['ABC Class', 'Instant Serves']
    
    fig_abc = px.pie(instant_counts, values='Instant Serves', names='ABC Class', hole=0.4,
                     color_discrete_sequence=px.colors.sequential.Purp)
    st.plotly_chart(fig_abc, use_container_width=True)

st.divider()

# BOTTOM ROW: RAW DATA & SEASONALITY
col_b1, col_b2 = st.columns([2, 1])

with col_b1:
    st.subheader("Live Simulation Data (Sample)")
    # Show an interactive dataframe of the updated data
    st.dataframe(df[['Date', 'Center', 'Category', 'Qty', 'Live_Proposed_Buffer', 'Live_Proposed_TAT', 'Net_Rev_Saved']].head(50), use_container_width=True)

with col_b2:
    st.subheader("Seasonality Trigger Check")
    # Show just the heatwave months to prove the trigger works
    df_heatwave = df[(df['Category'] == 'Battery') & (df['Month'].isin([5, 6]))]
    st.write(f"Total Battery Repairs in Heatwave (May/Jun): **{len(df_heatwave):,}**")
    st.write("Notice how the `Live_Proposed_Buffer` automatically expanded by +2 units to absorb this shock.")
    st.dataframe(df_heatwave[['Month', 'Qty', 'Live_Proposed_Buffer']].head(5))
