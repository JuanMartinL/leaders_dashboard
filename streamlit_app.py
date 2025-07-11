import streamlit as st
import pandas as pd
import plotly.express as px
import ast

# ——————————————————————————————
# 1. Load & cache data
# ——————————————————————————————
@st.cache_data
def load_data(path: str = "datain/scrap_leaders.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path)
    # Convert string-encoded lists back to actual lists
    if df["Main Titles"].dtype == object:
        df["Main Titles"] = df["Main Titles"].apply(
            lambda cell: ast.literal_eval(cell) if isinstance(cell, str) else cell
        )
    return df

leaders = load_data()

# ——————————————————————————————
# 2. Page config & header
# ——————————————————————————————
st.set_page_config(
    page_title="CESA Leads Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("CESA University • LATAM Leaders & Influencers")
st.markdown("Interactively explore and filter your classified leads for programs, conferences & alliances.")

# ——————————————————————————————
# 3. Sidebar filters
# ——————————————————————————————
st.sidebar.header("🔎 Filtros")

# Classification Category
cats = sorted(leaders["Category"].dropna().unique())
sel_cat = st.sidebar.multiselect("Clasificación", options=cats, default=cats)

# Main Titles (multi-role possible)
all_titles = sorted({role for roles in leaders["Main Titles"] for role in roles})
sel_titles = st.sidebar.multiselect("Cargo principal", options=all_titles, default=all_titles)

# Industry
industries = sorted(leaders["Industry"].dropna().unique())
sel_ind = st.sidebar.multiselect("Industria", options=industries, default=industries)

# Location filters
countries = sorted(leaders["Person Country"].dropna().unique())
sel_ctry = st.sidebar.multiselect("País", options=countries, default=countries)

# Followers range
min_fol, max_fol = int(leaders["Followers"].min()), int(leaders["Followers"].max())
sel_fol = st.sidebar.slider("Rango de seguidores", min_value=min_fol, max_value=max_fol, value=(min_fol, max_fol))

# Free-text search
search = st.sidebar.text_input("Buscar nombre o bio")

# ——————————————————————————————
# 4. Filter logic
# ——————————————————————————————
def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    mask = (
        df["Category"].isin(sel_cat) &
        df["Industry"].isin(sel_ind) &
        df["Person Country"].isin(sel_ctry) &
        df["Followers"].between(sel_fol[0], sel_fol[1])
    )
    # Main Titles: any overlap
    mask &= df["Main Titles"].apply(lambda roles: any(t in roles for t in sel_titles))
    # Text search
    if search:
        mask &= (
            df["First Name"].str.contains(search, case=False, na=False) |
            df["Last Name"].str.contains(search, case=False, na=False)   |
            df["Bio"].str.contains(search, case=False, na=False)
        )
    return df[mask]

filtered = filter_df(leaders)

# ——————————————————————————————
# 5. Key metrics
# ——————————————————————————————
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total leads", len(filtered))
col2.metric("Categorías", filtered["Category"].nunique())
col3.metric("Industrias", filtered["Industry"].nunique())
col4.metric("Promedio seguidores", f"{int(filtered['Followers'].mean()):,}")

# ——————————————————————————————
# 6. Visualizaciones
# ——————————————————————————————
st.subheader("Distribución por País")
ctry_counts = filtered["Person Country"].value_counts().reset_index()
ctry_counts.columns = ["País", "Cantidad"]
fig_ctry = px.bar(ctry_counts, x="País", y="Cantidad", text="Cantidad", title=None)
st.plotly_chart(fig_ctry, use_container_width=True)

st.subheader("Leads por Categoría")
cat_counts = filtered["Category"].value_counts().reset_index()
cat_counts.columns = ["Categoría", "Cantidad"]
fig_cat = px.pie(cat_counts, names="Categoría", values="Cantidad", title=None)
st.plotly_chart(fig_cat, use_container_width=True)

# ——————————————————————————————
# 7. Tabla de datos + export
# ——————————————————————————————
st.subheader("Detalles de leads")
st.dataframe(
    filtered[
        [
            "First Name", "Last Name", "Category", "Main Titles",
            "Industry", "Person Country", "Followers", "Person Linkedin Url"
        ]
    ],
    height=500
)

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Descargar CSV filtrado",
    data=csv,
    file_name="cesa_leads_filtrados.csv",
    mime="text/csv"
)