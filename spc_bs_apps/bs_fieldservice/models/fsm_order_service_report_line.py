from odoo import fields, models


class FSMOrderServiceReportLine(models.Model):
    _name = "bs.fsm.order.service_report.line"
    _description = "FSM Order Service Report Line"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)

    # PHE columns
    check_sheet_no = fields.Char(string="Check Sheet")
    tag_no = fields.Char(string="Tag No.")
    maker_model = fields.Char(string="Maker / Model")
    report_type = fields.Selection(
        [("h", "H"), ("hs", "HS"), ("e", "E")], string="H/HS/E"
    )
    job_type = fields.Char(string="Job Type")
    mech_clean = fields.Boolean(string="Mech Clean")
    re_gasket = fields.Boolean(string="Re-gasket")
    pt_test_status = fields.Char(string="PT Test")
    hydro_test = fields.Char(string="Hydro Test")
    result = fields.Selection(
        [("pass", "Pass"), ("pending", "Pending")], string="Result", default="pending"
    )

    # Pump columns
    work_done = fields.Char(string="Work Done")
    vibration_before = fields.Char(string="Vibration Before")
    vibration_after = fields.Char(string="Vibration After")
    alignment = fields.Char(string="Alignment")
