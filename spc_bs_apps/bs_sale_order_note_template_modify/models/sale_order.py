from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    subject_template_id = fields.Many2one(
        "sale.terms_template",
        string="Subject Template",
        domain=[("template_type", "=", "subject")],
    )
    other_template_id = fields.Many2one(
        "sale.terms_template",
        string="Other Template",
        domain=[("template_type", "=", "other")],
    )
    subject_template_text = fields.Html(string="Review")
    other_template_text = fields.Html(string="Review")

    @api.onchange("subject_template_id")
    def _onchange_subject_template_id(self):
        if self.subject_template_id:
            self.subject_template_text = self.subject_template_id.get_value(self)

    @api.onchange("other_template_id")
    def _onchange_other_template_id(self):
        if self.other_template_id:
            self.other_template_text = self.other_template_id.get_value(self)
