#!/usr/bin/env python3
"""
utils_entity.py - Entity extraction for legal documents using GPT-4o-mini

Extracts structured entities from document chunks:
- PERSON (parties, attorneys, witnesses, notaries)
- PARCEL (property identifiers, legal descriptions)
- DATE (recording dates, effective dates, execution dates)
- AMOUNT (purchase prices, consideration amounts)
- ORG (corporations, LLCs, government entities)

With legal-specific roles:
- grantor/grantee (conveyance parties)
- subject (property being conveyed)
- witness/notary (signing parties)
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime


# Entity extraction configuration
ENTITY_CONFIG = {
    "version": "1.0",
    "types": [
        {
            "name": "PERSON",
            "description": "Individual parties (grantors, grantees, witnesses, attorneys, notaries)",
            "examples": ["John Smith", "Mary Johnson, Jr.", "Robert Williams"]
        },
        {
            "name": "PARCEL",
            "description": "Property identifiers (parcel numbers, tract numbers, legal descriptions)",
            "examples": ["Parcel 123", "Tract 7", "Lot 45", "Abstract 456"]
        },
        {
            "name": "DATE",
            "description": "Any date (recording, execution, effective dates)",
            "examples": ["December 5, 2022", "2022-12-05", "12/5/2022"]
        },
        {
            "name": "AMOUNT",
            "description": "Monetary values (purchase prices, consideration, tax amounts)",
            "examples": ["$500,000", "Five Hundred Thousand Dollars", "$1.5M"]
        },
        {
            "name": "ORG",
            "description": "Organizations (corporations, LLCs, government entities, partnerships)",
            "examples": ["Silver Hill Haynesville E&P LLC", "Shelby County", "Marathon Oil"]
        }
    ],
    "roles": [
        {"name": "grantor", "description": "Party conveying property"},
        {"name": "grantee", "description": "Party receiving property"},
        {"name": "subject", "description": "Property/parcel being conveyed"},
        {"name": "witness", "description": "Signing witness"},
        {"name": "notary", "description": "Notary public"},
        {"name": None, "description": "Other/unknown role"}
    ]
}


def build_entity_extraction_prompt(text: str, config: Dict = ENTITY_CONFIG) -> str:
    """
    Build GPT-4o-mini prompt for entity extraction.

    Args:
        text: Document chunk text
        config: Entity configuration

    Returns:
        Formatted prompt string
    """
    entity_types_desc = "\n".join([
        f"- **{et['name']}**: {et['description']}\n  Examples: {', '.join(et['examples'])}"
        for et in config["types"]
    ])

    roles_desc = "\n".join([
        f"- **{r['name'] or 'null'}**: {r['description']}"
        for r in config["roles"]
    ])

    prompt = f"""You are a legal document analyst. Extract structured entities from the following text.

ENTITY TYPES:
{entity_types_desc}

ENTITY ROLES (for PERSON and PARCEL types):
{roles_desc}

TEXT TO ANALYZE:
{text}

INSTRUCTIONS:
1. Extract all entities of the types listed above
2. For PERSON and PARCEL entities, assign a role if evident from context
3. Return entities as a JSON array
4. Be precise - only extract entities explicitly mentioned in the text
5. Include confidence score (0.0-1.0) for each entity

OUTPUT FORMAT:
{{
  "entities": [
    {{
      "text": "John Smith",
      "type": "PERSON",
      "role": "grantor",
      "confidence": 0.95
    }},
    {{
      "text": "Parcel 123",
      "type": "PARCEL",
      "role": "subject",
      "confidence": 0.90
    }}
  ]
}}

Return ONLY the JSON object, no additional text."""

    return prompt


def extract_entities_gpt4o(
    text: str,
    config: Dict = ENTITY_CONFIG,
    api_key: Optional[str] = None,
    track_costs: bool = True
) -> Dict:
    """
    Extract entities from text using GPT-4o-mini.

    Args:
        text: Document chunk text
        config: Entity configuration
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        track_costs: If True, log token usage and costs

    Returns:
        Dict with extracted entities and metadata:
        {
            "entities": [...],
            "cost": 0.0015,
            "tokens_in": 1234,
            "tokens_out": 123,
            "model": "gpt-4o-mini",
            "extracted_at": "2025-10-29T17:30:00Z"
        }
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI SDK not installed. Install with: pip install openai"
        )

    # Initialize OpenAI client
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
        )

    client = OpenAI(api_key=api_key)

    # Build prompt
    prompt = build_entity_extraction_prompt(text, config)

    # Call GPT-4o-mini
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal document analyst specializing in entity extraction. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,  # Deterministic extraction
            max_tokens=2500,  # Increased for legal docs with many entities
            response_format={"type": "json_object"}  # Ensure JSON response
        )

        # Parse response
        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # Track costs if enabled
        metadata = {
            "model": "gpt-4o-mini",
            "extracted_at": datetime.utcnow().isoformat() + "Z"
        }

        if track_costs:
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

            # GPT-4o-mini pricing (as of Oct 2024)
            cost_per_1m_in = 0.150  # $0.150 per 1M input tokens
            cost_per_1m_out = 0.600  # $0.600 per 1M output tokens

            cost = (tokens_in * cost_per_1m_in + tokens_out * cost_per_1m_out) / 1_000_000

            metadata.update({
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost": cost
            })

        # Merge entities with metadata
        result.update(metadata)

        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse GPT response as JSON: {e}\nResponse: {result_text}")
    except Exception as e:
        raise RuntimeError(f"Entity extraction failed: {e}")


def normalize_entities(entities: List[Dict]) -> List[Dict]:
    """
    Normalize extracted entities for consistency.

    Normalization:
    - Lowercase entity text (for matching/deduping)
    - Strip whitespace
    - Deduplicate identical entities
    - Sort by confidence (highest first)

    Args:
        entities: List of entity dicts from GPT extraction

    Returns:
        Normalized entity list
    """
    normalized = []
    seen = set()

    for entity in entities:
        # Create normalized version for deduping
        text_normalized = entity["text"].strip().lower()
        entity_type = entity.get("type", "UNKNOWN")
        role = entity.get("role")

        # Create unique key for deduping
        key = (text_normalized, entity_type, role)

        if key not in seen:
            seen.add(key)

            # Keep original text, add normalized version
            entity["text_normalized"] = text_normalized
            normalized.append(entity)

    # Sort by confidence (highest first)
    normalized.sort(key=lambda e: e.get("confidence", 0.0), reverse=True)

    return normalized


def extract_entities(
    text: str,
    extractor: str = "gpt-4o-mini",
    config: Dict = ENTITY_CONFIG,
    normalize: bool = True,
    **kwargs
) -> Dict:
    """
    Main entity extraction function with pluggable extractors.

    Args:
        text: Document chunk text
        extractor: Extractor to use ("gpt-4o-mini", "gliner", "spacy")
        config: Entity configuration
        normalize: If True, normalize entities
        **kwargs: Passed to extractor function

    Returns:
        Extraction result dict with entities and metadata
    """
    if extractor == "gpt-4o-mini":
        result = extract_entities_gpt4o(text, config=config, **kwargs)
    elif extractor == "gliner":
        # Future: implement GLiNER extractor
        raise NotImplementedError("GLiNER extractor not yet implemented")
    elif extractor == "spacy":
        # Future: implement spaCy extractor
        raise NotImplementedError("spaCy extractor not yet implemented")
    else:
        raise ValueError(f"Unknown extractor: {extractor}")

    # Normalize entities if requested
    if normalize and "entities" in result:
        result["entities"] = normalize_entities(result["entities"])

    return result


# Export configuration for use in other modules
__all__ = [
    "ENTITY_CONFIG",
    "extract_entities",
    "extract_entities_gpt4o",
    "normalize_entities",
    "build_entity_extraction_prompt"
]
