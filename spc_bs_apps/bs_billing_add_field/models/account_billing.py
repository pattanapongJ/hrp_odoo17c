from odoo import fields, models


class AccountBilling(models.Model):
    _inherit = "account.billing"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
    )
