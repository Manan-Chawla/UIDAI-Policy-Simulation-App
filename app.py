import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="UIDAI Policy Simulator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; color: #1f77b4; font-weight: bold;}
    .metric-card {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 1rem; border-radius: 10px; text-align: center;}
    .policy-card {background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                  color: white; padding: 1rem; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_uidai_csv_data():
    csv_path = "uidai-data.csv"  # Root folder me rakh
    
    if os.path.exists(csv_path):
        try:
            data = pd.read_csv(csv_path)
            st.success(f"✅ UIDAI Data loaded: {len(data):,} records | Shape: {data.shape}")
            st.info(f"Columns: {list(data.columns)}")
            return data
        except Exception as e:
            st.error(f"❌ CSV load error: {e}")
            st.stop()
    
    st.error("❌ Data is not avaliable or fetched")
    st.stop()

# ✅ LOAD YOUR CSV DATA
data = load_uidai_csv_data()

def calculate_priority_score(row, policy_params):
    # Safe defaults
    child_ratio = row.get('child_ratio', row.get('age_0_5', 30) + row.get('age_5_17', 50)) / row.get('total_population', 100) * 100
    enrollments = row.get('total_enrollments', row.get('total_enrollments', 100))
    
    base_score = (100 - child_ratio) * enrollments / 100
    school_boost = policy_params['school_multiplier'] if enrollments < 100 else 1
    migration_factor = policy_params['migration_rate'] / 100
    return base_score * school_boost * (1 + migration_factor)

def policy_simulation(data, policy_params):
    sim_data = data.copy()
    sim_data['priority_score'] = sim_data.apply(
        lambda row: calculate_priority_score(row, policy_params), axis=1
    )
    return sim_data

# Main App
st.markdown('<h1 class="main-header">🅾️ UIDAI Policy Simulator</h1>', unsafe_allow_html=True)
st.markdown("**Your uidai-data.csv loaded successfully!**")

# Sidebar
st.sidebar.header("🔍 Filters")
state_col = 'state' if 'state' in data.columns else None
selected_state = st.sidebar.selectbox("State", ['All'] + sorted(data[state_col].unique().tolist()) if state_col else ['All'])

st.sidebar.header("🎯 Policy Simulator")
policy_params = {
    'school_multiplier': st.sidebar.slider("🏫 School Multiplier", 1.0, 3.0, 1.2, 0.1),
    'migration_rate': st.sidebar.slider("📈 Migration Rate (%)", 0.0, 50.0, 5.0, 1.0),
}

# Filter data
filtered_data = data.copy()
if selected_state != 'All' and state_col:
    filtered_data = filtered_data[filtered_data[state_col] == selected_state].copy()

# Run simulation
simulated_data = policy_simulation(filtered_data, policy_params)

# Metrics
col1, col2, col3, col4 = st.columns(4)
total_records = len(simulated_data)
total_enrollments = simulated_data.get('total_enrollments', pd.Series([100]*len(simulated_data))).sum()
avg_priority = simulated_data['priority_score'].mean()
high_priority_count = len(simulated_data[simulated_data['priority_score'] > simulated_data['priority_score'].quantile(0.9)])

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Total Records</h3>
        <h2>{total_records:,}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Total Enrollments</h3>
        <h2>{int(total_enrollments):,}</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Avg Priority</h3>
        <h2>{avg_priority:.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h3>High Priority</h3>
        <h2>{high_priority_count}</h2>
    </div>
    """, unsafe_allow_html=True)

# Charts - Works with ANY CSV columns
st.header("📈 Policy Impact")
col1, col2 = st.columns(2)

with col1:
    fig1 = px.histogram(simulated_data, x='priority_score', 
                       color=state_col, title="Priority Distribution")
    fig1.update_layout(height=400)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Top priority areas
    if state_col and 'district' in data.columns:
        top_areas = simulated_data.groupby([state_col, 'district'])['priority_score'].mean().reset_index()
    else:
        top_areas = simulated_data.nlargest(10, 'priority_score')[['priority_score']]
    st.dataframe(top_areas.head(10), use_container_width=True)

# Scenarios
st.header("🔬 Policy Scenarios")
tab1, tab2, tab3 = st.tabs(["Schools", "Migration", "Live"])

with tab1:
    scenarios = {"No Change": 1.0, "10 Schools": 1.5, "20 Schools": 2.0, "30 Schools": 2.5}
    scenario_data = pd.DataFrame()
    for name, mult in scenarios.items():
        temp_params = policy_params.copy()
        temp_params['school_multiplier'] = mult
        temp_data = policy_simulation(filtered_data, temp_params)
        temp_data['scenario'] = name
        scenario_data = pd.concat([scenario_data, temp_data])
    
    fig_school = px.box(scenario_data, x='scenario', y='priority_score', 
                       color=state_col if state_col else None)
    st.plotly_chart(fig_school, use_container_width=True)

with tab2:
    mig_scenarios = {"Current": 5.0, "High": 25.0, "Very High": 50.0}
    scenario_data = pd.DataFrame()
    for name, rate in mig_scenarios.items():
        temp_params = policy_params.copy()
        temp_params['migration_rate'] = rate
        temp_data = policy_simulation(filtered_data, temp_params)
        temp_data['scenario'] = name
        scenario_data = pd.concat([scenario_data, temp_data])
    
    fig_mig = px.line(scenario_data.groupby(['scenario', state_col])['priority_score'].mean().reset_index() if state_col else 
                     scenario_data.groupby('scenario')['priority_score'].mean().reset_index(),
                     x='scenario', y='priority_score', color=state_col if state_col else None)
    st.plotly_chart(fig_mig, use_container_width=True)

with tab3:
    col1, col2 = st.columns(2)
    with col1:
        live_school = st.slider("Live School Mult", 1.0, 3.0, 1.5)
        live_mig = st.slider("Live Migration %", 0.0, 50.0, 10.0)
        
        live_params = {'school_multiplier': live_school, 'migration_rate': live_mig}
        live_data = policy_simulation(filtered_data, live_params)
        
        st.metric("Live Avg Priority", f"{live_data['priority_score'].mean():.0f}")
        st.metric("Live High Priority", len(live_data[live_data['priority_score'] > live_data['priority_score'].quantile(0.9)]))
    
    with col2:
        fig_live = px.bar(live_data.nlargest(10, 'priority_score')['priority_score'], title="Top Priority Live")
        st.plotly_chart(fig_live)

# Recommendations
st.header("💡 Recommendations")
high_priority = simulated_data.nsmallest(5, 'priority_score')

st.markdown("""
<div class="policy-card">
<h3>🚨 Priority Areas:</h3>
""", unsafe_allow_html=True)

for idx, row in high_priority.iterrows():
    state_name = row.get(state_col, 'Unknown') if state_col else 'Area'
    district_name = row.get('district', f'Row_{idx}')
    st.markdown(f"""
    • **{state_name} - {district_name}**<br>
      Priority: {row['priority_score']:.0f}<br>
      <b>Add {policy_params['school_multiplier']:.1f}x schools</b>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# Raw data
with st.expander("📋 Raw CSV Data"):
    st.dataframe(data.head(1000), use_container_width=True)

st.markdown("---")
st.success("✅ uidai-data.csv se chal raha hai! Deploy ready.")

