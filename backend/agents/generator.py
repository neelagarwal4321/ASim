import random
import uuid

from agents.models import AgentProfile, TraitVector
from agents.archetypes import ARCHETYPES
from agents.voice_styles import VOICE_STYLES

_FIRST_NAMES = [
    "Alice", "Marcus", "Sarah", "James", "Priya", "David", "Elena", "Omar",
    "Jessica", "Thomas", "Amara", "Carlos", "Mei", "Noah", "Fatima", "Liam",
    "Zoe", "Raj", "Hannah", "Kwame", "Sofia", "Andre", "Yuki", "Patrick",
    "Ingrid", "Darius", "Clara", "Tariq", "Nadia", "Sebastian",
]

_LAST_NAMES = [
    "Chen", "Rivera", "Johnson", "Okoye", "Patel", "Kim", "Vasquez", "Hassan",
    "Williams", "Berg", "Diallo", "Santos", "Lin", "Freeman", "Al-Rashid",
    "Murphy", "Torres", "Nakamura", "Schmidt", "Mensah", "Greco", "Dubois",
    "Tanaka", "O'Brien", "Larsson", "Nkosi", "Fischer", "Bakr", "Petrov", "Walsh",
]


def _clamp(val: float) -> float:
    return max(0.0, min(1.0, val))


def generate_agents(count: int = 50, seed: int | None = None) -> list[AgentProfile]:
    rng = random.Random(seed)
    archetype_keys = list(ARCHETYPES.keys())
    used_names: set[str] = set()
    agents: list[AgentProfile] = []

    for _ in range(count):
        archetype_key = rng.choice(archetype_keys)
        base = ARCHETYPES[archetype_key]
        base_tv = base["trait_vector"]

        trait_vector = TraitVector(
            openness=_clamp(base_tv["openness"] + rng.gauss(0, 0.10)),
            conscientiousness=_clamp(base_tv["conscientiousness"] + rng.gauss(0, 0.10)),
            extraversion=_clamp(base_tv["extraversion"] + rng.gauss(0, 0.10)),
            agreeableness=_clamp(base_tv["agreeableness"] + rng.gauss(0, 0.10)),
            neuroticism=_clamp(base_tv["neuroticism"] + rng.gauss(0, 0.10)),
            moral_rigidity=_clamp(base_tv["moral_rigidity"] + rng.gauss(0, 0.05)),
            susceptibility=_clamp(base_tv["susceptibility"] + rng.gauss(0, 0.05)),
        )

        # Generate unique name
        for _ in range(20):
            name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break

        beliefs = base["beliefs"]
        selected_beliefs = rng.sample(beliefs, k=min(3, len(beliefs)))

        agents.append(AgentProfile(
            id=str(uuid.UUID(int=rng.getrandbits(128))),
            name=name,
            archetype=archetype_key,
            trait_vector=trait_vector,
            core_beliefs=selected_beliefs,
            voice_style=VOICE_STYLES[archetype_key],
            moral_alignment=base["moral_alignment"],
            appeal_type=base["appeal_type"],
        ))

    return agents
