from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def crear_pdf(nombre_archivo, fecha, lista_items):
  c = canvas.Canvas(nombre_archivo, pagesize=A4)
  width, height = A4

  # Encabezado típico de distribuidora
  c.setFont("Helvetica-Bold", 14)
  c.drawString(50, height - 50, "DISTRIBUIDORA FERRETERA DEL CENTRO S.R.L.")

  c.setFont("Helvetica", 10)
  c.drawString(50, height - 70, "CUIT: 30-71458923-4 | Córdoba, Argentina")
  c.drawString(50, height - 85, f"Fecha de vigencia: {fecha} | Moneda: ARS")
  c.drawString(
      50,
      height - 100,
      "Nota: Los precios expresados no incluyen IVA (21%) salvo indicación.",
  )

  # Cabecera de tabla
  y = height - 135
  c.setFont("Helvetica-Bold", 10)
  c.drawString(50, y, "CÓDIGO")
  c.drawString(130, y, "DESCRIPCIÓN DEL ARTÍCULO")
  c.drawString(410, y, "IVA %")
  c.drawString(470, y, "PRECIO UNIT.")
  c.line(50, y - 5, 550, y - 5)

  # Filas de productos
  y -= 25
  c.setFont("Helvetica", 10)
  for sku, desc, iva, precio in lista_items:
    c.drawString(50, y, sku)
    c.drawString(130, y, desc)
    c.drawString(415, y, f"{iva}%")
    c.drawString(470, y, f"$ {precio:,.2f}")
    y -= 20

  c.save()
  print(f"Generado: {nombre_archivo}")


# Archivo 1: Precios base (Octubre 2026)
items_octubre = [
    ("FER-101", "Taladro Percutor 13mm 750W Industrial", 21.0, 85000.00),
    ("FER-104", "Amoladora Angular 115mm 820W", 21.0, 62500.00),
    ("ELE-202", "Rollo Cable Unipolar 2.5mm x 100m Normalizado", 21.0, 48000.00),
    ("ELE-215", "Llave Térmica Bipolar 2x25A Curva C", 21.0, 14200.00),
    ("PIN-308", "Látex Interior Mate Blanco x 20 Litros", 21.0, 74000.00),
    ("HER-412", "Juego Llaves Combinadas 8 a 19mm (12 piezas)", 10.5, 39500.00),
]

# Archivo 2: Precios actualizados (Noviembre 2026) con aumentos mixtos
items_noviembre = [
    (
        "FER-101",
        "Taladro Percutor 13mm 750W Industrial",
        21.0,
        98600.00,
    ),  # +16% (Alerta > 10%)
    ("FER-104", "Amoladora Angular 115mm 820W", 21.0, 65000.00),  # +4% (Normal)
    (
        "ELE-202",
        "Rollo Cable Unipolar 2.5mm x 100m Normalizado",
        21.0,
        56640.00,
    ),  # +18% (Alerta > 10%)
    (
        "ELE-215",
        "Llave Térmica Bipolar 2x25A Curva C",
        21.0,
        14200.00,
    ),  # 0% (Sin cambios)
    (
        "PIN-308",
        "Látex Interior Mate Blanco x 20 Litros",
        21.0,
        85100.00,
    ),  # +15% (Alerta > 10%)
    (
        "HER-412",
        "Juego Llaves Combinadas 8 a 19mm (12 piezas)",
        10.5,
        41475.00,
    ),  # +5% (Normal)
]

if __name__ == "__main__":
  crear_pdf("lista_octubre.pdf", "2026-10-15", items_octubre)
  crear_pdf("lista_noviembre.pdf", "2026-11-20", items_noviembre)