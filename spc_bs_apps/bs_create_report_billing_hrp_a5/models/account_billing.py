from odoo import models


class AccountBilling(models.Model):
    _inherit = "account.billing"

    def get_billing_report_pages_a5(self, page_size=3):
        lines = list(self.billing_line_ids)
        page_count = max(1, -(-len(lines) // page_size))
        pages = []
        for i in range(page_count):
            chunk = lines[i * page_size:(i + 1) * page_size]
            chunk += [False] * (page_size - len(chunk))
            pages.append(chunk)
        return pages
