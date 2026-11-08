from pydantic import BaseModel, Field
from typing import Optional


class CreateCaseRequest(BaseModel):
    userId: str
    nome: str
    descricao: str
    status: str
    prioridade: str
    enderecoCep: str | None = None        # ← novo
    enderecoLogradouro: str | None = None
    enderecoNumero: str | None = None
    enderecoBairro: str | None = None
    enderecoCidade: str | None = None
    enderecoEstado: str | None = None
    dataOcorrencia: str | None = None

class UpdateUncertaintyRequest(BaseModel):
    incerteza: float

class UpdateCaseRequest(BaseModel):
    nome: str
    descricao: str
    status: str
    prioridade: str

    enderecoCep: Optional[str] = None
    enderecoLogradouro: Optional[str] = None
    enderecoNumero: Optional[str] = None
    enderecoBairro: Optional[str] = None
    enderecoCidade: Optional[str] = None
    enderecoEstado: Optional[str] = None

    dataOcorrencia: str


class EstimatedProfileRequest(BaseModel):
    historicoCriminal: float = Field(..., ge=0, le=100)
    caracteristicasCriminais: float = Field(..., ge=0, le=100)
    significanciaTempoLugar: float = Field(..., ge=0, le=100)
    coerenciaInterpessoal: float = Field(..., ge=0, le=100)
    conscienciaForense: float = Field(..., ge=0, le=100)
