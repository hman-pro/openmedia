"""Card taps: duplicates, forwarded cards, expiry and the publish/tap race."""

from __future__ import annotations

import asyncio

import pytest

from tests.e2e import E2E

pytestmark = E2E

PROCESSING = "That request is already processing. Please wait; no duplicate download was started."
STALE = "This choice is stale. Submit the link again for current choices."
EXPIRED = "Those choices expired. Submit the link again."


async def test_double_tap_starts_one_delivery(chat, case):
    result = await chat.exchange(case("youtube-video"), prefer=("Audio only",), double_tap=True)
    assert len(result.files) == 1, result.final_status
    assert sorted(a or "" for a in result.tap_answers) == sorted(["Audio only", PROCESSING])


async def test_forwarded_card_has_no_buttons_and_the_original_still_works(chat, case):
    result = await chat.exchange(case("youtube-video"), tap=False, download=False, quiet=3)
    assert result.buttons, result.events
    copy = await chat.client.forward_messages("me", result.card)
    try:
        assert not copy.reply_markup, "a forwarded card must not carry tappable buttons"
    finally:
        await copy.delete()
    answer = await result.card.click(text="Audio only")
    assert getattr(answer, "message", None) == "Audio only"
    await asyncio.sleep(15)
    later = await chat.client.get_messages(chat.bot, limit=3)
    assert sum(1 for m in later if m.document and m.id > result.card.id) == 1


async def test_instant_tap_is_accepted(chat, case):
    """Known defect (T066): a tap before the card is recorded is answered "stale".

    The card is published before the request moves to awaiting-selection, so a tap in that
    gap finds the request still checking. Three instant taps; any stale answer marks the
    known defect as expected-fail, and the test passes once the race is fixed.
    """
    for _ in range(3):
        result = await chat.exchange(case("youtube-video"), prefer=("Audio only",), tap_delay=0, download=False)
        if STALE in result.tap_answers:
            pytest.xfail("publish/tap race: an instant tap was answered stale (follow-up 7)")
        assert result.files, result.final_status


async def test_tap_after_expiry_is_refused(chat, case, slow):
    result = await chat.exchange(case("youtube-video"), tap=False, download=False, quiet=3)
    await asyncio.sleep(905)  # selection expiry is fixed at 900 s
    answer = await result.card.click(text="Audio only")
    assert getattr(answer, "message", None) == EXPIRED
    await asyncio.sleep(10)
    later = await chat.client.get_messages(chat.bot, limit=3)
    assert not any(m.document and m.id > result.card.id for m in later)
