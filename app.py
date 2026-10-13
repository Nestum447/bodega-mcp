
import asyncio
import sys
from pathlib import Path

import streamlit as st
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("server.py")


async def ejecutar_herramienta(nombre, argumentos=None):
    parametros = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)]
    )

    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()

            resultado = await sesion.call_tool(
                nombre,
                argumentos or {}
            )

            if resultado.isError:
                raise RuntimeError("Error al ejecutar herramienta MCP")

            return [
                bloque.text
                for bloque in resultado.content
                if hasattr(bloque, "text")
            ]


def consultar(nombre, argumentos=None):
    return asyncio.run(
        ejecutar_herramienta(nombre, argumentos)
    )


st.set_page_config(
    page_title="Inventario de Bodega",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Inventario")
st.caption("Demo conectada mediante MCP")

opcion = st.sidebar.selectbox(
    "Selecciona una operación",
    [
        "Consultar producto",
        "Ubicaciones vacías",
        "Inventario completo"
    ]
)

if opcion == "Consultar producto":
    codigo = st.text_input("Código del producto", "A100")

    if st.button("Consultar"):
        try:
            resultado = consultar(
                "consultar_producto",
                {"codigo": codigo}
            )
            st.json(resultado)
        except Exception as error:
            st.error(f"Error: {error}")

elif opcion == "Ubicaciones vacías":
    if st.button("Buscar ubicaciones"):
        try:
            resultado = consultar("ubicaciones_vacias")
            st.json(resultado)
        except Exception as error:
            st.error(f"Error: {error}")

else:
    if st.button("Mostrar inventario"):
        try:
            resultado = consultar("listar_inventario")
            st.json(resultado)
        except Exception as error:
            st.error(f"Error: {error}")

