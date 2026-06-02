from agents.models import AgentState


def compute_verdict(states: list[AgentState]) -> dict:
    """Pure Python: compute dominant outcome from final agent states."""
    n = len(states)
    if n == 0:
        return {"verdict": "No data — simulation produced no agent states.",
                "confidence": 0.0,
                "distribution": {"support": 0.0, "oppose": 0.0, "undecided": 1.0},
                "avg_stance": 0.0}

    support = [s for s in states if s.stance >= 0.6]
    oppose = [s for s in states if s.stance <= 0.4]
    undecided = [s for s in states if 0.4 < s.stance < 0.6]

    sp = len(support) / n
    op = len(oppose) / n
    up = len(undecided) / n
    avg = sum(s.stance for s in states) / n

    if sp > op and sp > up:
        verdict = "Society reaches broad consensus in support"
        confidence = sp
    elif op > sp and op > up:
        verdict = "Society rejects the proposition"
        confidence = op
    elif up > 0.40:
        verdict = "Society remains deeply divided"
        confidence = up
    elif sp > op:
        verdict = "Marginal support with significant opposition"
        confidence = sp
    else:
        verdict = "Marginal opposition with contested public opinion"
        confidence = op

    return {
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "distribution": {"support": round(sp, 3), "oppose": round(op, 3), "undecided": round(up, 3)},
        "avg_stance": round(avg, 3),
    }
