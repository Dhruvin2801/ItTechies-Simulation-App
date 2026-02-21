import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 1. Page Configuration (Full Width for App Feel)
st.set_page_config(page_title="ItTechies Supply Chain Digital Twin", layout="wide")

# App Header
st.title("ItTechies Services Pvt Ltd: Supply Chain Simulator")
st.markdown("**Interactive Digital Twin (100,000 Transactions | 50 Flagship Centers)**")
st.markdown("---")

# 2. Data Loading
@st.cache_data
def load_data():
  return pd.read_csv("Simulation_Data.csv")

try:
    df_raw = load_data()
except FileNotFoundError:
    st.error("Error: Could not find 'Simulation_Data.csv'. Please upload it to the repository.")
    st.stop()

# 3. F-PATTERN TOP ROW: Control Board & KPIs
top_left, top_right = st.columns([1, 2.5])

with top_left:
    st.subheader("⚙️ Control Board (MSL)")
    st.markdown("Adjust Local Buffer Limits")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a: buffer_A = st.selectbox("Class A", [0, 1, 2, 3, 4, 5, 6, 7, 8], index=4)
    with col_b: buffer_B = st.selectbox("Class B", [0, 1, 2, 3, 4, 5, 6], index=2)
    with col_c: buffer_C = st.selectbox("Class C", [0, 1, 2, 3, 4], index=0)
    
    st.markdown("---")
    st.subheader("📍 Center Analysis")
    centers = sorted(df_raw['Center'].unique().tolist())
    selected_center = st.selectbox("Select Service Center", ["NETWORK AGGREGATE (ALL 50)"] + centers)

# 4. Core Simulation Engine (Partial Batch Fulfillment)
df = df_raw.copy()
buffer_map = {'A': buffer_A, 'B': buffer_B, 'C': buffer_C}
df['Base_Buffer'] = df['ABC_Class'].map(buffer_map)

# Seasonality Triggers
df['Season_Trigger'] = np.where(
    ((df['Category'] == 'Battery') & (df['Month'].isin([5, 6]))) | 
    ((df['Category'] == 'Display') & (df['Month'] == 8)), 
    2, 0
)
df['Proposed_Buffer'] = df['Base_Buffer'] + df['Season_Trigger']

# Partial Batch Fulfillment TAT Formula
df['Proposed_TAT'] = (np.minimum(df['Qty'], df['Proposed_Buffer']) * 0.1 + 
                      np.maximum(0, df['Qty'] - df['Proposed_Buffer']) * df['Current_TAT']) / df['Qty']

# Financials
df['Express_Upside'] = np.minimum(df['Qty'], df['Proposed_Buffer']) * 200
df['Lost_Rev_Current'] = np.where(df['Current_TAT'] > 3, 0.15 * df['Total_Value'], 0)
df['Lost_Rev_Proposed'] = np.where(df['Proposed_TAT'] > 3, 0.15 * df['Total_Value'], 0)
df['Net_Rev_Saved'] = df['Lost_Rev_Current'] - df['Lost_Rev_Proposed']

# Filter data based on center selection
if selected_center != "NETWORK AGGREGATE (ALL 50)":
    df_view = df[df['Center'] == selected_center]
else:
    df_view = df

# Top-Level KPIs for selected view
total_demand = df_view['Qty'].sum()
avg_current_tat = df_view['Current_TAT'].mean()
avg_proposed_tat = df_view['Proposed_TAT'].mean()
net_rev_saved = df_view['Net_Rev_Saved'].sum()
express_upside = df_view['Express_Upside'].sum()

# Dynamic App UI formatting
tat_delta = avg_proposed_tat - avg_current_tat

with top_right:
    st.subheader("📊 Hero KPIs")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Conditional Formatting is built into the delta function (inverse makes negative/drop = Green)
    kpi1.metric("Total Annual Volume", f"{total_demand:,.0f} Parts")
    kpi2.metric("Current Avg TAT", f"{avg_current_tat:.2f} Days")
    kpi3.metric("Proposed Avg TAT", f"{avg_proposed_tat:.2f} Days", f"{tat_delta:.2f} Days (Drop)", delta_color="inverse")
    
    if selected_center == "NETWORK AGGREGATE (ALL 50)":
        kpi4.metric("Total ROI Created", f"₹{(net_rev_saved + express_upside)/10000000:.2f} Cr", "+ ROI", delta_color="normal")
    else:
        # Micro-Visual: Sparkline for individual center TAT trend
        monthly_tat = df_view.groupby('Month')['Proposed_TAT'].mean().reset_index()
        fig_spark = go.Figure(go.Scatter(x=monthly_tat['Month'], y=monthly_tat['Proposed_TAT'], mode='lines', line=dict(color='#00CC96', width=3)))
        fig_spark.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0), height=50, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        kpi4.markdown(f"**{selected_center} 12-Month TAT Trend**")
        kpi4.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")

# 5. Full 7-Chart Dashboard Layout
tab1, tab2, tab3 = st.tabs(["Operational Impact", "Financials & Inventory", "Live Simulation Engine"])

with tab1:
    col_op1, col_op2, col_op3 = st.columns(3)
    
    with col_op1:
        # Chart 1: Current vs Proposed Average TAT
        fig_tat = go.Figure(data=[
            go.Bar(name='Current System', x=['TAT'], y=[avg_current_tat], marker_color='#ff9999'),
            go.Bar(name='Proposed System', x=['TAT'], y=[avg_proposed_tat], marker_color='#66b3ff')
        ])
        fig_tat.update_layout(title_text='Current vs Proposed Average TAT', barmode='group')
        st.plotly_chart(fig_tat, use_container_width=True)

    with col_op2:
        # Chart 2: Wait Time Shift
        tat_bins_current = pd.cut(df_view['Current_TAT'], bins=[-1, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        tat_bins_proposed = pd.cut(df_view['Proposed_TAT'], bins=[-1, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        
        df_tat_shift = pd.DataFrame({'Current': tat_bins_current, 'Proposed': tat_bins_proposed}).reset_index()
        df_tat_shift = df_tat_shift.melt(id_vars='index', var_name='System', value_name='Volume')
        
        fig_shift = px.bar(df_tat_shift, x='index', y='Volume', color='System', barmode='group',
                           title='Wait Time Shift (Push vs Pull)', color_discrete_sequence=['#ff9999', '#66b3ff'])
        st.plotly_chart(fig_shift, use_container_width=True)
        
    with col_op3:
        # Chart 4 (Moved here for Operational Flow): Seasonality Tracking
        df_seas = df_view.groupby(['Month', 'Category'])['Qty'].sum().reset_index()
        df_seas_filtered = df_seas[df_seas['Category'].isin(['Battery', 'Display'])]
        fig_seas = px.line(df_seas_filtered, x='Month', y='Qty', color='Category', markers=True,
                           title="Demand Triggers (Monsoon vs Summer)", color_discrete_sequence=['red', 'blue'])
        fig_seas.update_xaxes(tickmode='linear', tick0=1, dtick=1)
        st.plotly_chart(fig_seas, use_container_width=True)

with tab2:
    col_fin1, col_fin2, col_fin3 = st.columns(3)

    with col_fin1:
        # Chart 3: Financial Wins (Monetary Upside)
        fig_fin = go.Figure(data=[
            go.Bar(name='Net Revenue Saved', x=['Financial Wins'], y=[net_rev_saved], marker_color='#2ca02c'),
            go.Bar(name='Express Fee Upside', x=['Financial Wins'], y=[express_upside], marker_color='#98df8a')
        ])
        fig_fin.update_layout(title_text='Monetary Upside Generated (INR)', barmode='stack')
        st.plotly_chart(fig_fin, use_container_width=True)

    with col_fin2:
        # Chart 5: Value Doughnut by Part Category
        df_cat = df_view.groupby('Category')['Total_Value'].sum().reset_index()
        fig_pie = px.pie(df_cat, values='Total_Value', names='Category', hole=0.5,
                         title="Working Capital by Category", color_discrete_sequence=px.colors.sequential.Purp)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_fin3:
        # Chart 6: Instant Serves by ABC Class
        instant_df = df_view[df_view['Proposed_TAT'] <= 1]
        abc_instant = instant_df['ABC_Class'].value_counts().reset_index()
        abc_instant.columns = ['ABC_Class', 'Instant_Serves']
        fig_abc = px.pie(abc_instant, values='Instant_Serves', names='ABC_Class', 
                         title="Instant Serves by ABC Class", color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_abc, use_container_width=True)

with tab3:
    st.subheader("Data Matrix & Digital Twin Output")
    col_data1, col_data2 = st.columns([1, 2.5])
    
    with col_data1:
        # Chart 7 / Micro-Visuals: Data Bars for Top Centers
        st.markdown("**Top Flagship Centers by Volume**")
        df_top_centers = df.groupby('Center')['Qty'].sum().reset_index().rename(columns={'Qty': 'Total_Repairs'}).sort_values(by='Total_Repairs', ascending=False)
        
        st.dataframe(
            df_top_centers,
            hide_index=True,
            column_config={
                "Center": "Service Center ID",
                "Total_Repairs": st.column_config.ProgressColumn(
                    "Repair Volume",
                    help="Total part volume processed",
                    format="%d",
                    min_value=0,
                    max_value=int(df_top_centers['Total_Repairs'].max()),
                ),
            }
        )
        
    with col_data2:
        st.markdown("**Live Simulation Engine Execution Log**")
        # Native Streamlit dataframe efficiently paginates the full 100,000 rows
        st.dataframe(df_view[['Date', 'Center', 'Category', 'ABC_Class', 'Qty', 'Current_TAT', 'Proposed_Buffer', 'Proposed_TAT', 'Net_Rev_Saved']], use_container_width=True)
