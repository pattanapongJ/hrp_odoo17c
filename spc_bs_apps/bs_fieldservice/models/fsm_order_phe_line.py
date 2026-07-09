from odoo import _, api, fields, models


class FSMOrderPheLine(models.Model):
    _name = "bs.fsm.order.phe.line"
    _description = "FSM Order PHE Equipment Line"
    _order = "sequence, id"
    _rec_name = "name"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Name", compute="_compute_name", store=True)
    tag_no = fields.Char(string="Tag No.")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    media = fields.Char(string="Media (H/C)")
    plate_mat = fields.Char(string="Plate Mat.")
    no_plate = fields.Integer(string="No.Plate")
    gasket = fields.Char(string="Gasket")
    mech = fields.Boolean(string="Mech")
    chem = fields.Boolean(string="Chem")
    pt_percent = fields.Integer(string="PT (%)")
    regskt_wh = fields.Boolean(string="Re-gskt WH")
    regskt_cus = fields.Boolean(string="Re-gskt CUS")
    source = fields.Char(string="Source")
    pressure_test = fields.Char(string="Pressure Test")

    @api.depends("tag_no", "brand", "model")
    def _compute_name(self):
        for line in self:
            parts = [line.tag_no, line.brand, line.model]
            line.name = " - ".join(p for p in parts if p) or _("PHE Equipment")
