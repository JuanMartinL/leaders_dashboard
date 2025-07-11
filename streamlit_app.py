import streamlit as st
import pandas as pd
import plotly.express as px
import ast

@st.cache_data
def load_data(path: str = "datain/scrap_leaders.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path)
    # Reconstruir listas si vienen serializadas
    if df["Main Titles"].dtype == object:
        df["Main Titles"] = df["Main Titles"].apply(
            lambda cell: ast.literal_eval(cell) if isinstance(cell, str) else cell
        )
    return df

leaders = load_data()

st.set_page_config(page_title="CESA Leads Dashboard", layout="wide")
st.title("CESA University • LATAM Leaders & Influencers")

# ---------------------------------------------------
# Create two tabs: Dashboard & CV Viewer
# ---------------------------------------------------
tab1, tab2 = st.tabs(["Dashboard", "CV Viewer"])

with tab1:
    st.markdown("**Explora y filtra tus leads** para programas, conferencias y alianzas.")
    # — Sidebar Filters (mismo código que antes) —
    st.sidebar.header("🔎 Filtros")
    cats   = sorted(leaders["Category"].dropna().unique())
    sel_cat = st.sidebar.multiselect("Clasificación", options=cats, default=cats)
    titles = sorted({r for roles in leaders["Main Titles"] for r in roles})
    sel_titles = st.sidebar.multiselect("Cargo principal", options=titles, default=titles)
    inds   = sorted(leaders["Industry"].dropna().unique())
    sel_ind = st.sidebar.multiselect("Industria", options=inds, default=inds)
    countries = sorted(leaders["Person Country"].dropna().unique())
    sel_ctry   = st.sidebar.multiselect("País", options=countries, default=countries)
    min_fol, max_fol = int(leaders["Followers"].min()), int(leaders["Followers"].max())
    sel_fol = st.sidebar.slider("Rango de seguidores", min_fol, max_fol, (min_fol, max_fol))
    search   = st.sidebar.text_input("Buscar nombre o bio")

    def filter_df(df):
        m = (
            df["Category"].isin(sel_cat) &
            df["Industry"].isin(sel_ind) &
            df["Person Country"].isin(sel_ctry) &
            df["Followers"].between(sel_fol[0], sel_fol[1])
        )
        m &= df["Main Titles"].apply(lambda roles: any(t in roles for t in sel_titles))
        if search:
            m &= (
                df["First Name"].str.contains(search, case=False, na=False) |
                df["Last Name"].str.contains(search, case=False, na=False)  |
                df["Bio"].str.contains(search, case=False, na=False)
            )
        return df[m]

    filtered = filter_df(leaders)

    # — Key metrics —
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total leads", len(filtered))
    c2.metric("Categorías", filtered["Category"].nunique())
    c3.metric("Industrias", filtered["Industry"].nunique())
    c4.metric("Prom. seguidores", f"{int(filtered['Followers'].mean()):,}")

    # — Charts —
    st.subheader("Distribución por País")
    df_ctry = filtered["Person Country"].value_counts().reset_index()
    df_ctry.columns = ["País","Cantidad"]
    st.plotly_chart(px.bar(df_ctry, x="País", y="Cantidad", text="Cantidad"), use_container_width=True)

    st.subheader("Leads por Categoría")
    df_cat = filtered["Category"].value_counts().reset_index()
    df_cat.columns = ["Categoría","Cantidad"]
    st.plotly_chart(px.pie(df_cat, names="Categoría", values="Cantidad"), use_container_width=True)

    # — Data table & download —
    st.subheader("Detalles de Leads")
    st.dataframe(
        filtered[[
            "First Name","Last Name","Category","Main Titles",
            "Industry","Person Country","Followers","Person Linkedin Url"
        ]],
        height=400
    )
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", data=csv, file_name="cesa_leads.csv")

with tab2:
    st.markdown("## CV Viewer\nSelecciona un lead para ver su ficha completa estilo currículum.")
    # Selector de persona
    names = leaders["First Name"] + " " + leaders["Last Name"]
    sel_person = st.selectbox("Elegir persona", options=names)

    # Mostrar datos
    person = leaders[names == sel_person].iloc[0]
    st.markdown(f"### {person['First Name']} {person['Last Name']}")
    st.markdown(f"**Título actual:** {person['Current Title']}")
    st.markdown(f"**Categoría:** {person['Category']}")
    st.markdown(f"**Roles principales:** {', '.join(person['Main Titles'])}")
    st.markdown(f"**Industria:** {person['Industry']}")
    st.markdown(f"**País:** {person['Person Country']}")
    st.markdown(f"**Seguidores:** {person['Followers']:,}")
    st.markdown(f"**LinkedIn:** [{person['Person Linkedin Url']}]({person['Person Linkedin Url']})")

    st.markdown("**Biografía completa:**")
    st.write(person["Bio"])

    if "Contact Email" in person:
        st.markdown(f"**Email de contacto:** {person['Contact Email']}")