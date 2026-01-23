"""
Quote Verifier for LDS Content
Verifies prophet quotes and scripture references for accuracy.
"""

import json
from typing import Optional
from difflib import SequenceMatcher

# Import the content database
from .content_search import SCRIPTURE_TOPICS, PROPHET_QUOTES


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def verify_lds_quote(
    quote: str,
    attributed_to: str,
    source: str = ""
) -> dict:
    """
    Verify if a prophet quote or scripture reference is accurate.

    Args:
        quote: The quote text to verify
        attributed_to: Who the quote is attributed to
        source: Optional claimed source

    Returns:
        dict: Verification result with status and details
    """
    result = {
        "quote": quote,
        "attributed_to": attributed_to,
        "claimed_source": source,
        "verification_status": "unverified",
        "confidence": 0.0,
        "details": {},
        "warnings": [],
        "recommendations": []
    }

    attributed_lower = attributed_to.lower()

    # Check if it's a scripture reference
    is_scripture = any(book in attributed_lower for book in [
        "nephi", "alma", "mosiah", "ether", "moroni", "mormon",
        "helaman", "jacob", "enos", "jarom", "omni", "words of mormon",
        "d&c", "doctrine and covenants", "pearl of great price",
        "joseph smith", "moses", "abraham", "articles of faith",
        "genesis", "exodus", "matthew", "john", "corinthians", "hebrews"
    ])

    if is_scripture:
        # Verify against scripture database
        best_match = None
        best_similarity = 0.0

        for topic, verses in SCRIPTURE_TOPICS.items():
            for verse in verses:
                sim = similarity_ratio(quote, verse["text"])
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = verse

        if best_similarity > 0.8:
            result["verification_status"] = "verified"
            result["confidence"] = best_similarity
            result["details"] = {
                "type": "scripture",
                "matched_reference": best_match["reference"],
                "matched_text": best_match["text"],
                "similarity": f"{best_similarity:.1%}"
            }
        elif best_similarity > 0.5:
            result["verification_status"] = "partial_match"
            result["confidence"] = best_similarity
            result["details"] = {
                "type": "scripture",
                "closest_match": best_match["reference"],
                "matched_text": best_match["text"],
                "similarity": f"{best_similarity:.1%}"
            }
            result["warnings"].append("Quote may be paraphrased. Verify exact wording.")
        else:
            result["verification_status"] = "not_found_in_database"
            result["recommendations"].append(
                "Search churchofjesuschrist.org/scriptures for exact wording"
            )

    else:
        # Verify against prophet quotes database
        best_match = None
        best_similarity = 0.0
        matched_prophet = None

        for prophet, quotes in PROPHET_QUOTES.items():
            prophet_name = prophet.replace("_", " ").lower()
            if prophet_name in attributed_lower or attributed_lower in prophet_name:
                for q in quotes:
                    sim = similarity_ratio(quote, q["quote"])
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match = q
                        matched_prophet = prophet.replace("_", " ").title()

        if best_similarity > 0.8:
            result["verification_status"] = "verified"
            result["confidence"] = best_similarity
            result["details"] = {
                "type": "prophet_quote",
                "prophet": matched_prophet,
                "verified_quote": best_match["quote"],
                "verified_source": best_match["source"],
                "similarity": f"{best_similarity:.1%}"
            }
        elif best_similarity > 0.5:
            result["verification_status"] = "partial_match"
            result["confidence"] = best_similarity
            result["details"] = {
                "type": "prophet_quote",
                "closest_prophet": matched_prophet,
                "closest_quote": best_match["quote"] if best_match else "N/A",
                "similarity": f"{best_similarity:.1%}"
            }
            result["warnings"].append("Quote may be paraphrased or from a different talk.")
        else:
            result["verification_status"] = "not_found_in_database"
            result["warnings"].append(
                f"Could not verify quote attributed to {attributed_to}"
            )
            result["recommendations"].extend([
                "Search General Conference talks at conference.churchofjesuschrist.org",
                "Check the Gospel Library app for exact quote",
                "Consider using a verified quote from the database instead"
            ])

    # Add general recommendations
    if result["verification_status"] != "verified":
        result["recommendations"].append(
            "IMPORTANT: Only use verified quotes in published content to maintain credibility"
        )

    # Add web search suggestion for unverified quotes
    if result["verification_status"] in ["not_found_in_database", "unverified"]:
        result["web_search_suggestion"] = f"""
To verify this quote, Claude should search:
1. "{quote[:50]}..." site:churchofjesuschrist.org
2. "{attributed_to}" "{quote[:30]}" General Conference
3. Check josephsmithpapers.org for historical quotes
"""

    return result


async def verify_batch_quotes(quotes: list[dict]) -> list[dict]:
    """
    Verify multiple quotes at once.

    Args:
        quotes: List of {"quote": str, "attributed_to": str, "source": str}

    Returns:
        list: Verification results for each quote
    """
    results = []
    for q in quotes:
        result = await verify_lds_quote(
            quote=q.get("quote", ""),
            attributed_to=q.get("attributed_to", ""),
            source=q.get("source", "")
        )
        results.append(result)
    return results
