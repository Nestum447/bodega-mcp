import re
import tempfile
import unicodedata
import os
from ollama import Client
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# -------------------------------
# CONFIGURACIÓN DE LA APLICACIÓN
# -------------------------------

st.set_page_config(
    page_title="Sistema de Inventario",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Inventario")
st.caption("Control de existencias y ubicaciones de bodega mediante MCP")

SERVER_PATH = Path(__file__).parent / "server.py"


# -------------------------------
# CONEXIÓN CON EL SERVIDOR MCP
# -------------------------------

async def ejecutar_mcp(nombre_herramienta, argumentos=None):
    ruta_datos = st.session_state.get("ruta_datos_mcp")

    argumentos_servidor = [str(SERVER_PATH)]

    if ruta_datos and Path(ruta_datos).exists():
        argumentos_servidor.append(str(ruta_datos))

    parametros = StdioServerParameters(
        command=sys.executable,
        args=argumentos_servidor
    )

    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()

            resultado = await sesion.call_tool(
                nombre_herramienta,
                arguments=argumentos or {}
            )

            if resultado.isError:
                raise RuntimeError(
                    f"El servidor MCP reportó un error en {nombre_herramienta}"
                )

            return resultado


def convertir_respuesta(resultado):
    """Convierte la respuesta de MCP en datos utilizables por Python."""

    datos = getattr(resultado, "structuredContent", None)

    if datos is not None:
        if isinstance(datos, dict):
            for clave in ("result", "data", "inventario"):
                if clave in datos:
                    return convertir_datos(datos[clave])
        return convertir_datos(datos)

    textos = []

    for contenido in resultado.content:
        if hasattr(contenido, "text"):
            textos.append(contenido.text)

    datos_parseados = []

    for texto in textos:
        try:
            datos_parseados.append(json.loads(texto))
        except (json.JSONDecodeError, TypeError):
            continue

    if len(datos_parseados) == 1:
        return convertir_datos(datos_parseados[0])

    return convertir_datos(datos_parseados)


def convertir_datos(datos):
    if isinstance(datos, str):
        try:
            return convertir_datos(json.loads(datos))
        except json.JSONDecodeError:
            return datos

    if isinstance(datos, dict):
        for clave in ("result", "data", "inventario"):
            if clave in datos:
                return convertir_datos(datos[clave])

    return datos


def consultar_inventario():
    resultado = asyncio.run(
        ejecutar_mcp("listar_inventario")
    )

    datos = convertir_respuesta(resultado)

    if isinstance(datos, dict):
        datos = [datos]

    if not isinstance(datos, list):
        raise ValueError("La respuesta no contiene una lista de productos.")

    registros = []

    for producto in datos:
        if isinstance(producto, dict):
            registros.append(producto)
        elif isinstance(producto, str):
            try:
                registro = json.loads(producto)
                if isinstance(registro, dict):
                    registros.append(registro)
            except json.JSONDecodeError:
                continue

    return pd.DataFrame(registros)


# -------------------------------
# CARGA DE DATOS
# -------------------------------

# ---------- CARGA Y NORMALIZACION DE ARCHIVOS ----------

def normalizar_encabezado(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", texto)


ALIAS_COLUMNAS = {
    "codigo": [
        "codigo", "codigoproducto", "sku", "material",
        "item", "articulo", "productcode", "partnumber"
    ],
    "producto": [
        "producto", "descripcion", "descripcionmaterial",
        "articulo", "nombre", "product", "description"
    ],
    "existencia": [
        "existencia", "existencias", "stock", "cantidad",
        "cantidaddisponible", "disponible", "inventory",
        "onhand", "qty", "quantity"
    ],
    "ubicacion": [
        "ubicacion", "posicion", "rack", "bin",
        "location", "warehousebin"
    ],
    "costo_unitario": [
        "costounitario", "costounit", "preciocosto",
        "cost", "unitcost", "costoperunit"
    ],

   "fecha_recibo": [
        "fechaderecibo",
        "fecharecibo",
        "fechaderecepcion",
        "fecharecepcion",
        "fechaingreso",
        "receiptdate",
        "receivingdate"
    ]

}


def detectar_columna(columnas, campo):
    columnas_normalizadas = {
        columna: normalizar_encabezado(columna)
        for columna in columnas
    }

    for alias in ALIAS_COLUMNAS[campo]:
        for columna, normalizada in columnas_normalizadas.items():
            if normalizada == alias:
                return columna

    return "— No asignar —"


def leer_archivo_inventario(archivo):
    extension = Path(archivo.name).suffix.lower()

    if extension == ".xlsx":
        return pd.read_excel(archivo, dtype=str)

    if extension == ".csv":
        try:
            archivo.seek(0)
            return pd.read_csv(
                archivo, dtype=str, sep=None,
                engine="python", encoding="utf-8-sig"
            )
        except UnicodeDecodeError:
            archivo.seek(0)
            return pd.read_csv(
                archivo, dtype=str, sep=None,
                engine="python", encoding="latin-1"
            )

    raise ValueError("Formato no compatible. Utiliza Excel .xlsx o CSV.")


st.divider()
st.subheader("📂 Cargar inventario desde un archivo")

archivo_inventario = st.file_uploader(
    "Selecciona tu archivo Excel o CSV",
    type=["xlsx", "csv"],
    key="archivo_inventario"
)

if archivo_inventario is not None:
    try:
        df_original = leer_archivo_inventario(archivo_inventario)
        df_original.columns = [
            str(columna).strip()
            for columna in df_original.columns
        ]

        if df_original.empty:
            st.warning("El archivo no contiene registros.")
        else:
            columnas_archivo = list(df_original.columns)
            opciones_columnas = [
                "— No asignar —"
            ] + columnas_archivo

            st.success(
                f"Archivo leído: {len(df_original):,} filas "
                f"y {len(columnas_archivo)} columnas."
            )

            with st.expander("Vista previa del archivo", expanded=True):
                st.dataframe(
                    df_original.head(10),
                    hide_index=True,
                    use_container_width=True
                )

            st.markdown("**Confirma qué columna corresponde a cada campo.**")

            with st.form("formulario_mapeo_inventario"):
                c1, c2 = st.columns(2)

                with c1:
                    col_codigo = st.selectbox(
                        "Código del producto",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "codigo")
                        )
                    )

                    col_producto = st.selectbox(
                        "Descripción del producto",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "producto")
                        )
                    )

                    col_existencia = st.selectbox(
                        "Cantidad / existencia",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "existencia")
                        )
                    )

               
                with c2:
                    col_ubicacion = st.selectbox(
                        "Ubicación (opcional)",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "ubicacion")
                        )
                    )

                    col_costo = st.selectbox(
                        "Costo unitario (opcional)",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "costo_unitario")
                        )
                    )

                    col_fecha_recibo = st.selectbox(
                        "Fecha de recibo (opcional)",
                        opciones_columnas,
                        index=opciones_columnas.index(
                            detectar_columna(columnas_archivo, "fecha_recibo")
                        )
                    )

                aplicar_archivo = st.form_submit_button(
                    "✅ Aplicar archivo al inventario",
                    type="primary"
                )

            if aplicar_archivo:
                if "— No asignar —" in (
                    col_codigo, col_producto, col_existencia
                ):
                    st.error(
                        "Debes asignar las columnas de código, "
                        "producto y existencia."
                    )
                elif len({
                    col_codigo, col_producto, col_existencia
                }) < 3:
                    st.error(
                        "Código, producto y existencia deben "
                        "ser columnas diferentes."
                    )
                else:
                    df_normalizado = pd.DataFrame({
                        "codigo": (
                            df_original[col_codigo]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                        ),
                        "producto": (
                            df_original[col_producto]
                            .fillna("")
                            .astype(str)
                            .str.strip()
                        ),
                        "existencia": pd.to_numeric(
                            df_original[col_existencia]
                            .astype(str)
                            .str.replace(",", "", regex=False)
                            .str.strip(),
                            errors="coerce"
                        ).fillna(0)
                    })

                    if col_ubicacion != "— No asignar —":
                        df_normalizado["ubicacion"] = (
                            df_original[col_ubicacion]
                            .fillna("Sin ubicación")
                            .astype(str)
                            .str.strip()
                        )

# Fecha de recibo opcional
                    if col_fecha_recibo != "— No asignar —":
                        fechas = pd.to_datetime(
                            df_original[col_fecha_recibo],
                            errors="coerce",
                            dayfirst=True
                        )

                        df_normalizado["fecha_recibo"] = (
                            fechas.dt.strftime("%Y-%m-%d")
                        )




                    
                    else:
                        df_normalizado["ubicacion"] = "Sin ubicación"

                    if col_costo != "— No asignar —":
                        df_normalizado["costo_unitario"] = pd.to_numeric(
                            df_original[col_costo]
                            .astype(str)
                            .str.replace(",", "", regex=False)
                            .str.strip(),
                            errors="coerce"
                        )

                    df_normalizado["ubicacion"] = (
                        df_normalizado["ubicacion"]
                        .replace("", "Sin ubicación")
                    )

                    # El mismo conjunto de datos se utiliza en la
                    # interfaz y se entrega al servidor MCP como JSON.
                    registros = json.loads(
                        df_normalizado.to_json(
                            orient="records",
                            force_ascii=False
                        )
                    )

                    archivo_temporal = tempfile.NamedTemporaryFile(
                        mode="w",
                        suffix=".json",
                        encoding="utf-8",
                        delete=False
                    )

                    with archivo_temporal:
                        json.dump(
                            registros,
                            archivo_temporal,
                            ensure_ascii=False
                        )

                    ruta_anterior = st.session_state.get(
                        "ruta_datos_mcp"
                    )

                    st.session_state["ruta_datos_mcp"] = (
                        archivo_temporal.name
                    )
                    st.session_state["inventario"] = df_normalizado

                    if ruta_anterior and ruta_anterior != archivo_temporal.name:
                        try:
                            Path(ruta_anterior).unlink(missing_ok=True)
                        except OSError:
                            pass

                    st.session_state["nombre_archivo_inventario"] = (
                        archivo_inventario.name
                    )

                    st.success(
                        "Inventario aplicado correctamente. "
                        "La tabla utilizará los datos del archivo."
                    )
                    st.rerun()

    except Exception as error:
        st.error(f"No se pudo procesar el archivo: {error}")






if "inventario" not in st.session_state:
    st.session_state.inventario = None

if st.button("🔄 Actualizar inventario"):
    st.session_state.inventario = None

if st.session_state.inventario is None:
    try:
        with st.spinner("Consultando el servidor MCP..."):
            st.session_state.inventario = consultar_inventario()
    except Exception as error:
        st.error(f"No se pudo consultar el inventario: {error}")
        st.stop()

df = st.session_state.inventario.copy()

# -------------------------------
# CALCULO DE AGING
# -------------------------------

if "fecha_recibo" in df.columns:
    df["fecha_recibo"] = pd.to_datetime(
        df["fecha_recibo"],
        errors="coerce",
        dayfirst=True
    )

    fecha_actual = pd.Timestamp.today().normalize()

    df["aging_dias"] = (
        fecha_actual - df["fecha_recibo"].dt.normalize()
    ).dt.days

    df["rango_aging"] = pd.cut(
        df["aging_dias"],
        bins=[-1, 30, 60, 90, float("inf")],
        labels=[
            "0-30 días",
            "31-60 días",
            "61-90 días",
            "Más de 90 días"
        ]
    )
else:
    df["fecha_recibo"] = pd.NaT
    df["aging_dias"] = float("nan")
    df["rango_aging"] = None






if df.empty:
    st.warning("No se encontraron registros de inventario.")
    st.stop()

columnas = ["codigo", "producto", "ubicacion", "existencia"]
faltantes = [col for col in columnas if col not in df.columns]

if faltantes:
    st.error(f"Faltan columnas en la respuesta MCP: {faltantes}")
    st.stop()

df["existencia"] = pd.to_numeric(
    df["existencia"], errors="coerce"
).fillna(0)

df["estado"] = df["existencia"].apply(
    lambda cantidad:
        "Sin existencias" if cantidad <= 0
        else "Stock bajo" if cantidad <= 20
        else "Disponible"
)


# -------------------------------
# INDICADORES PRINCIPALES
# -------------------------------

total_productos = len(df)
total_unidades = int(df["existencia"].sum())
ubicaciones_vacias = int((df["existencia"] <= 0).sum())
productos_stock_bajo = int(
    ((df["existencia"] > 0) & (df["existencia"] <= 20)).sum()
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("📋 Productos registrados", total_productos)
c2.metric("📦 Unidades disponibles", f"{total_unidades:,}")
c3.metric("⚠️ Sin existencias", ubicaciones_vacias)
c4.metric("🔎 Stock bajo", productos_stock_bajo)

st.divider()


# -------------------------------
# BÚSQUEDA Y FILTROS
# -------------------------------

st.subheader("🔍 Consultar inventario")

f1, f2 = st.columns([2, 1])

with f1:
    busqueda = st.text_input(
        "Buscar producto",
        placeholder="Escribe un código o nombre..."
    )

with f2:
    filtro_estado = st.selectbox(
        "Filtrar por estado",
        ["Todos", "Disponible", "Stock bajo", "Sin existencias"]
    )

filtrado = df.copy()

if busqueda:
    coincidencia = (
        filtrado["codigo"].astype(str).str.contains(
            busqueda, case=False, na=False
        )
        | filtrado["producto"].astype(str).str.contains(
            busqueda, case=False, na=False
        )
    )
    filtrado = filtrado[coincidencia]

if filtro_estado != "Todos":
    filtrado = filtrado[filtrado["estado"] == filtro_estado]


# -------------------------------
# TABLA DE INVENTARIO
# -------------------------------

st.dataframe(
     filtrado[
        [
            "codigo",
            "producto",
            "ubicacion",
            "existencia",
            "fecha_recibo",
            "aging_dias",
            "rango_aging",
            "estado"
        ]
    ],
    hide_index=True,
    use_container_width=True,
    column_config={
        "codigo": st.column_config.TextColumn("Código"),
        "producto": st.column_config.TextColumn("Producto"),
        "ubicacion": st.column_config.TextColumn("Ubicación"),
        "existencia": st.column_config.NumberColumn(
            "Existencias", format="%d"
        ),
        "estado": st.column_config.TextColumn("Estado"),

         "fecha_recibo": st.column_config.DateColumn(
            "Fecha de recibo",
            format="DD/MM/YYYY"
        ),
        "aging_dias": st.column_config.NumberColumn(
            "Aging (días)",
            format="%d"
        ),
        "rango_aging": st.column_config.TextColumn(
            "Rango de antigüedad"
        )

        
    }
)

st.caption(f"Se muestran {len(filtrado)} de {total_productos} productos.")

# -------------------------------
# UBICACIONES SIN EXISTENCIAS
# -------------------------------

with st.expander("📍 Ver ubicaciones sin existencias"):
    vacios = df[df["existencia"] <= 0][
        ["codigo", "producto", "ubicacion", "existencia"]
    ]

    if vacios.empty:
        st.success("No hay ubicaciones sin existencias.")
    else:
        st.dataframe(
            vacios,
            hide_index=True,
            use_container_width=True
        )

# -------------------------------
# DESCARGAR INVENTARIO
# -------------------------------

archivo_csv = filtrado.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="📥 Descargar inventario en CSV",
    data=archivo_csv,
    file_name="inventario_bodega.csv",
    mime="text/csv"
)

# -------------------------------
# ASISTENTE IA CON OLLAMA CLOUD + MCP
# -------------------------------

def obtener_configuracion_ollama():
    api_key = st.secrets.get(
        "OLLAMA_API_KEY",
        os.environ.get("OLLAMA_API_KEY", "")
    )

    modelo = st.secrets.get(
        "OLLAMA_MODEL",
        os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")
    )

    if not api_key:
        raise ValueError(
            "Falta configurar OLLAMA_API_KEY en los Secrets de Streamlit."
        )

    cliente = Client(
        host="https://ollama.com",
        headers={"Authorization": f"Bearer {api_key}"}
    )

    return cliente, modelo


HERRAMIENTAS_IA = [
    {
        "type": "function",
        "function": {
            "name": "listar_inventario",
            "description": (
                "Obtiene todos los productos registrados, "
                "sus ubicaciones y sus existencias."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_producto",
            "description": (
                "Consulta un producto usando su código exacto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {
                        "type": "string",
                        "description": "Código del producto, por ejemplo A100."
                    }
                },
                "required": ["codigo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ubicaciones_vacias",
            "description": (
                "Encuentra los productos cuya existencia es cero. "
                "La herramienta devuelve la ubicación y el producto."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


def ejecutar_herramienta_ia(nombre, argumentos):
    
def ejecutar_herramienta_ia(nombre, argumentos):
    herramientas_permitidas = {
        "listar_inventario",
        "consultar_producto",
        "ubicaciones_vacias"
    }

    if nombre not in herramientas_permitidas:
        raise ValueError(f"Herramienta no permitida: {nombre}")

    resultado = asyncio.run(
        ejecutar_mcp(nombre, argumentos)
    )

    datos = convertir_respuesta(resultado)

    # Los cálculos del inventario se realizan con Python,
    # no con la IA.
    if nombre == "listar_inventario":

        if isinstance(datos, dict):
            datos = [datos]

        if not isinstance(datos, list):
            raise ValueError(
                "La herramienta no devolvió una lista de registros."
            )

        registros = [
            producto for producto in datos
            if isinstance(producto, dict)
        ]

        # Obtener las existencias y convertirlas a números.
        existencias = pd.to_numeric(
            pd.Series([
                producto.get("existencia", 0)
                for producto in registros
            ]).astype(str).str.replace(
                ",", "", regex=False
            ).str.strip(),
            errors="coerce"
        ).fillna(0)

        total_registros = len(registros)
        total_unidades = float(existencias.sum())

        # Evitar decimales innecesarios cuando el total es entero.
        if total_unidades.is_integer():
            total_unidades = int(total_unidades)

        respuesta = {
            "resumen_calculado_por_python": {
                "total_registros": total_registros,
                "total_unidades": total_unidades,
                "criterio": (
                    "total_registros cuenta las filas del inventario; "
                    "total_unidades suma la columna existencia."
                )
            },
            "registros": registros
        }

        return json.dumps(
            respuesta,
            ensure_ascii=False,
            default=str
        )

    return json.dumps(
        datos,
        ensure_ascii=False,
        default=str
    )

def consultar_ia(pregunta):
    cliente, modelo = obtener_configuracion_ollama()

    instrucciones = (
        "Eres un asistente inteligente de inventario de bodega. "
        "Responde siempre en español, de forma clara y profesional. "
        "Utiliza las herramientas MCP para consultar datos reales "
        "cuando el usuario pregunte sobre productos, existencias "
        "o ubicaciones. No inventes códigos, cantidades ni ubicaciones. "
        "Interpreta las preguntas de seguimiento usando el historial "
        "de conversación. Si el usuario dice 'ellos', 'esos productos', "
        "'allí' o '¿y dónde?', utiliza el contexto anterior para entender "
        "a qué se refiere. Si falta información, pregunta al usuario. "
        "La herramienta ubicaciones_vacias identifica productos con "
        "existencia cero; no confirma que el espacio físico esté libre."
        "Cuando consultes la herramienta listar_inventario, utiliza los campos total_registros y total_unidades del objeto resumen_calculado_por_python para responder preguntas sobre cantidades totales. Estos valores han sido calculados mediante Python y son la fuente de referencia para los totales. No vuelvas a sumar manualmente los registros ni estimes cantidades. Si preguntan cuántos productos hay, distingue entre número de registros y total de unidades. Responde con el valor correspondiente al significado de la pregunta."
    )

    # Recuperar el historial de la sesión.
    # La pregunta actual ya se agregó en el bloque de la interfaz.
    historial = st.session_state.historial_ia[-12:]

    mensajes = [
        {
            "role": "system",
            "content": instrucciones
        }
    ]

    # Enviar las últimas 12 intervenciones como contexto.
    for elemento in historial:
        mensajes.append({
            "role": elemento["role"],
            "content": elemento["content"]
        })

    # La IA puede consultar herramientas MCP.
    for _ in range(5):
        respuesta = cliente.chat(
            model=modelo,
            messages=mensajes,
            tools=HERRAMIENTAS_IA
        )

        mensaje = respuesta.message
        llamadas = mensaje.tool_calls or []

        # Si la IA no necesita herramientas, responder al usuario.
        if not llamadas:
            return (
                mensaje.content
                or "No se recibió una respuesta de la IA."
            )

        # Conservar el mensaje que solicita las herramientas.
        mensajes.append(mensaje)

        # Ejecutar cada herramienta solicitada por la IA.
        for llamada in llamadas:
            nombre = llamada.function.name
            argumentos = llamada.function.arguments or {}

            try:
                resultado = ejecutar_herramienta_ia(
                    nombre,
                    argumentos
                )
            except Exception as error:
                resultado = json.dumps({
                    "error": str(error)
                }, ensure_ascii=False)

            mensajes.append({
                "role": "tool",
                "tool_name": nombre,
                "content": resultado
            })

    return (
        "La consulta necesitó más pasos de los permitidos. "
        "Intenta formular una pregunta más específica."
    )


# -------------------------------
# INTERFAZ DEL ASISTENTE
# -------------------------------

st.divider()
st.header("🤖 Asistente inteligente de inventario")
st.caption(
    "Pregunta sobre productos, códigos, existencias y ubicaciones. "
    "La IA puede consultar el servidor MCP."
)

if "historial_ia" not in st.session_state:
    st.session_state.historial_ia = []

for mensaje in st.session_state.historial_ia:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

pregunta = st.chat_input(
    "Ejemplo: ¿Qué productos están agotados?"
)

if pregunta:
    st.session_state.historial_ia.append({
        "role": "user",
        "content": pregunta
    })

    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Consultando Ollama Cloud y MCP..."):
                respuesta_ia = consultar_ia(pregunta)

            st.markdown(respuesta_ia)

            st.session_state.historial_ia.append({
                "role": "assistant",
                "content": respuesta_ia
            })

        except Exception as error:
            st.error(
                "No se pudo completar la consulta con la IA. "
                f"Detalle: {error}"
            )
