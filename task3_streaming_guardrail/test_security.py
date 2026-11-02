
import asyncio
import tracemalloc

from task3_streaming_guardrail.guardrail import guard_stream


async def fake_stream(chunks):
    for chunk in chunks:
        yield chunk


async def collect_output(chunks):
    output = []

    async for chunk in guard_stream(fake_stream(chunks)):
        output.append(chunk)

    return "".join(output)


async def test_partial_card_leak():
    """
    Test whether a credit card number can be exposed
    when the buffer flushes near a whitespace boundary.
    """

    card = "4111 1111 1111 1111"
    failures = []

    for padding in range(0, 600):
        text = ("hello " * padding) + "Card: " + card + " end"

        card_start = text.index(card)

        chunks = [
            text[:card_start + 5],
            text[card_start + 5:card_start + 10],
            text[card_start + 10:card_start + 15],
            text[card_start + 15:]
        ]

        result = await collect_output(chunks)

        if "4111" in result:
            failures.append(padding)

    if failures:
        print("FAIL: Partial card digits leaked")
        print("Failing padding values:", failures[:20])
        return False

    print("PASS: No partial card digits leaked")
    return True


async def test_partial_email_leak():
    """
    Test email addresses across different
    streaming buffer positions.
    """

    email = "john.smith@example.com"
    failures = []

    for padding in range(0, 600):
        text = ("hello " * padding) + "Email: " + email + " end"

        email_start = text.index(email)

        chunks = [
            text[:email_start + 4],
            text[email_start + 4:email_start + 12],
            text[email_start + 12:]
        ]

        result = await collect_output(chunks)

        if email in result or "john.smith" in result:
            failures.append(padding)

    if failures:
        print("FAIL: Partial email information leaked")
        print("Failing padding values:", failures[:20])
        return False

    print("PASS: No partial email information leaked")
    return True


async def test_email_at_buffer_boundary():
    """
    Test whether an email address crossing the
    256-character buffer boundary leaks information.
    """

    chunks = [
        "a" * 255,
        "b@example.com",
        " end"
    ]

    result = await collect_output(chunks)

    if "b@example.com" in result or "example.com" in result:
        print("FAIL: Email information leaked at buffer boundary")
        print("Output ending:", repr(result[-120:]))
        return False

    print("PASS: Email boundary protection")
    return True


async def test_memory_usage():
    """
    Measure memory usage while processing
    a large stream without retaining output.
    """

    async def large_stream():
        for _ in range(10000):
            yield "a" * 1000

    tracemalloc.start()

    try:
        async for _ in guard_stream(large_stream()):
            pass

        current, peak = tracemalloc.get_traced_memory()

    finally:
        tracemalloc.stop()

    print(f"Peak traced memory: {peak / 1024 / 1024:.2f} MB")

    if peak < 10 * 1024 * 1024:
        print("PASS: Memory usage stayed below 10 MB")
        return True

    print("FAIL: Memory usage exceeded 10 MB")
    return False


async def main():
    print("Running Task 3 security tests...\n")

    results = []

    results.append(await test_partial_card_leak())
    results.append(await test_partial_email_leak())
    results.append(await test_email_at_buffer_boundary())
    results.append(await test_memory_usage())

    passed = sum(results)
    total = len(results)

    print(f"\n{passed}/{total} security tests passed")

    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
