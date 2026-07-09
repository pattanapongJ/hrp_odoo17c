from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMOrderScheduleSlot(models.Model):
    _name = "bs.fsm.order.schedule.slot"
    _description = "FSM Order Schedule Sub-slot"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "fsm.order", string="Order", required=True, ondelete="cascade"
    )
    person_id = fields.Many2one(
        related="order_id.person_id",
        string="Worker",
        store=True,
        help="Mirrors the order's Assigned To - an order only ever has one "
        "worker, so slots don't need an independent worker selection.",
    )
    sequence = fields.Integer(default=10)
    slot_type = fields.Selection(
        [
            ("travel_disassemble", "เดินทาง/ถอด"),
            ("idle", "ว่าง"),
            ("travel_assemble", "เดินทาง/ประกอบ"),
            ("other", "อื่นๆ"),
        ],
        string="ประเภท",
        required=True,
        default="other",
    )
    date_from = fields.Date(string="วันที่เริ่ม")
    date_to = fields.Date(string="วันที่สิ้นสุด")
    time_from = fields.Float(string="เวลาเริ่ม")
    time_to = fields.Float(string="เวลาสิ้นสุด")
    location = fields.Char(string="สถานที่")

    def _get_datetime_range(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            return None, None
        start = datetime.combine(self.date_from, time.min) + timedelta(
            hours=self.time_from or 0.0
        )
        end = datetime.combine(self.date_to, time.min) + timedelta(
            hours=self.time_to or 0.0
        )
        return start, end

    @api.constrains("date_from", "date_to", "time_from", "time_to")
    def _check_no_overlap(self):
        for slot in self:
            start, end = slot._get_datetime_range()
            if not start or not end:
                continue
            for other in slot.order_id.schedule_slot_ids - slot:
                other_start, other_end = other._get_datetime_range()
                if not other_start or not other_end:
                    continue
                if start < other_end and other_start < end:
                    type_label = dict(
                        other._fields["slot_type"].selection
                    ).get(other.slot_type, other.slot_type)
                    raise ValidationError(
                        _(
                            "This slot's date/time range overlaps with "
                            "another slot (%(type)s, %(from)s - %(to)s) on "
                            "the same order.",
                            type=type_label,
                            **{"from": other_start, "to": other_end},
                        )
                    )
