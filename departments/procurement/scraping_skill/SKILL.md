# E-Commerce Universal Extractor Skill

## Description
Esta habilidad permite la extracción masiva y estructurada de datos de productos (precio, nombre, stock) desde múltiples URLs de comercio electrónico. Combina navegación headless asíncrona (Playwright) para la recuperación de contenido y procesamiento LLM para la extracción agnóstica de estructura.

## Usage
Utiliza esta habilidad cuando el usuario solicite información de productos de una lista de URLs, especialmente si las webs son desconocidas o variadas.

## Input Parameters
- `urls`: Lista de strings con las URLs completas de los productos.
- `output_format`: (Opcional) Formato de salida ('csv' o 'json'). Default: 'csv'.
- `concurrency`: (Opcional) Número de workers simultáneos. Default: 5.

## Implementation Steps
1. **Setup**: Verifica que las dependencias estén instaladas.
2. **Fetch**: Ejecuta `scripts/scraper_engine.py` generando `raw_scraping_results.json`.
3. **Parse**: Ejecuta `scripts/llm_parser.py` para procesar el HTML crudo con Gemini.
4. **Verify**: Devuelve el archivo CSV resultante.

## Error Handling
- Si hay bloqueos (403/429), el motor intentará reintentos automáticos con esperas exponenciales.
