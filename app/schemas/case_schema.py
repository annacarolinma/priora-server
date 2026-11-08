from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

# Situações possíveis de um caso. Nomes antigos (usados por versões anteriores do
# front) continuam aceitos e são convertidos.
CaseStatus = Literal["Ativo", "Pendente", "Finalizado"]
LEGACY_STATUS = {"Arquivado": "Pendente", "Concluído": "Finalizado"}


def normalize_status(value):
    return LEGACY_STATUS.get(value, value)


class CreateCaseRequest(BaseModel):
    userId: str
    nome: str
    descricao: str
    status: CaseStatus
    prioridade: str
    enderecoCep: str | None = None        # ← novo
    enderecoLogradouro: str | None = None
    enderecoNumero: str | None = None
    enderecoBairro: str | None = None
    enderecoCidade: str | None = None
    enderecoEstado: str | None = None
    dataOcorrencia: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, v):
        return normalize_status(v)


class UpdateUncertaintyRequest(BaseModel):
    incerteza: float

class UpdateCaseRequest(BaseModel):
    nome: str
    descricao: str
    status: CaseStatus
    prioridade: str

    enderecoCep: Optional[str] = None
    enderecoLogradouro: Optional[str] = None
    enderecoNumero: Optional[str] = None
    enderecoBairro: Optional[str] = None
    enderecoCidade: Optional[str] = None
    enderecoEstado: Optional[str] = None

    dataOcorrencia: str

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, v):
        return normalize_status(v)


class EstimatedProfileRequest(BaseModel):
    historicoCriminal: float = Field(..., ge=0, le=100)
    caracteristicasCriminais: float = Field(..., ge=0, le=100)
    significanciaTempoLugar: float = Field(..., ge=0, le=100)
    coerenciaInterpessoal: float = Field(..., ge=0, le=100)
    conscienciaForense: float = Field(..., ge=0, le=100)
