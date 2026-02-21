import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="ItTechies Supply Chain Digital Twin", layout="wide")
st.title("ItTechies Services Pvt Ltd: Supply Chain Simulator")
st.markdown("Interactive Monte Carlo Simulation (100,000 Transactions | 50 Centers)")

# 2. Data Loading (Cached for lightning speed)
@st.cache_data
def load_data():
    # Ensure Simulation_Data.csv is in the same folder
    df = pd.read_csv("Simulation_Data.csv")
    return df

try:
    df_raw = load_data()
except FileNotFoundError:
    st.error("Error: Could not find 'Simulation_Data.csv'. Please upload it to the repository.")
    st.stop()

# 3. Sidebar Controls (The Interactive Engine)
st.sidebar.header("Control Panel: MSL Buffers")
buffer_A = st.sidebar.slider("Class A Buffer Limit", 0, 8, 4)
buffer_B = st.sidebar.slider("Class B Buffer Limit", 0, 6, 2)
buffer_C = st.sidebar.slider("Class C Buffer Limit", 0, 4, 0)

st.sidebar.markdown("---")
st.sidebar.header("Granular Analysis")
# Get unique centers and sort them, add an "ALL" option
centers = sorted(df_raw['Center'].unique().tolist())
selected_center = st.sidebar.selectbox("Select Service Center", ["ALL"] + centers)

# 4. Dynamic Calculations (The Digital Twin Engine)
df = df_raw.copy()

# Map the base buffers based on slider inputs
buffer_map = {'A': buffer_A, 'B': buffer_B, 'C': buffer_C}
df['Base_Buffer'] = df['ABC_Class'].map(buffer_map)

# Re-apply Seasonality Triggers (Batteries in Summer, Displays in Monsoon)
df['Season_Trigger'] = np.where(
    ((df['Category'] == 'Battery') & (df['Month'].isin([5, 6]))) | 
    ((df['Category'] == 'Display') & (df['Month'] == 8)), 
    2, 0
)
df['Proposed_Buffer'] = df['Base_Buffer'] + df['Season_Trigger']

# The "Partial Batch Fulfillment" TAT Formula
df['Proposed_TAT'] = (np.minimum(df['Qty'], df['Proposed_Buffer']) * 0.1 + 
                      np.maximum(0, df['Qty'] - df['Proposed_Buffer']) * df['Current_TAT']) / df['Qty']

# Financial Calculations
df['Express_Upside'] = np.minimum(df['Qty'], df['Proposed_Buffer']) * 200
df['Lost_Rev_Current'] = np.where(df['Current_TAT'] > 3, 0.15 * df['Total_Value'], 0)
df['Lost_Rev_Proposed'] = np.where(df['Proposed_TAT'] > 3, 0.15 * df['Total_Value'], 0)
df['Net_Rev_Saved'] = df['Lost_Rev_Current'] - df['Lost_Rev_Proposed']

# 5. Filter for Individual Center (if selected)
if selected_center != "ALL":
    df = df[df['Center'] == selected_center]

# 6. Calculate Top-Level KPIs
total_demand = df['Qty'].sum()
avg_current_tat = df['Current_TAT'].mean()
avg_proposed_tat = df['Proposed_TAT'].mean()
net_rev_saved = df['Net_Rev_Saved'].sum()
express_upside = df['Express_Upside'].sum()

# 7. Dashboard Layout: KPI Row
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Parts Demanded", f"{total_demand:,.0f}")
col2.metric("Current Avg TAT", f"{avg_current_tat:.2f} Days")
col3.metric("Proposed Avg TAT", f"{avg_proposed_tat:.2f} Days", f"{(avg_proposed_tat - avg_current_tat):.2f} Days", delta_color="inverse")
col4.metric("Net Revenue Saved", f"₹{net_rev_saved/100000:,.2f} Lakhs")
col5.metric("Express Fee Upside", f"₹{express_upside/10000000:,.2f} Cr")

st.markdown("---")

# 8. Visualizations using Tabs
tab1, tab2, tab3 = st.tabs(["Performance Charts", "Seasonality Insights", "Raw Simulation Data"])

with tab1:
    col_chart1, col_chart2 = st.columns(2)
    
    # Chart 1: TAT Shift
    with col_chart1:
        st.subheader("Turnaround Time Shift")
        tat_bins_current = pd.cut(df['Current_TAT'], bins=[0, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        tat_bins_proposed = pd.cut(df['Proposed_TAT'], bins=[0, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        
        df_tat = pd.DataFrame({'Current': tat_bins_current, 'Proposed': tat_bins_proposed}).reset_index()
        df_tat = df_tat.melt(id_vars='index', var_name='System', value_name='Volume')
        
        fig1 = px.bar(df_tat, x='index', y='Volume', color='System', barmode='group', 
                      labels={'index': 'Wait Time Category'}, color_discrete_sequence=['#ff9999', '#66b3ff'])
        st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Category Value Breakdown
    with col_chart2:
        st.subheader("Working Capital by Category")
        df_cat = df.groupby('Category')['Total_Value'].sum().reset_index()
        fig2 = px.pie(df_cat, values='Total_Value', names='Category', hole=0.4, 
                      color_discrete_sequence=px.colors.sequential.Purp)
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.subheader("Demand Seasonality & Trigger Validation")
    df_seas = df.groupby(['Month', 'Category'])['Qty'].sum().reset_index()
    df_seas_filtered = df_seas[df_seas['Category'].isin(['Battery', 'Display'])]
    
    fig3 = px.line(df_seas_filtered, x='Month', y='Qty', color='Category', markers=True,
                   title="Battery vs Display Demand Spikes",
                   color_discrete_sequence=['red', 'blue'])
    fig3.update_xaxes(tickmode='linear', tick0=1, dtick=1)
    st.plotly_chart(fig3, use_container_width=True)

with tab3:
    st.subheader("Live Simulation Engine Output")
    st.markdown("Viewing a random sample of 100 transactions representing B2B and B2C operational scenarios.")
    st.dataframe(df[['Date', 'Center', 'Category', 'ABC_Class', 'Qty', 'Proposed_Buffer', 'Current_TAT', 'Proposed_TAT']].sample(100))
