#!/usr/bin/env python3
"""Seed dee_profiles table with canonical taxonomy data + Gemini embeddings.

Usage:
    python scripts/seed_dee_profiles.py
    python scripts/seed_dee_profiles.py --dry-run
    python scripts/seed_dee_profiles.py --dsn "postgresql://user:pass@host:5432/db"

Requires: google-generativeai, asyncpg, pgvector

Environment variables:
    GOOGLE_API_KEY  — Gemini API key
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS — database connection
    DATABASE_URL    — alternative full DSN
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("seed_dee_profiles")

# Add netrun-dee src to path
_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_this_dir, "..", "src"))


def build_dsn(args_dsn: str | None) -> str:
    """Build DSN from args or environment."""
    if args_dsn:
        return args_dsn
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "charlotte_db")
    user = os.environ.get("DB_USER", "charlotte_user")
    pw = os.environ.get("DB_PASS", "")
    if host.startswith("/"):
        return f"postgresql://{user}:{pw}@/{name}"
    return f"postgresql://{user}:{pw}@{host}:{port}/{name}"


def load_taxonomy() -> list[dict]:
    """Load the 39 DEE profiles from taxonomy JSON + lexicon data."""
    from netrun.dee.taxonomy import DEE_PROFILES_LIST
    from netrun.dee.lexicon import DEE_LEXICONS

    profiles = []
    for p in DEE_PROFILES_LIST:
        # Build embedding text: name + behavioral_markers + creative_use
        embed_text = f"{p.name}. {p.behavioral_markers}"
        if p.creative_use:
            embed_text += f" {p.creative_use}"

        # Serialize lexicon entries for this profile
        lexicon_entries = DEE_LEXICONS.get(p.id, [])
        lexicon_json = [
            {
                "pattern": e.pattern,
                "weight": e.weight,
                "category": e.category,
                "is_regex": e.is_regex,
            }
            for e in lexicon_entries
        ]

        profiles.append(
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "valence": p.valence,
                "arousal": p.arousal,
                "dominance": p.dominance,
                "variants": p.variants,
                "behavioral_markers": p.behavioral_markers,
                "embed_text": embed_text,
                "lexicon": lexicon_json,
            }
        )
    return profiles


_genai_configured = False
_genai_lock = threading.Lock()


def ensure_genai():
    global _genai_configured
    if _genai_configured:
        return
    with _genai_lock:
        if not _genai_configured:
            import google.generativeai as genai
            genai.configure(api_key=os.environ.get("GOOGLE_API_KEY", ""))
            _genai_configured = True


def embed_sync(text: str) -> list[float]:
    """Generate 768-dim embedding synchronously."""
    ensure_genai()
    import google.generativeai as genai

    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        output_dimensionality=768,
        task_type="RETRIEVAL_DOCUMENT",
    )
    emb = result["embedding"]
    return emb if isinstance(emb[0], float) else emb[0]


async def embed_all(profiles: list[dict]) -> list[list[float]]:
    """Generate embeddings for all profiles."""
    embeddings = []
    for i, p in enumerate(profiles):
        emb = await asyncio.to_thread(embed_sync, p["embed_text"])
        embeddings.append(emb)
        logger.info("Embedded %d/%d: %s (%s)", i + 1, len(profiles), p["id"], p["name"])
    return embeddings


async def upsert_profiles(dsn: str, profiles: list[dict], embeddings: list[list[float]], db_host: str | None = None):
    """Upsert all profiles into dee_profiles table."""
    import asyncpg

    pool_kwargs = {
        "dsn": dsn,
        "min_size": 1,
        "max_size": 3,
        "command_timeout": 60,
    }
    if db_host and db_host.startswith("/"):
        pool_kwargs["host"] = db_host

    pool = await asyncpg.create_pool(**pool_kwargs)
    try:
        for p, emb in zip(profiles, embeddings):
            emb_str = "[" + ",".join(f"{v:.10f}" for v in emb) + "]"
            await pool.execute(
                """
                INSERT INTO dee_profiles
                    (id, name, category, valence, arousal, dominance,
                     variants, behavioral_markers, embedding, lexicon)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::vector, $10::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    valence = EXCLUDED.valence,
                    arousal = EXCLUDED.arousal,
                    dominance = EXCLUDED.dominance,
                    variants = EXCLUDED.variants,
                    behavioral_markers = EXCLUDED.behavioral_markers,
                    embedding = EXCLUDED.embedding,
                    lexicon = EXCLUDED.lexicon
                """,
                p["id"],
                p["name"],
                p["category"],
                p["valence"],
                p["arousal"],
                p["dominance"],
                json.dumps(p["variants"]),
                p["behavioral_markers"],
                emb_str,
                json.dumps(p["lexicon"]),
            )
            logger.info("Upserted %s: %s", p["id"], p["name"])
    finally:
        await pool.close()


async def main():
    parser = argparse.ArgumentParser(description="Seed DEE profiles with Gemini embeddings")
    parser.add_argument("--dsn", help="Database DSN")
    parser.add_argument("--dry-run", action="store_true", help="Load and embed only, skip DB write")
    args = parser.parse_args()

    dsn = build_dsn(args.dsn)

    logger.info("Loading taxonomy...")
    profiles = load_taxonomy()
    logger.info("Loaded %d profiles", len(profiles))

    logger.info("Generating Gemini embeddings (text-embedding-004, 768 dims)...")
    embeddings = await embed_all(profiles)
    logger.info("All embeddings generated")

    if args.dry_run:
        logger.info("DRY RUN — skipping database writes")
        for p, emb in zip(profiles, embeddings):
            logger.info(
                "  %s %-25s  embedding_dims=%d  lexicon_entries=%d",
                p["id"],
                p["name"],
                len(emb),
                len(p["lexicon"]),
            )
        return

    db_host = os.environ.get("DB_HOST", "")
    logger.info("Upserting profiles to database...")
    await upsert_profiles(dsn, profiles, embeddings, db_host if db_host.startswith("/") else None)
    logger.info("Seed complete: %d profiles upserted", len(profiles))


if __name__ == "__main__":
    asyncio.run(main())
