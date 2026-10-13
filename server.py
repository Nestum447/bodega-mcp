
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("BodegaInventario")

# Datos de prueba
inventario = [
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


@mcp.tool()
def consultar_producto(codigo: str) -> dict:
    """Consulta un producto por su codigo."""
    for item in inventario:
        if item["codigo"].upper() == codigo.upper():
            return item

    return {"mensaje": "Producto no encontrado"}


@mcp.tool()
def ubicaciones_vacias() -> list:
    """Busca productos con existencia cero."""
    return [
        {
            "ubicacion": item["ubicacion"],
            "producto": item["producto"]
        }
        for item in inventario
        if item["existencia"] == 0
    ]


@mcp.tool()
def listar_inventario() -> list:
    """Lista todos los productos."""
    return inventario


if __name__ == "__main__":
    mcp.run(transport="stdio")

