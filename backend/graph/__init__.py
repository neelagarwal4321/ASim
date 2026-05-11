"""Graph module: community detection + relationship edge building."""
from graph.community_detector import detect_communities
from graph.edge_builder import build_edges

__all__ = ["detect_communities", "build_edges"]
