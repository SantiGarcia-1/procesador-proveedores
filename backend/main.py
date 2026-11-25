"""API HTTP para procesar listas de precios y descargar comparaciones."""

import logging
import re
import unicodedata
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.genai.errors import APIError

from .database import (
    guardar_y_comparar,
    listar_proveedores,
    obtener_lote_para_exportar,
)
from .excel_builder import generar_excel
from .extractor import extraer_lista_proveedores


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sanear_nombre_archivo(valor: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", valor)
    ascii_base = "".join(
        caracter
        for caracter in sin_acentos
        if not unicodedata.combining(caracter)
    )
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_base).strip("_-")
    return limpio or "proveedor"


app = FastAPI(title="Procesador de listas de proveedores", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.post("/api/procesar")
async def procesar_pdf(
    proveedor: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    nombre = proveedor.strip()
    if not nombre:
        raise HTTPException(status_code=422, detail="Indica el nombre del proveedor.")
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="El archivo debe ser un PDF.")

    try:
        contenido = await file.read()
        if not contenido.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=415, detail="El archivo recibido no es un PDF válido."
            )
    finally:
        await file.close()

    try:
        datos = extraer_lista_proveedores(contenido)
        lote_id = str(uuid.uuid4())
        items = guardar_y_comparar(nombre, datos, lote_id=lote_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except APIError as error:
        logger.exception("No se pudo procesar el PDF del proveedor %s", nombre)
        raise HTTPException(
            status_code=502,
            detail="El servicio de IA no pudo procesar el documento.",
        ) from error

    return {
        "lote_id": lote_id,
        "proveedor": nombre,
        "proveedor_detectado": datos.proveedor_detectado,
        "fecha_documento": datos.fecha_documento,
        "items": items,
    }


@app.get("/api/descargar-excel/{lote_id}")
def descargar_excel(lote_id: str) -> StreamingResponse:
    lote = obtener_lote_para_exportar(lote_id)
    if lote is None:
        raise HTTPException(status_code=404, detail="No se encontró el lote solicitado.")
    proveedor = _sanear_nombre_archivo(lote["proveedor"])
    fecha = _sanear_nombre_archivo(lote["fecha_documento"] or "sin_fecha")
    nombre_archivo = f"{proveedor}_{fecha}.xlsx"
    archivo = generar_excel(lote["items"])
    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}"'
        },
    )


@app.get("/api/proveedores")
def obtener_proveedores() -> dict[str, list[str]]:
    return {"proveedores": listar_proveedores()}


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend",
)
