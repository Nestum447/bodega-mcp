
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
    parametros = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)]
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
        ["codigo", "producto", "ubicacion", "existencia", "estado"]
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
        "estado": st.column_config.TextColumn("Estado")
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
