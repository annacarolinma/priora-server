from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Literal


class TipoEvidencia(str, Enum):
    """Tipos padrão. Além deles, o campo `tipo` aceita um nome livre (a opção "Outra" do formulário)."""
    Digital = "Digital"
    DNA = "DNA"
    Depoimento = "Depoimento"
    Documental = "Documental"
    Fisica = "Física"
    Audiovisual = "Audiovisual"
    Biologica = "Biológica"
    Motivacao = "Motivação"
    Antecedente = "Antecedente"
    Pericial = "Pericial"
    Telefonica = "Telefônica"
    Comportamento = "Comportamento"


TIPO_MAX = 60


def normalizar_tipo(valor: str) -> str:
    """Tipo padrão ou nome personalizado (sem espaços nas pontas, até TIPO_MAX caracteres)."""
    texto = " ".join((valor or "").split())
    if not texto:
        raise ValueError("Informe o tipo da evidência.")
    if len(texto) > TIPO_MAX:
        raise ValueError(f"O tipo deve ter no máximo {TIPO_MAX} caracteres.")
    return texto


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
    # Incrimina (padrão): a evidência aponta para o suspeito. Inocenta: ela o afasta (ex.: álibi).
    efeito: Literal["Incrimina", "Inocenta"] = "Incrimina"


class CreateEvidenceRequest(BaseModel):
    casoId: str
    vinculos: list[VinculoInput]

    nome: str = Field(..., example="Digital no local")
    tipo: str
    status: StatusEvidencia = StatusEvidencia.Coletada
    descricao: str | None = None
    # Origem da informação (laudo, depoimento, documento, reportagem...)
    fonte: str | None = Field(default=None, max_length=300)

    dataColeta: str = Field(..., example="2025-04-24")

    peso: float = Field(..., gt=0.0, lt=1.0, example=0.5)

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        return normalizar_tipo(v)


class DeleteEvidencesRequest(BaseModel):
    ids: list[str]


class UpdateEvidenceRequest(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    status: StatusEvidencia | None = None
    descricao: str | None = None
    fonte: str | None = Field(default=None, max_length=300)
    dataColeta: str | None = None
    peso: float | None = Field(default=None, gt=0.0, lt=1.0)
    vinculos: list[VinculoInput] | None = None

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str | None) -> str | None:
        return None if v is None else normalizar_tipo(v)
