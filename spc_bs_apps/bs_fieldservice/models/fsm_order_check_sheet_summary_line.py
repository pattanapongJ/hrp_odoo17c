from odoo import api, fields, models


class FSMOrderCheckSheetSummaryLine(models.Model):
    _name = "bs.fsm.order.check_sheet_summary.line"
    _description = "FSM Order Check Sheet Summary (grouped by Model)"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    maker = fields.Char(string="Maker")
    model_id = fields.Many2one("bs.equipment.model", string="Model")
    check_sheet_count = fields.Integer(string="Check Sheet Count")
    result = fields.Selection(
        [("pass", "Pass"), ("pending", "Pending")], string="Result"
    )

    # Service Report - Cleaning
    sr_clean_mech_naoh = fields.Boolean(string="NaOH")
    sr_clean_mech_acid = fields.Boolean(string="Acid")
    sr_clean_cip_naoh = fields.Boolean(string="NaOH")
    sr_clean_cip_acid = fields.Boolean(string="Acid")
    sr_remark_fouling_hot = fields.Char(string="Remark Fouling — Hot side")
    sr_remark_fouling_cold = fields.Char(string="Remark Fouling — Cold side")

    # Service Report - PT Test Results
    sr_pt_tested_plates = fields.Integer(string="Tested plates")
    sr_pt_leakage_found = fields.Integer(string="Leakage found")
    sr_pt_replaced_from_customer = fields.Boolean(string="Customer")
    sr_pt_replaced_from_warehouse = fields.Boolean(string="Warehouse")
    sr_pt_old_plate_return = fields.Boolean(string="Return")
    sr_pt_old_plate_dispose = fields.Boolean(string="Dispose")

    # Service Report - Re-gasket
    sr_gasket_material_type = fields.Char(string="Material / Type")
    sr_gasket_channel_qty = fields.Integer(string="Channel gasket")
    sr_gasket_oring_qty = fields.Integer(string="O-ring")
    sr_gasket_new_from_customer = fields.Boolean(string="Customer")
    sr_gasket_new_from_warehouse = fields.Boolean(string="Warehouse")

    # Service Report - Supervisor's Comment
    sr_supervisor_comment = fields.Text(string="Supervisor's Comment")

    @api.onchange("sr_pt_replaced_from_customer")
    def _onchange_sr_pt_replaced_from_customer(self):
        if self.sr_pt_replaced_from_customer:
            self.sr_pt_replaced_from_warehouse = False

    @api.onchange("sr_pt_replaced_from_warehouse")
    def _onchange_sr_pt_replaced_from_warehouse(self):
        if self.sr_pt_replaced_from_warehouse:
            self.sr_pt_replaced_from_customer = False

    @api.onchange("sr_pt_old_plate_return")
    def _onchange_sr_pt_old_plate_return(self):
        if self.sr_pt_old_plate_return:
            self.sr_pt_old_plate_dispose = False

    @api.onchange("sr_pt_old_plate_dispose")
    def _onchange_sr_pt_old_plate_dispose(self):
        if self.sr_pt_old_plate_dispose:
            self.sr_pt_old_plate_return = False

    @api.onchange("sr_gasket_new_from_customer")
    def _onchange_sr_gasket_new_from_customer(self):
        if self.sr_gasket_new_from_customer:
            self.sr_gasket_new_from_warehouse = False

    @api.onchange("sr_gasket_new_from_warehouse")
    def _onchange_sr_gasket_new_from_warehouse(self):
        if self.sr_gasket_new_from_warehouse:
            self.sr_gasket_new_from_customer = False
