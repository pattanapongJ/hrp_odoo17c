# Copyright 2021 Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class SaleOrder(models.Model):

    _inherit = "sale.order"

    terms_template_ids = fields.Many2many(
        "sale.terms_template",
        string="Terms and conditions templates",
    )

    @api.onchange("terms_template_ids")
    def _onchange_terms_template_ids(self):
        if self.terms_template_ids:
            self.note = "".join(
                template.get_value(self) for template in self.terms_template_ids
            )
