"""Persistencia SQLite y comparación de precios por proveedor."""

import re
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .schemas import ListaProveedoresExtraida


DB_PATH = Path(__file__).with_name("proveedores.db")


def _conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH, timeout=30)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


@contextmanager
def _conexion() -> Iterator[sqlite3.Connection]:
    conexion = _conectar()
    try:
        with conexion:
            yield conexion
    finally:
        conexion.close()


def normalizar_descripcion(descripcion: str) -> str:
    """Normaliza acentos, mayúsculas y puntuación para emparejar descripciones."""
    sin_acentos = unicodedata.normalize("NFKD", descripcion)
    ascii_base = "".join(
        caracter
        for caracter in sin_acentos
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_base.casefold()).strip()


def inicializar_db() -> None:
    """Crea las tablas necesarias; es seguro llamarla al iniciar la aplicación."""
    with _conexion() as conexion:
        conexion.executescript(
            """
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE COLLATE NOCASE
            );
            CREATE TABLE IF NOT EXISTS historial_cargas (
                id TEXT PRIMARY KEY,
                proveedor_id INTEGER NOT NULL REFERENCES proveedores(id),
                fecha_documento TEXT,
                creado_en TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            CREATE TABLE IF NOT EXISTS items_precios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                carga_id TEXT NOT NULL REFERENCES historial_cargas(id),
                codigo_sku TEXT,
                descripcion TEXT NOT NULL,
                descripcion_normalizada TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                precio_anterior REAL,
                porcentaje_variacion REAL,
                moneda TEXT NOT NULL,
                iva_porcentaje REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_items_sku
                ON items_precios(codigo_sku, id);
            CREATE INDEX IF NOT EXISTS idx_items_descripcion
                ON items_precios(descripcion_normalizada, id);
            CREATE INDEX IF NOT EXISTS idx_historial_proveedor
                ON historial_cargas(proveedor_id, creado_en);
            """
        )


def guardar_y_comparar(
    proveedor_nombre: str,
    datos: ListaProveedoresExtraida,
    lote_id: str | None = None,
) -> list[dict[str, Any]]:
    """Compara con la última carga anterior y guarda los precios de este lote."""
    nombre = proveedor_nombre.strip()
    if not nombre:
        raise ValueError("El nombre del proveedor no puede estar vacío.")
    lote_id = lote_id or str(uuid.uuid4())
    enriquecidos: list[dict[str, Any]] = []

    with _conexion() as conexion:
        conexion.execute(
            "INSERT OR IGNORE INTO proveedores (nombre) VALUES (?)", (nombre,)
        )
        proveedor = conexion.execute(
            "SELECT id, nombre FROM proveedores WHERE nombre = ? COLLATE NOCASE",
            (nombre,),
        ).fetchone()
        if proveedor is None:
            raise RuntimeError("No se pudo registrar el proveedor.")

        # La carga se inserta después de comparar para que nunca se compare consigo misma.
        comparaciones: list[tuple[dict[str, Any], float | None, float | None]] = []
        for item in datos.items:
            producto = item.model_dump()
            if producto["codigo_sku"]:
                anterior = conexion.execute(
                    """
                    SELECT i.precio_unitario
                    FROM items_precios AS i
                    JOIN historial_cargas AS h ON h.id = i.carga_id
                    WHERE h.proveedor_id = ? AND i.codigo_sku = ?
                    ORDER BY h.creado_en DESC, i.id DESC
                    LIMIT 1
                    """,
                    (proveedor["id"], producto["codigo_sku"]),
                ).fetchone()
            else:
                anterior = conexion.execute(
                    """
                    SELECT i.precio_unitario
                    FROM items_precios AS i
                    JOIN historial_cargas AS h ON h.id = i.carga_id
                    WHERE h.proveedor_id = ?
                      AND i.codigo_sku IS NULL
                      AND i.descripcion_normalizada = ?
                    ORDER BY h.creado_en DESC, i.id DESC
                    LIMIT 1
                    """,
                    (proveedor["id"], normalizar_descripcion(producto["descripcion"])),
                ).fetchone()

            precio_anterior = float(anterior["precio_unitario"]) if anterior else None
            variacion = None
            if precio_anterior is not None and precio_anterior != 0:
                variacion = (
                    (producto["precio_unitario"] - precio_anterior)
                    / precio_anterior
                    * 100
                )
            enriquecido = {
                **producto,
                "precio_anterior": precio_anterior,
                "porcentaje_variacion": variacion,
            }
            comparaciones.append((enriquecido, precio_anterior, variacion))

        conexion.execute(
            """
            INSERT INTO historial_cargas (id, proveedor_id, fecha_documento)
            VALUES (?, ?, ?)
            """,
            (lote_id, proveedor["id"], datos.fecha_documento),
        )
        for enriquecido, precio_anterior, variacion in comparaciones:
            conexion.execute(
                """
                INSERT INTO items_precios (
                    carga_id, codigo_sku, descripcion, descripcion_normalizada,
                    precio_unitario, precio_anterior, porcentaje_variacion,
                    moneda, iva_porcentaje
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lote_id,
                    enriquecido["codigo_sku"],
                    enriquecido["descripcion"],
                    normalizar_descripcion(enriquecido["descripcion"]),
                    enriquecido["precio_unitario"],
                    precio_anterior,
                    variacion,
                    enriquecido["moneda"],
                    enriquecido["iva_porcentaje"],
                ),
            )
            enriquecidos.append(enriquecido)

    return enriquecidos


def listar_proveedores() -> list[str]:
    """Devuelve los nombres de proveedor registrados, ordenados alfabéticamente."""
    with _conexion() as conexion:
        filas = conexion.execute(
            "SELECT nombre FROM proveedores ORDER BY nombre COLLATE NOCASE"
        ).fetchall()
    return [fila["nombre"] for fila in filas]


def obtener_lote_para_exportar(lote_id: str) -> dict[str, Any] | None:
    """Recupera los datos del proveedor, fecha y productos de un lote."""
    with _conexion() as conexion:
        carga = conexion.execute(
            """
            SELECT p.nombre AS proveedor, h.fecha_documento
            FROM historial_cargas AS h
            JOIN proveedores AS p ON p.id = h.proveedor_id
            WHERE h.id = ?
            """,
            (lote_id,),
        ).fetchone()
        if carga is None:
            return None
        filas = conexion.execute(
            """
            SELECT codigo_sku, descripcion, precio_unitario, precio_anterior,
                   porcentaje_variacion, moneda, iva_porcentaje
            FROM items_precios
            WHERE carga_id = ?
            ORDER BY id
            """,
            (lote_id,),
        ).fetchall()
    return {
        "proveedor": carga["proveedor"],
        "fecha_documento": carga["fecha_documento"],
        "items": [dict(fila) for fila in filas],
    }


def obtener_items_lote(lote_id: str) -> list[dict[str, Any]] | None:
    """Recupera los productos y variaciones persistidos para una descarga."""
    lote = obtener_lote_para_exportar(lote_id)
    return lote["items"] if lote is not None else None


inicializar_db()
