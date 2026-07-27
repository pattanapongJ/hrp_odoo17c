import textwrap

from odoo import models
from odoo.tools import html2plaintext

# Approx characters that fit on one REMARK column line, and how many such
# lines fit in the space left under the first page's 15-row item table.
# Calibrated against real wkhtmltopdf output: a ~14-line column already
# overflowed that space, so the safe budget is kept small.
REMARK_CHARS_PER_LINE = 40
REMARK_PAGE1_MAX_LINES = 18

# Approx characters that fit on one Description-column line, and how many
# such line slots fit in the space left for the item table on one page.
# ARTICLE_DESC_CHARS_PER_LINE is calibrated against real wkhtmltopdf
# output, not the column's raw mm width: measured real wrapped lines came
# out at 57-61 characters before breaking, so 45 was undercounting badly
# (e.g. a real 4-line description was estimated at 8 lines). Kept a bit
# under the observed max so a slightly longer line still overestimates
# (wastes a little space) rather than undercounts (risks the row
# overflowing past this module's page-count prediction).
ARTICLE_DESC_CHARS_PER_LINE = 58
# Measured empirically by test-rendering real PDFs at increasing budgets:
# 19 already leaves only ~24pt of margin before the footer, and 20
# overflows badly (physical page count jumps from 4 to 7 unexpectedly).
# 18 is the highest value that still keeps a safe ~36pt margin.
ARTICLE_LINE_SLOTS_PER_PAGE = 18


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

    def _get_quotation_order_line_slots(self, line):
        """Estimated number of printed lines (line slots) the item row
        for ``line`` will take, based on how many lines its Description
        wraps to - the column most likely to wrap and grow the row
        taller than a single line.
        """
        text = (line.name or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=ARTICLE_DESC_CHARS_PER_LINE) or [""])
        return max(1, len(lines))

    def _get_quotation_report_pages(self):
        """Split order lines into pages sized to the space actually left
        by each line's Description, rather than a flat rows-per-page
        count: a row whose Description wraps to 2 lines uses 2 of the
        page's ``ARTICLE_LINE_SLOTS_PER_PAGE`` slots instead of 1, so the
        natural render height stays inside what wkhtmltopdf fits on one
        physical page. Each page is padded with ``(False, False)`` blank
        single-line rows up to its slot budget, so the printed table
        always shows a full set of ruled rows regardless of how much
        real data there is. ``row_number`` starts at 1 and only counts
        real lines.

        Extended with fully-blank pages if REMARK needs more pages than
        the item table does, so REMARK always has somewhere to continue.
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        numbered_lines = list(enumerate(lines, start=1))

        pages = []
        current_page = []
        current_slots = 0
        for entry in numbered_lines:
            slots = self._get_quotation_order_line_slots(entry[1])
            if current_page and current_slots + slots > ARTICLE_LINE_SLOTS_PER_PAGE:
                pages.append((current_page, current_slots))
                current_page = []
                current_slots = 0
            current_page.append(entry)
            current_slots += slots
        pages.append((current_page, current_slots))

        while len(pages) < self._get_quotation_remark_page_count():
            pages.append(([], 0))

        return [
            page_lines + [(False, False)] * max(0, ARTICLE_LINE_SLOTS_PER_PAGE - slots)
            for page_lines, slots in pages
        ]

    def _get_quotation_total_page_count(self):
        """Total number of physical report pages - simply the length of
        ``_get_quotation_report_pages()``, so the footer's per-page
        REMARK blocks are always in sync with what the body actually
        renders (never a separately-estimated number that could drift
        out of sync).
        """
        self.ensure_one()
        return len(self._get_quotation_report_pages())
