from odoo import fields, models


class BsBrandLogo(models.Model):
    _name = "bs.brand.logo"
    _description = "Brand Logo"

    name = fields.Char(required=True)
    logo = fields.Binary(string="Logo", attachment=True)
