from odoo import models
from odoo.tools import html2plaintext


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

    def _get_quotation_report_pages(self, rows_per_page=15):
        """Split order lines into fixed-size pages for the G Plus report.

        Each page is a list of exactly ``rows_per_page`` entries of
        ``(row_number, line)`` tuples, padded with ``(False, False)`` so
        the printed table always shows the same number of ruled rows on
        every page. ``row_number`` starts at 1 and only counts real lines.
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        numbered_lines = list(enumerate(lines, start=1))

        page_count = max(1, -(-len(numbered_lines) // rows_per_page))
        pages = []
        for index in range(page_count):
            chunk = numbered_lines[index * rows_per_page:(index + 1) * rows_per_page]
            chunk += [(False, False)] * (rows_per_page - len(chunk))
            pages.append(chunk)
        return pages
