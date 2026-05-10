from pydantic import BaseModel, Field, field_validator


class HumanizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The AI-generated text to humanize.",
    )

    @field_validator("text")
    @classmethod
    def not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Input text cannot be empty or whitespace only.")
        return v


class HumanizeResponse(BaseModel):
    status: str = Field(
        ...,
        pattern="^(AI_GENERATED|HUMAN_LIKE|INVALID_INPUT)$",
        description="Classification of the result.",
    )
    message: str = Field(..., description="Short explanation of the result.")
    output: str = Field(..., description="Rewritten text or original text.")
