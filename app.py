import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="ItTechies Digital Twin", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #ffffff;
    border: 1px solid #e6e6e6;
    padding: 5% 5% 5% 10%;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}
[data-testid="stMetricValue"] {
    font-size: 1.8rem;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    return pd.read_csv("Simulation_Data.csv")

try:
    df_raw = load_data()
except FileNotFoundError:
    st.error("Error: Could not find 'Simulation_Data.csv'. Please upload it to the repository.")
    st.stop()

# ==========================================
# 3. THE SIDEBAR (Control Panel & Filters)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2933/2933116.png", width=60)
    st.title("Control Panel")
    st.markdown("---")
    
    st.subheader("⚙️ Local Buffer Limits")
    buffer_A = st.selectbox("Class A (High Value)", [0, 1, 2, 3, 4, 5, 6, 7, 8], index=4, 
                            help="Minimum Stock Level for high-value, fast-moving items.")
    buffer_B = st.selectbox("Class B (Med Value)", [0, 1, 2, 3, 4, 5, 6], index=2,
                            help="Minimum Stock Level for medium-value items.")
    buffer_C = st.selectbox("Class C (Low Value)", [0, 1, 2, 3, 4], index=0,
                            help="Minimum Stock Level for low-value, slow-moving items.")
    
    st.markdown("---")
    st.subheader("📍 Drill Down Analysis")
    
    centers = sorted(df_raw['Center'].unique().tolist())
    selected_center = st.selectbox("Select Service Center", ["NETWORK AGGREGATE (ALL 50)"] + centers,
                                   help="Isolate KPIs and trends for a specific flagship location.")
    
    # NEW: Global Category Filter
    categories_list = ["ALL CATEGORIES"] + sorted(df_raw['Category'].dropna().unique().tolist())
    selected_category = st.selectbox("Select Part Category", categories_list, 
                                     help="Isolate operational and financial impact for specific parts.")

# ==========================================
# 4. CORE SIMULATION ENGINE (Math & Logic)
# ==========================================
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

# Apply Filters
df_view = df.copy()
if selected_center != "NETWORK AGGREGATE (ALL 50)":
    df_view = df_view[df_view['Center'] == selected_center]
if selected_category != "ALL CATEGORIES":
    df_view = df_view[df_view['Category'] == selected_category]

# Top-Level KPIs
total_demand = df_view['Qty'].sum()
# Prevent division by zero if filters yield empty data
if total_demand > 0:
    avg_current_tat = df_view['Current_TAT'].mean()
    avg_proposed_tat = df_view['Proposed_TAT'].mean()
else:
    avg_current_tat = 0
    avg_proposed_tat = 0

net_rev_saved = df_view['Net_Rev_Saved'].sum()
express_upside = df_view['Express_Upside'].sum()
tat_delta = avg_proposed_tat - avg_current_tat

# ==========================================
# 5. MAIN PAGE HERO BANNER
# ==========================================
st.title("Supply Chain Digital Twin")
st.markdown("### Executive Dashboard")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Total Annual Volume", f"{total_demand:,.0f} Parts", help="Total component demand processed.")
kpi2.metric("Current Avg TAT", f"{avg_current_tat:.2f} Days", help="Wait time under the legacy 'Pull' system.")
kpi3.metric("Proposed Avg TAT", f"{avg_proposed_tat:.2f} Days", f"{tat_delta:.2f} Days", delta_color="inverse", help="Wait time using the Consignment Push MSL strategy.")

if selected_center == "NETWORK AGGREGATE (ALL 50)" and selected_category == "ALL CATEGORIES":
    total_roi = (net_rev_saved + express_upside) / 10000000
    kpi4.metric("Total ROI Created", f"₹{total_roi:.2f} Cr", "+ ROI Generated", delta_color="normal", help="Combined Express Fee Upside and Churn Revenue Saved.")
else:
    # Micro-Visual: Sparkline for individual center/category TAT trend
    monthly_tat = df_view.groupby('Month')['Proposed_TAT'].mean().reset_index()
    fig_spark = go.Figure(go.Scatter(x=monthly_tat['Month'], y=monthly_tat['Proposed_TAT'], mode='lines', line=dict(color='#00CC96', width=4)))
    fig_spark.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0), height=50, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    kpi4.markdown("**12-Month TAT Trend**")
    kpi4.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")

# ==========================================
# 6. HELPER FUNCTION: CLEAN CHARTS
# ==========================================
def clean_layout(fig):
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='#ebebeb', zeroline=False),
        xaxis=dict(showgrid=False, zeroline=False)
    )
    return fig

# ==========================================
# 7. DASHBOARD TABS & CHARTS
# ==========================================
tab1, tab2, tab3 = st.tabs(["Operational Impact", "Financials & Inventory", "Data Matrix & Export"])

with tab1:
    col_op1, col_op2, col_op3 = st.columns(3)
    
    with col_op1:
        # TAT Comparison
        fig_tat = go.Figure(data=[
            go.Bar(name='Current System', x=['TAT'], y=[avg_current_tat], marker_color='#ff9999'),
            go.Bar(name='Proposed System', x=['TAT'], y=[avg_proposed_tat], marker_color='#66b3ff')
        ])
        fig_tat.update_layout(title_text='Current vs Proposed Average TAT', barmode='group')
        st.plotly_chart(clean_layout(fig_tat), use_container_width=True)

    with col_op2:
        # Wait Time Shift
        tat_bins_current = pd.cut(df_view['Current_TAT'], bins=[-1, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        tat_bins_proposed = pd.cut(df_view['Proposed_TAT'], bins=[-1, 1, 3, 16], labels=['Instant (<1d)', 'Standard (3d)', 'Delayed (>3d)']).value_counts()
        df_tat_shift = pd.DataFrame({'Current': tat_bins_current, 'Proposed': tat_bins_proposed}).reset_index().melt(id_vars='index', var_name='System', value_name='Volume')
        
        fig_shift = px.bar(df_tat_shift, x='index', y='Volume', color='System', barmode='group',
                           title='Wait Time Shift', color_discrete_sequence=['#ff9999', '#66b3ff'])
        st.plotly_chart(clean_layout(fig_shift), use_container_width=True)
        
    with col_op3:
        # NEW: Executive Service Level Gauge Chart
        if total_demand > 0:
            instant_volume = df_view[df_view['Proposed_TAT'] <= 1]['Qty'].sum()
            service_level = (instant_volume / total_demand) * 100
        else:
            service_level = 0

        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = service_level,
            number = {'suffix': "%", 'valueformat': '.1f'},
            title = {'text': "Instant Service Level Target"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#00CC96"},
                'steps': [
                    {'range': [0, 50], 'color': "#ff9999"},
                    {'range': [50, 80], 'color': "#ffcc66"},
                    {'range': [80, 100], 'color': "#e6ffe6"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 85}
            }
        ))
        st.plotly_chart(clean_layout(fig_gauge), use_container_width=True)

    # Put Seasonality Full Width Below
    st.markdown("---")
    df_seas = df_view.groupby(['Month', 'Category'])['Qty'].sum().reset_index()
    # If filtered to a category, show that, otherwise show Battery/Display
    if selected_category != "ALL CATEGORIES":
        df_seas_filtered = df_seas
    else:
        df_seas_filtered = df_seas[df_seas['Category'].isin(['Battery', 'Display'])]
        
    fig_seas = px.line(df_seas_filtered, x='Month', y='Qty', color='Category', markers=True,
                       title="Demand Triggers & Seasonality", color_discrete_sequence=['#e63946', '#1d3557'])
    fig_seas.update_xaxes(tickmode='linear', tick0=1, dtick=1)
    st.plotly_chart(clean_layout(fig_seas), use_container_width=True)

with tab2:
    col_fin1, col_fin2, col_fin3 = st.columns(3)

    with col_fin1:
        # NEW: Formatted Financial Axes
        fig_fin = go.Figure(data=[
            go.Bar(name='Net Revenue Saved', x=['Financial Wins'], y=[net_rev_saved], marker_color='#2ca02c'),
            go.Bar(name='Express Fee Upside', x=['Financial Wins'], y=[express_upside], marker_color='#98df8a')
        ])
        fig_fin.update_layout(
            title_text='Monetary Upside Generated', 
            barmode='stack',
            yaxis=dict(tickprefix="₹", title="Value (INR)")
        )
        st.plotly_chart(clean_layout(fig_fin), use_container_width=True)

    with col_fin2:
        df_cat = df_view.groupby('Category')['Total_Value'].sum().reset_index()
        fig_pie = px.pie(df_cat, values='Total_Value', names='Category', hole=0.5,
                         title="Working Capital by Category", color_discrete_sequence=px.colors.sequential.Purp)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_fin3:
        instant_df = df_view[df_view['Proposed_TAT'] <= 1]
        abc_instant = instant_df['ABC_Class'].value_counts().reset_index()
        abc_instant.columns = ['ABC_Class', 'Instant_Serves']
        fig_abc = px.pie(abc_instant, values='Instant_Serves', names='ABC_Class', 
                         title="Instant Serves by ABC Class", color_discrete_sequence=px.colors.qualitative.Set3)
        fig_abc.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_abc, use_container_width=True)

with tab3:
    col_data1, col_data2 = st.columns([1.5, 2])
    
    with col_data1:
        st.markdown("#### Top Flagship Centers by Volume")
        df_top_centers = df_view.groupby('Center')['Qty'].sum().reset_index().rename(columns={'Qty': 'Total_Repairs'}).sort_values(by='Total_Repairs', ascending=False)
        st.dataframe(
            df_top_centers,
            hide_index=True,
            column_config={
                "Center": "Service Center ID",
                "Total_Repairs": st.column_config.ProgressColumn("Repair Volume", help="Total part volume processed", format="%d", min_value=0, max_value=int(df_top_centers['Total_Repairs'].max())),
            }
        )
        
    with col_data2:
        st.markdown("#### System Audit & Data Export")
        with st.expander("🔍 Click to view Raw Simulation Data Engine & Export"):
            st.info("This table displays the live algorithmic outputs for partial batch fulfillment.")
            
            # NEW: Download Button
            csv = df_view.to_csv(index=False).encode('utf-8')
            file_name_export = f"ItTechies_Simulation_{selected_center}_{selected_category}.csv".replace(" ", "_")
            
            st.download_button(
                label="📥 Download Filtered Dataset (CSV)",
                data=csv,
                file_name=file_name_export,
                mime="text/csv"
            )
            
            st.dataframe(df_view[['Date', 'Center', 'Category', 'ABC_Class', 'Qty', 'Current_TAT', 'Proposed_Buffer', 'Proposed_TAT', 'Net_Rev_Saved']], use_container_width=True)
