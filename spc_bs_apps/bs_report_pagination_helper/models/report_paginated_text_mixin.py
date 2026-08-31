import textwrap

from odoo import models
from odoo.tools import html2plaintext


class ReportPageSplitter:
    """Splits a list of pre-wrapped text lines across the physical pages of
    a report footer/header, reserving a number of lines on the first and/or
    last page for other content (boilerplate, totals, signature block, ...).
    """

    def __init__(self, lines, lines_per_page, first_page_reserved=0, last_page_reserved=0):
        self._lines = lines
        self._lines_per_page = lines_per_page
        self._first_page_reserved = first_page_reserved
        self._last_page_reserved = last_page_reserved
        self._page_count = self._compute_page_count()

    @property
    def page_count(self):
        return self._page_count

    def page_text(self, page_index, pad_char="\xa0"):
        """Portion of the lines belonging on ``page_index`` (0-based),
        padded with ``pad_char`` up to that page's own budget so the
        footer reserves the same line height on every page.
        """
        start = sum(self._page_budget(i, self._page_count) for i in range(page_index))
        budget = self._page_budget(page_index, self._page_count)
        page_lines = self._lines[start:start + budget]
        page_lines += [pad_char] * (budget - len(page_lines))
        return "\n".join(page_lines)

    def _page_budget(self, page_index, total_pages):
        budget = self._lines_per_page
        if page_index == 0:
            budget -= self._first_page_reserved
        if page_index == total_pages - 1:
            budget -= self._last_page_reserved
        return max(1, budget)

    def _compute_page_count(self):
        pages = 1
        while True:
            capacity = sum(self._page_budget(i, pages) for i in range(pages))
            if len(self._lines) <= capacity:
                return pages
            pages += 1


class ReportPaginatedTextMixin(models.AbstractModel):
    _name = "bs.report.paginated.text.mixin"
    _description = "Wrap and paginate long text for report footers/headers"

    def _report_wrap_html_lines(self, html_value, chars_per_line):
        """Wrap the plain-text (HTML tags stripped) rendering of
        ``html_value`` into printed lines of at most ``chars_per_line``
        characters. Also usable on its own (without pagination) to
        estimate how many lines a piece of text will take, e.g. to size a
        table row.
        """
        text = html2plaintext(html_value or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=chars_per_line) or [""])
        # A leading/trailing blank paragraph in the source HTML (common
        # with Odoo's rich-text editor) would otherwise survive as its own
        # blank wrapped line, showing as a stray gap next to whatever
        # static content surrounds it in the report.
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def _report_paginate_lines(self, lines, lines_per_page, first_page_reserved=0, last_page_reserved=0):
        """Return a :class:`ReportPageSplitter` for ``lines`` (as produced
        by :meth:`_report_wrap_html_lines`), splitting them across as many
        pages as needed given ``lines_per_page`` and the reserved lines on
        the first/last page.
        """
        return ReportPageSplitter(lines, lines_per_page, first_page_reserved, last_page_reserved)
