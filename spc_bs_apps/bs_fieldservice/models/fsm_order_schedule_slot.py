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
            ("pending_delivery", "รอส่งมอบ"),
            ("other", "อื่นๆ"),
        ],
        string="ประเภท",
        required=True,
        default="other",
    )
    duration_type = fields.Selection(
        [("full_day", "Full day"), ("custom", "Custom")],
        string="Duration",
        required=True,
        default="custom",
    )
    date_from = fields.Date(string="วันที่เริ่ม")
    date_to = fields.Date(string="วันที่สิ้นสุด")
    time_from = fields.Float(string="เวลาเริ่ม")
    time_to = fields.Float(string="เวลาสิ้นสุด")
    location = fields.Char(string="สถานที่")

    @api.onchange("duration_type")
    def _onchange_duration_type(self):
        # Full day covers the entire date_from-date_to range - time_to=24.0
        # extends the range to exactly midnight after date_to, i.e. the
        # whole last day, matching how _get_datetime_range() combines them.
        if self.duration_type == "full_day":
            self.time_from = 0.0
            self.time_to = 24.0

    @staticmethod
    def _full_day_time_vals(vals):
        if vals.get("duration_type") == "full_day":
            return dict(vals, time_from=0.0, time_to=24.0)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        # time_from/time_to are readonly in the view once duration_type is
        # "full_day" (see fsm_order_views.xml) - the onchange above sets
        # them client-side, but a view-readonly field isn't reliably
        # included in the web client's save payload, so enforce the same
        # 00:00-24:00 values here too, independent of whatever the client
        # actually sent.
        vals_list = [self._full_day_time_vals(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        return super().write(self._full_day_time_vals(vals))

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

    def _find_overlap(self):
        """Return (other_slot, is_same_order, other_start, other_end) for
        the first overlapping slot found - same order checked first, then
        other orders for the same worker (person_id) - idle slots never
        count as a conflict. Returns None if there's no overlap. Shared by
        the hard constraint below and the onchange warning, so both use
        the exact same definition of "overlap"."""
        self.ensure_one()
        start, end = self._get_datetime_range()
        if not start or not end:
            return None
        for other in self.order_id.schedule_slot_ids - self:
            other_start, other_end = other._get_datetime_range()
            if other_start and other_end and start < other_end and other_start < end:
                return other, True, other_start, other_end
        if self.person_id:
            current_id = self._origin.id if self._origin else self.id
            cross_order_others = self.env["bs.fsm.order.schedule.slot"].search(
                [
                    ("person_id", "=", self.person_id.id),
                    ("order_id", "!=", self.order_id.id),
                    ("id", "!=", current_id if isinstance(current_id, int) else 0),
                    # idle ("ว่าง") means the worker is free during that
                    # slot - it's not a real commitment, so it never blocks
                    # another order from booking the same date/time.
                    ("slot_type", "!=", "idle"),
                ]
            )
            for other in cross_order_others:
                other_start, other_end = other._get_datetime_range()
                if other_start and other_end and start < other_end and other_start < end:
                    return other, False, other_start, other_end
        return None

    @api.constrains("date_from", "date_to", "time_from", "time_to", "person_id")
    def _check_no_overlap(self):
        for slot in self:
            found = slot._find_overlap()
            if not found:
                continue
            other, is_same_order, other_start, other_end = found
            if is_same_order:
                type_label = dict(other._fields["slot_type"].selection).get(
                    other.slot_type, other.slot_type
                )
                raise ValidationError(
                    _(
                        "This slot's date/time range overlaps with "
                        "another slot (%(type)s, %(from)s - %(to)s) on "
                        "the same order.",
                        type=type_label,
                        **{"from": other_start, "to": other_end},
                    )
                )
            raise ValidationError(
                _(
                    "%(person)s already has a schedule slot on order "
                    "%(order)s (%(from)s - %(to)s) that overlaps "
                    "with this date/time range.",
                    person=slot.person_id.name,
                    order=other.order_id.name,
                    **{"from": other_start, "to": other_end},
                )
            )

    @api.onchange("duration_type", "date_from", "date_to", "time_from", "time_to")
    def _onchange_check_no_overlap_warning(self):
        # @api.constrains only runs on actual Save (write/create) - this
        # gives the same "already booked" feedback immediately while still
        # editing in the browser, as a non-blocking heads up. The real
        # enforcement remains _check_no_overlap above.
        found = self._find_overlap()
        if not found:
            return
        other, is_same_order, other_start, other_end = found
        if is_same_order:
            message = _(
                "This slot's date/time range overlaps with another slot "
                "on the same order (%(from)s - %(to)s). This will be "
                "blocked when you Save.",
                **{"from": other_start, "to": other_end},
            )
        else:
            message = _(
                "%(person)s already has a schedule slot on order "
                "%(order)s (%(from)s - %(to)s) that overlaps with this "
                "date/time range. This will be blocked when you Save.",
                person=self.person_id.name,
                order=other.order_id.name,
                **{"from": other_start, "to": other_end},
            )
        return {
            "warning": {
                "title": _("Overlapping Schedule"),
                "message": message,
            }
        }
