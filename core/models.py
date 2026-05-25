from pydantic import BaseModel, Field, field_validator


class HumanizeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The AI-generated text to humanize.",
    )
    mode: str = Field(
        default="HUMANIZER",
        description="Transformation mode: HUMANIZER, CLEAR, PROFESSIONAL, ACADEMIC, or CREATIVE.",
    )

    @field_validator("text")
    @classmethod
    def not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Input text cannot be empty or whitespace only.")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = {"HUMANIZER", "CLEAR", "PROFESSIONAL", "ACADEMIC", "CREATIVE"}
        val = v.upper().strip()
        if val not in allowed:
            raise ValueError(f"Mode must be one of {sorted(allowed)}")
        return val


class HumanizeResponse(BaseModel):
    ai_evaluation: str = Field(
        ...,
        pattern="^(AI_GENERATED|HUMAN_LIKE|INVALID_INPUT)$",
        description="AI detection classification result.",
    )
    execution_mode: str = Field(
        ...,
        pattern="^(HUMANIZER|CLEAR|PROFESSIONAL|ACADEMIC|CREATIVE|UNKNOWN)$",
        description="The mode that was executed.",
    )
    message: str = Field(..., description="Short explanation of the result.")
    output: str = Field(..., description="Rewritten text or original/fallback text.")

