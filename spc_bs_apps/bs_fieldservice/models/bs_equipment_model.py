from odoo import fields, models


class BSEquipmentModel(models.Model):
    _name = "bs.equipment.model"
    _description = "Equipment Model"
    _order = "code"
    _rec_name = "code"

    code = fields.Char(required=True, string="Model")
    # Many2one, not Char: one Brand (e.g. "Alfa Laval") has many Models
    # (M6, M10, M15, ...). Importing several Models under the same Brand
    # text used to hit unique(brand) below and fail as a false "duplicate
    # Brand" - Brand is now its own master (bs.equipment.brand), shared
    # across Models, with its own uniqueness constraint on name instead.
    brand = fields.Many2one("bs.equipment.brand", string="Brand")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "This Model code already exists."),
    ]
