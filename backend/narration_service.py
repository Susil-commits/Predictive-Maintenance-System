"""
Narration Service & RAG Vector Engine for Predictive Maintenance System (PMS).

This module implements a separate abstraction layer on top of predictor.py:
1. Component 1: LLM Narration grounded strictly in prediction JSON and retrieved RAG context.
2. Component 2: Lightweight RAG vector store indexing standard industrial maintenance procedures.
3. Component 3: Linear orchestration pipeline (predict -> retrieve -> narrate -> assemble).

CRITICAL INVARIANT:
- Does NOT modify or depend upon modifying predictor.py's core prediction logic.
- Gracefully and silently falls back to canned suggested_action on any LLM failure or timeout.
- Fully auditable: Returns retrieved procedure chunks alongside the generated narrative.
"""

import os
import re
import glob
import time
import logging
import httpx
from typing import Optional, Dict, Any, List

from .predictor import predictor, find_minimal_fix, calibrated_model, scaler, FEATURE_ORDER

logger = logging.getLogger("pms.narration")

# Directory paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(CURRENT_DIR, "knowledge_base")
CHROMA_PERSIST_DIR = os.path.join(CURRENT_DIR, "chroma_db")
COLLECTION_NAME = "pms_maintenance_procedures"

# Query mapping from top_risk_factor / failure mode to semantic RAG search queries
QUERY_EXPANSIONS: Dict[str, str] = {
    "temperature": "Thermal Heat Dissipation Failure (HDF) cooling circuit heat exchanger inspection",
    "thermal": "Thermal Heat Dissipation Failure (HDF) cooling circuit heat exchanger inspection",
    "pressure": "Overstrain Failure (OSF) hydraulic overpressure relief valve accumulator strain",
    "overstrain": "Overstrain Failure (OSF) hydraulic overpressure relief valve accumulator strain",
    "vibration": "Vibration Fatigue bearing wear dynamic rotor imbalance shaft misalignment",
    "operating_hours": "Tool Wear Failure (TWF) cumulative cutting flank wear insert replacement",
    "tool_wear": "Tool Wear Failure (TWF) cumulative cutting flank wear insert replacement",
    "tool wear": "Tool Wear Failure (TWF) cumulative cutting flank wear insert replacement",
    "rpm": "Power Failure (PWF) electrical drive motor torque stall speed unbalance",
    "power": "Power Failure (PWF) electrical drive motor torque stall speed unbalance",
}

FAILURE_MODE_MAP: Dict[str, str] = {
    "temperature": "Thermal (HDF)",
    "thermal": "Thermal (HDF)",
    "pressure": "Overstrain (OSF)",
    "overstrain": "Overstrain (OSF)",
    "vibration": "Vibration Fatigue (VIB)",
    "operating_hours": "Tool Wear (TWF)",
    "tool_wear": "Tool Wear (TWF)",
    "tool wear": "Tool Wear (TWF)",
    "rpm": "Power (PWF)",
    "power": "Power (PWF)",
}


class MaintenanceRAGStore:
    """
    Lightweight vector store for industrial maintenance procedures using ChromaDB.
    Maintains a robust fallback mechanism if ChromaDB cannot initialize.
    """
    def __init__(self, kb_dir: str = KNOWLEDGE_BASE_DIR, persist_dir: str = CHROMA_PERSIST_DIR):
        self.kb_dir = kb_dir
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self._fallback_chunks: List[Dict[str, Any]] = []
        self._init_store()

    def _parse_markdown_chunks(self) -> List[Dict[str, Any]]:
        """
        Parses all .md files in the knowledge base into semantic chunks.
        Each chunk represents a logical section (Overview, Symptoms, Protocol, Causes, Remediation).
        """
        chunks = []
        md_files = glob.glob(os.path.join(self.kb_dir, "*.md"))
        if not md_files:
            logger.warning(f"No knowledge base documents found in {self.kb_dir}")
            return chunks

        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title from # header
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else os.path.basename(file_path)

                # Determine failure mode
                lower_title = title.lower()
                if "thermal" in lower_title:
                    failure_mode = "Thermal (HDF)"
                elif "overstrain" in lower_title:
                    failure_mode = "Overstrain (OSF)"
                elif "tool wear" in lower_title:
                    failure_mode = "Tool Wear (TWF)"
                elif "power" in lower_title:
                    failure_mode = "Power (PWF)"
                elif "vibration" in lower_title:
                    failure_mode = "Vibration Fatigue (VIB)"
                else:
                    failure_mode = "General Maintenance"

                # Split by ## headers (sections)
                sections = re.split(r"\n(?=##\s+)", content)
                sec_idx = 0
                for sec in sections:
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue
                    sec_header_match = re.match(r"^##\s+(.+)$", sec_clean, re.MULTILINE)
                    if not sec_header_match:
                        # Skip pure title block if it contains no substantive body text
                        body_without_title = re.sub(r"^#\s+[^\n]+", "", sec_clean).strip()
                        if not body_without_title:
                            continue
                        sec_name = "Overview & System Context"
                    else:
                        sec_name = sec_header_match.group(1).strip()

                    sec_idx += 1
                    chunk_id = f"{os.path.splitext(os.path.basename(file_path))[0]}_chunk_{sec_idx}"
                    chunks.append({
                        "id": chunk_id,
                        "failure_mode": failure_mode,
                        "title": title,
                        "section": sec_name,
                        "content": sec_clean
                    })
            except Exception as e:
                logger.error(f"Failed to parse markdown document {file_path}: {e}")

        return chunks

    def _init_store(self):
        """Initializes ChromaDB persistent client and collection, seeding chunks if needed."""
        chunks = self._parse_markdown_chunks()
        self._fallback_chunks = chunks

        try:
            import chromadb
            os.makedirs(self.persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Standard Industrial Maintenance Procedures for PMS"}
            )

            # Check if collection already has documents
            if self.collection.count() == 0 and chunks:
                logger.info(f"Indexing {len(chunks)} maintenance procedure chunks into ChromaDB...")
                ids = [str(c["id"]) for c in chunks]
                docs = [str(c["content"]) for c in chunks]
                metadatas: Any = [{
                    "failure_mode": str(c["failure_mode"]),
                    "title": str(c["title"]),
                    "section": str(c["section"])
                } for c in chunks]

                self.collection.add(
                    ids=ids,
                    documents=docs,
                    metadatas=metadatas
                )
                logger.info("ChromaDB indexing completed successfully.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed ({e}). Operating in memory fallback mode.")
            self.collection = None

    def retrieve(self, query: str, n_results: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves the top matching procedure chunks for a given query or failure mode.
        Returns auditable chunk dictionaries.
        """
        if not query:
            query = "vibration"

        norm_query = query.lower().strip()
        semantic_query = QUERY_EXPANSIONS.get(norm_query, query)
        target_mode = FAILURE_MODE_MAP.get(norm_query)

        # 1. Try ChromaDB retrieval
        if self.collection is not None:
            try:
                # Optionally filter by failure_mode if identified
                where_clause = {"failure_mode": target_mode} if target_mode else None
                query_args: Dict[str, Any] = {
                    "query_texts": [semantic_query],
                    "n_results": min(n_results, max(1, self.collection.count()))
                }
                if where_clause:
                    query_args["where"] = where_clause

                results = self.collection.query(**query_args)
                docs_list = results.get("documents") or []
                metas_list = results.get("metadatas") or []
                dists_list = results.get("distances") or []

                # If filtered search returned empty, query without where clause
                if (not docs_list or not docs_list[0]) and where_clause:
                    del query_args["where"]
                    results = self.collection.query(**query_args)
                    docs_list = results.get("documents") or []
                    metas_list = results.get("metadatas") or []
                    dists_list = results.get("distances") or []

                retrieved = []
                docs = docs_list[0] if docs_list else []
                metas = metas_list[0] if metas_list else []
                distances = dists_list[0] if dists_list else [None] * len(docs)

                for doc, meta, dist in zip(docs, metas, distances):
                    meta_dict = meta if isinstance(meta, dict) else {}
                    retrieved.append({
                        "failure_mode": str(meta_dict.get("failure_mode", "General")),
                        "title": str(meta_dict.get("title", "")),
                        "section": str(meta_dict.get("section", "")),
                        "content": str(doc),
                        "relevance_score": round(1.0 - float(dist), 4) if dist is not None else None
                    })

                if retrieved:
                    return retrieved
            except Exception as e:
                logger.warning(f"ChromaDB query failed ({e}); falling back to in-memory matching.")

        # 2. Resilient In-Memory Fallback
        return self._fallback_retrieve(norm_query, target_mode, n_results)

    def _fallback_retrieve(self, norm_query: str, target_mode: Optional[str], n_results: int) -> List[Dict[str, Any]]:
        """Simple deterministic matching fallback using target failure mode or keyword overlap."""
        matches = []
        for chunk in self._fallback_chunks:
            score = 0.0
            if target_mode and chunk["failure_mode"] == target_mode:
                score += 2.0
            if norm_query in chunk["content"].lower():
                score += 1.0
            if "remediation" in chunk["section"].lower() or "protocol" in chunk["section"].lower():
                score += 0.5

            if score > 0:
                matches.append((score, chunk))

        matches.sort(key=lambda x: x[0], reverse=True)
        top = matches[:n_results]

        return [{
            "failure_mode": c["failure_mode"],
            "title": c["title"],
            "section": c["section"],
            "content": c["content"],
            "relevance_score": round(score / 3.5, 4)
        } for score, c in top]


# Global RAG store singleton
rag_store = MaintenanceRAGStore()


class LLMNarrationClient:
    """
    Client for generating fluent, grounded operational narratives using external LLMs.
    Guarantees strict grounding in provided numbers and graceful fallback to canned guidance.
    """
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model_name = os.getenv("LLM_MODEL", "gemini-1.5-flash")
        self.timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "5.0"))

    def build_prompt(
        self,
        prediction: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        counterfactual: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Builds a narrow, strictly grounded prompt using only pre-computed structured metrics.
        Never passes raw unvalidated telemetry.
        """
        prob_pct = round(float(prediction.get("probability", 0.0)) * 100, 1)
        top_factor = prediction.get("top_risk_factor") or "Unspecified"
        contrib_pct = prediction.get("contribution_pct", 0.0)
        risk_level = prediction.get("failure_risk", "UNKNOWN")

        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            context_blocks.append(
                f"[Source {idx}: {chunk.get('title')} - {chunk.get('section')}]\n{chunk.get('content')}"
            )
        context_text = "\n\n".join(context_blocks) if context_blocks else "Standard industrial operating procedures."

        cf_info = ""
        if counterfactual and not counterfactual.get("already_safe", True):
            feat = counterfactual.get("feature_to_change")
            curr = counterfactual.get("current_value")
            target = counterfactual.get("target_value")
            reduct = counterfactual.get("reduction_needed_pct")
            risk_after = counterfactual.get("risk_after")
            cf_info = (
                f"\nRemediation Target: Adjust {feat} from {curr} to {target} "
                f"({reduct}% reduction) to lower risk to {risk_after}%."
            )

        prompt = f"""You are a technical maintenance advisor for an industrial machinery reliability team.
Write a concise, authoritative, and fluent 2 to 3 sentence operational briefing for plant technicians.

GIVEN STRUCTURED PREDICTION METRICS:
- Failure Risk Level: {risk_level}
- Failure Probability: {prob_pct}%
- Dominant Risk Driver: {top_factor} (contributes {contrib_pct}% of total risk){cf_info}

OFFICIAL MAINTENANCE STANDARD OPERATING PROCEDURE (CONTEXT):
{context_text}

STRICT INSTRUCTIONS:
1. Write exactly 2 to 3 clear, professional sentences explaining the equipment's current risk state and actionable next steps.
2. Ground your briefing STRICTLY in the exact numbers and metrics given above. DO NOT invent, hallucinate, or alter any numerical figures, percentages, or units.
3. Quote or reference specific action items from the retrieved Standard Operating Procedure.
4. Keep the tone technical, objective, and urgent if risk is HIGH, or reassuring if risk is LOW.
5. Return ONLY the narrative text. Do not output markdown headers or bullet points.
"""
        return prompt

    def generate_narrative(
        self,
        prediction: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        counterfactual: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Executes the LLM narration call with robust error handling.
        Silently falls back to canned suggested_action if the external LLM is down,
        times out, or is unconfigured.
        """
        fallback_text = prediction.get("suggested_action") or "Telemetry indicates nominal baseline operation."
        prompt = self.build_prompt(prediction, retrieved_chunks, counterfactual)

        # 1. Check if an API key is available
        if not self.gemini_api_key and not self.openai_api_key:
            logger.debug("No external LLM API key detected; using canned prescriptive guidance.")
            return fallback_text

        # 2. Call external LLM with strict timeout
        try:
            if self.gemini_api_key:
                return self._call_gemini(prompt)
            elif self.openai_api_key:
                return self._call_openai(prompt)
        except Exception as e:
            logger.warning(f"External LLM call failed ({e}); gracefully falling back to canned guidance.")

        return fallback_text

    def _call_gemini(self, prompt: str) -> str:
        """Calls Google Gemini API via REST using httpx."""
        model = self.model_name if "gemini" in self.model_name else "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 200
            }
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            raise RuntimeError("Gemini returned empty candidate content")

    def _call_openai(self, prompt: str) -> str:
        """Calls OpenAI-compatible Chat Completions API via REST using httpx."""
        model = self.model_name if "gpt" in self.model_name else "gpt-4o-mini"
        url = f"{self.openai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a machinery reliability diagnostic engine."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 200
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            raise RuntimeError("OpenAI returned empty choices")


# Global LLM client singleton
llm_client = LLMNarrationClient()


# ─────────────────────────────────────────────────────────────────────────────
# Component 3: Orchestration Function
# ─────────────────────────────────────────────────────────────────────────────

def orchestrate_predict_and_narrate(
    input_dict: Dict[str, Any],
    threshold: Optional[float] = None,
    include_counterfactual: bool = False
) -> Dict[str, Any]:
    """
    Linear function composition that executes:
    1. Core Prediction: calls predictor.predict (unchanged)
    2. Optional Counterfactual: computes minimal fix if requested
    3. RAG Retrieval: pulls top matching procedure chunks based on top_risk_factor
    4. LLM Narration: synthesizes metrics and procedure context into a fluent briefing
    5. Assembly: combines prediction, suggested_action, narrative, and auditable sources

    Pure composition — simple, debuggable, zero dependency on heavy orchestration frameworks.
    """
    active_threshold = threshold if threshold is not None else getattr(predictor, "threshold", 0.50)

    # Step 1: Execute existing prediction logic
    pred_result = predictor.predict(input_dict, threshold=active_threshold)

    # Step 2: Optionally compute counterfactual remediation
    cf_result = None
    if include_counterfactual:
        try:
            cf_result = find_minimal_fix(
                calibrated_model,
                scaler,
                input_dict,
                FEATURE_ORDER,
                threshold=active_threshold
            )
        except Exception as cf_err:
            logger.warning(f"Counterfactual calculation failed in orchestration: {cf_err}")

    # Step 3: RAG Retrieval keyed on top_risk_factor
    top_risk = pred_result.get("top_risk_factor") or "vibration"
    retrieved_sources = rag_store.retrieve(query=top_risk, n_results=2)

    # Step 4: LLM Narration synthesis (with silent fallback to canned suggested_action)
    try:
        narrative = llm_client.generate_narrative(
            prediction=pred_result,
            retrieved_chunks=retrieved_sources,
            counterfactual=cf_result
        )
    except Exception as llm_err:
        logger.warning(f"LLM narration call failed ({llm_err}); silently falling back to canned guidance.")
        narrative = pred_result.get("suggested_action") or "Telemetry indicates nominal baseline operation."

    # Step 5: Assemble output payload
    output = dict(pred_result)
    output["narrative"] = narrative
    output["retrieved_sources"] = retrieved_sources
    if cf_result:
        output["counterfactual"] = cf_result

    return output
