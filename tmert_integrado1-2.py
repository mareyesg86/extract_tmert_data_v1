import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import openai
import pandas as pd
from pathlib import Path
import json
import os
import configparser
import threading

# Intentar importar dotenv, pero continuar si no está disponible
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    print("Módulo 'python-dotenv' no instalado. Las variables de entorno no serán cargadas automáticamente.")

class TmertApp:
    def __init__(self, root):
        # Cargar configuración
        self.config = self.cargar_configuracion()
        
        # Configurar la ventana principal
        self.root = root
        self.root.title("Procesador de Matrices TMERT")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.filepath_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Listo para procesar archivos")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.openai_key_var = tk.StringVar(value=self.config.get('openai', 'api_key', fallback=''))
        self.sheet_var = tk.StringVar(value="1")
        
        # Crear interfaz
        self.crear_interfaz()
        
    def cargar_configuracion(self):
        # Cargar variables de entorno si dotenv está disponible
        if HAS_DOTENV:
            load_dotenv()
        
        # Crear o cargar archivo de configuración
        config = configparser.ConfigParser()
        config_path = Path.home() / 'tmert_config.ini'
        
        if config_path.exists():
            config.read(config_path)
        else:
            # Configuración predeterminada
            config['openai'] = {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': 'gpt-4o',
                'temperature': '0.1'
            }
            
            # Guardar configuración
            with open(config_path, 'w') as configfile:
                config.write(configfile)
                
        # Configurar OpenAI si hay clave API
        api_key = config.get('openai', 'api_key', fallback=os.getenv('OPENAI_API_KEY', ''))
        if api_key:
            openai.api_key = api_key
            
        return config
        
    def guardar_configuracion(self):
        config_path = Path.home() / 'tmert_config.ini'
        
        # Actualizar valores de configuración
        self.config['openai']['api_key'] = self.openai_key_var.get()
        
        # Guardar configuración
        with open(config_path, 'w') as configfile:
            self.config.write(configfile)
            
        # Actualizar OpenAI API key
        openai.api_key = self.openai_key_var.get()
        messagebox.showinfo("Configuración", "Configuración guardada correctamente")
        
    def crear_interfaz(self):
        # Crear pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Pestaña principal
        tab_main = ttk.Frame(notebook)
        notebook.add(tab_main, text="Procesamiento")
        
        # Pestaña de configuración
        tab_config = ttk.Frame(notebook)
        notebook.add(tab_config, text="Configuración")
        
        # --- Pestaña principal ---
        frame_file = ttk.LabelFrame(tab_main, text="Selección de archivo")
        frame_file.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Entry(frame_file, textvariable=self.filepath_var, width=50).pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        ttk.Button(frame_file, text="Examinar", command=self.seleccionar_archivo).pack(side=tk.LEFT, padx=5, pady=5)
        
        frame_process = ttk.LabelFrame(tab_main, text="Procesamiento")
        frame_process.pack(fill=tk.BOTH, padx=10, pady=10, expand=True)
        
        frame_options = ttk.Frame(frame_process)
        frame_options.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(frame_options, text="Hoja:").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Combobox(frame_options, textvariable=self.sheet_var, values=["1", "2"], width=5).pack(side=tk.LEFT, padx=5, pady=5)
        
        frame_buttons = ttk.Frame(frame_process)
        frame_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_buttons, text="Procesar datos generales (hoja 1)", 
                   command=lambda: self.iniciar_proceso(self.procesar_datos_generales)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_buttons, text="Procesar tareas (hoja 2)", 
                   command=lambda: self.iniciar_proceso(self.procesar_tareas)).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(frame_buttons, text="Procesar todo", 
                   command=self.procesar_todo).pack(side=tk.LEFT, padx=5, pady=5)
        
        frame_status = ttk.Frame(tab_main)
        frame_status.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame_status, textvariable=self.status_var).pack(side=tk.TOP, padx=5, pady=5, anchor=tk.W)
        self.progress_bar = ttk.Progressbar(frame_status, variable=self.progress_var, maximum=100.0)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # --- Pestaña de configuración ---
        frame_api = ttk.LabelFrame(tab_config, text="Configuración de OpenAI")
        frame_api.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame_api, text="API Key:").pack(anchor=tk.W, padx=5, pady=5)
        ttk.Entry(frame_api, textvariable=self.openai_key_var, width=50, show="*").pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(frame_api, text="Modelo:").pack(anchor=tk.W, padx=5, pady=5)
        model_var = tk.StringVar(value=self.config.get('openai', 'model', fallback='gpt-4o'))
        ttk.Combobox(frame_api, textvariable=model_var, values=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"], 
                    state="readonly").pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(frame_api, text="Guardar configuración", command=self.guardar_configuracion).pack(anchor=tk.E, padx=5, pady=10)
        
    def seleccionar_archivo(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Archivos Excel", "*.xlsx *.xls")]
        )
        if filepath:
            self.filepath_var.set(filepath)
            self.status_var.set(f"Archivo seleccionado: {Path(filepath).name}")
            
    def iniciar_proceso(self, funcion_proceso):
        if not self.filepath_var.get():
            messagebox.showerror("Error", "Por favor seleccione un archivo Excel primero")
            return
            
        if not openai.api_key:
            messagebox.showerror("Error", "Por favor configure la API Key de OpenAI en la pestaña de Configuración")
            return
            
        # Iniciar proceso en un hilo separado para no bloquear la interfaz
        self.progress_var.set(0)
        self.status_var.set("Procesando...")
        
        thread = threading.Thread(target=funcion_proceso)
        thread.daemon = True
        thread.start()
        
    def actualizar_estado(self, mensaje, progreso=None):
        self.status_var.set(mensaje)
        if progreso is not None:
            self.progress_var.set(progreso)
        self.root.update_idletasks()
        
    def procesar_datos_generales(self):
        try:
            filepath = self.filepath_var.get()
            hoja = self.sheet_var.get()
            
            self.actualizar_estado(f"Extrayendo texto de la hoja {hoja}...", 10)
            texto = self.extraer_texto_desde_excel(filepath, hoja)
            
            self.actualizar_estado("Consultando a OpenAI...", 30)
            json_resultado = self.consultar_openai(texto)
            
            if not json_resultado:
                self.actualizar_estado("Error al procesar con OpenAI", 0)
                return
            
            # Convertir resultado JSON a DataFrame
            self.actualizar_estado("Procesando resultados...", 70)
            datos_dict = json.loads(json_resultado)
            
            # Crear DataFrame con los datos generales (una fila, múltiples columnas)
            df_general = pd.DataFrame([datos_dict])
            
            # Guardar en archivo Excel (se creará si no existe)
            output_path = Path(filepath).with_name("resultados_tmert.xlsx")
            
            # Verificar si el archivo ya existe para preservar otras hojas
            if output_path.exists():
                with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_general.to_excel(writer, sheet_name='Datos Generales', index=False)
            else:
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    df_general.to_excel(writer, sheet_name='Datos Generales', index=False)
            
            self.actualizar_estado(f"Datos generales guardados en: {output_path}", 100)
            messagebox.showinfo("Procesamiento completo", f"Datos extraídos y guardados en la hoja 'Datos Generales' de:\n{output_path}")
            
        except Exception as e:
            self.actualizar_estado(f"Error: {str(e)}", 0)
            messagebox.showerror("Error en procesamiento", str(e))
    
    def procesar_tareas(self):
        try:
            filepath = self.filepath_var.get()
            
            self.actualizar_estado("Leyendo hoja de tareas...", 20)
            
            # Leer encabezados (primeras 2 filas)
            encabezados_raw = pd.read_excel(filepath, sheet_name="2", header=None, skiprows=11, nrows=2, dtype=str).fillna("")
            encabezados = []
            
            for col in range(encabezados_raw.shape[1]):
                fila1 = str(encabezados_raw.iat[0, col]).strip()
                fila2 = str(encabezados_raw.iat[1, col]).strip()
                if fila1 and fila2 and fila1 != fila2:
                    encabezados.append(f"{fila1} - {fila2}")
                else:
                    encabezados.append(fila1 or fila2 or f"Col_{col}")
            
            self.actualizar_estado("Procesando datos de tareas...", 50)
            
            # Leer datos de tareas
            tareas = pd.read_excel(filepath, sheet_name="2", header=None, skiprows=13, names=encabezados, dtype=str).fillna("")
            
            # Filtrar filas vacías
            tareas = tareas[tareas.astype(str).apply(lambda x: x.str.strip() != "").any(axis=1)]
            
            # Agregar columnas de riesgos si no existen
            riesgos = ["TRMS", "POSTURA", "MMC LDT", "MMC EA", "VIBRACIONES CC", "VIBRACIONES SMB"]
            for r in riesgos:
                if r not in tareas.columns:
                    tareas[r] = ""
            
            self.actualizar_estado("Exportando resultados...", 80)
            
            # Guardar en el mismo archivo Excel que los datos generales
            output_path = Path(filepath).with_name("resultados_tmert.xlsx")
            
            # Verificar si el archivo ya existe para preservar otras hojas
            if output_path.exists():
                with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    tareas.to_excel(writer, sheet_name='Tareas', index=False)
            else:
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    tareas.to_excel(writer, sheet_name='Tareas', index=False)
            
            self.actualizar_estado(f"Proceso completado. Se encontraron {len(tareas)} tareas.", 100)
            messagebox.showinfo("Procesamiento completo", 
                               f"Se encontraron {len(tareas)} tareas. \nLos datos han sido guardados en la hoja 'Tareas' de:\n{output_path}")
            
        except Exception as e:
            self.actualizar_estado(f"Error: {str(e)}", 0)
            messagebox.showerror("Error en procesamiento de tareas", str(e))
            
    def extraer_texto_desde_excel(self, filepath, hoja):
        try:
            df = pd.read_excel(filepath, sheet_name=hoja, header=None, dtype=str).fillna("")
            texto = df.astype(str).apply(lambda row: " ".join(row), axis=1).str.cat(sep="\n")
            return texto
        except Exception as e:
            raise Exception(f"Error al leer hoja {hoja}: {e}")
    
    def consultar_openai(self, texto):
        try:
            # Obtener configuración de OpenAI
            modelo = self.config.get('openai', 'model', fallback='gpt-4o')
            temperatura = float(self.config.get('openai', 'temperature', fallback='0.1'))
            
            # Prompt base mejorado
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
        except Exception as e:
            messagebox.showerror("Error en consulta a OpenAI", f"Se produjo un error:\n{e}")
            return ""

    def procesar_todo(self):
        """Procesa tanto los datos generales como las tareas en una sola operación"""
        if not self.filepath_var.get():
            messagebox.showerror("Error", "Por favor seleccione un archivo Excel primero")
            return
            
        if not openai.api_key:
            messagebox.showerror("Error", "Por favor configure la API Key de OpenAI en la pestaña de Configuración")
            return
        
        # Iniciar proceso en un hilo separado
        self.progress_var.set(0)
        self.status_var.set("Procesando todo...")
        
        thread = threading.Thread(target=self._procesar_todo_thread)
        thread.daemon = True
        thread.start()
    
    def _procesar_todo_thread(self):
        """Función interna para procesar todo en un hilo separado"""
        try:
            # Primero procesar datos generales
            self.actualizar_estado("Procesando datos generales...", 10)
            
            filepath = self.filepath_var.get()
            
            # Procesar hoja 1 (datos generales)
            texto = self.extraer_texto_desde_excel(filepath, "1")
            
            self.actualizar_estado("Consultando a OpenAI para datos generales...", 20)
            json_resultado = self.consultar_openai(texto)
            
            if not json_resultado:
                self.actualizar_estado("Error al procesar con OpenAI", 0)
                return
            
            # Convertir resultado JSON a DataFrame
            self.actualizar_estado("Procesando resultados de datos generales...", 30)
            datos_dict = json.loads(json_resultado)
            df_general = pd.DataFrame([datos_dict])
            
            # Luego procesar tareas
            self.actualizar_estado("Procesando tareas...", 40)
            
            # Leer encabezados (primeras 2 filas)
            encabezados_raw = pd.read_excel(filepath, sheet_name="2", header=None, skiprows=11, nrows=2, dtype=str).fillna("")
            encabezados = []
            
            for col in range(encabezados_raw.shape[1]):
                fila1 = str(encabezados_raw.iat[0, col]).strip()
                fila2 = str(encabezados_raw.iat[1, col]).strip()
                if fila1 and fila2 and fila1 != fila2:
                    encabezados.append(f"{fila1} - {fila2}")
                else:
                    encabezados.append(fila1 or fila2 or f"Col_{col}")
            
            self.actualizar_estado("Leyendo datos de tareas...", 60)
            
            # Leer datos de tareas
            tareas = pd.read_excel(filepath, sheet_name="2", header=None, skiprows=13, names=encabezados, dtype=str).fillna("")
            
            # Filtrar filas vacías
            tareas = tareas[tareas.astype(str).apply(lambda x: x.str.strip() != "").any(axis=1)]
            
            # Agregar columnas de riesgos si no existen
            riesgos = ["TRMS", "POSTURA", "MMC LDT", "MMC EA", "VIBRACIONES CC", "VIBRACIONES SMB"]
            for r in riesgos:
                if r not in tareas.columns:
                    tareas[r] = ""
            
            # Guardar todo en un solo archivo Excel
            self.actualizar_estado("Guardando resultados en Excel...", 80)
            
            output_path = Path(filepath).with_name("resultados_tmert.xlsx")
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_general.to_excel(writer, sheet_name='Datos Generales', index=False)
                tareas.to_excel(writer, sheet_name='Tareas', index=False)
                
                # Crear una hoja de resumen
                resumen = pd.DataFrame({
                    'Información': [
                        'Fecha de procesamiento',
                        'Empresa',
                        'RUT',
                        'Centro de trabajo',
                        'Total de tareas analizadas'
                    ],
                    'Valor': [
                        pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                        datos_dict.get('empresa_razon_social', ''),
                        datos_dict.get('rut_empresa', ''),
                        datos_dict.get('centro_trabajo', ''),
                        len(tareas)
                    ]
                })
                resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
            self.actualizar_estado(f"Procesamiento completo. Archivo guardado en: {output_path}", 100)
            messagebox.showinfo("Procesamiento completo", 
                               f"Se han procesado los datos generales y {len(tareas)} tareas.\n\nArchivo guardado en:\n{output_path}")
            
        except Exception as e:
            self.actualizar_estado(f"Error durante el procesamiento: {str(e)}", 0)
            messagebox.showerror("Error en procesamiento", str(e))

def main():
    root = tk.Tk()
    app = TmertApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()