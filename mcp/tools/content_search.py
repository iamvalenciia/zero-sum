"""
LDS Content Search Tools
Search scriptures, prophet quotes, conference talks, and world news.
"""

import json
import os
from datetime import datetime
from typing import Optional


# LDS Scripture references database (expandable)
SCRIPTURE_TOPICS = {
    "faith": [
        {"reference": "Alma 32:21", "text": "Faith is not to have a perfect knowledge of things; therefore if ye have faith ye hope for things which are not seen, which are true."},
        {"reference": "Ether 12:6", "text": "I would show unto the world that faith is things which are hoped for and not seen; wherefore, dispute not because ye see not, for ye receive no witness until after the trial of your faith."},
        {"reference": "Hebrews 11:1", "text": "Now faith is the substance of things hoped for, the evidence of things not seen."},
        {"reference": "Moroni 7:33", "text": "And Christ hath said: If ye will have faith in me ye shall have power to do whatsoever thing is expedient in me."},
    ],
    "hope": [
        {"reference": "Ether 12:4", "text": "Wherefore, whoso believeth in God might with surety hope for a better world, yea, even a place at the right hand of God."},
        {"reference": "Moroni 7:41", "text": "And what is it that ye shall hope for? Behold I say unto you that ye shall have hope through the atonement of Christ."},
    ],
    "charity": [
        {"reference": "Moroni 7:47", "text": "But charity is the pure love of Christ, and it endureth forever; and whoso is found possessed of it at the last day, it shall be well with him."},
        {"reference": "1 Corinthians 13:13", "text": "And now abideth faith, hope, charity, these three; but the greatest of these is charity."},
    ],
    "repentance": [
        {"reference": "Mosiah 26:30", "text": "Yea, and as often as my people repent will I forgive them their trespasses against me."},
        {"reference": "Alma 34:31", "text": "Yea, I would that ye would come forth and harden not your hearts any longer; for behold, now is the time and the day of your salvation."},
        {"reference": "D&C 58:42", "text": "Behold, he who has repented of his sins, the same is forgiven, and I, the Lord, remember them no more."},
    ],
    "first_vision": [
        {"reference": "Joseph Smith—History 1:17", "text": "I saw two Personages, whose brightness and glory defy all description, standing above me in the air. One of them spake unto me, calling me by name and said, pointing to the other—This is My Beloved Son. Hear Him!"},
        {"reference": "Joseph Smith—History 1:19", "text": "I was answered that I must join none of them, for they were all wrong."},
    ],
    "book_of_mormon": [
        {"reference": "Introduction to the Book of Mormon", "text": "We invite all men everywhere to read the Book of Mormon, to ponder in their hearts the message it contains, and then to ask God, the Eternal Father, in the name of Christ if the book is true."},
        {"reference": "Moroni 10:4", "text": "And when ye shall receive these things, I would exhort you that ye would ask God, the Eternal Father, in the name of Christ, if these things are not true."},
    ],
    "prayer": [
        {"reference": "3 Nephi 18:19", "text": "Therefore ye must always pray unto the Father in my name."},
        {"reference": "Alma 37:37", "text": "Counsel with the Lord in all thy doings, and he will direct thee for good."},
        {"reference": "D&C 19:38", "text": "Pray always, and I will pour out my Spirit upon you."},
    ],
    "temples": [
        {"reference": "D&C 109:8", "text": "Organize yourselves; prepare every needful thing, and establish a house, even a house of prayer, a house of fasting, a house of faith, a house of learning."},
        {"reference": "D&C 124:40", "text": "And verily I say unto you, let this house be built unto my name, that I may reveal mine ordinances therein unto my people."},
    ],
    "family": [
        {"reference": "The Family: A Proclamation to the World", "text": "The family is ordained of God. Marriage between man and woman is essential to His eternal plan."},
        {"reference": "Mosiah 4:15", "text": "But ye will teach them to walk in the ways of truth and soberness; ye will teach them to love one another, and to serve one another."},
    ],
    "jesus_christ": [
        {"reference": "3 Nephi 11:10-11", "text": "Behold, I am Jesus Christ, whom the prophets testified shall come into the world. And behold, I am the light and the life of the world."},
        {"reference": "Mosiah 3:17", "text": "And moreover, I say unto you, that there shall be no other name given nor any other way nor means whereby salvation can come unto the children of men, only in and through the name of Christ, the Lord Omnipotent."},
        {"reference": "John 14:6", "text": "Jesus saith unto him, I am the way, the truth, and the life: no man cometh unto the Father, but by me."},
    ],
}

# Prophet quotes database (expandable)
PROPHET_QUOTES = {
    "russell_m_nelson": [
        {
            "quote": "The Lord loves effort, because effort brings rewards that cannot come without it.",
            "source": "October 2023 General Conference",
            "topic": "effort"
        },
        {
            "quote": "God loves you and wants you to feel His love.",
            "source": "April 2021 General Conference",
            "topic": "love"
        },
        {
            "quote": "We can choose to let God prevail in our lives, or not. We can choose to let God be the most important influence in our lives, or not.",
            "source": "October 2020 General Conference",
            "topic": "faith"
        },
        {
            "quote": "The Savior knows how to succor His people. He will heal the brokenhearted.",
            "source": "October 2022 General Conference",
            "topic": "healing"
        },
    ],
    "dallin_h_oaks": [
        {
            "quote": "The Final Judgment is not just an evaluation of a sum total of good and evil acts—what we have done. It is an acknowledgment of the final effect of our acts and thoughts—what we have become.",
            "source": "October 2000 General Conference",
            "topic": "judgment"
        },
    ],
    "jeffrey_r_holland": [
        {
            "quote": "Don't give up. Don't you quit. You keep walking. You keep trying. There is help and happiness ahead.",
            "source": "October 1999 General Conference",
            "topic": "hope"
        },
        {
            "quote": "The size of your faith or the depth of your conviction is not the issue—it is the direction you are facing.",
            "source": "April 2013 General Conference",
            "topic": "faith"
        },
    ],
    "dieter_f_uchtdorf": [
        {
            "quote": "The desire to create is one of the deepest yearnings of the human soul.",
            "source": "October 2008 General Conference",
            "topic": "creativity"
        },
        {
            "quote": "Doubt your doubts before you doubt your faith.",
            "source": "October 2013 General Conference",
            "topic": "doubt"
        },
    ],
    "gordon_b_hinckley": [
        {
            "quote": "Be believing. Be happy. Don't get discouraged. Things will work out.",
            "source": "Various talks",
            "topic": "optimism"
        },
    ],
    "thomas_s_monson": [
        {
            "quote": "Never let a problem to be solved become more important than a person to be loved.",
            "source": "Various talks",
            "topic": "love"
        },
    ],
    "joseph_smith": [
        {
            "quote": "Happiness is the object and design of our existence.",
            "source": "Teachings of the Prophet Joseph Smith",
            "topic": "happiness"
        },
        {
            "quote": "A man filled with the love of God, is not content with blessing his family alone, but ranges through the whole world, anxious to bless the whole human race.",
            "source": "History of the Church",
            "topic": "love"
        },
    ],
}


async def search_lds_content(
    query: str,
    source_type: str = "all",
    max_results: int = 5
) -> dict:
    """
    Search for LDS scriptures, prophet quotes, and church content.

    Args:
        query: Search query (topic or keywords)
        source_type: "scriptures", "conference", "liahona", or "all"
        max_results: Maximum number of results to return

    Returns:
        dict: Search results with sources
    """
    results = {
        "query": query,
        "source_type": source_type,
        "results": [],
        "suggestions": []
    }

    query_lower = query.lower().replace(" ", "_").replace("-", "_")

    # Search scriptures
    if source_type in ["scriptures", "all"]:
        for topic, verses in SCRIPTURE_TOPICS.items():
            if query_lower in topic or topic in query_lower or any(query_lower in v["text"].lower() for v in verses):
                for verse in verses[:max_results]:
                    results["results"].append({
                        "type": "scripture",
                        "reference": verse["reference"],
                        "text": verse["text"],
                        "topic": topic,
                        "verified": True
                    })

    # Search prophet quotes
    if source_type in ["conference", "all"]:
        for prophet, quotes in PROPHET_QUOTES.items():
            for quote in quotes:
                if (query_lower in quote["topic"] or
                    query_lower in quote["quote"].lower() or
                    query_lower in prophet.replace("_", " ")):
                    results["results"].append({
                        "type": "prophet_quote",
                        "prophet": prophet.replace("_", " ").title(),
                        "quote": quote["quote"],
                        "source": quote["source"],
                        "topic": quote["topic"],
                        "verified": True
                    })

    # Limit results
    results["results"] = results["results"][:max_results]

    # Add suggestions for expanding search
    if len(results["results"]) < max_results:
        results["suggestions"] = [
            "Try searching for related topics: faith, hope, charity, repentance, prayer",
            "Search by prophet name: President Nelson, Elder Holland, Joseph Smith",
            "Search specific scriptures: Book of Mormon, Doctrine and Covenants"
        ]

    # Add note about web search capability
    results["note"] = """
For more comprehensive results, Claude can also:
1. Search churchofjesuschrist.org for current content
2. Search General Conference talks at conference.churchofjesuschrist.org
3. Search the Gospel Library for scriptures and manuals

These sources can be accessed through web search for the most up-to-date content.
"""

    return results


async def search_world_news(
    topic: str,
    find_gospel_connection: bool = True
) -> dict:
    """
    Search for recent world news and find relevant LDS teachings.

    This is a placeholder that instructs Claude to use web search.

    Args:
        topic: News topic to search
        find_gospel_connection: Whether to suggest related gospel teachings

    Returns:
        dict: Instructions for Claude to search and connect
    """
    result = {
        "topic": topic,
        "search_instructions": f"""
To find current world news about '{topic}', please:

1. Use web search to find recent news articles about: {topic}
2. Summarize the key points that could connect to gospel principles
3. Focus on themes that members can relate to:
   - Finding peace in troubled times
   - Hope during challenges
   - Faith during uncertainty
   - Family and community
   - Service and charity

4. Then use search_lds_content to find related scriptures and prophet quotes
""",
        "suggested_gospel_connections": []
    }

    # Suggest gospel connections based on topic keywords
    topic_lower = topic.lower()

    if any(word in topic_lower for word in ["peace", "war", "conflict", "violence"]):
        result["suggested_gospel_connections"].extend([
            {"topic": "peace", "search": "search_lds_content for 'peace'"},
            {"topic": "hope", "search": "search_lds_content for 'hope'"},
        ])

    if any(word in topic_lower for word in ["economy", "money", "financial", "job"]):
        result["suggested_gospel_connections"].extend([
            {"topic": "faith", "search": "search_lds_content for 'faith'"},
            {"topic": "trust in God", "search": "search_lds_content for 'prayer'"},
        ])

    if any(word in topic_lower for word in ["family", "children", "marriage"]):
        result["suggested_gospel_connections"].extend([
            {"topic": "family", "search": "search_lds_content for 'family'"},
        ])

    if any(word in topic_lower for word in ["hope", "optimism", "good news"]):
        result["suggested_gospel_connections"].extend([
            {"topic": "hope", "search": "search_lds_content for 'hope'"},
            {"topic": "faith", "search": "search_lds_content for 'faith'"},
        ])

    return result
