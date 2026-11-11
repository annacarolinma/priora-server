from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class TendenciaSuspeito(str, Enum):
    Alta = "Alta"
    Baixa = "Baixa"
    Estavel = "Estável"


class RespostaHistorico(str, Enum):
    Sim = "Sim"
    NaoSei = "Não sei"
    Nao = "Não"


class CreateSuspectRequest(BaseModel):
    casoId: str

    nome: str = Field(..., example="Elvin Bond")
    idade: int = Field(..., ge=0, example=32)
    fotoUrl: Optional[str] = None
    # Observações sobre o suspeito (relação com a vítima, contexto, fonte da suspeita...)
    descricao: Optional[str] = Field(default=None, max_length=1000)

    historicoCriminal: float = Field(..., ge=0, le=100, example=70)
    caracteristicasCriminais: float = Field(..., ge=0, le=100, example=55)
    significanciaTempoLugar: float = Field(..., ge=0, le=100, example=80)
    coerenciaInterpessoal: float = Field(..., ge=0, le=100, example=60)
    conscienciaForense: float = Field(..., ge=0, le=100, example=20)

    crimeSimilarAntes: RespostaHistorico
    histDescumprimento: RespostaHistorico

class UpdateSuspectRequest(BaseModel):
    nome: str
    idade: Optional[int] = None
    fotoUrl: Optional[str] = None
    descricao: Optional[str] = Field(default=None, max_length=1000)

    historicoCriminal: float
    caracteristicasCriminais: float
    significanciaTempoLugar: float
    coerenciaInterpessoal: float
    conscienciaForense: float

    crimeSimilarAntes: str
    histDescumprimento: str