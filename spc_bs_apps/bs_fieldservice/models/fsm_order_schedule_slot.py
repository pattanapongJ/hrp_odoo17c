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
    # Freely selectable by the user, but restricted in the view (domain +
    # no_create) to only the order's own Request Workers via
    # requested_person_ids - an order can now have several Request
    # Workers, each with their own set of sub-slots, so this is no longer
    # mirrored from a single Assigned To. Never auto-added: a sub-slot row
    # only ever exists if a user creates it here directly.
    person_id = fields.Many2one("fsm.person", string="Worker")
    order_request_early = fields.Datetime(
        related="order_id.request_early",
        string="Order Earliest Request Date",
        help="Mirrored purely so the date picker widget (bs_schedule_slot_date) "
        "can hard-block days outside the order's requested window without an "
        "extra RPC - not meant to be shown/edited on this line.",
    )
    order_request_late = fields.Datetime(
        related="order_id.request_late",
        string="Order Latest Request Date",
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

    def _local_request_window_dates(self):
        """order_id.request_early/request_late's CALENDAR DATE (not time),
        in the current user's timezone - request_early/request_late mark
        which DAYS the job may happen on, not an hour-level boundary within
        those days, so only the date component matters here (converting to
        local first, since these are Datetime fields stored as naive UTC,
        before taking .date())."""
        self.ensure_one()
        early = self.order_id.request_early
        late = self.order_id.request_late
        if early:
            early = fields.Datetime.context_timestamp(self, early).date()
        if late:
            late = fields.Datetime.context_timestamp(self, late).date()
        return early, late

    def _find_out_of_window(self):
        """Return (request_early, request_late) if this slot's date_from/
        date_to falls outside its order's requested window, else None -
        checked by DATE only, any time-of-day on an in-window day is fine.
        A specific date/time already claimed by another order is a
        separate, second-layer check (_check_no_overlap) - this only
        enforces which DAYS are open to begin with. A missing
        request_late means no upper bound (fieldservice normally always
        computes one, but don't assume)."""
        self.ensure_one()
        if not self.date_from or not self.date_to:
            return None
        early, late = self.order_id.request_early, self.order_id.request_late
        if not early:
            return None
        early_date, late_date = self._local_request_window_dates()
        if self.date_from >= early_date and (not late_date or self.date_to <= late_date):
            return None
        return early, late

    @api.constrains("date_from", "date_to")
    def _check_within_request_window(self):
        for slot in self:
            found = slot._find_out_of_window()
            if not found:
                continue
            early, late = found
            raise ValidationError(
                _(
                    "This slot's dates must stay within the order's "
                    "requested window (%(early)s - %(late)s).",
                    early=early,
                    late=late or _("no limit"),
                )
            )

    def _find_overlap(self):
        """Return (other_slot, is_same_order, other_start, other_end) for
        the first overlapping slot found - same order checked first, then
        other orders for the same worker (person_id) - idle slots never
        count as a conflict. Returns None if there's no overlap. Shared by
        the hard constraint below and the onchange warning, so both use
        the exact same definition of "overlap".

        The same-order check only compares slots that share the SAME
        worker - an order can now have several Request Workers, each with
        their own independent sub-slots, so two DIFFERENT workers legitimately
        overlapping in time on the same order is not a conflict at all (it's
        two people working in parallel). A slot with no worker chosen yet
        skips this check entirely - there's nothing to compare identity
        against."""
        self.ensure_one()
        start, end = self._get_datetime_range()
        if not start or not end:
            return None
        if self.person_id:
            for other in self.order_id.schedule_slot_ids - self:
                if other.person_id != self.person_id:
                    continue
                other_start, other_end = other._get_datetime_range()
                if other_start and other_end and start < other_end and other_start < end:
                    return other, True, other_start, other_end

            current_id = self._origin.id if self._origin else self.id
            # sudo(): workers are a pool shared across all 7 companies, so a
            # double-booking on an order belonging to a company the current
            # user doesn't have active in the company switcher must still be
            # caught. fsm.order carries a global multi-company ir.rule, so
            # without sudo this search would silently miss those orders
            # (false negative), and even when found via search alone,
            # reading `other.order_id.name` below would raise AccessError
            # instead of surfacing the intended ValidationError message.
            cross_order_others = self.env["bs.fsm.order.schedule.slot"].sudo().search(
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

    @api.onchange(
        "duration_type", "date_from", "date_to", "time_from", "time_to", "person_id"
    )
    def _onchange_check_no_overlap_warning(self):
        # @api.constrains only runs on actual Save (write/create) - this
        # gives the same feedback immediately while still editing in the
        # browser, as a non-blocking heads up. The real enforcement remains
        # _check_within_request_window/_check_no_overlap above. Checked
        # first since staying in the requested window is the more
        # fundamental constraint (only one warning can show at a time -
        # multiple onchange methods on the same trigger would just
        # overwrite each other's, so both checks live in one method).
        out_of_window = self._find_out_of_window()
        if out_of_window:
            early, late = out_of_window
            return {
                "warning": {
                    "title": _("Outside Requested Window"),
                    "message": _(
                        "This slot's dates must stay within the order's "
                        "requested window (%(early)s - %(late)s). "
                        "This will be blocked when you Save.",
                        early=early,
                        late=late or _("no limit"),
                    ),
                }
            }
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
