from odoo import fields, models


class BSEquipmentModel(models.Model):
    _name = "bs.equipment.model"
    _description = "Equipment Model"
    _order = "code"
    _rec_name = "code"

    code = fields.Char(required=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "This Model code already exists."),
    ]
