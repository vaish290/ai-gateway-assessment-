
import re
from collections.abc import AsyncIterable, AsyncIterator

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z])"
)

SSN_PATTERN = re.compile(
    r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"
)

CARD_PATTERN = re.compile(
    r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
)

MAX_CANDIDATE_LENGTH = 256
LOOKBEHIND = 64

EMAIL_CHARS = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789._%+-@"
)


def redact_pii(text: str) -> str:
    """Replace detected PII with redaction markers."""

    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = CARD_PATTERN.sub("[REDACTED_CARD]", text)

    return text


async def guard_stream(
    chunks: AsyncIterable[str],
) -> AsyncIterator[str]:
    """Redact PII while streaming with bounded buffering."""

    buffer = ""

    async for chunk in chunks:
        # Process each character so a large incoming chunk
        # does not force the retained buffer to grow.
        for char in chunk:
            buffer += char

            if len(buffer) <= MAX_CANDIDATE_LENGTH:
                continue

            # Find a safe boundary before the trailing window.
            safe_limit = len(buffer) - LOOKBEHIND

            split_at = -1

            for index in range(safe_limit - 1, -1, -1):
                if buffer[index].isspace():
                    split_at = index + 1
                    break

            if split_at != -1:
                safe_text = buffer[:split_at]
                buffer = buffer[split_at:]

                if safe_text:
                    yield redact_pii(safe_text)

            elif len(buffer) > MAX_CANDIDATE_LENGTH:
                # Fail closed on an excessively long candidate.
                # Do not expose its original contents.
                yield "[REDACTED_LONG_CANDIDATE]"
                buffer = ""

    if buffer:
        yield redact_pii(buffer)
