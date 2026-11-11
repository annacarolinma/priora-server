from pydantic import BaseModel, Field
from enum import Enum


class TipoEvidencia(str, Enum):
    Digital = "Digital"
    DNA = "DNA"
    Depoimento = "Depoimento"
    Documental = "Documental"
    Fisica = "Física"
    Audiovisual = "Audiovisual"
    Biologica = "Biológica"


class StatusEvidencia(str, Enum):
    Coletada = "Coletada"
    EmAnalise = "Em análise"
    Custodiada = "Custodiada"
    Descartada = "Descartada"
    EnviadaPericia = "Enviada a perícia"


class VinculoInput(BaseModel):
    """Peso do vínculo entre a evidência e UM suspeito específico (estritamente entre 0 e 1: nunca 0% nem 100%)."""
    suspeitoId: str
    pesoVinculo: float = Field(..., gt=0.0, lt=1.0, example=0.75)


class CreateEvidenceRequest(BaseModel):
    casoId: str
    vinculos: list[VinculoInput]

    nome: str = Field(..., example="Digital no local")
    tipo: TipoEvidencia
    status: StatusEvidencia = StatusEvidencia.Coletada
    descricao: str | None = None
    # Origem da informação (laudo, depoimento, documento, reportagem...)
    fonte: str | None = Field(default=None, max_length=300)

    dataColeta: str = Field(..., example="2025-04-24")

    peso: float = Field(..., gt=0.0, lt=1.0, example=0.5)


class DeleteEvidencesRequest(BaseModel):
    ids: list[str]


class UpdateEvidenceRequest(BaseModel):
    nome: str | None = None
    tipo: TipoEvidencia | None = None
    status: StatusEvidencia | None = None
    descricao: str | None = None
    fonte: str | None = Field(default=None, max_length=300)
    dataColeta: str | None = None
    peso: float | None = Field(default=None, gt=0.0, lt=1.0)
    vinculos: list[VinculoInput] | None = None
