from odoo import fields, models


class FSMOrderWorkerStatusLog(models.Model):
    _name = "bs.fsm.order.worker.status.log"
    _description = "FSM Order Request Worker Status Change Log"
    _order = "changed_on desc, id desc"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    person_id = fields.Many2one("fsm.person", string="Worker", required=True)
    status_from = fields.Selection(
        [("available", "Available"), ("conflict", "Conflict")], string="From"
    )
    status_to = fields.Selection(
        [("available", "Available"), ("conflict", "Conflict")],
        string="To",
        required=True,
    )
    changed_on = fields.Datetime(
        string="Changed On", default=fields.Datetime.now, required=True
    )
