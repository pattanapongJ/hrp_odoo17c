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
    # Inverse of fsm.person.team_id - lets fsm.order's Team Info panel (and
    # Request Workers' auto-populate) look up "who's on this team" as a
    # real, dependency-trackable relation instead of an ad-hoc search.
    member_ids = fields.One2many("fsm.person", "team_id", string="Team Members")
