from odoo import fields, models


class AccountBilling(models.Model):
    _inherit = "account.billing"

    def get_billing_report_pages(self, page_size=15):
        # TEMPORARY TEST DATA — 16 fake lines to check that every page
        # always shows `page_size` rows and the totals/หมายเหตุ/signature
        # block renders only once, after the last page.
        # Remove this block and uncomment the real logic below when done testing.
        lines = []
        # for i in range(1, 17):
        #     fake_invoice = self.env["account.move"].new({
        #         "name": "IV-TEST-%02d" % i,
        #         "invoice_date": fields.Date.today(),
        #         "invoice_date_due": fields.Date.today(),
        #         "amount_total": 100.0 * i,
        #     })
        #     fake_line = self.env["account.billing.line"].new({
        #         "invoice_id": fake_invoice.id,
        #         "total": 50.0 * i,
        #     })
        #     lines.append(fake_line)

        lines = list(self.billing_line_ids)

        page_count = max(1, -(-len(lines) // page_size))
        pages = []
        for i in range(page_count):
            chunk = lines[i * page_size:(i + 1) * page_size]
            chunk += [False] * (page_size - len(chunk))
            pages.append(chunk)
        return pages
