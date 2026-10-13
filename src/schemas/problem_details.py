from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    type: str = Field(..., description="URI de referencia al tipo de error")
    title: str = Field(..., description="Título legible del error")
    status: int = Field(..., description="Código de estado HTTP")
    detail: str = Field(..., description="Descripción detallada de la causa")
    instance: str = Field(..., description="Ruta de la petición donde ocurrió")
    code: str = Field(..., description="Código de error de negocio interno")
    correlation_id: Optional[str] = Field(None, description="Identificador de correlación")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Fecha y hora UTC")
