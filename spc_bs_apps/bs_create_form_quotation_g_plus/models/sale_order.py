import textwrap

from odoo import models
from odoo.tools import html2plaintext

# Approx characters that fit on one REMARK column line, and how many such
# lines fit in the space left under the first page's 15-row item table.
# Calibrated against real wkhtmltopdf output: a ~14-line column already
# overflowed that space, so the safe budget is kept small.
REMARK_CHARS_PER_LINE = 40
REMARK_PAGE1_MAX_LINES = 21


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_quotation_terms_template_text(self, index):
        """Return the full rendered text (plain text) of the template at
        ``index`` (0-based) in ``terms_template_ids``, or an empty string
        if there is no template at that position.
        """
        self.ensure_one()
        templates = self.terms_template_ids
        if index >= len(templates):
            return ""
        rendered_html = templates[index].get_value(self)
        return html2plaintext(rendered_html or "")

    def _get_quotation_remark_lines(self, index):
        """Wrap the terms-template text at ``index`` into printed lines,
        so the first-page/overflow split can be sliced precisely.
        """
        self.ensure_one()
        text = self._get_quotation_terms_template_text(index).strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=REMARK_CHARS_PER_LINE) or [""])
        return lines

    def _get_quotation_remark_page_count(self):
        """How many pages the REMARK text needs, at
        ``REMARK_PAGE1_MAX_LINES`` lines per page (every page has the
        same 15-row item table, so the space left for REMARK is the same
        everywhere).
        """
        self.ensure_one()
        max_lines = max(
            len(self._get_quotation_remark_lines(0)),
            len(self._get_quotation_remark_lines(1)),
        )
        return max(1, -(-max_lines // REMARK_PAGE1_MAX_LINES))

    def _get_quotation_remark_text(self, index, page_index):
        """Portion of the terms-template text at ``index`` (0 or 1) that
        belongs on ``page_index`` (0-based): each page gets its own
        ``REMARK_PAGE1_MAX_LINES``-line slice, so the text keeps flowing
        onto as many pages as it needs instead of being cut off.

        Padded with invisible (non-breaking space) lines up to the full
        ``REMARK_PAGE1_MAX_LINES`` budget, so the block always reserves
        the same height regardless of how much real text there is.
        """
        self.ensure_one()
        lines = self._get_quotation_remark_lines(index)
        start = page_index * REMARK_PAGE1_MAX_LINES
        page_lines = lines[start:start + REMARK_PAGE1_MAX_LINES]
        page_lines += [" "] * (REMARK_PAGE1_MAX_LINES - len(page_lines))
        return "\n".join(page_lines)

    def _get_quotation_report_pages(self, rows_per_page=15):
        """Split order lines into fixed-size pages for the G Plus report.

        Each page is a list of exactly ``rows_per_page`` entries of
        ``(row_number, line)`` tuples, padded with ``(False, False)`` so
        the printed table always shows the same number of ruled rows on
        every page. ``row_number`` starts at 1 and only counts real lines.

        If the REMARK text needs more pages than there are item pages,
        fully blank extra pages (same ruled table format) are appended so
        it always has somewhere to continue.
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        numbered_lines = list(enumerate(lines, start=1))

        item_page_count = max(1, -(-len(numbered_lines) // rows_per_page))
        page_count = max(item_page_count, self._get_quotation_remark_page_count())

        pages = []
        for index in range(page_count):
            chunk = numbered_lines[index * rows_per_page:(index + 1) * rows_per_page]
            chunk += [(False, False)] * (rows_per_page - len(chunk))
            pages.append(chunk)
        return pages
