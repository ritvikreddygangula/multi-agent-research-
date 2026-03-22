"""
Pinecone vector memory for the research pipeline.

HOW VECTORS ARE UPSERTED — step by step
────────────────────────────────────────
1. TEXT SELECTION
   We pick the most semantically rich text from the final report:
       "{topic}: {executive_summary}"
   e.g. "How does CRISPR work?: CRISPR-Cas9 edits DNA by..."

2. EMBEDDING
   OpenAI's text-embedding-ada-002 converts that string into a
   list of 1536 floats (a point in 1536-dimensional space).
   Similar texts land near each other in that space.

       "CRISPR gene editing" ──► [0.021, -0.134, 0.087, ..., 0.003]
                                   ▲                               ▲
                                dim_0                          dim_1535

3. UPSERT
   We push one record to Pinecone:
   {
       "id":     "5f7a4706-fd2d-48bf-92cf-27dd66ff993e",  ← run_id (UUID)
       "values": [0.021, -0.134, 0.087, ..., 0.003],      ← 1536 floats
       "metadata": {
           "topic":      "How does CRISPR work?",
           "summary":    "CRISPR-Cas9 edits DNA by...",
           "confidence": 0.673,
           "run_id":     "5f7a4706-..."
       }
   }

4. RETRIEVAL (before next research run on a related topic)
   The new topic is embedded the same way, then Pinecone returns
   the top-K vectors with the highest cosine similarity.
   Cosine similarity = dot-product of unit vectors = angle between them.
   Score 1.0 = identical direction, 0.0 = orthogonal, <0 = opposite.
   We only surface results with score > 0.75.

   "What does CRISPR do?" ──► embed ──► query Pinecone
       match: "How does CRISPR work?"  score=0.91  ← returned as context
       match: "RNA splicing mechanisms" score=0.61  ← filtered out (< 0.75)
"""

import logging
from typing import List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.75
_EMBED_MODEL = "text-embedding-ada-002"


class PineconeMemoryService:

    def __init__(self):
        from pinecone import Pinecone, ServerlessSpec
        from langchain_openai import OpenAIEmbeddings

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME

        existing = [i.name for i in pc.list_indexes()]
        if index_name not in existing:
            pc.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info("[pinecone] Created index '%s'", index_name)

        self.index = pc.Index(index_name)
        self.embeddings = OpenAIEmbeddings(
            model=_EMBED_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def retrieve_similar(self, topic: str, top_k: int = 3) -> List[dict]:
        """
        Embed `topic` and return prior research runs with cosine similarity > threshold.

        Example return value:
        [
            {
                "topic": "How does CRISPR work?",
                "summary": "CRISPR-Cas9 edits DNA by...",
                "confidence": 0.673,
                "similarity_score": 0.91,
                "run_id": "5f7a4706-..."
            }
        ]
        """
        try:
            vector = self.embeddings.embed_query(topic)
            results = self.index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True,
            )
            matches = [
                {
                    "topic":            m["metadata"].get("topic", ""),
                    "summary":          m["metadata"].get("summary", ""),
                    "confidence":       m["metadata"].get("confidence", 0.0),
                    "similarity_score": round(m["score"], 4),
                    "run_id":           m["metadata"].get("run_id", ""),
                }
                for m in results.get("matches", [])
                if m["score"] >= _SIMILARITY_THRESHOLD
            ]
            logger.info("[pinecone] '%s' → %d similar runs found", topic, len(matches))
            return matches
        except Exception as e:
            logger.warning("[pinecone] retrieve_similar failed (non-fatal): %s", e)
            return []

    def upsert_report(self, run_id: str, final_report: dict) -> None:
        """
        Embed the completed report and store it in Pinecone.

        The text we embed is: "{topic}: {executive_summary}"
        This captures both the subject and the key findings in one vector,
        making retrieval effective for semantically related future queries.

        Example upserted record:
        {
            "id": "5f7a4706-fd2d-48bf-92cf-27dd66ff993e",
            "values": [0.021, -0.134, 0.087, ..., 0.003],   ← 1536 floats
            "metadata": {
                "topic":      "How does CRISPR work?",
                "summary":    "CRISPR-Cas9 edits DNA by guiding...",
                "confidence": 0.673,
                "run_id":     "5f7a4706-..."
            }
        }
        """
        if not run_id:
            logger.warning("[pinecone] upsert skipped — empty run_id")
            return

        try:
            topic = final_report.get("topic", "")
            summary = final_report.get("summary", "")
            text_to_embed = f"{topic}: {summary}"

            vector = self.embeddings.embed_query(text_to_embed)

            self.index.upsert(vectors=[{
                "id": run_id,
                "values": vector,
                "metadata": {
                    "topic":      topic,
                    "summary":    summary[:500],     # Pinecone metadata limit
                    "confidence": final_report.get("confidence_score", 0.0),
                    "run_id":     run_id,
                },
            }])
            logger.info("[pinecone] Upserted run_id=%s (dim=1536)", run_id)
        except Exception as e:
            logger.warning("[pinecone] upsert failed (non-fatal): %s", e)
