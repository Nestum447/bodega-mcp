# bodega-mcp
# 📦 Sistema Inteligente de Inventario de Bodega

Aplicación web para la gestión, consulta y análisis de inventarios mediante **Python, Streamlit, Model Context Protocol (MCP) y Ollama Cloud**.

El sistema permite cargar inventarios desde archivos Excel o CSV, visualizar existencias, consultar productos y ubicaciones, identificar productos agotados y utilizar un asistente de inteligencia artificial para realizar consultas sobre los datos.

## 🎯 Objetivo del proyecto

Desarrollar una herramienta de inventario que integre datos operativos con inteligencia artificial, facilitando el acceso a información de bodega, la identificación de riesgos de abastecimiento y la toma de decisiones basada en datos.

## 🚀 Funcionalidades principales

### 1. Carga de inventario

- Carga de archivos Excel (`.xlsx`) y CSV (`.csv`).
- Vista previa de los datos antes de aplicarlos.
- Asignación de columnas mediante un formulario de mapeo.
- Normalización de los datos para facilitar su consulta.
- Soporte para campos como código, producto, existencia, ubicación y costo unitario.
- Preparación para incorporar campos adicionales, como la fecha de recibo.

### 2. Control de existencias

- Consulta del inventario cargado.
- Búsqueda de productos por código o descripción.
- Identificación de productos sin existencias.
- Identificación de productos con stock bajo.
- Visualización de indicadores generales del inventario.
- Exportación de los resultados a CSV.

### 3. Análisis de antigüedad del inventario (Aging)

La aplicación puede ampliarse para calcular la antigüedad de los productos a partir de su fecha de recibo.

El cálculo se basa en:

**Aging = Fecha actual − Fecha de recibo**

Este análisis permite clasificar el inventario por rangos de antigüedad, por ejemplo:

- 0–30 días.
- 31–60 días.
- 61–90 días.
- Más de 90 días.

La disponibilidad de esta función depende de que el campo de fecha esté incorporado en la versión desplegada.

### 4. Asistente de inteligencia artificial

El sistema integra Ollama Cloud para interpretar preguntas en lenguaje natural y consultar información mediante herramientas MCP.

Ejemplos de consultas:

- ¿Cuántos productos están registrados?
- ¿Cuáles productos tienen existencia cero?
- ¿Qué existencia tiene el código A100?
- ¿En qué ubicación se encuentra un producto?
- ¿Qué productos tienen stock bajo?
- ¿Qué productos tienen más de 90 días de antigüedad? *(cuando el aging esté integrado en las herramientas MCP).*

El asistente utiliza las herramientas disponibles para consultar los datos del inventario y generar respuestas basadas en ellos.

## 🧠 Arquitectura del sistema

La aplicación utiliza una arquitectura que separa la interfaz, los datos, las herramientas de consulta y el modelo de inteligencia artificial.

```text
Usuario
   |
   v
Streamlit
Interfaz web y carga de archivos
   |
   v
Normalización de datos
Excel / CSV
   |
   v
Archivo JSON normalizado
   |
   v
Servidor MCP
Herramientas de consulta
   |
   v
Ollama Cloud
Modelo de inteligencia artificial
   |
   v
Respuesta en lenguaje natural
```

**Componentes principales:**

- **Streamlit:** interfaz web, visualización de datos y controles de usuario.
- **Pandas:** lectura, transformación y análisis de los datos.
- **MCP:** expone herramientas que permiten consultar el inventario desde la IA.
- **Ollama Cloud:** interpreta las preguntas y decide cuándo utilizar las herramientas disponibles.
- **JSON:** permite transferir los registros normalizados entre la aplicación y el servidor MCP.

## 🛠️ Tecnologías utilizadas

| Tecnología | Función |
|---|---|
| Python | Lenguaje principal |
| Streamlit | Interfaz web |
| Pandas | Procesamiento de datos |
| Model Context Protocol (MCP) | Comunicación con herramientas de inventario |
| Ollama Cloud | Inteligencia artificial |
| JSON | Intercambio de datos |
| GitHub | Control de versiones y almacenamiento del código |
| Streamlit Community Cloud | Despliegue web, si se utiliza este servicio |

## 📁 Estructura del proyecto

```text
bodega-mcp/
│
├── app.py
│   └── Interfaz, carga de archivos,
│       indicadores y asistente de IA
│
├── server.py
│   └── Servidor MCP y herramientas
│       de consulta del inventario
│
├── requirements.txt
│   └── Dependencias de Python
│
└── README.md
    └── Documentación del proyecto
```

## ⚙️ Instalación y ejecución local

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/bodega-mcp.git
cd bodega-mcp
```

Reemplaza `TU_USUARIO` por el nombre de tu cuenta de GitHub.

### 2. Crear un entorno virtual

```bash
python -m venv .venv
```

Activar el entorno en Windows:

```bash
.venv\Scripts\activate
```

### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

El archivo de dependencias debe incluir los paquetes utilizados por la aplicación, como Streamlit, Pandas, MCP y el cliente de Ollama, además de las librerías necesarias para leer archivos Excel.

### 4. Configurar Ollama Cloud

La aplicación necesita una clave de API de Ollama Cloud y un modelo compatible con las herramientas utilizadas.

Para una ejecución local, se pueden configurar variables de entorno o utilizar los mecanismos de configuración segura correspondientes.

No publiques la clave de API en el repositorio ni directamente en el código.

### 5. Ejecutar la aplicación

```bash
streamlit run app.py
```

Streamlit mostrará la dirección local para abrir la aplicación en el navegador.

## 🔐 Configuración de secretos

Si la aplicación se despliega en Streamlit Community Cloud, configura las siguientes variables en la sección **Secrets**:

```toml
OLLAMA_API_KEY = "TU_CLAVE_DE_API"
OLLAMA_MODEL = "gpt-oss:20b"
```

El nombre del modelo debe corresponder a uno disponible y compatible con tu cuenta de Ollama Cloud.

La clave debe mantenerse privada.

## 🔄 Flujo de funcionamiento

1. El usuario carga un archivo de inventario.
2. La aplicación identifica las columnas disponibles.
3. El usuario confirma el mapeo de los campos.
4. Los registros se normalizan y se guardan temporalmente en formato JSON.
5. El servidor MCP recibe la ruta del archivo y expone las herramientas de consulta.
6. El usuario consulta el inventario desde la interfaz o mediante el asistente de IA.
7. Ollama Cloud interpreta la pregunta y solicita las herramientas MCP necesarias.
8. La aplicación devuelve los resultados al usuario.

## 📊 Aplicaciones potenciales en operaciones y logística

- Monitoreo de existencias y productos agotados.
- Identificación de inventario con baja disponibilidad.
- Análisis de antigüedad y detección de inventario de lenta rotación.
- Consultas operativas en lenguaje natural.
- Integración futura con costos, valoración de inventario y análisis financiero.
- Base para desarrollar indicadores de abastecimiento y gestión de almacenes.

## ⚠️ Consideraciones

- Los resultados dependen de la calidad y consistencia del archivo cargado.
- La fecha de recibo debe tener un formato reconocible para calcular correctamente el aging.
- Las herramientas MCP deben devolver los campos requeridos para que la IA pueda analizarlos.
- La función de productos con existencia cero no confirma por sí sola que una ubicación física esté libre.
- Los archivos temporales y el estado de sesión no constituyen una base de datos persistente.
- Para un entorno productivo, se recomienda incorporar almacenamiento persistente, validación de datos, control de acceso y registro de operaciones.

## 🔮 Mejoras futuras

- Filtros interactivos por antigüedad, ubicación y categoría.
- Indicadores de inventario con más de 30, 60 y 90 días.
- Valoración económica del inventario.
- Alertas de stock mínimo.
- Historial de movimientos y recibos.
- Integración con bases de datos o sistemas ERP.
- Herramientas MCP especializadas en aging, rotación y riesgo de abastecimiento.

## 👨‍💻 Autoría

Proyecto de desarrollo de una aplicación de inventario inteligente que combina automatización, gestión de datos e inteligencia artificial para apoyar las operaciones de bodega.

**Repositorio:** `bodega-mcp`
