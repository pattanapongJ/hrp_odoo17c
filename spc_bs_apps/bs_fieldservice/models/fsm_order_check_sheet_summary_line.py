from odoo import fields, models


class FSMOrderCheckSheetSummaryLine(models.Model):
    _name = "bs.fsm.order.check_sheet_summary.line"
    _description = "FSM Order Check Sheet Summary (grouped by Model)"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    maker = fields.Char(string="Maker")
    model_id = fields.Many2one("bs.equipment.model", string="Model")
    check_sheet_count = fields.Integer(string="Check Sheet Count")
    result = fields.Selection(
        [("pass", "Pass"), ("pending", "Pending")], string="Result"
    )
