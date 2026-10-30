from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator


class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EntidadesTecnicas(BaseModel):
    tecnologias: List[str] = Field(
        ..., min_length=1,
        description="Lista de tecnologías, frameworks o herramientas mencionadas en el texto"
    )
    nivel_de_criticidad: NivelCriticidad = Field(
        ..., description="Gravedad del problema o relevancia de la arquitectura descripta"
    )
    resumen_tecnico: str = Field(
        ..., min_length=10,
        description="Resumen técnico de 1-2 oraciones sobre el contenido del texto"
    )

    @field_validator("tecnologias")
    @classmethod
    def sin_duplicados_ni_vacios(cls, v: List[str]) -> List[str]:
        limpio = [t.strip() for t in v if t.strip()]
        if not limpio:
            raise ValueError("La lista de tecnologías no puede quedar vacía tras limpiar")
        return list(dict.fromkeys(limpio))
