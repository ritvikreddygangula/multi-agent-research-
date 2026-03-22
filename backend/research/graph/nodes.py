"""
LangGraph node implementations.

Each node function:
- Receives the full ResearchState
- Returns a PARTIAL state dict (only the keys it changes)
- Never mutates state in place
- Appends to graph_events for frontend streaming
"""

import json
import time
import logging
from typing import List

from langchain_openai import ChatOpenAI
from django.conf import settings

from .state import ResearchState, SubQuestionResult, CriticFeedback, GraphEvent
from .tools import TOOL_REGISTRY, route_tools_for_question, compute_confidence

logger = logging.getLogger(__name__)

# ── Shared LLM instance ───────────────────────────────────────────────────────

def _get_llm(temperature: float = 0.5) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_json_response(raw: str, fallback: dict) -> dict:
    """Extract JSON from an LLM response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed, using fallback. Raw: %s", raw[:200])
        return fallback


def _ts() -> float:
    return round(time.time(), 3)


def _event(node: str, status: str, meta: dict = None) -> GraphEvent:
    return {"node": node, "status": status, "ts": _ts(), "meta": meta or {}}


def _update_status(node: str, status: str) -> dict:
    """Return a single-key dict — the _merge_dicts reducer merges it into the full statuses."""
    return {node: status}


# ── Node 1: Planner ───────────────────────────────────────────────────────────

def planner_node(state: ResearchState) -> dict:
    """
    Decomposes the research topic into 3-5 focused sub-questions
    and identifies key aspects to investigate.
    """
    logger.info("[planner] Starting for topic: %s", state["topic"])
    llm = _get_llm(temperature=0.4)

    rag_hint = ""
    if state.get("rag_context"):
        summaries = [r.get("summary", "") for r in state["rag_context"][:2]]
        rag_hint = f"\n\nPrior research context (use to avoid duplication):\n" + "\n".join(summaries)

    prompt = f"""You are a research planning expert. Decompose the following topic into a precise research plan.

Topic: {state["topic"]}{rag_hint}

Return ONLY valid JSON in this exact shape — no markdown fences, no extra text:
{{
    "understanding": "2-3 sentence explanation of what this topic entails and why it matters",
    "sub_questions": ["specific question 1", "specific question 2", "specific question 3", "specific question 4"],
    "key_aspects": ["aspect 1", "aspect 2", "aspect 3"]
}}

Rules:
- sub_questions: 3-5 items, each specific enough to web-search independently
- key_aspects: 3-5 high-level dimensions of the topic
- understanding: factual framing, not opinions"""

    raw = llm.invoke(prompt).content
    plan = _parse_json_response(raw, {
        "understanding": state["topic"],
        "sub_questions": [state["topic"]],
        "key_aspects": [state["topic"]],
    })

    sub_questions = plan.get("sub_questions", [state["topic"]])[:5]
    key_aspects = plan.get("key_aspects", [])[:5]
    understanding = plan.get("understanding", state["topic"])

    logger.info("[planner] Generated %d sub-questions", len(sub_questions))

    return {
        "sub_questions": sub_questions,
        "key_aspects": key_aspects,
        "understanding": understanding,
        "node_statuses": _update_status("planner", "done"),
        "graph_events": [_event("planner", "done", {"sub_question_count": len(sub_questions)})],
    }


# ── Node 2: Branch Research (factory) ────────────────────────────────────────

def branch_research_node(question_index: int):
    """
    Returns a node function scoped to one sub-question.
    Runs tools in parallel-per-branch (each branch is its own graph node).
    Fails soft: if tools fail the LLM still synthesises from what it knows.
    """
    node_id = f"branch_{question_index}"

    def node(state: ResearchState) -> dict:
        # Guard: if this index doesn't exist (fewer sub-questions than max branches) skip cleanly
        if question_index >= len(state.get("sub_questions", [])):
            return {
                "branch_results": [],
                "node_statuses": _update_status(node_id, "skipped"),
                "graph_events": [_event(node_id, "skipped")],
            }

        question = state["sub_questions"][question_index]
        logger.info("[%s] Researching: %s", node_id, question)

        # ── Run tools ────────────────────────────────────────────────────────
        tool_names = route_tools_for_question(question)
        all_sources: List[dict] = []
        errors: List[str] = []

        for name in tool_names:
            try:
                results = TOOL_REGISTRY[name](question, max_results=4)
                all_sources.extend(results)
                logger.info("[%s] %s returned %d sources", node_id, name, len(results))
            except Exception as e:
                err = f"{node_id}/{name}: {str(e)}"
                errors.append(err)
                logger.warning("[%s] Tool %s failed: %s", node_id, name, e)

        # Deduplicate by URL, keep top 6 by relevance
        seen_urls: set = set()
        deduped: List[dict] = []
        for src in sorted(all_sources, key=lambda s: s.get("relevance_score", 0), reverse=True):
            if src["url"] not in seen_urls:
                deduped.append(src)
                seen_urls.add(src["url"])
            if len(deduped) >= 6:
                break

        # ── LLM synthesis from real sources ──────────────────────────────────
        sources_text = "\n\n".join(
            f"[{s['source_type'].upper()}] {s['title']}\n{s['snippet']}"
            for s in deduped[:5]
        ) if deduped else "No external sources retrieved."

        # Optionally inject RAG context
        rag_hint = ""
        if state.get("rag_context"):
            rag_hint = "\n\nRelated prior research:\n" + "\n".join(
                r.get("summary", "") for r in state["rag_context"][:1]
            )

        llm = _get_llm(temperature=0.5)
        synthesis_prompt = f"""You are a research analyst. Answer the following research question using ONLY the provided sources.
Be specific, cite evidence, and acknowledge uncertainty where sources are thin.

Question: {question}

Sources:
{sources_text}{rag_hint}

Write a focused 2-4 paragraph response that directly answers the question."""

        try:
            findings_text = llm.invoke(synthesis_prompt).content
        except Exception as e:
            findings_text = f"Research synthesis failed: {str(e)}"
            errors.append(str(e))

        confidence = compute_confidence(deduped)

        result: SubQuestionResult = {
            "question": question,
            "findings": findings_text,
            "sources": deduped[:5],
            "confidence": confidence,
            "status": "done",
            "error": "; ".join(errors) if errors else None,
        }

        logger.info("[%s] Done. Confidence=%.2f, sources=%d", node_id, confidence, len(deduped))

        return {
            "branch_results": [result],
            "node_statuses": _update_status(node_id, "done"),
            "graph_events": [_event(node_id, "done", {"confidence": confidence, "source_count": len(deduped)})],
            "errors": errors,
        }

    node.__name__ = node_id
    return node


# ── Node stubs (implemented in Steps 5 & 6) ──────────────────────────────────

def aggregator_node(state: ResearchState) -> dict:
    """Merges all branch results into a synthesis draft. Implemented in Step 5."""
    return {
        "synthesis_draft": "[aggregator not yet implemented]",
        "node_statuses": _update_status("aggregator", "done"),
        "graph_events": [_event("aggregator", "done")],
    }


def critic_node(state: ResearchState) -> dict:
    """Adversarial quality review. Implemented in Step 5."""
    feedback: CriticFeedback = {
        "passed": True,
        "score": 1.0,
        "issues": [],
        "suggestions": [],
        "iteration": 1,
    }
    return {
        "critic_feedback": [feedback],
        "critic_iteration": state.get("critic_iteration", 0) + 1,
        "node_statuses": _update_status("critic", "done"),
        "graph_events": [_event("critic", "done", {"score": 1.0})],
    }


def synthesizer_node(state: ResearchState) -> dict:
    """Final report generation. Implemented in Step 6."""
    branch_results = state.get("branch_results", [])
    findings_preview = [r["question"] for r in branch_results if r.get("status") == "done"]
    return {
        "final_report": {
            "topic": state["topic"],
            "overview": state.get("understanding", ""),
            "key_concepts": state.get("key_aspects", []),
            "important_findings": findings_preview,
            "summary": state.get("synthesis_draft", ""),
            "confidence_score": 0.0,
            "sources": [],
        },
        "node_statuses": _update_status("synthesizer", "done"),
        "graph_events": [_event("synthesizer", "done")],
    }
