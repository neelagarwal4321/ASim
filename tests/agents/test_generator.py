import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.generator import generate_agents
from agents.models import AgentProfile


def test_generates_correct_count():
    agents = generate_agents(count=10, seed=42)
    assert len(agents) == 10


def test_all_agents_are_profiles():
    agents = generate_agents(count=5, seed=1)
    for agent in agents:
        assert isinstance(agent, AgentProfile)
        assert agent.id
        assert agent.name
        assert 0.0 <= agent.trait_vector.openness <= 1.0


def test_seed_reproducibility():
    agents_a = generate_agents(count=20, seed=99)
    agents_b = generate_agents(count=20, seed=99)
    assert [a.id for a in agents_a] == [a.id for a in agents_b]
    assert [a.archetype for a in agents_a] == [a.archetype for a in agents_b]


def test_different_seeds_give_variety():
    agents_a = generate_agents(count=20, seed=1)
    agents_b = generate_agents(count=20, seed=2)
    archetypes_a = {a.archetype for a in agents_a}
    archetypes_b = {a.archetype for a in agents_b}
    # At least some archetypes appear in both — not completely different
    assert archetypes_a & archetypes_b


def test_agents_have_variety_of_archetypes():
    agents = generate_agents(count=50, seed=7)
    archetypes = {a.archetype for a in agents}
    assert len(archetypes) >= 5, "Expected at least 5 distinct archetypes in 50 agents"


def test_all_trait_values_in_range():
    agents = generate_agents(count=50, seed=42)
    for agent in agents:
        tv = agent.trait_vector
        for val in [tv.openness, tv.conscientiousness, tv.extraversion,
                    tv.agreeableness, tv.neuroticism, tv.moral_rigidity, tv.susceptibility]:
            assert 0.0 <= val <= 1.0
