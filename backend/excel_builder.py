"""Construcción del libro Excel normalizado y su hoja de alertas."""

from io import BytesIO
from typing import Any

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


COLUMNAS = [
    "Código",
    "Descripción",
    "Precio Anterior",
    "Precio Nuevo",
    "Variación %",
    "Moneda",
    "IVA %",
]


def generar_excel(items: list[dict[str, Any]]) -> BytesIO:
    """Genera un .xlsx en memoria con la lista completa y las alertas > 10%."""
    filas = [
        {
            "Código": item.get("codigo_sku"),
            "Descripción": item["descripcion"],
            "Precio Anterior": item.get("precio_anterior"),
            "Precio Nuevo": item["precio_unitario"],
            "Variación %": item.get("porcentaje_variacion"),
            "Moneda": item["moneda"],
            "IVA %": item["iva_porcentaje"],
        }
        for item in items
    ]
    tabla = pd.DataFrame(filas, columns=COLUMNAS)
    alertas = tabla[tabla["Variación %"].fillna(0) > 10]
    salida = BytesIO()
    relleno_alerta = PatternFill(
        fill_type="solid",
        start_color="FCE4D6",
        end_color="FCE4D6",
    )
    fuente_alerta = Font(color="9C0006")

    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        tabla.to_excel(escritor, sheet_name="Lista Normalizada", index=False)
        alertas.to_excel(escritor, sheet_name="Alertas de Aumento", index=False)

        for hoja in escritor.book.worksheets:
            hoja.freeze_panes = "A2"
            hoja.auto_filter.ref = hoja.dimensions
            for celda in hoja[1]:
                celda.font = Font(bold=True, color="FFFFFF")
                celda.fill = PatternFill("solid", fgColor="1F4E78")
                celda.alignment = Alignment(horizontal="center")

            for columna in hoja.columns:
                letra = get_column_letter(columna[0].column)
                ancho = max(
                    (len(str(celda.value or "")) for celda in columna),
                    default=0,
                )
                hoja.column_dimensions[letra].width = min(max(ancho + 2, 12), 55)

            encabezados = {celda.value: celda.column for celda in hoja[1]}
            for fila in range(2, hoja.max_row + 1):
                for encabezado in ("Precio Anterior", "Precio Nuevo"):
                    columna = encabezados[encabezado]
                    hoja.cell(fila, columna).number_format = '#,##0.00'
                hoja.cell(fila, encabezados["Variación %"]).number_format = "0.00%"
                celda_iva = hoja.cell(fila, encabezados["IVA %"])
                if celda_iva.value is not None:
                    celda_iva.value = celda_iva.value / 100
                celda_iva.number_format = "0.00%"
                hoja.cell(fila, encabezados["Descripción"]).alignment = Alignment(
                    vertical="top", wrap_text=True
                )

            # La variación se recibe como porcentaje (10 = 10%) y Excel usa fracciones.
            variacion_columna = encabezados["Variación %"]
            for fila in range(2, hoja.max_row + 1):
                celda = hoja.cell(fila, variacion_columna)
                if celda.value is not None:
                    if celda.value > 10:
                        for celda_fila in hoja[fila]:
                            celda_fila.fill = relleno_alerta
                            celda_fila.font = fuente_alerta
                    celda.value = celda.value / 100
                celda.number_format = "0.00%"

    salida.seek(0)
    return salida
