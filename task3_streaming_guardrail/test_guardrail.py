
import asyncio

from task3_streaming_guardrail.guardrail import guard_stream


async def fake_stream(chunks):
    """Simulate an LLM producing text chunks."""
    for chunk in chunks:
        yield chunk


async def check_case(name, chunks, expected):
    """Compare the guardrail output against expected text."""

    output = []

    async for chunk in guard_stream(fake_stream(chunks)):
        output.append(chunk)

    result = "".join(output)

    if result == expected:
        print(f"PASS: {name}")
        return True

    print(f"FAIL: {name}")
    print(f"  Expected: {expected!r}")
    print(f"  Actual:   {result!r}")
    return False


async def test_long_text():
    """Verify long uninterrupted text is handled safely."""

    long_text = "a" * 10000
    output = []

    async for chunk in guard_stream(fake_stream([long_text])):
        output.append(chunk)

    result = "".join(output)

    passed = (
        "[REDACTED]" in result
        and long_text not in result
    )

    if passed:
        print("PASS: Long candidate handled safely")
    else:
        print("FAIL: Long candidate handling")
        print("Output:", result[:200])

    return passed


async def test_streaming_latency():
    """Verify output arrives before the producer finishes."""

    async def long_stream():
        yield "a" * 10000

        await asyncio.sleep(0.5)

        yield " end"

    stream = guard_stream(long_stream())

    try:
        first_output = await asyncio.wait_for(
            anext(stream),
            timeout=0.2
        )

        print(
            "PASS: Guardrail produced output before "
            "the input stream finished"
        )
        print("First output length:", len(first_output))

        return True

    except asyncio.TimeoutError:
        print(
            "FAIL: Guardrail waited too long "
            "before producing output"
        )
        return False

    finally:
        await stream.aclose()


async def test_credit_card_boundary():
    """
    Ensure credit card digits are not leaked
    across streaming buffer boundaries.
    """

    chunks = [
        "Safe introduction. " + ("hello " * 50),
        "Card: 4111 1111 ",
        "1111 1111",
        " End of message."
    ]

    output = []

    async for chunk in guard_stream(fake_stream(chunks)):
        output.append(chunk)

    result = "".join(output)

    complete_card_redacted = (
        "[REDACTED]" in result
        and "4111 1111 1111 1111" not in result
    )

    no_card_digits_leaked = "4111" not in result

    passed = complete_card_redacted and no_card_digits_leaked

    if passed:
        print(
            "PASS: Credit card protected "
            "across buffer boundaries"
        )
    else:
        print("FAIL: Credit card boundary handling")
        print("Output tail:", result[-200:])

    return passed


async def test_all_card_boundaries():
    """Test credit card redaction at different buffer positions."""

    card = "4111 1111 1111 1111"
    failures = []

    for padding in range(220, 281):
        text = ("x" * padding) + " " + card + " end"

        output = []

        async for chunk in guard_stream(fake_stream([
            text[:padding + 8],
            text[padding + 8:padding + 15],
            text[padding + 15:]
        ])):
            output.append(chunk)

        result = "".join(output)

        if "4111" in result:
            failures.append(padding)

    if failures:
        print(
            "FAIL: Card digits leaked at padding lengths:",
            failures
        )
        return False

    print("PASS: Credit card protected at all tested boundaries")
    return True


async def main():
    results = []

    # TEST 1: Email split across chunks
    results.append(await check_case(
        "Email split across chunks",
        [
            "Contact john",
            "@example",
            ".com now"
        ],
        "Contact [REDACTED] now"
    ))

    # TEST 2: SSN split across chunks
    results.append(await check_case(
        "SSN split across chunks",
        [
            "SSN: 123-",
            "45-",
            "6789."
        ],
        "SSN: [REDACTED]."
    ))

    # TEST 3: Credit card split across chunks
    results.append(await check_case(
        "Credit card split across chunks",
        [
            "Card: 4111 1111",
            " 1111 ",
            "1111."
        ],
        "Card: [REDACTED]."
    ))

    # TEST 4: Multiple sensitive values
    results.append(await check_case(
        "Multiple PII types",
        [
            "Email: jane@example.com ",
            "SSN: 123-45-6789 "
        ],
        "Email: [REDACTED] SSN: [REDACTED] "
    ))

    # TEST 5: Long text without whitespace
    results.append(await test_long_text())

    # TEST 6: Streaming latency
    results.append(await test_streaming_latency())

    # TEST 7: Credit card across buffer boundaries
    results.append(await test_credit_card_boundary())

    # TEST 8: Credit card at 61 different buffer positions
    results.append(await test_all_card_boundaries())

    passed = sum(results)
    total = len(results)

    print(f"\n{passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
