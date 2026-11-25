# Procesador de proveedores

MVP local para extraer productos de listas de precios PDF, comparar sus valores
con cargas anteriores y descargar el resultado en Excel. La extracción usa
Gemini; requiere una clave de API propia.

## Puesta en marcha

1. Usá Python 3.10 o superior y creá un entorno virtual dentro del proyecto.
2. Instalá las dependencias:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   ```

3. Copiá `backend\.env.example` a `backend\.env` y completá `GEMINI_API_KEY`.
4. Desde la raíz del proyecto, iniciá la aplicación:

   ```powershell
   uvicorn backend.main:app --reload
   ```

5. Abrí <http://localhost:8000>. La base SQLite `backend\proveedores.db` se
   crea automáticamente al iniciar.

Los endpoints JSON están disponibles en `/api/procesar`, `/api/proveedores` y
`/api/descargar-excel/{lote_id}`.
