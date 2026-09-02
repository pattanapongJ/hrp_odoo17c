from odoo import fields, models


class FSMTeamMemberLine(models.Model):
    _name = "bs.fsm.team.member.line"
    _description = "FSM Team Member"
    _order = "sequence, id"

    team_id = fields.Many2one(
        "fsm.team", string="Team", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    person_id = fields.Many2one("fsm.person", string="Worker", required=True)
    category_ids = fields.Many2many(
        related="person_id.category_ids", string="Category", readonly=True
    )

    _sql_constraints = [
        (
            "team_person_uniq",
            "unique (team_id, person_id)",
            "This worker is already a member of this team.",
        )
    ]
