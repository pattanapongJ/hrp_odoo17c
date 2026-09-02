from odoo import fields, models


class FSMEquipment(models.Model):
    _inherit = "fsm.equipment"

    code = fields.Char(string="Code")
    serial_number = fields.Char(string="Serial Number")
    # Equipment is a pool shared across all 7 companies (like fsm.person
    # already is) - base fieldservice makes company_id required and
    # defaults it to the creating user's current company, which would
    # silently make every new piece of equipment company-locked again.
    # Relaxing required + clearing the default lets a blank company_id
    # pass the base module's own ir.rule (fsm_equipment_comp_rule already
    # allows company_id = False), making the record visible/selectable
    # from any company. Existing per-company equipment is left untouched.
    company_id = fields.Many2one(required=False, default=False)
