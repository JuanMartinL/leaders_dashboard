import streamlit as st
import pandas as pd
import plotly.express as px
import ast
import pydeck as pdk
import io
import folium
from streamlit_folium import st_folium
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

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
tab1, tab2, tab3 = st.tabs(["Estadísticas Generales", "Visor de Líderes", "Network"])

with tab1:
    st.markdown("**Explora y filtra tus leads** para programas, conferencias y alianzas.")
    
    # Sidebar Filters
    st.sidebar.header("Filtros")
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

    # Key metrics
    total_leads = len(filtered)
    categories_count = filtered["Category"].nunique()
    industries_count = filtered["Industry"].nunique()
    mean_followers = filtered["Followers"].mean()
    followers_display = "0" if pd.isna(mean_followers) else f"{int(mean_followers):,}"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total leads", total_leads)
    col2.metric("Categorías", categories_count)
    col3.metric("Industrias", industries_count)
    col4.metric("Prom. seguidores", followers_display)

    # Charts
    st.subheader("Distribución por País")
    df_ctry = filtered["Person Country"].value_counts().reset_index()
    df_ctry.columns = ["País","Cantidad"]
    st.plotly_chart(px.bar(df_ctry, x="País", y="Cantidad", text="Cantidad"), use_container_width=True)

    map_df = leaders.dropna(subset=["Latitude", "Longitude"])

    # Create Folium map centered on average lat/lon
    m = folium.Map(
        location=[map_df["Latitude"].mean(), map_df["Longitude"].mean()],
        zoom_start=3,
        tiles="CartoDB positron"
    )

    # Add circle markers
    for _, row in map_df.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=5,
            color="crimson",
            fill=True,
            fill_opacity=0.7,
            popup=f"{row['First Name']} {row['Last Name']}"
        ).add_to(m)

    # Use the already-filtered DataFrame
    map_df = filtered.dropna(subset=["Latitude", "Longitude"])

    # Group by Country + Lat/Lon
    grouped = map_df.groupby(["Person Country", "Latitude", "Longitude"]).size().reset_index(name="Count")

    # Optional: scale radius using power or log
    grouped["Bubble Size"] = grouped["Count"].apply(lambda x: max(6, min(50, x**0.8)))

    # Create the map centered on the filtered data
    m = folium.Map(
        location=[grouped["Latitude"].mean(), grouped["Longitude"].mean()],
        zoom_start=3,
        tiles="CartoDB positron",
        control_scale=True
    )

    # Add bubbles
    for _, row in grouped.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=row["Bubble Size"],
            color="crimson",
            fill=True,
            fill_opacity=0.6,
            popup=f"{row['Person Country']}: {row['Count']} personas"
        ).add_to(m)

    # Display map in full width
    st_folium(m, width="100%", height=500)

    # Donut charts side by side
    chart_col1, chart_col2 = st.columns(2)

    # Donut Charts
    with chart_col1:
        st.subheader("Leads por Categoría")
        cat_counts = filtered["Category"].value_counts().reset_index()
        cat_counts.columns = ["Categoría", "Cantidad"]
        fig_cat = px.pie(
            cat_counts,
            names="Categoría",
            values="Cantidad",
            hole=0.4,
            title=None
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with chart_col2:
        st.subheader("Leads por Industria")
        ind_counts = filtered["Industry"].value_counts().reset_index()
        ind_counts.columns = ["Industria", "Cantidad"]
        fig_ind = px.pie(
            ind_counts,
            names="Industria",
            values="Cantidad",
            hole=0.4,
            title=None
        )
        st.plotly_chart(fig_ind, use_container_width=True)

    # — Data table & download —
    st.subheader("Detalles de Leads")
    st.dataframe(
        filtered[[
            "First Name","Last Name","Category","Main Titles",
            "Industry","Person Country","Followers","Person Linkedin Url"
        ]],
        height=400
    )

    # Download buttom
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        filtered.to_excel(writer, index=False)
    output.seek(0)

    st.download_button(
        label="Descargar Excel",
        data=output,
        file_name="cesa_leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


with tab2:
    st.markdown("## Visor de Líderes")
    st.markdown("Selecciona un lead para ver su perfil completo y decidir su pertinencia para conferencias, programas académicos o alianzas.")

    names = leaders["First Name"] + " " + leaders["Last Name"]
    sel_person = st.selectbox("Elegir persona", options=sorted(names.unique()))

    person = leaders[names == sel_person].iloc[0]

    left, right = st.columns([1, 3])

    with left:
        # if "Profile_Pic_URL" in person and pd.notna(person["Profile_Pic_URL"]):
        #     st.image(person["Profile_Pic_URL"], width=160)
        # else:
        #     st.image("https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png", width=160)

        st.markdown(f"**Seguidores:** {int(person['Followers']):,}" if not pd.isna(person['Followers']) else "**Seguidores:** N/A")
        if "Contact Email" in person and pd.notna(person["Contact Email"]):
            st.markdown(f"Email: {person['Contact Email']}")
        if pd.notna(person["Person Linkedin Url"]):
            st.markdown(f"[Ver en LinkedIn]({person['Person Linkedin Url']})", unsafe_allow_html=True)

    with right:
        st.markdown(f"### {person['First Name']} {person['Last Name']}")
        st.markdown(f"**{person['Current Title']}**")
        st.markdown(" ")

        tags = []
        if isinstance(person["Main Titles"], list):
            tags.extend(person["Main Titles"])
        if pd.notna(person["Category"]):
            tags.append(person["Category"])
        if pd.notna(person["Industry"]):
            tags.append(person["Industry"])
        if pd.notna(person["Person Country"]):
            tags.append(person["Person Country"])

        st.markdown("**Áreas clave:**")
        st.markdown(" | ".join(tags))

        st.markdown("**Biografía:**")
        st.info(person["Bio"] if pd.notna(person["Bio"]) else "No hay biografía disponible.")

    st.markdown("---")

with tab3:
    st.subheader("Matriz de Red: Top Conectados")

    import networkx as nx
    from pyvis.network import Network
    import streamlit.components.v1 as components
    from itertools import combinations
    from collections import defaultdict

    # Preparar nodos
    sub = filtered.copy()
    sub["Full Name"] = sub["First Name"] + " " + sub["Last Name"]
    sub = sub.dropna(subset=["Main Titles"])
    sub = sub.reset_index(drop=True)

    # Construir red de co-ocurrencia por rol
    edges = defaultdict(int)
    name_roles = list(zip(sub["Full Name"], sub["Main Titles"]))
    for (name1, roles1), (name2, roles2) in combinations(name_roles, 2):
        if set(roles1) & set(roles2):
            edges[(name1, name2)] += 1

    # Crear grafo
    G = nx.Graph()
    for name in sub["Full Name"]:
        G.add_node(name)
    for (n1, n2), w in edges.items():
        G.add_edge(n1, n2, weight=w)

    # Filtrar top N por centralidad
    deg = nx.degree_centrality(G)
    top_n = 50
    top_nodes = sorted(deg, key=deg.get, reverse=True)[:top_n]
    G = G.subgraph(top_nodes).copy()

    # Crear red PyVis
    net = Network(height="600px", width="100%", notebook=False)
    net.set_options("""
        var options = {
          physics: {
            repulsion: {
              centralGravity: 0.1,
              springLength: 100,
              springConstant: 0.01,
              nodeDistance: 200,
              damping: 0.1
            },
            solver: 'repulsion'
          }
        }
    """)
    for n in G.nodes:
        net.add_node(n, label=n)
    for u, v, d in G.edges(data=True):
        net.add_edge(u, v, value=d["weight"])

    # Exportar y mostrar
    net.write_html("network.html")
    with open("network.html", "r", encoding="utf-8") as f:
        components.html(f.read(), height=600)
