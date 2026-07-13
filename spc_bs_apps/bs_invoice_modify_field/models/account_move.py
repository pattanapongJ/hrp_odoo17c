from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    apply_down_payment = fields.Boolean(
        string="Apply Down Payment",
        default=False,
    )
