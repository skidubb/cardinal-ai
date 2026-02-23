#!/usr/bin/env python3
"""
Download, chunk, tag (via Haiku), and upsert academic papers to Pinecone.
Target index: multi-agent-kb | Namespace: academic-papers
"""

import os
import re
import json
import time
import hashlib
import requests
import fitz  # PyMuPDF
import anthropic
from pinecone import Pinecone

# --- Config ---
PINECONE_INDEX = "multi-agent-kb"
NAMESPACE = "academic-papers"
CHUNK_SIZE = 1500  # chars per chunk
CHUNK_OVERLAP = 200
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "context", "papers_pdf")
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# --- Papers to process ---
PAPERS = [
    {"id": 22, "title": "Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate", "url": "https://arxiv.org/abs/2509.05396", "tier": 1, "category": "debate"},
    {"id": 31, "title": "Rethinking the Bounds of LLM Reasoning: Are Multi-Agent Discussions the Key?", "url": "https://arxiv.org/pdf/2402.18272.pdf", "tier": 2, "category": "debate"},
    {"id": 34, "title": "Multi-Agent Consensus Seeking via Large Language Models", "url": "https://arxiv.org/pdf/2310.20151.pdf", "tier": 3, "category": "debate"},
    {"id": 41, "title": "Unlocking the Power of Multi-Agent LLM for Reasoning: From Lazy Agents to Deliberation", "url": "https://arxiv.org/abs/2511.02303", "tier": 2, "category": "debate"},
    {"id": 142, "title": "ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate", "url": "https://arxiv.org/abs/2308.07201", "tier": 2, "category": "debate"},
    {"id": 145, "title": "Adversarial Multi-Agent Evaluation of Large Language Models through Iterative Debates", "url": "https://arxiv.org/pdf/2410.04663", "tier": 3, "category": "debate"},
    {"id": 44, "title": "RouteMoA: Dynamic Routing without Pre-Inference Boosts Efficient Mixture-of-Agents", "url": "https://arxiv.org/abs/2601.18130", "tier": 1, "category": "routing"},
    {"id": 59, "title": "TCAndon-Router: Adaptive Reasoning Router for Multi-Agent Collaboration", "url": "https://arxiv.org/abs/2601.04544", "tier": 1, "category": "routing"},
    {"id": 143, "title": "RouteLLM: An Open-Source Framework for Cost-Effective LLM Routing", "url": "https://arxiv.org/abs/2406.18665", "tier": 2, "category": "routing"},
    {"id": 14, "title": "LLM Cascades with Mixture of Thoughts for Cost-efficient Reasoning", "url": "https://arxiv.org/abs/2310.03094", "tier": 2, "category": "routing"},
    {"id": 11, "title": "Mixture-of-Agents Enhances Large Language Model Capabilities", "url": "https://arxiv.org/abs/2406.04692", "tier": 1, "category": "topology"},
    {"id": 10, "title": "Chain of Agents: Large Language Models Collaborating on Long-Context Tasks", "url": "https://arxiv.org/abs/2406.02818", "tier": 1, "category": "topology"},
    {"id": 194, "title": "Talk Structurally, Act Hierarchically: A Collaborative Framework for LLM Multi-Agent Systems", "url": "https://arxiv.org/abs/2502.11098", "tier": 1, "category": "topology"},
    {"id": 58, "title": "Multi-Agent Collaboration via Evolving Orchestration", "url": "https://arxiv.org/abs/2504.07461", "tier": 1, "category": "topology"},
    {"id": 19, "title": "AGENTSNET: Coordination and Collaborative Reasoning in Multi-Agent LLMs", "url": "https://arxiv.org/abs/2507.08616", "tier": 1, "category": "topology"},
    {"id": 206, "title": "LLM Voting: Human Choices and AI Collective Decision Making", "url": "https://arxiv.org/abs/2402.01766", "tier": 2, "category": "voting"},
    {"id": 208, "title": "An Electoral Approach to Diversify LLM-based Multi-Agent Collective Decision-Making", "url": "https://arxiv.org/abs/2402.10727", "tier": 3, "category": "voting"},
    {"id": 135, "title": "Wisdom of the Silicon Crowd: LLM Ensemble Prediction Capabilities Match Human Crowd Accuracy", "url": "https://arxiv.org/abs/2402.19379", "tier": 2, "category": "voting"},
    {"id": 147, "title": "Why Do Multi-Agent LLM Systems Fail?", "url": "https://arxiv.org/abs/2503.13657", "tier": 1, "category": "evaluation"},
    {"id": 54, "title": "The Collaboration Gap", "url": "https://arxiv.org/abs/2511.02687", "tier": 1, "category": "evaluation"},
    {"id": 137, "title": "Are More LLM Calls All You Need? Towards Scaling Laws of Compound Inference Systems", "url": "https://arxiv.org/abs/2403.02419", "tier": 2, "category": "evaluation"},
    {"id": 43, "title": "Towards a Science of Scaling Agent Systems", "url": "https://arxiv.org/abs/2512.08296", "tier": 2, "category": "evaluation"},
    {"id": 4, "title": "More Agents is All You Need", "url": "https://arxiv.org/abs/2402.05120", "tier": 2, "category": "evaluation"},
    {"id": 160, "title": "Generative Agents: Interactive Simulacra of Human Behavior", "url": "https://arxiv.org/abs/2304.03442", "tier": 3, "category": "simulation"},
    {"id": 164, "title": "Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents", "url": "https://arxiv.org/abs/2404.16698", "tier": 3, "category": "simulation"},
    {"id": 170, "title": "Cultural Evolution of Cooperation among LLM Agents", "url": "https://arxiv.org/abs/2412.10270", "tier": 3, "category": "simulation"},
    {"id": 172, "title": "AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents", "url": "https://arxiv.org/abs/2502.08691", "tier": 3, "category": "simulation"},
]

# Protocol mapping for Haiku tagging
PROTOCOL_MAP = {
    "debate": ["P4-Debate", "P5-Negotiation", "P16-ACH", "P17-RedBlueWhite"],
    "routing": ["P0a-Router", "P0b-SkipGate", "P0c-Escalation"],
    "topology": ["P3-Synthesis", "P14-1-2-4-All", "P22-Pipeline"],
    "voting": ["P12-25/10", "P19-Vickrey", "P20-Borda"],
    "evaluation": ["Cross-cutting"],
    "simulation": ["Phase6-ABM"],
}


def arxiv_to_pdf_url(url: str) -> str:
    """Convert arxiv abs URL to PDF URL."""
    if "/abs/" in url:
        arxiv_id = url.split("/abs/")[-1].rstrip("/")
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    if "/pdf/" in url and not url.endswith(".pdf"):
        return url + ".pdf"
    return url


def download_pdf(url: str, filepath: str) -> bool:
    """Download PDF with retries."""
    if os.path.exists(filepath):
        print(f"  [cached] {os.path.basename(filepath)}")
        return True

    pdf_url = arxiv_to_pdf_url(url)
    for attempt in range(3):
        try:
            resp = requests.get(pdf_url, timeout=30, headers={"User-Agent": "CoordinationLab/1.0"})
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"  [downloaded] {os.path.basename(filepath)}")
                return True
            elif resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  [rate limited] waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [failed] status={resp.status_code} url={pdf_url}")
                return False
        except Exception as e:
            print(f"  [error] {e}")
            time.sleep(2)
    return False


def extract_text(filepath: str) -> str:
    """Extract text from PDF."""
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind('\n\n', start, end)
            if para_break > start + chunk_size // 2:
                end = para_break
            else:
                # Look for sentence break
                sent_break = text.rfind('. ', start, end)
                if sent_break > start + chunk_size // 2:
                    end = sent_break + 1

        chunk = text[start:end].strip()
        if len(chunk) > 50:  # Skip tiny chunks
            chunks.append(chunk)
        start = end - overlap if end < len(text) else len(text)

    return chunks


def tag_with_haiku(client: anthropic.Anthropic, chunk: str, paper: dict) -> dict:
    """Use Haiku to tag a chunk with protocol relevance and topics."""
    prompt = f"""You are tagging academic paper chunks for a multi-agent coordination research program.

Paper: "{paper['title']}"
Category: {paper['category']}
Related protocols: {', '.join(PROTOCOL_MAP.get(paper['category'], []))}

Chunk:
{chunk[:2000]}

Return ONLY valid JSON with these fields:
- "protocols": list of relevant protocol IDs from [P0a, P0b, P0c, P1-P5, P6-P15, P16-P18, P19-P21, P22-P23, P24-P25, P26-P27, Phase6-ABM]
- "topics": list of 2-4 topic tags from [debate, consensus, routing, cost-optimization, topology, scaling, emergence, cooperation, voting, evaluation, failure-modes, agent-design, communication, reasoning, simulation, reinforcement, negotiation, architecture]
- "key_finding": one sentence summarizing the chunk's main insight (empty string if chunk is boilerplate/references)
- "relevance": float 0.0-1.0 indicating relevance to multi-agent coordination research"""

    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1].lstrip("json\n")
        return json.loads(text)
    except Exception as e:
        print(f"    [haiku error] {e}")
        return {
            "protocols": PROTOCOL_MAP.get(paper["category"], []),
            "topics": [paper["category"]],
            "key_finding": "",
            "relevance": 0.5,
        }


def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Init clients
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    anthropic_client = anthropic.Anthropic()

    index = pc.Index(PINECONE_INDEX)

    total_chunks = 0
    failed_downloads = []

    for paper in PAPERS:
        print(f"\n[{paper['id']}] {paper['title']}")

        # Download
        safe_title = re.sub(r'[^\w\-]', '_', paper['title'])[:80]
        filepath = os.path.join(DOWNLOAD_DIR, f"{paper['id']}_{safe_title}.pdf")

        if not download_pdf(paper['url'], filepath):
            failed_downloads.append(paper['title'])
            continue

        # Extract & chunk
        text = extract_text(filepath)
        if len(text) < 200:
            print(f"  [skip] too little text extracted ({len(text)} chars)")
            failed_downloads.append(paper['title'])
            continue

        chunks = chunk_text(text)
        print(f"  {len(chunks)} chunks from {len(text)} chars")

        # Tag & upsert in batches
        records = []
        for i, chunk in enumerate(chunks):
            # Tag with Haiku
            tags = tag_with_haiku(anthropic_client, chunk, paper)

            # Skip low-relevance chunks (references, boilerplate)
            if tags.get("relevance", 0.5) < 0.2:
                continue

            chunk_id = hashlib.md5(f"{paper['id']}_{i}".encode()).hexdigest()

            record = {
                "_id": f"paper-{paper['id']}-chunk-{i:03d}",
                "text": chunk,
                "paper_id": paper["id"],
                "paper_title": paper["title"],
                "category": paper["category"],
                "tier": paper["tier"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "protocols": ", ".join(tags.get("protocols", [])),
                "topics": ", ".join(tags.get("topics", [])),
                "key_finding": tags.get("key_finding", ""),
                "relevance_score": tags.get("relevance", 0.5),
                "source_url": paper["url"],
            }
            records.append(record)

            # Upsert in batches of 20
            if len(records) >= 20:
                index.upsert_records(NAMESPACE, records)
                total_chunks += len(records)
                print(f"    upserted {len(records)} chunks (total: {total_chunks})")
                records = []
                time.sleep(0.5)  # Rate limit courtesy

        # Upsert remaining
        if records:
            index.upsert_records(NAMESPACE, records)
            total_chunks += len(records)
            print(f"    upserted {len(records)} chunks (total: {total_chunks})")

        # Brief pause between papers to respect arxiv rate limits
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Done! {total_chunks} chunks upserted to {PINECONE_INDEX}/{NAMESPACE}")
    if failed_downloads:
        print(f"\nFailed downloads ({len(failed_downloads)}):")
        for title in failed_downloads:
            print(f"  - {title}")


if __name__ == "__main__":
    main()
