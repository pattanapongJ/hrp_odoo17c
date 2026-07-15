from odoo import api, fields, models


class FSMOrderWorkerLine(models.Model):
    _name = "bs.fsm.order.worker.line"
    _description = "FSM Order Request Worker"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    person_id = fields.Many2one("fsm.person", string="Name", required=True)
    category_ids = fields.Many2many(
        related="person_id.category_ids", string="Category", readonly=True
    )
    schedule_display = fields.Char(
        string="Schedule", compute="_compute_schedule_display"
    )
    status = fields.Selection(
        [("available", "Available"), ("conflict", "Conflict")],
        string="Status",
        default="available",
        help="Placeholder for now - manually set. Automatic cross-order "
        "conflict detection is a follow-up phase.",
    )

    @api.depends("order_id.scheduled_date_start", "order_id.scheduled_date_end")
    def _compute_schedule_display(self):
        for line in self:
            start = line.order_id.scheduled_date_start
            end = line.order_id.scheduled_date_end
            if start and end:
                line.schedule_display = "{}-{}".format(
                    start.strftime("%H:%M"), end.strftime("%H:%M")
                )
            else:
                line.schedule_display = ""
