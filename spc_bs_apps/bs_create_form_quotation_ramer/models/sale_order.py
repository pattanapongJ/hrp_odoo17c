from odoo import models

# Total lines available in the footer's free-text area per page, at 21px
# Times New Roman over this report's bottom margin (see
# paper_format_bs_create_quotation_ramer_report). First-pass estimate -
# NOT calibrated against a real print; re-check against an actual
# long-text quotation PDF and adjust if lines overflow the footer's
# reserved bottom margin or wrap noticeably short.
RAMER_OTHER_CHARS_PER_LINE = 130
RAMER_FOOTER_LINES_PER_PAGE = 18
# Lines reserved out of the first page's budget for the "Cancellation of
# order..." boilerplate (rendered as ``.o_report_first_page`` in the
# footer template) - real other-template text only starts after it.
RAMER_FOOTER_INTRO_RESERVED_LINES = 2


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]

    def _get_ramer_footer_splitter(self):
        """``ReportPageSplitter`` for ``other_template_text``, wrapped and
        split across pages per this report's own line budget (see
        ``bs_report_pagination_helper`` for the generic pagination
        logic).
        """
        self.ensure_one()
        lines = self._report_wrap_html_lines(self.other_template_text, RAMER_OTHER_CHARS_PER_LINE)
        return self._report_paginate_lines(
            lines,
            RAMER_FOOTER_LINES_PER_PAGE,
            first_page_reserved=RAMER_FOOTER_INTRO_RESERVED_LINES,
        )

    def _get_ramer_total_page_count(self):
        """How many physical pages the other-template text needs.
        Computed purely from that text's length; unrelated to how many
        order lines there are (the item table is never split - only the
        footer paginates).
        """
        self.ensure_one()
        return self._get_ramer_footer_splitter().page_count

    def _get_ramer_other_text(self, page_index):
        """Portion of the other-template text belonging on ``page_index``
        (0-based), padded to that page's own budget.
        """
        self.ensure_one()
        return self._get_ramer_footer_splitter().page_text(page_index)
