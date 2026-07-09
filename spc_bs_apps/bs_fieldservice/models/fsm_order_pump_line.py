from odoo import fields, models


class FSMOrderPumpLine(models.Model):
    _name = "bs.fsm.order.pump.line"
    _description = "FSM Order Pump Equipment Line"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    tag_no = fields.Char(string="Tag No.")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    flow = fields.Float(string="Flow (m3/h)")
    head = fields.Float(string="Head (m)")
    power = fields.Float(string="Power (kW)")
    equipment_type = fields.Char(string="Type")
    scope_of_service = fields.Char(string="Scope of Service")
