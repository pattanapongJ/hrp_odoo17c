from odoo import fields, models


class BSEquipmentBrand(models.Model):
    _name = "bs.equipment.brand"
    _description = "Equipment Brand"
    _order = "name"

    name = fields.Char(required=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "This Brand name already exists."),
    ]
