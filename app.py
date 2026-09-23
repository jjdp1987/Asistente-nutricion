import streamlit as st
import os
import requests
import time
from google import genai
from google.genai import errors
from dotenv import load_dotenv

# 1. Configuración visual de la página
st.set_page_config(page_title="Radar de Nutrición AI", page_icon="🔬", layout="centered")
st.title("🔬 Radar de Investigación Deportiva")
st.markdown("Buscá los papers más recientes y obtené el análisis clínico al instante.")

# 2. Cargar credenciales
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 3. Panel de control (La interfaz de usuario)
with st.form("panel_busqueda"):
    tema_busqueda = st.text_input(
        "Términos de búsqueda (recomendado en inglés):", 
        value='("sports nutrition"[Title/Abstract] OR "muscle hypertrophy"[Title/Abstract])'
    )
    cantidad_papers = st.slider("Cantidad de estudios a analizar:", min_value=1, max_value=10, value=3)
    boton_buscar = st.form_submit_button("Buscar y Analizar 🚀")

# 4. Motor de búsqueda y análisis
if boton_buscar:
    if not api_key:
        st.error("⚠️ No se encontró la clave de Gemini en el archivo .env")
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
            with st.spinner(f"Analizando {len(ids_encontrados)} estudios con Inteligencia Artificial..."):
                ids_juntos = ",".join(ids_encontrados)
                url_textos = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                parametros_textos = {
                    "db": "pubmed",
                    "id": ids_juntos,
                    "retmode": "json"
                }
                respuesta_textos = requests.get(url_textos, params=parametros_textos)
                datos_articulos = respuesta_textos.json().get("result", {})

                st.success("¡Análisis completado!")
                st.divider()

                # Mostrar resultados en pantalla
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
                            st.markdown(f"**[🔗 Leer paper original] (https://pubmed.ncbi.nlm.nih.gov/{id_paper}/)**")
                            break
                        except errors.ServerError:
                            time.sleep(5)
                        except Exception as e:
                            st.error(f"Error al analizar con IA: {e}")
                            break
                    st.divider()