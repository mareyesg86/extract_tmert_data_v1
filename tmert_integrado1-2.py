import streamlit as st
import openai
import pandas as pd
from io import BytesIO
import json
import os
from pathlib import Path
import configparser

# Intentar importar dotenv, pero continuar si no está disponible
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Cargar configuración
def cargar_configuracion():
    if HAS_DOTENV:
        load_dotenv()

    config = configparser.ConfigParser()
    config_path = Path.home() / 'tmert_config.ini'

    if config_path.exists():
        config.read(config_path)
    else:
        config['openai'] = {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'model': 'gpt-4o',
            'temperature': '0.1'
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)

    api_key = config.get('openai', 'api_key', fallback=os.getenv('OPENAI_API_KEY', ''))
    if api_key:
        openai.api_key = api_key

    return config

config = cargar_configuracion()

# Función para eliminar columnas vacías
def eliminar_columnas_vacias(df):
    # Eliminar columnas que no tienen ningún valor no vacío
    df = df.loc[:, (df != "").any(axis=0)]
    return df

def extraer_texto_desde_excel(file, hoja):
    df = pd.read_excel(file, sheet_name=hoja, header=None, dtype=str).fillna("")
    texto = df.astype(str).apply(lambda row: " ".join(row), axis=1).str.cat(sep="\n")
    return texto

def consultar_openai(texto):
    modelo = config.get('openai', 'model', fallback='gpt-4o')
    temperatura = float(config.get('openai', 'temperature', fallback='0.1'))

    prompt_base = '''Actúa como un asistente experto en análisis de matrices TMERT.

    Recibirás como entrada el texto crudo extraído desde una hoja de Excel mal estructurada completada manualmente por distintas empresas.

    Tu tarea es identificar y devolver los siguientes campos como JSON limpio:
    - empresa_razon_social
    - rut_empresa
    - actividad_economica
    - codigo_ciiu
    - direccion_matriz
    - comuna_matriz
    - representante_legal
    - centro_trabajo
    - direccion_centro
    - comuna_centro
    - trabajadores_hombres
    - trabajadores_mujeres
    - responsable_nombre
    - responsable_cargo
    - responsable_email
    - responsable_telefono

    No inventes datos. Devuelve "" para campos no encontrados.'''

    respuesta = openai.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": "Eres un asistente experto en matrices TMERT."},
            {"role": "user", "content": prompt_base + "\n\nTexto de entrada:\n" + texto}
        ],
        temperature=temperatura,
        response_format={"type": "json_object"}
    )
    return respuesta.choices[0].message.content

st.title("Procesador de Matrices TMERT")

uploaded_file = st.file_uploader("Carga tu archivo Excel", type="xlsx")

if uploaded_file is not None:
    st.write("Archivo cargado exitosamente.")

    hoja = st.selectbox("Selecciona la hoja a procesar", ["1", "2"])

    if st.button("Procesar datos generales"):
        texto = extraer_texto_desde_excel(uploaded_file, hoja)
        json_resultado = consultar_openai(texto)

        if json_resultado:
            datos_dict = json.loads(json_resultado)
            df_general = pd.DataFrame([datos_dict])

            # Eliminar columnas vacías
            df_general = eliminar_columnas_vacias(df_general)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_general.to_excel(writer, sheet_name='Datos Generales', index=False)
            output.seek(0)

            st.download_button(
                label="Descargar archivo Excel ordenado",
                data=output,
                file_name="resultados_tmert.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Error al procesar con OpenAI")

    if st.button("Procesar tareas"):
        encabezados_raw = pd.read_excel(uploaded_file, sheet_name="2", header=None, skiprows=11, nrows=2, dtype=str).fillna("")
        encabezados = []

        for col in range(encabezados_raw.shape[1]):
            fila1 = str(encabezados_raw.iat[0, col]).strip()
            fila2 = str(encabezados_raw.iat[1, col]).strip()
            if fila1 and fila2 and fila1 != fila2:
                encabezados.append(f"{fila1} - {fila2}")
            else:
                encabezados.append(fila1 or fila2 or f"Col_{col}")

        tareas = pd.read_excel(uploaded_file, sheet_name="2", header=None, skiprows=13, names=encabezados, dtype=str).fillna("")
        tareas = tareas[tareas.astype(str).apply(lambda x: x.str.strip() != "").any(axis=1)]

        riesgos = ["TRMS", "POSTURA", "MMC LDT", "MMC EA", "VIBRACIONES CC", "VIBRACIONES SMB"]
        for r in riesgos:
            if r not in tareas.columns:
                tareas[r] = ""

        # Eliminar columnas vacías
        tareas = eliminar_columnas_vacias(tareas)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            tareas.to_excel(writer, sheet_name='Tareas', index=False)
        output.seek(0)

        st.download_button(
            label="Descargar archivo Excel de tareas",
            data=output,
            file_name="tareas_tmert.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
