"""
gdocs_tool.py — Google Docs append_to_doc implementation.
"""

import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_auth import get_credentials

logger = logging.getLogger(__name__)


def append_to_doc(
    document_id: str,
    text: str,
    add_newline: bool = True,
) -> dict:
    """
    Append text to the end of an existing Google Doc.

    Args:
        document_id: The ID of the Google Doc (from its URL).
        text:        The text to append.
        add_newline: If True, prepend a newline before the appended text.

    Returns:
        dict with keys: documentId, revisionsId
    """
    creds = get_credentials()
    service = build("docs", "v1", credentials=creds, cache_discovery=False)

    # Fetch the document to determine its length (end index)
    try:
        doc = service.documents().get(documentId=document_id).execute()
    except HttpError as exc:
        logger.error("Failed to fetch document: %s", exc)
        raise RuntimeError(
            f"Could not fetch Google Doc '{document_id}': "
            f"HTTP {exc.resp.status} — {exc.reason}"
        ) from exc

    body_content = doc.get("body", {}).get("content", [])
    end_index = 1  # default fallback
    if body_content:
        last_element = body_content[-1]
        end_index = last_element.get("endIndex", 1)

    # insertText at end_index - 1 (just before the final newline sentinel)
    insert_index = max(end_index - 1, 1)
    content_to_insert = ("\n" if add_newline else "") + text

    requests = [
        {
            "insertText": {
                "location": {"index": insert_index},
                "text": content_to_insert,
            }
        }
    ]

    try:
        result = (
            service.documents()
            .batchUpdate(documentId=document_id, body={"requests": requests})
            .execute()
        )
    except HttpError as exc:
        logger.error("Google Docs API error: %s", exc)
        raise RuntimeError(
            f"Google Docs API error {exc.resp.status}: {exc.reason}"
        ) from exc

    revision_id = result.get("writeControl", {}).get("requiredRevisionId", "")
    logger.info(
        "Text appended to doc '%s' (revisionId=%s)", document_id, revision_id
    )
    return {
        "documentId": result.get("documentId", document_id),
        "revisionsId": revision_id,
    }
