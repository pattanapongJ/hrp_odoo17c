import textwrap

from odoo import models
from odoo.tools import html2plaintext

# Total lines available in the Footer's REMARK column per page - the
# entire per-page vertical budget for that column at 12.90px AngsanaUPC
# in its 70.1%-wide space. First-pass estimates - NOT calibrated against
# a real print (unlike the old article-table constants this module used
# to have); re-check against an actual long-remark quotation PDF and
# adjust if lines overflow the footer's reserved bottom margin or wrap
# noticeably short.
REMARK_CHARS_PER_LINE = 90
FOOTER_LINES_PER_PAGE = 29
# Lines reserved out of the first page's budget for the boilerplate intro
# text + "REMARK :" label (rendered as ``.first-page`` in the footer
# template) - 2 intro sentences + the label, so real REMARK text only
# starts after them.
FOOTER_INTRO_RESERVED_LINES = 3
# Lines reserved out of the last page's budget for the
# quotation-signature block. If the first page also ends up being the
# last page, both reservations apply together.
REMARK_SIGNATURE_RESERVED_LINES = 8


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_quotation_remark_lines(self):
        """Wrap the plain-text (HTML tags stripped) rendering of
        ``subject_template_text`` into printed lines, so the per-page
        split can be sliced precisely.
        """
        self.ensure_one()
        text = html2plaintext(self.other_template_text or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=REMARK_CHARS_PER_LINE) or [""])
        # A leading/trailing blank paragraph in the source HTML (common
        # with Odoo's rich-text editor) would otherwise survive as its
        # own blank wrapped line, showing as a stray gap next to the
        # static "REMARK :" label.
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return lines

    def _get_quotation_footer_page_budget(self, page_index, total_pages):
        """Real-text line budget for ``page_index`` (0-based) out of
        ``total_pages``: the full per-page budget, minus the intro
        reservation on page 0 and minus the signature reservation on
        the last page - both at once if page 0 is also the last page.
        """
        budget = FOOTER_LINES_PER_PAGE
        if page_index == 0:
            budget -= FOOTER_INTRO_RESERVED_LINES
        if page_index == total_pages - 1:
            budget -= REMARK_SIGNATURE_RESERVED_LINES
        return max(1, budget)

    def _get_quotation_total_page_count(self):
        """How many physical pages the REMARK text needs, filling each
        page's real-text budget (see ``_get_quotation_footer_page_budget``)
        before overflowing onto the next. Computed purely from REMARK
        text length; unrelated to how many order lines there are (the
        item table is never split - only the footer paginates).
        """
        self.ensure_one()
        lines = self._get_quotation_remark_lines()
        pages = 1
        while True:
            capacity = sum(
                self._get_quotation_footer_page_budget(i, pages) for i in range(pages)
            )
            if len(lines) <= capacity:
                return pages
            pages += 1

    def _get_quotation_remark_text(self, page_index):
        """Portion of the REMARK text belonging on ``page_index``
        (0-based). Real text fills each page up to its own budget from
        ``_get_quotation_footer_page_budget``, then pads with blank lines
        up to that *same* budget - not the raw ``FOOTER_LINES_PER_PAGE``.
        This is what actually makes the intro/signature reservations free
        up real vertical space: the box's rendered height must shrink by
        the reserved amount on page 0 / the last page, otherwise the
        reserved lines only turn into blank filler *inside* an
        always-full-height box, and whatever sits after it (signature)
        still gets pushed past the physical page.
        """
        self.ensure_one()
        lines = self._get_quotation_remark_lines()
        total_pages = self._get_quotation_total_page_count()
        start = sum(
            self._get_quotation_footer_page_budget(i, total_pages) for i in range(page_index)
        )
        real_budget = self._get_quotation_footer_page_budget(page_index, total_pages)
        page_lines = lines[start:start + real_budget]
        page_lines += [" "] * (real_budget - len(page_lines))
        return "\n".join(page_lines)
