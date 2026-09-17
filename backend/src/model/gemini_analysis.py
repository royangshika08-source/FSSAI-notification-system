import os
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from google import genai
from google.genai import types


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


# ============================================================
# CONFIGURATION
# ============================================================

EMBEDDING_MODEL = "hkunlp/instructor-large"

COLLECTION_NAME = "fssai_notifications_instructor"

TOP_K = 5

QUERY_INSTRUCTION = (
    "Represent the question for retrieving "
    "relevant FSSAI regulatory documents:"
)

GEMINI_MODEL = "gemini-3.6-flash"


# ============================================================
# VALIDATE CREDENTIALS
# ============================================================

print("=" * 70)
print("FSSAI GEMINI REGULATORY ANALYSIS")
print("=" * 70)

print("\nLoading credentials...")

print(
    "GEMINI API key loaded:",
    bool(GEMINI_API_KEY)
)

print(
    "QDRANT URL loaded:",
    bool(QDRANT_URL)
)

print(
    "QDRANT API key loaded:",
    bool(QDRANT_API_KEY)
)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found in .env"
    )

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError(
        "QDRANT_URL or QDRANT_API_KEY not found in .env"
    )


# ============================================================
# INITIALIZE CLIENTS
# ============================================================

print("\nLoading embedding model...")

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

print("INSTRUCTOR-large loaded.")


print("\nConnecting to Qdrant Cloud...")

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

print("Qdrant Cloud connection established.")


print("\nConnecting to Gemini...")

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)

print("Gemini client initialized.")


# ============================================================
# QDRANT RETRIEVAL
# ============================================================

def retrieve_chunks(query):

    query_pair = [
        QUERY_INSTRUCTION,
        query
    ]

    print("\nGenerating query embedding...")

    query_vector = embedding_model.encode(
        [query_pair],
        normalize_embeddings=True
    )[0].tolist()

    print(
        "Query vector dimension:",
        len(query_vector)
    )

    print(
        f"Searching Qdrant for top {TOP_K} results..."
    )

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using="dense_vec",
        limit=TOP_K,
        with_payload=True
    ).points

    print(
        f"Retrieved {len(results)} chunks."
    )

    return results


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(
    user_query,
    retrieved_results
):
    context_parts = []

    for i, result in enumerate(retrieved_results, start=1):

        payload = result.payload or {}

        context_parts.append(
            f"""
==============================
DOCUMENT CHUNK {i}
==============================

Title:
{payload.get("title", "")}

Uploaded Date:
{payload.get("uploaded_date", "")}

PDF URL:
{payload.get("pdf_url", "")}

Chunk Text:
{payload.get("text", "")}
"""
        )

    retrieved_context = "\n".join(
        context_parts
    )

    prompt = f"""
You are an AI Regulatory Intelligence Agent analyzing
official FSSAI notification documents.

USER QUESTION:
{user_query}

RETRIEVED DOCUMENT CHUNKS:
{retrieved_context}

========================================================
STRICT GROUNDING RULES
========================================================

Analyze ONLY the information contained in the retrieved
document chunks.

Do NOT use outside knowledge.

Do NOT guess.

Do NOT invent:

- regulation names
- section numbers
- section codes
- subsection names
- document names
- PDF names
- PDF links
- affected areas
- changes

If a piece of information is not present in the retrieved
document text, return null.

If the retrieved chunks contain only metadata and do not
contain enough information to determine an exact section
or affected provision, return null for that field.

========================================================
1. RELEVANT NOTIFICATIONS
========================================================

Identify the notification(s) relevant to the user's question.

For each notification provide:

- title
- uploaded_date
- pdf_url

========================================================
2. REASON
========================================================

Explain the reason/purpose of the relevant notification
based only on the retrieved text.

========================================================
3. REGULATIONS
========================================================

Identify the regulation, regulatory document, appendix,
schedule, provision, or other legal document that is
actually affected or referred to by the notification.

For EACH identified regulation/document provide:

- title
- section
- subsection
- change
- pdf_name
- pdf_link

The title should be the actual title/name appearing in
the retrieved document.

The section should identify the relevant section of the
regulation/document when explicitly available.

The subsection should identify the relevant subsection,
clause, paragraph, appendix part, etc., when explicitly
available.

The change should describe what the notification actually
changes, adds, removes, replaces, approves, modifies,
notifies, or otherwise affects.

pdf_name must contain the actual regulation/document PDF
name only when it is explicitly available.

pdf_link must contain the actual regulation/document PDF
link only when it is explicitly available.

IMPORTANT:

The notification PDF and the affected regulation PDF are
NOT automatically the same document.

Do not use the notification PDF as pdf_link for a regulation
unless the retrieved text explicitly establishes that it is
the regulation/document PDF.

========================================================
4. AFFECTED AREAS
========================================================

Identify the EXACT areas inside the affected regulation
or document.

For EACH affected area provide:

- section_code
- section_title
- subsection
- description

section_code should contain the exact code/number appearing
in the document, for example "1.2.0", ONLY if that exact
value appears in the retrieved text.

section_title should contain the exact title associated with
that section code.

subsection should contain the exact subsection/clause when
available.

description should explain what part of that section is
affected and how it is affected.

IMPORTANT:

Do not generate generic stakeholder categories such as:

- Food businesses
- Laboratories
- Food industry
- Regional offices
- Consumers

unless the retrieved document explicitly identifies them as
an affected area.

We need document-level and section-level affected areas,
not broad industry categories.

========================================================
5. DETECTED CHANGES
========================================================

List the actual changes explicitly supported by the
retrieved notification text.

========================================================
OUTPUT
========================================================

Return ONLY valid JSON matching the required schema.

Use null whenever information cannot be determined from
the retrieved document chunks.
"""

    response_schema = {
        "type": "object",
        "properties": {

            "relevant_notifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "title": {
                            "type": "string"
                        },

                        "uploaded_date": {
                            "type": "string"
                        },

                        "pdf_url": {
                            "type": "string"
                        }
                    },

                    "required": [
                        "title",
                        "uploaded_date",
                        "pdf_url"
                    ]
                }
            },

            "reason": {
                "type": "string"
            },

            "regulations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "title": {
                            "type": ["string", "null"]
                        },

                        "section": {
                            "type": ["string", "null"]
                        },

                        "subsection": {
                            "type": ["string", "null"]
                        },

                        "change": {
                            "type": ["string", "null"]
                        },

                        "pdf_name": {
                            "type": ["string", "null"]
                        },

                        "pdf_link": {
                            "type": ["string", "null"]
                        }
                    },

                    "required": [
                        "title",
                        "section",
                        "subsection",
                        "change",
                        "pdf_name",
                        "pdf_link"
                    ]
                }
            },

            "affected_areas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "section_code": {
                            "type": ["string", "null"]
                        },

                        "section_title": {
                            "type": ["string", "null"]
                        },

                        "subsection": {
                            "type": ["string", "null"]
                        },

                        "description": {
                            "type": ["string", "null"]
                        }
                    },

                    "required": [
                        "section_code",
                        "section_title",
                        "subsection",
                        "description"
                    ]
                }
            },

            "detected_changes": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },

        "required": [
            "relevant_notifications",
            "reason",
            "regulations",
            "affected_areas",
            "detected_changes"
        ]
    }

    print("\nCalling Gemini...")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        )
    )

    return response.text
# ============================================================
# DIRECT NOTIFICATION ANALYSIS
# ============================================================

def analyze_notification_text(
    notification_text,
    pdf_url=None,
    notification_title=None,
    uploaded_date=None,
    file_name=None
):
    prompt = f"""
You are analyzing an official FSSAI Gazette Notification.

Analyze ONLY the notification text and supplied notification metadata.

NOTIFICATION TEXT:
{notification_text}

CURRENT NOTIFICATION TITLE:
{notification_title}

CURRENT NOTIFICATION UPLOADED DATE:
{uploaded_date}

CURRENT NOTIFICATION PDF URL:
{pdf_url}

CURRENT NOTIFICATION PDF FILE NAME:
{file_name}

Your task is to produce structured regulatory intelligence.

IMPORTANT METADATA RULES:

The following information is supplied directly by the project
and must be used as authoritative metadata for the current
notification:

CURRENT NOTIFICATION TITLE:
{notification_title}

CURRENT NOTIFICATION UPLOADED DATE:
{uploaded_date}

CURRENT NOTIFICATION PDF URL:
{pdf_url}

CURRENT NOTIFICATION PDF FILE NAME:
{file_name}

Use the supplied CURRENT NOTIFICATION PDF FILE NAME as pdf_name.

Use the supplied CURRENT NOTIFICATION PDF URL as pdf_link.

Do NOT return an empty pdf_name when CURRENT NOTIFICATION PDF
FILE NAME is supplied.

Do NOT return an empty pdf_link when CURRENT NOTIFICATION PDF
URL is supplied.

The PDF name and PDF link refer to the source notification PDF
being analyzed.

====================================================
SECTION AND SUBSECTION RULES
====================================================

Extract the section and subsection from the notification text
or notification title whenever they are stated.

The notification title may contain references such as:

- section 43(1)
- Section 43
- sub-section 5 of section 10
- Sub-section 5 of Section 10 read with Section 37
- section 10 read with section 45

Use the exact section and subsection information stated in the
notification.

If the notification title contains the section/subsection
reference and the body does not repeat it, use the information
from the notification title.

Do NOT leave section or subsection empty when the information is
explicitly available in the notification title or text.

Do NOT infer a subsection that is not stated.

Preserve the terminology used by the notification.

IMPORTANT GROUNDING RULES:
- Use ONLY information supported by the notification text.
- Do NOT guess or invent section numbers, section codes, titles,
  subsection names, PDF names, or PDF links.
- If information is not explicitly available, return an empty string.
- Do NOT use outside knowledge.
- Do NOT create information merely because it seems likely.
- Preserve the actual terminology used in the notification.

====================================================
1. REASON
====================================================

Explain clearly why this notification was issued and what
its main purpose is.

====================================================
2. REGULATIONS
====================================================

Identify the regulation, Act, notification, document, provision,
or other regulatory reference affected or referred to by this
notification.

For EACH regulation/document, identify:

- title
- section
- subsection
- change
- pdf_name
- pdf_link

====================================================
REGULATION IDENTIFICATION AND TITLE RULES
====================================================

For EACH regulation/document identified in the notification,
determine the ACTUAL regulatory instrument, document,
notification, regulation, order, table, schedule, list,
or other regulatory subject that is affected by the
current notification.

The "title" field MUST identify the actual affected
item.

IMPORTANT DISTINCTION:

The law or Act under which a notification is issued is
NOT automatically the affected regulation/document.

For example:

- "Food Safety and Standards Act, 2006" may be the parent
  Act or legal basis.
- A notification may instead amend a principal notification,
  regulation, table, schedule, list, order, or other document
  made under that Act.

If the notification explicitly identifies the affected item,
use its actual title or subject as the "title".

GENERAL TITLE RULES:

1. DO NOT automatically use the parent Act as the title.

2. If the notification explicitly states that it amends,
   substitutes, inserts into, omits from, modifies,
   replaces, rescinds, or otherwise changes another
   notification, regulation, order, table, schedule,
   list, or document, identify that affected item and
   use its actual title.

3. If the affected notification/document has an explicitly
   stated notification number, date, or other identifier,
   include that information in the title when it helps
   identify the affected document.

4. If the notification directly concerns a specific
   regulatory subject, table, list, schedule, or other
   document and no separate formal title is provided,
   use the exact subject or heading stated in the notification.

5. Preserve the terminology used in the notification.

6. DO NOT invent a title.

7. DO NOT use information from outside the supplied
   notification text.

8. DO NOT use the CURRENT NOTIFICATION TITLE as the
   affected regulation title unless the notification
   explicitly indicates that the current notification
   itself is the affected document.

9. DO NOT use a generic parent law such as
   "Food Safety and Standards Act, 2006" when the
   notification clearly identifies a more specific
   affected notification, regulation, table, schedule,
   list, order, or document.

10. If the notification genuinely affects the Act itself
    and explicitly identifies the Act as the affected
    instrument, then the Act may be used as the title.

11. The "title" must describe WHAT IS BEING AFFECTED.

12. The "change" field must separately describe WHAT WAS
    DONE TO IT.

Therefore:

TITLE = What regulation/document/subject is affected?

CHANGE = What amendment, insertion, deletion, substitution,
         appointment, recognition, modification, or other
         action was made?

Do not confuse the legal basis with the affected document.
  SECTION:

Extract the exact section reference stated in the notification
or its title.

Preserve the wording and numbering used in the notification.

Do NOT infer a section from general knowledge.

If multiple sections are explicitly relevant, include all of
them.

SUBSECTION:

Extract the exact subsection reference stated in the
notification or its title.

Preserve the wording and numbering used in the notification.

Do NOT infer a subsection from a section number.

If no subsection is explicitly stated, use an empty string.
====================================================
3. AFFECTED AREAS
====================================================

Identify the exact areas within the affected regulation/document.

For EACH affected area, identify:

- section_code
- section_title
- subsection
- description

For example, if the notification explicitly states that a
particular section such as "1.2.0" concerning a particular
food/product has been changed, extract that exact section code
and title.

The example above is only an illustration.
DO NOT invent "1.2.0" or any other value unless it actually
appears in the notification.

====================================================
4. CHANGES
====================================================

Identify the actual changes made by the notification.

Include amendments, additions, deletions, replacements,
appointments, approvals, recognitions, or other actions
explicitly described in the notification.

====================================================
FINAL RULE
====================================================

Return ONLY information that can be supported by the supplied
notification text.

If something cannot be determined, use an empty string instead of guessing.

Return the result as structured JSON.
"""

    response_schema = {
        "type": "object",
        "properties": {

            "relevant_notifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "title": {
                            "type": "string"
                        },

                        "uploaded_date": {
                            "type": "string"
                        },

                        "pdf_url": {
                            "type": "string"
                        }
                    },

                    "required": [
                        "title",
                        "uploaded_date",
                        "pdf_url"
                    ]
                }
            },

            "reason": {
                "type": "string"
            },

            "regulations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "title": {
                            "type": "string"
                        },

                        "section": {
                            "type": "string"
                        },

                        "subsection": {
                            "type": "string"
                        },

                        "change": {
                            "type": "string"
                        },

                        "pdf_name": {
                            "type": "string"
                        },

                        "pdf_link": {
                            "type": "string"
                        }
                    },

                    "required": [
                        "title",
                        "section",
                        "subsection",
                        "change",
                        "pdf_name",
                        "pdf_link"
                    ]
                }
            },

            "affected_areas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {

                        "section_code": {
                            "type": "string"
                        },

                        "section_title": {
                            "type": "string"
                        },

                        "subsection": {
                            "type": "string"
                        },

                        "description": {
                            "type": "string"
                        }
                    },

                    "required": [
                        "section_code",
                        "section_title",
                        "subsection",
                        "description"
                    ]
                }
            },

            "detected_changes": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },

        "required": [
            "relevant_notifications",
            "reason",
            "regulations",
            "affected_areas",
            "detected_changes"
        ]
    }

    print("\nAnalyzing selected notification with Gemini...")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        )
    )

    return response.text


# ============================================================
# MAIN
# ============================================================

def main():

    query = input(
        "\nEnter your question:\n> "
    ).strip()

    if not query:

        print("No query entered.")
        return

    # --------------------------------------------------------
    # Retrieve relevant chunks
    # --------------------------------------------------------

    results = retrieve_chunks(
        query
    )

    if not results:

        print(
            "\nNo relevant chunks found."
        )

        return

    # --------------------------------------------------------
    # Gemini analysis
    # --------------------------------------------------------

    analysis = analyze_with_gemini(
        query,
        results
    )

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("GEMINI ANALYSIS")
    print("=" * 70)

    print(analysis)

    print("\n")
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
