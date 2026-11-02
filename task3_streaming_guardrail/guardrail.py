
import re
from collections.abc import AsyncIterable, AsyncIterator


# Patterns for sensitive information
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z])"
)

SSN_PATTERN = re.compile(
    r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"
)

CARD_PATTERN = re.compile(
    r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
)


# Maximum amount of candidate text retained
MAX_CANDIDATE_LENGTH = 256

# Keep trailing context to protect PII split across chunks
LOOKBEHIND = 64

# Required replacement marker
REDACTION_MARKER = "[REDACTED]"


def redact_pii(text: str) -> str:
    """
    Replace email addresses, SSNs, and credit card
    numbers with the required redaction marker.
    """

    text = EMAIL_PATTERN.sub(REDACTION_MARKER, text)
    text = SSN_PATTERN.sub(REDACTION_MARKER, text)
    text = CARD_PATTERN.sub(REDACTION_MARKER, text)

    return text


async def guard_stream(
    chunks: AsyncIterable[str]
) -> AsyncIterator[str]:
    """
    Redact sensitive information from a streaming
    LLM response.

    Features:
    - Handles PII split across arbitrary chunks.
    - Uses bounded buffering.
    - Emits safe output incrementally.
    - Uses [REDACTED] for all redactions.
    - Fails closed on excessively long candidates.
    """

    buffer = ""
    discarding_line = False

    async for chunk in chunks:

        for char in chunk:

            # If a candidate exceeded the buffer limit,
            # discard the rest of the line to avoid
            # leaking sensitive information.
            if discarding_line:

                if char == "\n":
                    discarding_line = False
                    yield "\n"

                continue

            buffer += char

            # Continue collecting text until enough
            # context is available for safe processing.
            if len(buffer) <= MAX_CANDIDATE_LENGTH:
                continue

            safe_limit = len(buffer) - LOOKBEHIND
            split_at = -1

            # Find a whitespace boundary before
            # the retained lookbehind region.
            for index in range(safe_limit - 1, -1, -1):

                if buffer[index].isspace():
                    split_at = index + 1
                    break

            if split_at != -1:

                safe_text = buffer[:split_at]
                buffer = buffer[split_at:]

                if safe_text:
                    yield redact_pii(safe_text)

            else:
                # Fail closed on a long uninterrupted
                # candidate rather than leaking data.
                yield REDACTION_MARKER
                buffer = ""
                discarding_line = True

    # Process any remaining buffered text.
    if buffer and not discarding_line:
        yield redact_pii(buffer)
