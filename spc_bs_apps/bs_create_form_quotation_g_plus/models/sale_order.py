from odoo import models

# Total lines available in the Footer's REMARK column per page - the
# entire per-page vertical budget for that column at 12.09px AngsanaUPC
# in its 70.1%-wide space (rescaled from 12.90px for the report's dpi 96
# -> 90 change; see paper_format_bs_create_quotation_g_plus_report and
# the module README of bs_report_pagination_helper). First-pass
# estimates - NOT calibrated against a real print; re-check against an
# actual long-remark quotation PDF and adjust if lines overflow the
# footer's reserved bottom margin or wrap noticeably short.
REMARK_CHARS_PER_LINE = 90
FOOTER_LINES_PER_PAGE = 29
# Lines reserved out of the first page's budget for the boilerplate intro
# text + "REMARK :" label (rendered as ``.o_report_first_page`` in the
# footer template) - 2 intro sentences + the label, so real REMARK text
# only starts after them.
FOOTER_INTRO_RESERVED_LINES = 3
# Lines reserved out of the last page's budget for the
# quotation-signature block. If the first page also ends up being the
# last page, both reservations apply together.
REMARK_SIGNATURE_RESERVED_LINES = 8


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]

    def _get_quotation_remark_splitter(self):
        """``ReportPageSplitter`` for ``other_template_text``, wrapped and
        split across pages per this report's own line budget (see
        ``bs_report_pagination_helper`` for the generic pagination
        logic).
        """
        self.ensure_one()
        lines = self._report_wrap_html_lines(self.other_template_text, REMARK_CHARS_PER_LINE)
        return self._report_paginate_lines(
            lines,
            FOOTER_LINES_PER_PAGE,
            first_page_reserved=FOOTER_INTRO_RESERVED_LINES,
            last_page_reserved=REMARK_SIGNATURE_RESERVED_LINES,
        )

    def _get_quotation_total_page_count(self):
        """How many physical pages the REMARK text needs. Computed purely
        from REMARK text length; unrelated to how many order lines there
        are (the item table is never split - only the footer paginates).
        Also used by ``report_main_content_g_plus`` to add enough blank
        continuation pages for the item table.
        """
        self.ensure_one()
        return self._get_quotation_remark_splitter().page_count

    def _get_quotation_remark_page_lines(self, page_index):
        """Lines of the REMARK text belonging on ``page_index`` (0-based),
        padded to that page's own budget - render with one ``<br/>`` per
        line in the footer template.
        """
        self.ensure_one()
        return self._get_quotation_remark_splitter().page_text(page_index).split("\n")
