from odoo import models

# Total lines available in the footer's free-text area per page, over this
# report's bottom margin (see
# paper_format_bs_create_quotation_herring_plus_service_report). First-pass
# estimate - NOT calibrated against a real print; re-check against an
# actual long-text quotation PDF and adjust if lines overflow the
# footer's reserved bottom margin or wrap noticeably short.
HERRING_PLUS_SERVICE_OTHER_CHARS_PER_LINE = 130
HERRING_PLUS_SERVICE_FOOTER_LINES_PER_PAGE = 20
# Lines reserved out of the first page's budget for the "Above price..."
# boilerplate (rendered as ``.o_report_first_page`` in the footer
# template) - real note text only starts after it.
HERRING_PLUS_SERVICE_FOOTER_INTRO_RESERVED_LINES = 2


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]

    def _get_herring_plus_service_footer_splitter(self):
        """``ReportPageSplitter`` for ``other_template_text``, wrapped and
        split across pages per this report's own line budget (see
        ``bs_report_pagination_helper`` for the generic pagination
        logic).
        """
        self.ensure_one()
        lines = self._report_wrap_html_lines(self.other_template_text, HERRING_PLUS_SERVICE_OTHER_CHARS_PER_LINE)
        return self._report_paginate_lines(
            lines,
            HERRING_PLUS_SERVICE_FOOTER_LINES_PER_PAGE,
            first_page_reserved=HERRING_PLUS_SERVICE_FOOTER_INTRO_RESERVED_LINES,
        )

    def _get_herring_plus_service_total_page_count(self):
        """How many physical pages the note text needs. Computed purely
        from that text's length; unrelated to how many order lines there
        are (the item table is never split - only the footer paginates).
        """
        self.ensure_one()
        return self._get_herring_plus_service_footer_splitter().page_count

    def _get_herring_plus_service_other_page_lines(self, page_index):
        """Lines of the note text belonging on ``page_index`` (0-based),
        padded to that page's own budget - render with one ``<br/>`` per
        line in the footer template.
        """
        self.ensure_one()
        return self._get_herring_plus_service_footer_splitter().page_text(page_index).split("\n")
