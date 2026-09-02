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
    # Snapshot of which Team this worker was under and when they were added
    # to this order - set once at creation (see
    # fsm.order._compute_worker_line_ids) and never changed afterward, so
    # the append-only Request Workers list itself doubles as the Job
    # Handover history (who worked on this order, under which Team, since
    # when) without a separate log table.
    team_id = fields.Many2one("fsm.team", string="Team", readonly=True)
    joined_on = fields.Datetime(
        string="Joined On", default=fields.Datetime.now, readonly=True
    )
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
    released = fields.Boolean(
        string="Released",
        default=False,
        help="This worker's Team was reassigned away from this order (Job "
        "Handover) - the line is kept so the order still shows everyone "
        "who ever worked on it, but its status is force-set to Available "
        "and excluded from the normal conflict recompute, since they're "
        "free to be booked on other jobs immediately (see "
        "fsm.order._release_workers_not_in_current_team).",
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
