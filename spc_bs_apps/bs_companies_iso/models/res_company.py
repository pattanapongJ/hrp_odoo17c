from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    iso = fields.Char(string="ISO")
