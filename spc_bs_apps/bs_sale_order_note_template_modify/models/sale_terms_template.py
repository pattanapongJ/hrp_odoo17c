from odoo import fields, models


class SaleTermsTemplate(models.Model):
    _inherit = "sale.terms_template"

    template_type = fields.Selection(
        [("subject", "Subject Template"), ("other", "Other Template")],
        string="Template Type",
        default="other",
        required=True,
        readonly=True
    )
