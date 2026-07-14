from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_time = fields.Char(string="Delivery Time")
    brand_logo_id = fields.Many2one("bs.brand.logo", string="Brand Logo")
