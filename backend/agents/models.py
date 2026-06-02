"""
backend/agents/models.py — Pydantic models for agent identity and state.

Phase 1: In-memory only. No SQLAlchemy — these models are the sole data contracts
for agent data throughout the simulation.

Phase 2: SQLAlchemy ORM models will be added to db/models.py; these Pydantic models
will continue to serve as the serialization layer.
"""
from typing import Literal
from pydantic import BaseModel, Field

MoralAlignment = Literal["authoritarian", "libertarian", "utilitarian", "deontological", "nihilist"]
AppealType = Literal["emotional", "rational", "social", "authority"]
ActionType = Literal["debate", "persuade", "broadcast", "challenge", "agree", "withdraw", "rally"]
EmotionType = str  # not a Literal — LLM returns arbitrary emotion strings


class TraitVector(BaseModel):
    """Big Five personality trait scores, all in [0.0, 1.0]."""

    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)
    moral_rigidity: float = Field(ge=0.0, le=1.0)
    susceptibility: float = Field(ge=0.0, le=1.0)


class AgentProfile(BaseModel):
    """
    Fixed identity of an agent. Created once at simulation start and never mutated.
    Corresponds to the agent_profiles table in Phase 2.
    """

    id: str
    name: str
    archetype: str
    trait_vector: TraitVector
    core_beliefs: list[str]
    voice_style: str
    moral_alignment: MoralAlignment
    appeal_type: AppealType


class AgentState(BaseModel):
    """
    Mutable per-agent per-round state.
    Corresponds to the agent_states table in Phase 2.
    """

    agent_id: str
    round: int = 0
    stance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion: EmotionType = "neutral"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_text: str = ""
    influence_score: float = 0.0
    interaction_count: int = 0
    last_action: ActionType = "debate"
    last_target: str | None = None


class RoundAction(BaseModel):
    """
    An action taken by an agent in a round.
    """

    agent_id: str
    name: str
    archetype: str
    action: ActionType
    target_id: str | None
    free_text: str
    stance: float
    emotion: EmotionType
    confidence: float
    argument_quality: float = 0.5


class RelationshipEdge(BaseModel):
    """
    Directional trust relationship between two agents.
    Corresponds to the relationship_edges table in Phase 2.
    """

    from_agent: str
    to_agent: str
    trust_score: float = Field(ge=0.0, le=1.0)
    interaction_count: int = 0
    betrayed: bool = False
