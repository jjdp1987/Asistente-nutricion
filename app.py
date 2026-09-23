import streamlit as st
import os
import requests
import time
from google import genai
from dotenv import load_dotenv

# 1. Configuración visual de la página
st.set_page_config(page_title="Radar de Nutrición AI", page_icon="🔬", layout="centered")
st.title("🔬 Radar de Investigación Deportiva")
st.markdown("Buscá los papers más recientes y obtené el análisis clínico al instante.")

# 2. Cargar credenciales
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 3. Panel de control
with st.form("panel_busqueda"):
    # Modificamos el valor por defecto para evitar papers irrelevantes sobre autores con apellido Isak
    tema_busqueda = st.text_input(
        "Términos de búsqueda (recomendado en inglés):", 
        value='"cineanthropometry"[Title/Abstract] OR "ISAK"[Title/Abstract]'
    )
    cantidad_papers = st.slider("Cantidad de estudios a analizar:", min_value=1, max_value=10, value=3)
    boton_buscar = st.form_submit_button("Buscar y Analizar 🚀")

# 4. Motor de búsqueda y análisis
if boton_buscar:
    if not api_key:
        st.error("⚠️ No se encontró la clave de Gemini.")
    else:
        cliente = genai.Client()
        
        with st.spinner("Buscando en la base de datos de PubMed..."):
            url_busqueda = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            parametros_busqueda = {
                "db": "pubmed",
                "term": tema_busqueda,
                "retmode": "json",
                "retmax": cantidad_papers,
                "sort": "date" 
            }
            
            respuesta_busqueda = requests.get(url_busqueda, params=parametros_busqueda)
            ids_encontrados = respuesta_busqueda.json().get("esearchresult", {}).get("idlist", [])

        if not ids_encontrados:
            st.warning("No se encontraron estudios recientes con esos filtros.")
        else:
            with st.spinner(f"Analizando {len(ids_encontrados)} estudios... esto puede tomar unos segundos."):
                ids_juntos = ",".join(ids_encontrados)
                url_textos = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                parametros_textos = {
                    "db": "pubmed",
                    "id": ids_juntos,
                    "retmode": "json"
                }
                respuesta_textos = requests.get(url_textos, params=parametros_textos)
                datos_articulos = respuesta_textos.json().get("result", {})

                st.success("¡Lectura completada! Generando reportes...")
                st.divider()

                for id_paper in ids_encontrados:
                    articulo = datos_articulos.get(id_paper, {})
                    titulo = articulo.get("title", "Sin título")
                    
                    st.subheader(f"📑 {titulo}")
                    
                    prompt = f"""
                    Sos un experto en nutrición deportiva. Analizá el siguiente título de un paper científico recién publicado.
                    Devolveme la información en español, estructurada en estas 3 viñetas cortas y directas al grano:
                    * 🎯 Temática Principal:
                    * 🧪 Posible Intervención/Estudio:
                    * 💡 Relevancia Práctica:
                    
                    Título: {titulo}
                    """
                    
                    max_intentos = 3
                    for intento in range(max_intentos):
                        try:
                            respuesta_ia = cliente.models.generate_content(
                                model='gemini-3.6-flash', 
                                contents=prompt
                            )
                            st.write(respuesta_ia.text)
                            st.markdown(f"**[🔗 Leer paper original](https://pubmed.ncbi.nlm.nih.gov/{id_paper}/)**")
                            
                            # Pausa estratégica normal para no saturar
                            time.sleep(3)
                            break
                            
                        except Exception as e:
                            error_str = str(e)
                            # Capturamos el error 429 y lo obligamos a esperar 30 segundos
                            if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                                st.warning(f"⏳ Pausa de seguridad por límite de IA (Esperando 30 segundos...).")
                                time.sleep(32)
                            elif '503' in error_str or 'UNAVAILABLE' in error_str:
                                time.sleep(5)
                            else:
                                st.error(f"Error al analizar con IA: {e}")
                                break
                    st.divider()