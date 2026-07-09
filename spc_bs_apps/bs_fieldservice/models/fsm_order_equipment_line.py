from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMOrderEquipmentLine(models.Model):
    _name = "bs.fsm.order.equipment.line"
    _description = "FSM Order Equipment Line"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    equipment_id = fields.Many2one("fsm.equipment", string="Equipment", required=True)
    code = fields.Char(related="equipment_id.code", string="Code", store=True)
    equipment_name = fields.Char(
        related="equipment_id.name", string="Equipment Name", store=True
    )
    serial_number = fields.Char(
        related="equipment_id.serial_number", string="Serial", store=True
    )
    qty_total = fields.Integer(string="Qty Needed", default=1)
    qty_withdrawn = fields.Integer(string="Qty Withdrawn", default=0)
    qty_returned = fields.Integer(
        string="Qty Returned", compute="_compute_qty_returned", store=True
    )
    withdrawn_date = fields.Datetime(string="Withdrawn On")
    returned_date = fields.Datetime(string="Returned On")
    return_deadline = fields.Datetime(string="Return Deadline")
    notes = fields.Char(string="Notes")
    status = fields.Selection(
        [
            ("not_withdrawn", "Not Withdrawn"),
            ("in_use", "In Use"),
            ("partial", "Partial"),
            ("overdue", "Overdue"),
            ("returned", "Returned"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
    )
    return_status = fields.Selection(
        [
            ("not_withdrawn", "Not Withdrawn"),
            ("not_returned", "Not Returned"),
            ("partial", "Partial"),
            ("overdue", "Overdue"),
            ("complete", "Complete"),
        ],
        string="Return",
        compute="_compute_status",
        store=True,
    )

    @api.constrains("qty_total", "qty_withdrawn", "qty_returned")
    def _check_quantities(self):
        for line in self:
            if line.qty_total < 0 or line.qty_withdrawn < 0 or line.qty_returned < 0:
                raise ValidationError(_("Quantities cannot be negative."))
            if line.qty_returned > line.qty_withdrawn:
                raise ValidationError(
                    _("Returned quantity cannot exceed withdrawn quantity.")
                )

    @api.depends("returned_date", "qty_withdrawn")
    def _compute_qty_returned(self):
        # No manual "qty returned" input in the UI - filling in Returned On
        # implies the equipment was fully returned.
        for line in self:
            line.qty_returned = line.qty_withdrawn if line.returned_date else 0

    @api.depends("qty_total", "qty_withdrawn", "qty_returned", "return_deadline")
    def _compute_status(self):
        now = fields.Datetime.now()
        for line in self:
            overdue = bool(
                line.return_deadline
                and now > line.return_deadline
                and line.qty_returned < line.qty_withdrawn
            )
            if line.qty_withdrawn <= 0:
                line.status = "not_withdrawn"
                line.return_status = "not_withdrawn"
            elif overdue:
                line.status = "overdue"
                line.return_status = "overdue"
            elif (
                line.qty_returned >= line.qty_withdrawn
                and line.qty_withdrawn >= line.qty_total
            ):
                line.status = "returned"
                line.return_status = "complete"
            elif line.qty_withdrawn < line.qty_total or (
                0 < line.qty_returned < line.qty_withdrawn
            ):
                line.status = "partial"
                line.return_status = (
                    "partial" if line.qty_returned > 0 else "not_returned"
                )
            else:
                line.status = "in_use"
                line.return_status = "not_returned"
