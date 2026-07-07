"""reportlab PDF report generator for filtered speed-record exports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen import canvas

from app import config
from app.data.models import SpeedRecord
from app.formatting import format_date, format_speed, format_time_range

_TITLE = "Internet Speed Report"
_EMPTY_MESSAGE = "No records for this range."
_DEFAULT_FILTER_LABEL = "All records"
_COLUMN_FRACTIONS = (0.18, 0.32, 0.25, 0.25)


@dataclass(frozen=True, slots=True)
class _ColumnSpec:
    heading: str
    width: float
    right_align: bool = False


class _NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, generated_label: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._generated_label = generated_label
        self._saved_page_states: list[dict[str, object]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        total_pages = len(self._saved_page_states)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total_pages)
            super().showPage()

        super().save()

    def _draw_footer(self, total_pages: int) -> None:
        page_width, _ = self._pagesize
        footer_top = config.PDF_MARGIN_BOTTOM + config.PDF_FOOTER_HEIGHT
        footer_text_y = _text_baseline(
            config.PDF_MARGIN_BOTTOM,
            config.PDF_FOOTER_HEIGHT,
            config.PDF_FOOTER_FONT_SIZE,
        )

        self.saveState()
        self.setStrokeColor(_hex_color(config.PDF_TABLE_BORDER_COLOR))
        self.line(
            config.PDF_MARGIN_LEFT, footer_top, page_width - config.PDF_MARGIN_RIGHT, footer_top
        )
        self.setFillColor(_hex_color(config.PDF_FOOTER_TEXT_COLOR))
        self.setFont("Helvetica", config.PDF_FOOTER_FONT_SIZE)
        self.drawString(config.PDF_MARGIN_LEFT, footer_text_y, self._generated_label)
        self.drawRightString(
            page_width - config.PDF_MARGIN_RIGHT,
            footer_text_y,
            f"Page {self._pageNumber} of {total_pages}",
        )
        self.restoreState()


def _hex_color(value: str) -> Color:
    return HexColor(value)


def _text_baseline(box_bottom: float, box_height: float, font_size: int) -> float:
    return box_bottom + ((box_height - font_size) / 2.0) + 2.0


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _format_generated_label(now: datetime) -> str:
    zone_name = now.tzname() or ""
    date_part = now.strftime("%Y-%m-%d")
    time_part = now.strftime("%I:%M %p").lstrip("0")
    zone_part = f" {zone_name}" if zone_name else ""
    return f"Generated {date_part} {time_part}{zone_part}"


def _build_columns(page_width: float) -> tuple[_ColumnSpec, ...]:
    inner_width = page_width - config.PDF_MARGIN_LEFT - config.PDF_MARGIN_RIGHT
    date_width = inner_width * _COLUMN_FRACTIONS[0]
    time_width = inner_width * _COLUMN_FRACTIONS[1]
    download_width = inner_width * _COLUMN_FRACTIONS[2]
    upload_width = inner_width - date_width - time_width - download_width
    return (
        _ColumnSpec("Date", date_width),
        _ColumnSpec("Time Range", time_width),
        _ColumnSpec("Download", download_width, right_align=True),
        _ColumnSpec("Upload", upload_width, right_align=True),
    )


def _header_name(full_name: str) -> str:
    normalized = full_name.strip()
    return normalized or config.APP_NAME


def _header_filter_label(filter_label: str) -> str:
    normalized = filter_label.strip()
    return normalized or _DEFAULT_FILTER_LABEL


def _draw_document_header(pdf: canvas.Canvas, filter_label: str, full_name: str) -> float:
    page_width, page_height = pdf._pagesize
    band_top = page_height - config.PDF_MARGIN_TOP
    band_bottom = band_top - config.PDF_HEADER_HEIGHT
    band_width = page_width - config.PDF_MARGIN_LEFT - config.PDF_MARGIN_RIGHT
    text_x = config.PDF_MARGIN_LEFT + config.PDF_TABLE_CELL_PADDING

    pdf.saveState()
    pdf.setFillColor(_hex_color(config.ACCENT_COLOR))
    pdf.rect(
        config.PDF_MARGIN_LEFT, band_bottom, band_width, config.PDF_HEADER_HEIGHT, fill=1, stroke=0
    )
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", config.PDF_HEADER_TITLE_FONT_SIZE)
    pdf.drawString(text_x, band_top - 26.0, _TITLE)
    pdf.setFont("Helvetica-Bold", config.PDF_HEADER_NAME_FONT_SIZE)
    pdf.drawString(text_x, band_top - 48.0, _header_name(full_name))
    pdf.setFont("Helvetica", config.PDF_HEADER_RANGE_FONT_SIZE)
    pdf.drawString(text_x, band_top - 64.0, _header_filter_label(filter_label))
    pdf.restoreState()

    return band_bottom - config.PDF_SECTION_SPACING


def _draw_table_header(pdf: canvas.Canvas, columns: tuple[_ColumnSpec, ...], top_y: float) -> float:
    page_width, _ = pdf._pagesize
    header_bottom = top_y - config.PDF_TABLE_HEADER_HEIGHT
    x = config.PDF_MARGIN_LEFT

    pdf.saveState()
    pdf.setFillColor(_hex_color(config.PDF_TABLE_HEADER_COLOR))
    pdf.setStrokeColor(_hex_color(config.PDF_TABLE_BORDER_COLOR))
    pdf.rect(
        config.PDF_MARGIN_LEFT,
        header_bottom,
        page_width - config.PDF_MARGIN_LEFT - config.PDF_MARGIN_RIGHT,
        config.PDF_TABLE_HEADER_HEIGHT,
        fill=1,
        stroke=1,
    )
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", config.PDF_TABLE_HEADER_FONT_SIZE)
    text_y = _text_baseline(
        header_bottom,
        config.PDF_TABLE_HEADER_HEIGHT,
        config.PDF_TABLE_HEADER_FONT_SIZE,
    )

    for column in columns:
        if column.right_align:
            pdf.drawRightString(
                x + column.width - config.PDF_TABLE_CELL_PADDING, text_y, column.heading
            )
        else:
            pdf.drawString(x + config.PDF_TABLE_CELL_PADDING, text_y, column.heading)
        x += column.width

    pdf.restoreState()
    return header_bottom


def _draw_record_row(
    pdf: canvas.Canvas,
    columns: tuple[_ColumnSpec, ...],
    record: SpeedRecord,
    row_top: float,
    row_index: int,
) -> float:
    page_width, _ = pdf._pagesize
    row_bottom = row_top - config.PDF_TABLE_ROW_HEIGHT
    row_width = page_width - config.PDF_MARGIN_LEFT - config.PDF_MARGIN_RIGHT
    x = config.PDF_MARGIN_LEFT
    values = (
        format_date(record.start_ts),
        format_time_range(record.start_ts, record.end_ts),
        format_speed(record.download_bps),
        format_speed(record.upload_bps),
    )

    pdf.saveState()
    if row_index % 2 == 1:
        pdf.setFillColor(_hex_color(config.PDF_ROW_STRIPE_COLOR))
        pdf.rect(
            config.PDF_MARGIN_LEFT,
            row_bottom,
            row_width,
            config.PDF_TABLE_ROW_HEIGHT,
            fill=1,
            stroke=0,
        )

    pdf.setStrokeColor(_hex_color(config.PDF_TABLE_BORDER_COLOR))
    pdf.line(config.PDF_MARGIN_LEFT, row_bottom, page_width - config.PDF_MARGIN_RIGHT, row_bottom)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", config.PDF_TABLE_BODY_FONT_SIZE)
    text_y = _text_baseline(
        row_bottom, config.PDF_TABLE_ROW_HEIGHT, config.PDF_TABLE_BODY_FONT_SIZE
    )

    for column, value in zip(columns, values, strict=True):
        if column.right_align:
            pdf.drawRightString(x + column.width - config.PDF_TABLE_CELL_PADDING, text_y, value)
        else:
            pdf.drawString(x + config.PDF_TABLE_CELL_PADDING, text_y, value)
        x += column.width

    pdf.restoreState()
    return row_bottom


def _draw_empty_state(pdf: canvas.Canvas, top_y: float) -> None:
    page_width, _ = pdf._pagesize

    pdf.saveState()
    pdf.setFillColor(_hex_color(config.PDF_FOOTER_TEXT_COLOR))
    pdf.setFont("Helvetica-Oblique", config.PDF_EMPTY_STATE_FONT_SIZE)
    pdf.drawCentredString(page_width / 2.0, top_y - config.PDF_SECTION_SPACING, _EMPTY_MESSAGE)
    pdf.restoreState()


def _start_page(
    pdf: canvas.Canvas,
    columns: tuple[_ColumnSpec, ...],
    filter_label: str,
    full_name: str,
) -> float:
    table_top = _draw_document_header(pdf, filter_label, full_name)
    return _draw_table_header(pdf, columns, table_top)


def _needs_page_break(next_row_top: float) -> bool:
    min_body_bottom = (
        config.PDF_MARGIN_BOTTOM + config.PDF_FOOTER_HEIGHT + config.PDF_SECTION_SPACING
    )
    return next_row_top - config.PDF_TABLE_ROW_HEIGHT < min_body_bottom


def generate_report(
    records: Iterable[SpeedRecord],
    filter_label: str,
    full_name: str,
    out_path: Path,
) -> None:
    """Generate a paginated PDF report for ``records`` at ``out_path``."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    generated_label = _format_generated_label(_now_local())
    pdf = _NumberedCanvas(
        str(out_path),
        generated_label=generated_label,
        pagesize=(config.PDF_PAGE_WIDTH, config.PDF_PAGE_HEIGHT),
        pageCompression=1,
    )
    pdf.setCreator(config.APP_NAME)
    pdf.setTitle(_TITLE)
    pdf.setAuthor(_header_name(full_name))

    columns = _build_columns(config.PDF_PAGE_WIDTH)
    row_top = _start_page(pdf, columns, filter_label, full_name)
    has_records = False
    row_index = 0

    for record in records:
        has_records = True
        if _needs_page_break(row_top):
            pdf.showPage()
            row_top = _start_page(pdf, columns, filter_label, full_name)

        row_top = _draw_record_row(pdf, columns, record, row_top, row_index)
        row_index += 1

    if not has_records:
        _draw_empty_state(pdf, row_top)

    pdf.save()


__all__ = ["generate_report", "format_date", "format_speed", "format_time_range"]
