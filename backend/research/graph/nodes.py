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


# ── Node 3: Aggregator ────────────────────────────────────────────────────────

def aggregator_node(state: ResearchState) -> dict:
    """
    Merges all branch results into a coherent synthesis draft.
    On critic retry passes, injects the critic's improvement suggestions
    so the LLM can address them explicitly.
    """
    logger.info("[aggregator] Merging %d branch results", len(state.get("branch_results", [])))

    successful = [r for r in state.get("branch_results", []) if r.get("status") == "done"]

    if not successful:
        return {
            "synthesis_draft": "Insufficient research data to synthesize.",
            "node_statuses": _update_status("aggregator", "done"),
            "graph_events": [_event("aggregator", "done", {"branch_count": 0})],
        }

    # Build evidence blocks — one per sub-question
    evidence_blocks = "\n\n".join(
        f"**Sub-question {i+1}:** {r['question']}\n"
        f"**Findings:** {r['findings']}\n"
        f"**Confidence:** {r['confidence']:.2f}\n"
        f"**Sources:** {', '.join(s['title'][:40] for s in r['sources'][:3])}"
        for i, r in enumerate(successful)
    )

    # On retry passes, append critic's improvement instructions
    improvement_section = ""
    critic_feedbacks = state.get("critic_feedback", [])
    if critic_feedbacks:
        last = critic_feedbacks[-1]
        issues_txt = "\n".join(f"  - {i}" for i in last.get("issues", []))
        suggestions_txt = "\n".join(f"  - {s}" for s in last.get("suggestions", []))
        improvement_section = (
            f"\n\n---\n"
            f"**Previous review score: {last['score']:.2f} — FAILED**\n"
            f"Issues to fix:\n{issues_txt}\n"
            f"Suggestions:\n{suggestions_txt}\n"
            f"Address all of the above in your revised synthesis."
        )

    llm = _get_llm(temperature=0.4)
    prompt = f"""You are a senior research analyst. Synthesize the following research evidence into a coherent, well-structured draft report.

{evidence_blocks}{improvement_section}

Write a structured synthesis draft that:
1. Integrates all sub-question findings into a unified narrative
2. Highlights the most important and well-supported points
3. Notes where evidence is thin or conflicting
4. Is factual, specific, and avoids speculation

Write 4-6 focused paragraphs. Do not use headers."""

    try:
        draft = llm.invoke(prompt).content
    except Exception as e:
        logger.error("[aggregator] LLM call failed: %s", e)
        draft = "\n\n".join(r["findings"] for r in successful)

    iteration = state.get("critic_iteration", 0)
    logger.info("[aggregator] Draft ready (iteration %d, %d chars)", iteration, len(draft))

    return {
        "synthesis_draft": draft,
        "node_statuses": _update_status("aggregator", "done"),
        "graph_events": [_event("aggregator", "done", {"iteration": iteration, "branch_count": len(successful)})],
    }


# ── Node 4: Critic ────────────────────────────────────────────────────────────

# Scoring thresholds
_PASS_SCORE = 0.72          # critic score required to proceed to synthesizer
_MAX_ITERATIONS = 2         # hard cap on retry loops


def critic_node(state: ResearchState) -> dict:
    """
    Adversarially reviews the synthesis draft.
    Scores it 0.0–1.0 across four dimensions:
      - factual_consistency  (do findings support claims?)
      - source_diversity      (multiple source types used?)
      - coverage              (all sub-questions addressed?)
      - specificity           (concrete facts vs vague statements?)

    If score < threshold AND iterations not exhausted → marks for retry.
    """
    iteration = state.get("critic_iteration", 0) + 1
    logger.info("[critic] Review iteration %d", iteration)

    branch_results = state.get("branch_results", [])
    n_questions = len(state.get("sub_questions", []))
    n_answered = len([r for r in branch_results if r.get("status") == "done"])
    source_types = {s["source_type"] for r in branch_results for s in r.get("sources", [])}

    llm = _get_llm(temperature=0.2)   # low temp → consistent scoring
    prompt = f"""You are an adversarial research critic. Your job is to find weaknesses in this research synthesis.

**Research topic:** {state["topic"]}
**Sub-questions answered:** {n_answered}/{n_questions}
**Source types used:** {', '.join(source_types) if source_types else 'none'}

**Synthesis draft to review:**
{state.get("synthesis_draft", "")}

Score the synthesis on four dimensions (each 0.0–1.0):
- factual_consistency: Are claims grounded in the evidence provided?
- source_diversity: Are multiple source types (web, wikipedia, arxiv) represented?
- coverage: Does the synthesis address all {n_questions} sub-questions?
- specificity: Are concrete facts and figures cited, or is it vague?

Be harsh but fair. If the synthesis is genuinely good, score it highly.

Return ONLY valid JSON — no markdown fences, no extra text:
{{
    "factual_consistency": 0.0,
    "source_diversity": 0.0,
    "coverage": 0.0,
    "specificity": 0.0,
    "issues": ["issue 1", "issue 2"],
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""

    try:
        raw = llm.invoke(prompt).content
        scores_dict = _parse_json_response(raw, {
            "factual_consistency": 0.5,
            "source_diversity": 0.5,
            "coverage": 0.5,
            "specificity": 0.5,
            "issues": ["Could not parse critic response"],
            "suggestions": ["Re-run aggregation"],
        })
    except Exception as e:
        logger.error("[critic] LLM call failed: %s", e)
        scores_dict = {
            "factual_consistency": 0.5, "source_diversity": 0.5,
            "coverage": 0.5, "specificity": 0.5,
            "issues": [str(e)], "suggestions": [],
        }

    # Weighted average score
    score = round(
        scores_dict.get("factual_consistency", 0.5) * 0.35 +
        scores_dict.get("source_diversity", 0.5)    * 0.20 +
        scores_dict.get("coverage", 0.5)            * 0.30 +
        scores_dict.get("specificity", 0.5)         * 0.15,
        3,
    )

    passed = score >= _PASS_SCORE or iteration >= _MAX_ITERATIONS
    status = "done" if passed else "retry"

    logger.info(
        "[critic] Score=%.3f  passed=%s  (factual=%.2f source=%.2f coverage=%.2f specific=%.2f)",
        score, passed,
        scores_dict.get("factual_consistency", 0),
        scores_dict.get("source_diversity", 0),
        scores_dict.get("coverage", 0),
        scores_dict.get("specificity", 0),
    )

    feedback: CriticFeedback = {
        "passed": passed,
        "score": score,
        "issues": scores_dict.get("issues", []),
        "suggestions": scores_dict.get("suggestions", []),
        "iteration": iteration,
    }

    return {
        "critic_feedback": [feedback],
        "critic_iteration": iteration,
        "node_statuses": _update_status("critic", status),
        "graph_events": [_event("critic", status, {
            "score": score,
            "passed": passed,
            "iteration": iteration,
            "dimension_scores": {
                "factual_consistency": scores_dict.get("factual_consistency"),
                "source_diversity": scores_dict.get("source_diversity"),
                "coverage": scores_dict.get("coverage"),
                "specificity": scores_dict.get("specificity"),
            }
        })],
    }


# ── Node 5: Synthesizer ───────────────────────────────────────────────────────

def _deduplicate_sources(branch_results: list) -> list:
    """Merge all sources across branches, deduplicate by URL, sort by relevance."""
    seen: set = set()
    merged = []
    for branch in branch_results:
        for src in branch.get("sources", []):
            url = src.get("url", "")
            if url and url not in seen:
                merged.append(src)
                seen.add(url)
    return sorted(merged, key=lambda s: s.get("relevance_score", 0), reverse=True)


def _compute_overall_confidence(branch_results: list, critic_feedbacks: list) -> float:
    """
    Blend branch-level confidence scores with the final critic score.
    branch weight: 60%   critic weight: 40%
    """
    done = [r for r in branch_results if r.get("status") == "done"]
    if not done:
        return 0.0

    branch_avg = sum(r.get("confidence", 0) for r in done) / len(done)

    if critic_feedbacks:
        critic_score = critic_feedbacks[-1].get("score", branch_avg)
        blended = branch_avg * 0.6 + critic_score * 0.4
    else:
        blended = branch_avg

    return round(min(blended, 1.0), 3)


def synthesizer_node(state: ResearchState) -> dict:
    """
    Produces the final structured research report with:
    - Per-finding confidence scores and source attribution
    - Overall blended confidence (branch scores + critic score)
    - Deduplicated source list ranked by relevance
    - Concise executive summary
    Also persists the report to ResearchHistory (no user FK needed from graph).
    """
    logger.info("[synthesizer] Building final report for: %s", state["topic"])

    branch_results = state.get("branch_results", [])
    successful = [r for r in branch_results if r.get("status") == "done"]
    critic_feedbacks = state.get("critic_feedback", [])

    # ── Per-finding attributed blocks ─────────────────────────────────────────
    attributed_findings = []
    for r in successful:
        attributed_findings.append({
            "sub_question": r["question"],
            "finding": r["findings"],
            "confidence": r.get("confidence", 0.0),
            "sources": [
                {
                    "title": s["title"],
                    "url": s["url"],
                    "type": s["source_type"],
                }
                for s in r.get("sources", [])[:3]
            ],
        })

    # ── Overall confidence ────────────────────────────────────────────────────
    overall_confidence = _compute_overall_confidence(branch_results, critic_feedbacks)

    # ── Executive summary via LLM ─────────────────────────────────────────────
    synthesis_draft = state.get("synthesis_draft", "")
    llm = _get_llm(temperature=0.3)

    summary_prompt = f"""You are a research editor. Write a concise 3-sentence executive summary of this research.

Topic: {state["topic"]}

Full synthesis:
{synthesis_draft[:3000]}

Rules:
- 3 sentences maximum
- Start with the most important finding
- Be specific — include concrete facts if present
- Do NOT use the word 'delve'"""

    try:
        executive_summary = llm.invoke(summary_prompt).content.strip()
    except Exception as e:
        logger.error("[synthesizer] Summary LLM call failed: %s", e)
        executive_summary = synthesis_draft[:400]

    # ── All deduplicated sources ──────────────────────────────────────────────
    all_sources = _deduplicate_sources(branch_results)

    # ── Critic metadata for transparency ─────────────────────────────────────
    critic_meta = {}
    if critic_feedbacks:
        last = critic_feedbacks[-1]
        critic_meta = {
            "iterations": state.get("critic_iteration", 0),
            "final_score": last.get("score"),
            "passed_on_first_try": len(critic_feedbacks) == 1 and last.get("passed"),
        }

    final_report = {
        "topic": state["topic"],
        "run_id": state.get("run_id", ""),
        "overview": state.get("understanding", ""),
        "key_concepts": state.get("key_aspects", []),
        "important_findings": attributed_findings,
        "summary": executive_summary,
        "synthesis_draft": synthesis_draft,
        "confidence_score": overall_confidence,
        "sources": all_sources[:15],
        "critic": critic_meta,
        "node_statuses": dict(state.get("node_statuses", {})),
    }

    # ── Persist to DB (best-effort, no crash if it fails) ────────────────────
    try:
        from research.models import ResearchHistory
        ResearchHistory.objects.create(
            topic=state["topic"],
            run_id=state.get("run_id", ""),
            overview=state.get("understanding", ""),
            key_concepts=state.get("key_aspects", []),
            important_findings=[f["finding"][:500] for f in attributed_findings],
            summary=executive_summary,
            confidence_score=overall_confidence,
            final_report=final_report,
        )
        logger.info("[synthesizer] Saved to ResearchHistory run_id=%s", state.get("run_id"))
    except Exception as e:
        logger.warning("[synthesizer] DB persist failed (non-fatal): %s", e)

    logger.info(
        "[synthesizer] Done. confidence=%.3f  findings=%d  sources=%d  critic_iters=%d",
        overall_confidence, len(attributed_findings), len(all_sources),
        state.get("critic_iteration", 0),
    )

    return {
        "final_report": final_report,
        "node_statuses": _update_status("synthesizer", "done"),
        "graph_events": [_event("synthesizer", "done", {
            "confidence_score": overall_confidence,
            "finding_count": len(attributed_findings),
            "source_count": len(all_sources),
        })],
    }
