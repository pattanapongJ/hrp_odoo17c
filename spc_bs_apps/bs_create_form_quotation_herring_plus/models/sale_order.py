import textwrap

from odoo import models
from odoo.tools import html2plaintext

# Total lines available in the footer's free-text area per page, over this
# report's bottom margin (see
# paper_format_bs_create_quotation_herring_plus_report). First-pass
# estimate - NOT calibrated against a real print; re-check against an
# actual long-text quotation PDF and adjust if lines overflow the
# footer's reserved bottom margin or wrap noticeably short.
HERRING_PLUS_OTHER_CHARS_PER_LINE = 130
HERRING_PLUS_FOOTER_LINES_PER_PAGE = 20
# Lines reserved out of the first page's budget for the "Above price..."
# boilerplate (rendered as ``.first-page`` in the footer template) - real
# note text only starts after it.
HERRING_PLUS_FOOTER_INTRO_RESERVED_LINES = 2


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_herring_plus_other_lines(self):
        """Wrap the plain-text (HTML tags stripped) rendering of ``note``
        into printed lines, so the per-page split can be sliced precisely.
        """
        self.ensure_one()
        text = html2plaintext(self.other_template_text or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=HERRING_PLUS_OTHER_CHARS_PER_LINE) or [""])
        # A leading/trailing blank paragraph in the source HTML (common
        # with Odoo's rich-text editor) would otherwise survive as its own
        # blank wrapped line, showing as a stray gap next to the static
        # boilerplate text above it.
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def _get_herring_plus_footer_page_budget(self, page_index, total_pages):
        """Real-text line budget for ``page_index`` (0-based) out of
        ``total_pages``: the full per-page budget, minus the intro
        reservation on page 0.
        """
        budget = HERRING_PLUS_FOOTER_LINES_PER_PAGE
        if page_index == 0:
            budget -= HERRING_PLUS_FOOTER_INTRO_RESERVED_LINES
        return max(1, budget)

    def _get_herring_plus_total_page_count(self):
        """How many physical pages the note text needs, filling each
        page's real-text budget (see
        ``_get_herring_plus_footer_page_budget``) before overflowing onto
        the next. Computed purely from that text's length; unrelated to
        how many order lines there are (the item table is never split -
        only the footer paginates).
        """
        self.ensure_one()
        lines = self._get_herring_plus_other_lines()
        pages = 1
        while True:
            capacity = sum(
                self._get_herring_plus_footer_page_budget(i, pages) for i in range(pages)
            )
            if len(lines) <= capacity:
                return pages
            pages += 1

    def _get_herring_plus_other_text(self, page_index):
        """Portion of the note text belonging on ``page_index`` (0-based).
        Real text fills each page up to its own budget from
        ``_get_herring_plus_footer_page_budget``, then pads with blank
        lines up to that same budget.
        """
        self.ensure_one()
        lines = self._get_herring_plus_other_lines()
        total_pages = self._get_herring_plus_total_page_count()
        start = sum(
            self._get_herring_plus_footer_page_budget(i, total_pages) for i in range(page_index)
        )
        real_budget = self._get_herring_plus_footer_page_budget(page_index, total_pages)
        page_lines = lines[start:start + real_budget]
        # A plain space collapses to nothing under the template's
        # ``white-space: pre-line`` - a non-breaking space is needed so
        # each padding line still reserves a real line box.
        page_lines += ["\xa0"] * (real_budget - len(page_lines))
        return "\n".join(page_lines)
