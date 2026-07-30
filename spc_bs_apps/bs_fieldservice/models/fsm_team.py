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
