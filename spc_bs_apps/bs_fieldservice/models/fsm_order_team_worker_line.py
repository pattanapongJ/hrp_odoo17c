from odoo import fields, models


class FSMOrderTeamWorkerLine(models.Model):
    _name = "bs.fsm.order.team.worker.line"
    _description = "FSM Order Team Info Worker"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    # Not required=True at the DB level on purpose, even though a line is
    # conceptually meaningless without one - the web client's onchange ->
    # save round trip for this auto-populated one2many can submit blank
    # (0,0,{}) rows with no person_id at all (a reproducible quirk in how
    # Odoo serializes o2m rows created by an onchange method referencing
    # ANOTHER model's records, e.g. team_id.member_ids, rather than
    # sibling records created in the same editing session). A hard NOT
    # NULL constraint would turn that into a save-blocking crash instead
    # of something fsm.order._purge_blank_team_worker_lines can clean up
    # right after. See bs.fsm.order.schedule.slot.person_id for the same
    # trade-off made earlier for the identical reason.
    person_id = fields.Many2one("fsm.person", string="Name")
    category_ids = fields.Many2many(
        related="person_id.category_ids", string="Category", readonly=True
    )
    # Set explicitly to "team" only by fsm.order's _sync_team_worker_lines
    # when it auto-populates a row from the order's Team roster
    # (fsm.team.member_ids) - any row created any other way (i.e. the user
    # adding a line through the UI) falls through to the default "manual".
    # This is what lets a Team switch safely delete and re-derive only the
    # "team" rows without ever touching a manually added worker.
    source = fields.Selection(
        [("team", "From Team"), ("manual", "Added Manually")],
        string="Source",
        default="manual",
        required=True,
    )
