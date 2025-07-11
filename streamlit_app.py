import streamlit as st
import pandas as pd
import plotly.express as px
import ast
import pydeck as pdk
import io
import folium
from streamlit_folium import st_folium

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

    # Map
    st.subheader("Distribución Geográfica")

    with st.container():
        map_df = leaders.dropna(subset=["Latitude", "Longitude", "Followers"]).copy()

        # Normalize bubble sizes (log scale to prevent dominance by high values)
        map_df["Bubble Size"] = map_df["Followers"].apply(lambda x: max(5, min(50, x**0.5)))

        m = folium.Map(
            location=[map_df["Latitude"].mean(), map_df["Longitude"].mean()],
            zoom_start=3,
            tiles="CartoDB positron",
            control_scale=True
        )

        for _, row in map_df.iterrows():
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=row["Bubble Size"],
                color="crimson",
                fill=True,
                fill_opacity=0.6,
                popup=f"{row['First Name']} {row['Last Name']}<br>Followers: {int(row['Followers']):,}",
            ).add_to(m)

        st_folium(m, width="100%", height=500)

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
    st.markdown("## Viewer")
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