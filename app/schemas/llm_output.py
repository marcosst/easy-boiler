from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topico: str = Field(min_length=1)
    subtopico: str = Field(min_length=1)
    acao: str = Field(min_length=1)
    timestamp: str = Field(pattern=r"^\d{2}:\d{2}:\d{2}$")

    @field_validator("topico", "subtopico", "acao", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ResultadoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[ItemLLM]
