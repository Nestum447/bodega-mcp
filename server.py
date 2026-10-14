
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BodegaInventario")


def cargar_inventario():
    """Carga el inventario desde el archivo JSON recibido por la app."""
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1])

        if ruta.exists():
            with ruta.open("r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            if isinstance(datos, list):
                return datos

    # Datos de prueba si todavía no se ha cargado un archivo.
    return [
        {
            "codigo": "A100",
            "producto": "Papel bond",
            "ubicacion": "01-A-01",
            "existencia": 150
        },
        {
            "codigo": "A200",
            "producto": "Carpetas",
            "ubicacion": "01-A-02",
            "existencia": 0
        },
        {
            "codigo": "A300",
            "producto": "Boligrafos",
            "ubicacion": "01-B-01",
            "existencia": 80
        },
        {
            "codigo": "A400",
            "producto": "Archivadores",
            "ubicacion": "01-B-02",
            "existencia": 0
        }
    ]


inventario = cargar_inventario()


@mcp.tool()
def consultar_producto(codigo: str) -> dict:
    """Consulta un producto por su código."""
    for item in inventario:
        if str(item.get("codigo", "")).upper() == codigo.upper():
            return item

    return {"mensaje": "Producto no encontrado"}


@mcp.tool()
def ubicaciones_vacias() -> list:
    """Lista productos cuya existencia es cero o menor."""
    return [
        {
            "codigo": item.get("codigo", ""),
            "ubicacion": item.get("ubicacion", "Sin ubicación"),
            "producto": item.get("producto", "")
        }
        for item in inventario
        if float(item.get("existencia", 0) or 0) <= 0
    ]


@mcp.tool()
def listar_inventario() -> list:
    """Devuelve todos los productos del inventario cargado."""
    return inventario


if __name__ == "__main__":
    mcp.run(transport="stdio")
