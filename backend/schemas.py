"""Modelos de datos para la extracción y comparación de listas de precios."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemProducto(BaseModel):
    """Producto normalizado extraído de un documento de proveedor."""

    model_config = ConfigDict(str_strip_whitespace=True)

    codigo_sku: str | None = Field(
        default=None, description="Código SKU del producto; null si no aparece."
    )
    descripcion: str = Field(description="Descripción del producto tal como figura.")
    precio_unitario: float = Field(description="Precio unitario numérico.")
    moneda: str = Field(default="ARS", description="Código de moneda, por ejemplo ARS.")
    iva_porcentaje: float = Field(default=21.0, description="Alícuota de IVA en porcentaje.")

    @field_validator("codigo_sku")
    @classmethod
    def sku_vacio_es_nulo(cls, valor: str | None) -> str | None:
        return valor or None

    @field_validator("descripcion")
    @classmethod
    def descripcion_no_vacia(cls, valor: str) -> str:
        if not valor:
            raise ValueError("La descripción no puede estar vacía.")
        return valor


class ListaProveedoresExtraida(BaseModel):
    """Contenido estructurado de una lista de precios o factura."""

    model_config = ConfigDict(str_strip_whitespace=True)

    proveedor_detectado: str = Field(description="Nombre del proveedor del documento.")
    fecha_documento: str | None = Field(
        default=None, description="Fecha del documento en formato YYYY-MM-DD."
    )
    items: list[ItemProducto] = Field(description="Productos incluidos en el documento.")

    @field_validator("proveedor_detectado")
    @classmethod
    def proveedor_no_vacio(cls, valor: str) -> str:
        if not valor:
            raise ValueError("El proveedor detectado no puede estar vacío.")
        return valor

    @field_validator("fecha_documento")
    @classmethod
    def fecha_iso_valida(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        try:
            fecha = date.fromisoformat(valor)
        except ValueError as error:
            raise ValueError("La fecha debe tener formato YYYY-MM-DD.") from error
        if fecha.isoformat() != valor:
            raise ValueError("La fecha debe tener formato YYYY-MM-DD.")
        return valor
