from odoo import fields, models


class FSMTeam(models.Model):
    _inherit = "fsm.team"

    team_side = fields.Selection(
        [("phe", "PHE"), ("pump", "Pump")],
        string="Team Side",
        help="Restricts this team to be assignable only on orders with the "
        "matching Technician Profile.",
    )
    team_manager_id = fields.Many2one("fsm.person", string="Team Manager")
    # Membership is owned by the Team, not the person - fsm.person.team_id
    # (base fieldservice) only ever let a worker belong to ONE team, which
    # doesn't reflect reality once a worker can be requested onto orders
    # under different teams. This line model lets the same fsm.person
    # appear under several teams' member_ids at once. Managed directly from
    # the Team form's Members tab; fsm.order's Team Info panel (and Request
    # Workers' auto-populate) read member_ids.person_id as the roster.
    member_ids = fields.One2many(
        "bs.fsm.team.member.line", "team_id", string="Team Members"
    )
