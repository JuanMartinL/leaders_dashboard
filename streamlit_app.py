import streamlit as st
import pandas as pd
import plotly.express as px

@st.cache_data
def load_data():
    # Load LinkedIn leads data
    df = pd.read_excel('datain/Entrepreneur 650 leads .xlsx')
    return df

df = load_data()

# Page configuration
st.set_page_config(page_title='CESA Leaders Dashboard', layout='wide')

# Header
st.title('CESA University: LATAM Leaders & Influencers Dashboard')
st.markdown('Refine and explore potential collaborators for academic programs, conferences, and alliances.')

# Sidebar filters
st.sidebar.header('Filter Leads')

categories = st.sidebar.multiselect(
    'Category',
    options=df['Category'].dropna().unique(),
    default=df['Category'].dropna().unique()
)

industries = st.sidebar.multiselect(
    'Industry',
    options=df['Industry'].dropna().unique(),
    default=df['Industry'].dropna().unique()
)

locations = st.sidebar.multiselect(
    'Location',
    options=df['Location'].dropna().unique(),
    default=df['Location'].dropna().unique()
)

followers_min, followers_max = st.sidebar.slider(
    'Followers Range',
    min_value=int(df['Followers'].min()),
    max_value=int(df['Followers'].max()),
    value=(int(df['Followers'].min()), int(df['Followers'].max()))
)

search_term = st.sidebar.text_input('Search Name/Headline')

# Apply filters
def filter_df(data):
    mask = (
        data['Category'].isin(categories) &
        data['Industry'].isin(industries) &
        data['Location'].isin(locations) &
        data['Followers'].between(followers_min, followers_max)
    )
    if search_term:
        mask &= (
            data['Name'].str.contains(search_term, case=False, na=False) |
            data['Headline'].str.contains(search_term, case=False, na=False)
        )
    return data[mask]

filtered = filter_df(df)

# Key metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric('Total Leads', len(filtered))
col2.metric('Categories', filtered['Category'].nunique())
col3.metric('Industries', filtered['Industry'].nunique())
col4.metric('Avg Followers', f"{int(filtered['Followers'].mean()):,}")

# Visualizations
st.subheader('Leads by Location')
loc_counts = filtered['Location'].value_counts().reset_index()
loc_counts.columns = ['Location', 'Count']
fig_loc = px.bar(loc_counts, x='Location', y='Count', text='Count', title='Distribution by Location')
st.plotly_chart(fig_loc, use_container_width=True)

st.subheader('Category Breakdown')
fig_cat = px.pie(filtered, names='Category', title='Leads by Category')
st.plotly_chart(fig_cat, use_container_width=True)

# Data Table and Export
st.subheader('Leads Details')
st.dataframe(
    filtered[['Name', 'Category', 'Industry', 'Location', 'Followers', 'Headline', 'Profile URL']],
    height=500
)

csv = filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label='Download Filtered Data as CSV',
    data=csv,
    file_name='cesa_leads_filtered.csv',
    mime='text/csv'
)
