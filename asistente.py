import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google import genai
from google.genai import errors
from dotenv import load_dotenv

# 1. Despertar al asistente y cargar entorno
load_dotenv()
cliente = genai.Client()

# Levantar las credenciales del archivo .env
email_usuario = os.getenv("EMAIL_USUARIO")
email_clave = os.getenv("EMAIL_CLAVE")

print("🔎 Buscando estudios en PubMed...")

# 2. Búsqueda en PubMed
url_busqueda = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
parametros_busqueda = {
    "db": "pubmed",
    "term": '("sports nutrition"[Title/Abstract] OR ("muscle hypertrophy"[Title/Abstract] AND "exercise"[Title/Abstract]) OR "cineanthropometry"[Title/Abstract])',
    "retmode": "json",
    "retmax": 3, # Ahora pedimos 3 estudios para el reporte
    "sort": "date" 
}

respuesta_busqueda = requests.get(url_busqueda, params=parametros_busqueda)
ids_encontrados = respuesta_busqueda.json().get("esearchresult", {}).get("idlist", [])

if not ids_encontrados:
    print("❌ No se encontraron estudios hoy.")
else:
    ids_juntos = ",".join(ids_encontrados)
    url_textos = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    parametros_textos = {
        "db": "pubmed",
        "id": ids_juntos,
        "retmode": "json"
    }
    
    respuesta_textos = requests.get(url_textos, params=parametros_textos)
    datos_articulos = respuesta_textos.json().get("result", {})

    # Variable donde iremos armando el cuerpo del correo
    mensaje_final = "Hola! Acá tenés los últimos estudios analizados por tu asistente:\n\n"

    # 3. Leer y Resumir 
    for id_paper in ids_encontrados:
        articulo = datos_articulos.get(id_paper, {})
        titulo = articulo.get("title", "Sin título")
        
        print(f"🧠 Analizando: {titulo[:50]}...") # Imprime solo un pedacito en consola para que veas que avanza
        
        prompt = f"""
        Sos un experto en nutrición deportiva. Analizá el siguiente título de un paper científico recién publicado.
        Como PubMed a veces no entrega el resumen completo gratis, inferí de qué trata basándote en el título.
        
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
                # En lugar de imprimirlo, lo sumamos al correo
                mensaje_final += f"📑 TÍTULO: {titulo}\n"
                mensaje_final += respuesta_ia.text + "\n"
                mensaje_final += f"🔗 Link: https://pubmed.ncbi.nlm.nih.gov/{id_paper}/\n"
                mensaje_final += "-" * 50 + "\n\n"
                break
                
            except errors.ServerError as e:
                print(f"   ⚠️ Servidor ocupado. Esperando 5 segundos...")
                time.sleep(5)
            except Exception as e:
                print(f"   ❌ Error con IA: {e}")
                break

    # 4. Enviar el correo
    print("📧 Enviando el reporte a tu bandeja de entrada...")
    try:
        msg = MIMEMultipart()
        msg['From'] = email_usuario
        msg['To'] = email_usuario # Te lo enviás a vos mismo
        msg['Subject'] = "📚 Novedades Científicas: Nutrición Deportiva"
        
        # Adjuntamos el texto al mensaje
        msg.attach(MIMEText(mensaje_final, 'plain', 'utf-8'))
        
        # Nos conectamos a Gmail y lo mandamos
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(email_usuario, email_clave)
        servidor.send_message(msg)
        servidor.quit()
        print("✅ ¡Correo enviado exitosamente! Revisá tu Gmail.")
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")