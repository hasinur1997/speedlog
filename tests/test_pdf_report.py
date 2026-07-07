"""Tests for PDF report generation (NST-801)."""

from __future__ import annotations

import base64
import re
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - exercised only when dev deps are incomplete.
    PdfReader = None  # type: ignore[assignment]

import app.export.pdf_report as pdf_report_module
import app.formatting as formatting_module
from app.data.models import SpeedRecord
from app.export.pdf_report import generate_report

_PAGE_PATTERN = re.compile(rb"/Type\s*/Page\b")
_STREAM_PATTERN = re.compile(rb"stream\r?\n(.*?)endstream", re.DOTALL)
_LITERAL_PATTERN = re.compile(rb"\((?:\\.|[^\\()])*\)")


def _make_records(count: int) -> list[SpeedRecord]:
    base = datetime(2026, 7, 7, 10, 0, tzinfo=UTC)
    records: list[SpeedRecord] = []

    for index in range(count):
        start = base + timedelta(minutes=index * 10)
        start_ts = int(start.timestamp())
        records.append(
            SpeedRecord(
                session_id=1,
                start_ts=start_ts,
                end_ts=start_ts + 600,
                download_bps=5_020_000 + (index * 1_000),
                upload_bps=1_200_000 + (index * 500),
            )
        )

    return records


def _decode_pdf_literal(value: bytes) -> str:
    data = value[1:-1]
    decoded = bytearray()
    index = 0

    while index < len(data):
        current = data[index]
        if current != 0x5C:
            decoded.append(current)
            index += 1
            continue

        index += 1
        if index >= len(data):
            break

        escaped = data[index]
        if escaped in (0x28, 0x29, 0x5C):
            decoded.append(escaped)
            index += 1
            continue
        if escaped == 0x6E:
            decoded.append(0x0A)
            index += 1
            continue
        if escaped == 0x72:
            decoded.append(0x0D)
            index += 1
            continue
        if escaped == 0x74:
            decoded.append(0x09)
            index += 1
            continue
        if escaped == 0x62:
            decoded.append(0x08)
            index += 1
            continue
        if escaped == 0x66:
            decoded.append(0x0C)
            index += 1
            continue
        if escaped in (0x0A, 0x0D):
            if escaped == 0x0D and index + 1 < len(data) and data[index + 1] == 0x0A:
                index += 2
            else:
                index += 1
            continue
        if 0x30 <= escaped <= 0x37:
            octal_end = min(index + 3, len(data))
            octal_digits = bytes([escaped])
            look_ahead = index + 1
            while look_ahead < octal_end and 0x30 <= data[look_ahead] <= 0x37:
                octal_digits += bytes([data[look_ahead]])
                look_ahead += 1
            decoded.append(int(octal_digits, 8))
            index = look_ahead
            continue

        decoded.append(escaped)
        index += 1

    return decoded.decode("latin-1", errors="ignore")


def _fallback_pdf_text(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    page_count = len(_PAGE_PATTERN.findall(raw))
    text_fragments: list[str] = []

    for match in _STREAM_PATTERN.finditer(raw):
        for candidate in _stream_candidates(match.group(1)):
            text_fragments.extend(
                _decode_pdf_literal(token) for token in _LITERAL_PATTERN.findall(candidate)
            )

    return page_count, "\n".join(text_fragments)


def _maybe_decompress(stream: bytes) -> bytes | None:
    try:
        return zlib.decompress(stream)
    except zlib.error:
        return None


def _maybe_ascii85_decode(stream: bytes) -> bytes | None:
    try:
        return base64.a85decode(b"<~" + stream, adobe=True)
    except ValueError:
        return None


def _stream_candidates(stream: bytes) -> tuple[bytes, ...]:
    normalized = stream.rstrip(b"\r\n")
    candidates: list[bytes] = [normalized]
    flate = _maybe_decompress(normalized)
    ascii85 = _maybe_ascii85_decode(normalized)

    if ascii85 is not None:
        candidates.append(ascii85)
        ascii85_flate = _maybe_decompress(ascii85)
        if ascii85_flate is not None:
            candidates.append(ascii85_flate)
    elif flate is not None:
        candidates.append(flate)

    return tuple(candidates)


def _read_pdf(path: Path) -> tuple[int, str]:
    if PdfReader is not None:
        reader = PdfReader(path)
        return len(reader.pages), "\n".join(page.extract_text() or "" for page in reader.pages)
    return _fallback_pdf_text(path)


def test_generate_report_renders_empty_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: ZoneInfo("UTC"))
    monkeypatch.setattr(
        pdf_report_module,
        "_now_local",
        lambda: datetime(2026, 7, 7, 9, 15, tzinfo=UTC),
    )

    out_path = tmp_path / "empty-report.pdf"
    generate_report([], "July 7, 2026", "Taylor Example", out_path)

    page_count, text = _read_pdf(out_path)

    assert out_path.exists()
    assert page_count == 1
    assert "Internet Speed Report" in text
    assert "Taylor Example" in text
    assert "July 7, 2026" in text
    assert "No records for this range." in text
    assert "Generated 2026-07-07 9:15 AM UTC" in text
    assert "Page 1 of 1" in text


def test_generate_report_repeats_table_header_on_every_page(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: ZoneInfo("UTC"))
    monkeypatch.setattr(
        pdf_report_module,
        "_now_local",
        lambda: datetime(2026, 7, 7, 9, 15, tzinfo=UTC),
    )

    out_path = tmp_path / "paged-report.pdf"
    generate_report(_make_records(25), "July 7, 2026", "Taylor Example", out_path)

    page_count, text = _read_pdf(out_path)

    assert page_count >= 2
    assert text.count("Time Range") >= 2
    assert text.count("Download") >= 2
    assert "2026-07-07" in text
    assert "10:00 AM" in text
    assert "10:10 AM" in text
    assert "5.02 MB/s" in text


def test_generate_report_handles_hundreds_of_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: ZoneInfo("UTC"))
    monkeypatch.setattr(
        pdf_report_module,
        "_now_local",
        lambda: datetime(2026, 7, 7, 9, 15, tzinfo=UTC),
    )

    out_path = tmp_path / "large-report.pdf"
    generate_report(_make_records(500), "July 2026", "Taylor Example", out_path)

    page_count, text = _read_pdf(out_path)

    assert page_count > 10
    assert "Taylor Example" in text
    assert f"Page {page_count} of {page_count}" in text
    assert "July 2026" in text
