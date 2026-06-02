import uuid
from datetime import datetime, date as date_type, timezone
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="free")

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    simulations: Mapped[list["SimulationConfig"]] = relationship(back_populates="user")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "google" | "github"
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    family_id: Mapped[str] = mapped_column(String(36), default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class SimulationConfig(Base):
    __tablename__ = "simulation_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    agent_count: Mapped[int] = mapped_column(Integer, default=50)
    rounds: Mapped[int] = mapped_column(Integer, default=5)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|complete|failed|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="simulations")
    result: Mapped["SimulationResult | None"] = relationship(back_populates="config", uselist=False)
    agent_profiles: Mapped[list["AgentProfileDB"]] = relationship(back_populates="simulation")
    injected_events: Mapped[list["InjectedEvent"]] = relationship(back_populates="simulation")


class AgentProfileDB(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # same as Python UUID
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_configs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    archetype: Mapped[str] = mapped_column(String(50), nullable=False)
    moral_alignment: Mapped[str] = mapped_column(String(50), nullable=False)
    appeal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trait_vector: Mapped[dict] = mapped_column(JSON, nullable=False)
    core_beliefs: Mapped[list] = mapped_column(JSON, nullable=False)
    voice_style: Mapped[str] = mapped_column(Text, nullable=False)

    simulation: Mapped["SimulationConfig"] = relationship(back_populates="agent_profiles")


class RelationshipEdgeDB(Base):
    __tablename__ = "relationship_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_configs.id"), nullable=False)
    from_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_profiles.id"), nullable=False)
    to_agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_profiles.id"), nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=0.5)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    betrayed: Mapped[bool] = mapped_column(Boolean, default=False)


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_configs.id"), unique=True, nullable=False)
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    distribution: Mapped[dict] = mapped_column(JSON, nullable=False)
    avg_stance: Mapped[float] = mapped_column(Float, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    counterfactuals: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    report: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    hallucination_level: Mapped[str] = mapped_column(String(20), default="none")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    config: Mapped["SimulationConfig"] = relationship(back_populates="result")


class InjectedEvent(Base):
    __tablename__ = "injected_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    simulation_id: Mapped[str] = mapped_column(String(36), ForeignKey("simulation_configs.id"), nullable=False)
    round_num: Mapped[int] = mapped_column(Integer, nullable=False)
    event_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    simulation: Mapped["SimulationConfig"] = relationship(back_populates="injected_events")


class ApiKeyAudit(Base):
    __tablename__ = "api_key_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # "set" | "delete" | "use"
    simulation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class TierConfig(Base):
    __tablename__ = "tier_config"

    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    max_agents: Mapped[int] = mapped_column(Integer, nullable=False)
    max_rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_daily_sims: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrent: Mapped[int] = mapped_column(Integer, nullable=False)
    max_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class MetricsRollup(Base):
    __tablename__ = "metrics_rollup"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, unique=True)
    total_sims: Mapped[int] = mapped_column(Integer, default=0)
    verdict_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    avg_rounds: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
