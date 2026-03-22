"""
Real tool wrappers for research agents.
Each tool returns a uniform List[Source] shape so nodes can process them identically.
"""

import logging
from typing import List
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Shared source shape ────────────────────────────────────────────────────────

def _make_source(title: str, url: str, snippet: str, source_type: str, relevance_score: float = 0.5) -> dict:
    return {
        "title": title,
        "url": url,
        "snippet": snippet[:600],
        "source_type": source_type,
        "relevance_score": round(relevance_score, 3),
    }


# ── Tavily (live web search) ───────────────────────────────────────────────────

def tavily_search(query: str, max_results: int = 5) -> List[dict]:
    """Search the live web for recent information."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query, max_results=max_results, include_answer=False)
        results = response.get("results", [])
        return [
            _make_source(
                title=r.get("title", "Untitled"),
                url=r.get("url", ""),
                snippet=r.get("content", ""),
                source_type="web",
                relevance_score=r.get("score", 0.5),
            )
            for r in results
        ]
    except Exception as e:
        logger.warning("Tavily search failed for query '%s': %s", query, e)
        return []


# ── Wikipedia ─────────────────────────────────────────────────────────────────

def wikipedia_search(query: str, max_results: int = 3) -> List[dict]:
    """Retrieve encyclopedic background from Wikipedia."""
    try:
        import wikipediaapi
        wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="MultiAgentResearch/1.0 (research-tool)"
        )

        # Try the query directly first, then a simplified version
        for attempt in [query, query.split()[0] if query.split() else query]:
            page = wiki.page(attempt)
            if page.exists():
                summary = page.summary[:800]
                return [
                    _make_source(
                        title=page.title,
                        url=page.fullurl,
                        snippet=summary,
                        source_type="wikipedia",
                        relevance_score=0.75,
                    )
                ]
        return []
    except Exception as e:
        logger.warning("Wikipedia search failed for query '%s': %s", query, e)
        return []


# ── ArXiv (academic papers) ───────────────────────────────────────────────────

def arxiv_search(query: str, max_results: int = 3) -> List[dict]:
    """Search ArXiv for academic papers."""
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        sources = []
        for paper in client.results(search):
            sources.append(
                _make_source(
                    title=paper.title,
                    url=paper.entry_id,
                    snippet=paper.summary[:600],
                    source_type="arxiv",
                    relevance_score=0.8,
                )
            )
        return sources
    except Exception as e:
        logger.warning("ArXiv search failed for query '%s': %s", query, e)
        return []


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "tavily": tavily_search,
    "wikipedia": wikipedia_search,
    "arxiv": arxiv_search,
}


# ── Routing heuristic ─────────────────────────────────────────────────────────

_ACADEMIC_KEYWORDS = {
    "paper", "papers", "research", "study", "studies", "model", "models",
    "algorithm", "algorithms", "neural", "network", "dataset", "experiment",
    "theory", "theorem", "proof", "published", "journal", "arxiv",
}

_ENCYCLOPEDIC_KEYWORDS = {
    "history", "historical", "origin", "definition", "what is", "overview",
    "background", "founded", "invented", "biography", "describe", "explain",
    "concept", "meaning", "introduction",
}


def route_tools_for_question(question: str) -> List[str]:
    """
    Decide which tools to call for a given sub-question.
    Always includes Tavily (live web). Adds ArXiv for academic questions
    and Wikipedia for conceptual/encyclopedic questions.
    """
    q_lower = question.lower()
    tools = ["tavily"]  # always include live web search

    if any(kw in q_lower for kw in _ACADEMIC_KEYWORDS):
        tools.append("arxiv")

    if any(kw in q_lower for kw in _ENCYCLOPEDIC_KEYWORDS):
        tools.append("wikipedia")

    return tools


# ── Confidence heuristic ──────────────────────────────────────────────────────

def compute_confidence(sources: List[dict]) -> float:
    """
    Derive a confidence score (0–1) from source quantity and diversity.
    - More sources → higher base score (caps at 5 sources)
    - Multiple source types → diversity bonus
    """
    if not sources:
        return 0.1

    count_score = min(len(sources) / 5.0, 1.0)  # 5+ sources = 1.0

    types = {s.get("source_type") for s in sources}
    diversity_bonus = 0.1 * (len(types) - 1)     # +0.1 per extra type

    avg_relevance = sum(s.get("relevance_score", 0.5) for s in sources) / len(sources)

    raw = (count_score * 0.4) + (avg_relevance * 0.4) + diversity_bonus
    return round(min(raw, 1.0), 3)
