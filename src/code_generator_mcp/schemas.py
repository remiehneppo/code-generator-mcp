from pydantic import BaseModel, Field

class FunctionSpec(BaseModel):
    name: str = Field(..., description="Name of the function")
    signature: str = Field(..., description="Function signature with type annotations")
    description: str = Field(..., description="Detailed description of input, output and behavior")
    constraints: list[str] | None = Field(default=None, description="Constraints specific to this function")
    depends_on: str | None = Field(default=None, description="Name of another function that this function depends on")
