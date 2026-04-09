import streamlit as st
import requests
import pandas as pd
import io
import time

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Radar de Competencia V2.1",
    page_icon="🚀",
    layout="wide"
)

# Inicializar la variable en la memoria de Streamlit
if "df_maestro" not in st.session_state:
    st.session_state.df_maestro = pd.DataFrame()

# ==========================================
# FUNCIÓN PRINCIPAL (PLACES API NEW)
# ==========================================
def buscar_locales_v2(query, api_key, paginas_max=1):
    lugares_totales = []
    url_base = "https://places.googleapis.com/v1/places:searchText"
    
    # Agregamos 'places.types' para saber la categoría
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.nationalPhoneNumber,places.websiteUri,places.rating,places.userRatingCount,places.googleMapsUri,places.types,nextPageToken"
    }
    
    next_page_token = ""
    
    with st.status("🚀 Escaneando Google Maps...", expanded=True) as status_box:
        for pagina in range(paginas_max):
            status_box.write(f"➡️ Extrayendo página {pagina + 1}...")
            
            payload = {
                "textQuery": query,
                "pageSize": 20,
                "languageCode": "es"
            }
            
            if next_page_token:
                payload["pageToken"] = next_page_token
                
            response = requests.post(url_base, headers=headers, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                places = data.get('places', [])
                lugares_totales.extend(places)
                next_page_token = data.get('nextPageToken', '')
                if not next_page_token: break
            else:
                st.error(f"Error: {data.get('error', {}).get('message')}")
                break

        if not lugares_totales:
            status_box.update(label="❌ Sin resultados.", state="error")
            return pd.DataFrame()
            
        datos_extraidos = []
        for lugar in lugares_totales:
            # Limpiamos las categorías para que sean legibles
            tipos = lugar.get('types', [])
            categoria = tipos[0].replace('_', ' ').title() if tipos else "General"
            
            datos_extraidos.append({
                'Nombre del Local': lugar.get('displayName', {}).get('text', 'Sin nombre'),
                'Categoría': categoria,
                'Sitio Web': "Sí" if lugar.get('websiteUri') else "No",
                'URL Web': lugar.get('websiteUri', 'No disponible'),
                'Teléfono': lugar.get('nationalPhoneNumber', 'No disponible'),
                'Calificación': lugar.get('rating', 0.0),
                'Reseñas': lugar.get('userRatingCount', 0),
                'Link Google Maps': lugar.get('googleMapsUri', 'No disponible')
            })
            
        status_box.update(label=f"🎉 {len(datos_extraidos)} locales encontrados.", state="complete", expanded=False)
    
    df = pd.DataFrame(datos_extraidos)
    return df.sort_values(by='Reseñas', ascending=False) if not df.empty else df

# ==========================================
# INTERFAZ
# ==========================================
st.title("📊 Radar de Competencia y Leads")

col_sidebar, col_main = st.columns([1, 2.5])

with col_sidebar:
    st.header("⚙️ Configuración")
    api_key_input = st.text_input("🔑 Google API Key", type="password")
    
    tab1, tab2 = st.tabs(["🔍 Búsqueda General", "🎯 Local Específico"])
    
    with tab1:
        rubro = st.text_input("Rubro", value="Lencería")
        pais = st.text_input("País", value="Argentina")
        ciudad = st.text_input("Ciudad", value="CABA")
        barrio = st.text_input("Zona / Barrio", value="Flores")
        paginas = st.slider("Profundidad (Locales)", 20, 120, 60, 20)
        
    with tab2:
        st.info("Usa esto si un local no aparece en la búsqueda general.")
        nombre_especifico = st.text_input("Nombre del Local (ej: Lenceria Mimi)")

    if st.button("🚀 Iniciar Análisis", use_container_width=True, type="primary"):
        if api_key_input:
            if nombre_especifico:
                query = f"{nombre_especifico} en {barrio if barrio else ciudad}, {pais}"
                paginas_api = 1
            else:
                query = f"locales de {rubro} en {barrio}, {ciudad}, {pais}"
                paginas_api = int(paginas / 20)
                
            st.session_state.df_maestro = buscar_locales_v2(query, api_key_input, paginas_api)
        else:
            st.error("Ingresa tu API Key")

with col_main:
    df = st.session_state.df_maestro
    if not df.empty:
        # Filtros rápidos
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_web = st.radio("Filtro Web:", ["Todos", "Sin Web", "Con Web"], horizontal=True)
        with col_f2:
            search_box = st.text_input("🔎 Filtrar por nombre en esta lista:")

        df_final = df.copy()
        if filtro_web == "Sin Web": df_final = df_final[df_final['Sitio Web'] == "No"]
        if filtro_web == "Con Web": df_final = df_final[df_final['Sitio Web'] == "Sí"]
        if search_box: df_final = df_final[df_final['Nombre del Local'].str.contains(search_box, case=False)]

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Locales", len(df_final))
        m2.metric("Oportunidades (Sin Web)", len(df_final[df_final['Sitio Web'] == "No"]))
        m3.metric("Rating Promedio", f"{df_final['Calificación'].mean():.1f} ⭐")

        st.dataframe(df_final, use_container_width=True, hide_index=True)

        # Descargas
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button("📥 Descargar CSV", df_final.to_csv(index=False).encode('utf-8'), "reporte.csv", "text/csv", use_container_width=True)
        with col_d2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as w: df_final.to_excel(w, index=False)
            st.download_button("📊 Descargar Excel", buffer.getvalue(), "reporte.xlsx", use_container_width=True)
    else:
        st.info("Configura la búsqueda a la izquierda y dale a 'Iniciar Análisis'.")
