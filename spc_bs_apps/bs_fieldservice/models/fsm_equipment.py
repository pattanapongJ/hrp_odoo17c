from odoo import fields, models


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    code = fields.Char(string="Code")
    serial_number = fields.Char(string="Serial Number")
