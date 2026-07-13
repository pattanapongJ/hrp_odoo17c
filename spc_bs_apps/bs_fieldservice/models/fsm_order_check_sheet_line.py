from odoo import _, api, fields, models
from odoo.exceptions import AccessError

CONDITION_SELECTION = [("good", "Good"), ("fair", "Fair"), ("damage", "Damage")]


class FSMOrderCheckSheetLine(models.Model):
    _name = "bs.fsm.order.check_sheet.line"
    _description = "FSM Order Check Sheet"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed")],
        string="Status",
        default="draft",
        copy=False,
    )

    # Link to the source Assigned Worker equipment line - lets Tag No. and
    # Model stay live-synced instead of being a one-time copy at creation.
    phe_line_id = fields.Many2one(
        "bs.fsm.order.phe.line", string="Equipment Line", ondelete="cascade"
    )
    # readonly=False: related fields default to readonly=True unless told
    # otherwise, and the web client's save payload silently drops readonly
    # related fields - that was causing the JS-driven live sync (see
    # phe_line_table.js) to appear correct on screen but vanish after Save.
    # Non-editability in the popup form is enforced via the view instead
    # (readonly="1" on the <field>), which doesn't have this issue.
    tag_no = fields.Char(
        related="phe_line_id.tag_no", string="Tag No.", store=True, readonly=False
    )

    # Header
    report_no = fields.Char(string="Report No.", copy=False)
    report_type = fields.Selection(
        [("h", "H"), ("hs", "HS"), ("e", "E")], string="Type", default="h"
    )
    customer_id = fields.Many2one("res.partner", string="Customer")
    place = fields.Char(string="Place")
    work_start = fields.Datetime(string="Work start")
    work_finish = fields.Datetime(string="Work finish")
    job_mech_clean = fields.Boolean(string="Mech clean")
    job_replace_gasket = fields.Boolean(string="Replace new gasket")
    job_pt_test = fields.Boolean(string="PT test")
    item_no = fields.Integer(string="Item no.", default=1)
    maker = fields.Char(string="Maker")
    model_id = fields.Many2one(
        "bs.equipment.model",
        related="phe_line_id.model_id",
        string="Model",
        store=True,
        readonly=False,
    )
    serial_no = fields.Char(string="Serial no.")

    # Condition check
    a_measurement = fields.Float(string="A-measurement")
    pass_of_plate = fields.Integer(string="Pass of plate")
    no_of_plate = fields.Integer(string="No. of plate")
    wrench = fields.Char(string="Wrench")
    connection = fields.Char(string="Connection")
    tightening = fields.Char(string="Tightening")
    leakage_check = fields.Selection(
        [("pass", "Pass"), ("fail", "Fail")], string="Leakage check"
    )

    # Physical Condition
    pc_frame = fields.Selection(CONDITION_SELECTION, string="Frame")
    pc_connection = fields.Selection(CONDITION_SELECTION, string="Connection")
    pc_lining = fields.Selection(CONDITION_SELECTION, string="Lining")
    pc_tightening = fields.Selection(CONDITION_SELECTION, string="Tightening")

    # Plate inspection
    plate_material = fields.Char(string="Plate material")
    plate = fields.Selection(CONDITION_SELECTION, string="Plate")
    thick_plate = fields.Float(string="Thick plate")
    angle = fields.Char(string="Angle")
    immerse_plate = fields.Boolean(string="Immerse plate")
    photo_before_side1 = fields.Boolean(string="Side 1")
    photo_before_side2 = fields.Boolean(string="Side 2")
    photo_after_side1 = fields.Boolean(string="Side 1")
    photo_after_side2 = fields.Boolean(string="Side 2")

    # Gasket inspection
    gasket_material_nbr = fields.Boolean(string="NBR")
    gasket_material_epdm = fields.Boolean(string="EPDM")
    gasket_fair = fields.Boolean(string="Fair")
    gasket_damage = fields.Boolean(string="Damage")
    gasket_new_qty = fields.Integer(string="New")
    gasket_type_glue = fields.Boolean(string="Glue")
    gasket_type_clip_on = fields.Boolean(string="Clip on")
    gasket_photo_taken = fields.Boolean(string="ถ่ายภาพแล้ว")

    # PT test
    pt_test_yes = fields.Boolean(string="Yes")
    pt_test_no = fields.Boolean(string="No")
    pt_test_count = fields.Integer(string="No. of PT test")
    pt_new_replaced = fields.Integer(string="New replaced")
    pt_pinhole_crack_found = fields.Integer(string="Pin hole / crack found")
    pt_photo_red_side = fields.Boolean(string="Red side")
    pt_photo_white_side = fields.Boolean(string="White side")
    pt_remark_fouling = fields.Text(string="Remark fouling")

    # Assembly & Unit inspection
    existing_no_of_plate = fields.Integer(string="Existing no. of plate")
    final_installed = fields.Integer(string="Final installed")
    a_meas_before_dismantle = fields.Float(string="A-meas. before dismantle")
    a_meas_after_assembly = fields.Float(string="After assembly")
    service_test = fields.Boolean(string="Service test")
    leakage = fields.Boolean(string="Leakage")
    service_test_passed = fields.Boolean(string="Passed")
    hydro_hot_side = fields.Boolean(string="Hydro Hot side")
    hydro_hot_barg = fields.Char(string="barg")
    hydro_hot_min = fields.Char(string="min")
    hydro_hot_passed = fields.Boolean(string="Passed")
    hydro_cold_side = fields.Boolean(string="Hydro Cold side")
    hydro_cold_barg = fields.Char(string="barg")
    hydro_cold_min = fields.Char(string="min")
    hydro_cold_passed = fields.Boolean(string="Passed")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("report_no"):
                vals["report_no"] = self.env["ir.sequence"].next_by_code(
                    "bs.fsm.order.check_sheet"
                )
        return super().create(vals_list)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_reset_draft(self):
        # The view only hides this button via groups= for non-managers -
        # that's UI convenience, not enforcement. Check the real permission
        # here too, since the method can still be called directly (e.g. RPC).
        if not self.env.user.has_group("fieldservice.group_fsm_manager"):
            raise AccessError(
                _("Only a manager can reset a confirmed Check Sheet back to Draft.")
            )
        self.write({"state": "draft"})
