from datetime import date, datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    technician_profile = fields.Selection(
        [("phe", "PHE Technician"), ("pump", "Pump Technician")],
        string="Technician Profile",
        required=True,
        default="phe",
    )
    person_id = fields.Many2one(required=True)

    # Service Request SR - header
    job_no = fields.Char(string="Job No.")
    customer_po = fields.Char(string="Customer PO")
    sr_date = fields.Date(string="Date", default=fields.Date.context_today)
    full_address = fields.Char(string="Address", compute="_compute_full_address")
    contact_person_id = fields.Many2one(
        related="location_id.contact_id", string="Contact Person"
    )
    customer_type = fields.Selection(
        [("contractor", "Contractor"), ("end_user", "End User")],
        string="Customer Type",
    )
    sr_priority = fields.Selection(
        [("urgent", "Urgent"), ("normal", "Normal"), ("visit", "Visit")],
        string="Priority",
        default="normal",
    )
    sr_planned_date = fields.Date(string="Planned Date")
    sr_completion_date = fields.Date(string="Completion Date")

    # Reason for service
    reason_external_leakage = fields.Boolean(string="External Leakage")
    reason_internal_leakage = fields.Boolean(string="Internal Leakage")
    reason_preventive_maintenance = fields.Boolean(string="Preventive Maintenance")
    reason_other = fields.Boolean(string="Other")
    reason_other_note = fields.Char(string="Other, specify")

    # Scope of service
    scope_dismantle_unit = fields.Boolean(string="Dismantle Unit")
    scope_pickup_plate_pack = fields.Boolean(string="Pickup plate pack")
    scope_service_report_required = fields.Boolean(string="Service Report required")
    scope_transport_to_workshop = fields.Boolean(
        string="Transport PHE unit to workshop"
    )
    scope_onsite_service = fields.Boolean(string="On-site service")

    # Equipment line (PHE Technician)
    phe_line_ids = fields.One2many(
        "bs.fsm.order.phe.line", "order_id", string="Equipment Line"
    )

    # Equipment line (Pump Technician)
    pump_line_ids = fields.One2many(
        "bs.fsm.order.pump.line", "order_id", string="Equipment Line"
    )

    # Critical remarks
    remark_correction_work = fields.Boolean(string="Correction work")
    remark_messenger_pickup = fields.Boolean(string="Messenger pick-up")
    remark_glueless_work = fields.Boolean(string="Glueless work")
    remark_crane_work = fields.Boolean(string="Crane work")
    remark_explosion_proof_area = fields.Boolean(string="Explosion proof area")
    remark_safety_training_required = fields.Boolean(string="Safety training required")
    critical_remarks_note = fields.Text(string="Critical remarks / notes")

    # Spare parts from
    plate_from = fields.Selection(
        [("wh", "WH (Warehouse)"), ("cus", "CUS (Customer)")],
        string="Plate from",
    )
    plate_qty = fields.Integer(string="Plate Qty")
    gasket_from_wh = fields.Boolean(string="Gasket from WH (บริษัทเบิก)")
    gasket_from_cus = fields.Boolean(string="Gasket from CUS (ของลูกค้า)")
    gasket_qty = fields.Integer(string="Gasket Qty")

    check_sheet = fields.Html(string="Check Sheet")
    service_report = fields.Html(string="Service Report")

    # Planning - request teams / workers / schedule sub-slots
    assigned_team_ids = fields.Many2many(
        "fsm.team",
        "bs_fsm_order_assigned_team_rel",
        "order_id",
        "team_id",
        string="Request Teams",
    )
    worker_line_ids = fields.One2many(
        "bs.fsm.order.worker.line",
        "order_id",
        string="Request Workers",
        compute="_compute_worker_line_ids",
        store=True,
    )
    schedule_slot_ids = fields.One2many(
        "bs.fsm.order.schedule.slot", "order_id", string="Schedule Sub-slots"
    )
    worker_status_log_ids = fields.One2many(
        "bs.fsm.order.worker.status.log", "order_id", string="Worker Status Log"
    )
    schedule_slot_count = fields.Integer(
        string="Sub-slot Count", compute="_compute_schedule_slot_count"
    )
    actual_work_summary = fields.Char(
        string="Actual Work Summary",
        compute="_compute_actual_work_summary",
        store=True,
    )
    worker_busy_dates_summary = fields.Char(
        string="Worker's Other Bookings",
        compute="_compute_worker_busy_dates_summary",
    )

    # Equipments tab
    equipment_line_ids = fields.One2many(
        "bs.fsm.order.equipment.line", "order_id", string="Equipment Lines"
    )
    equipment_total_count = fields.Integer(
        string="Equipment Total", compute="_compute_equipment_counts"
    )
    equipment_withdrawn_count = fields.Integer(
        string="Equipment Withdrawn", compute="_compute_equipment_counts"
    )
    equipment_returned_count = fields.Integer(
        string="Equipment Returned", compute="_compute_equipment_counts"
    )
    equipment_overdue_count = fields.Integer(
        string="Equipment Overdue", compute="_compute_equipment_counts"
    )

    # Check Sheet tab - one check sheet per equipment/worker line (PHE or
    # Pump), kept 1:1 in sync with phe_line_ids/pump_line_ids by
    # _sync_check_sheet_lines(). Each line is edited in its own popup form.
    check_sheet_line_ids = fields.One2many(
        "bs.fsm.order.check_sheet.line", "order_id", string="Check Sheets"
    )

    # Service Report - header
    sr_report_no = fields.Char(string="Report No.", copy=False)
    sr_report_date = fields.Date(string="Date", default=fields.Date.context_today)
    sr_customer_id = fields.Many2one("res.partner", string="Customer")

    # Service Report - equipment summary: PHE-only, a read-only view
    # auto-grouped by Model from check_sheet_line_ids (mirrors Request
    # Workers in Planning), with Result reflecting Confirm status. Pump
    # has no Check Sheet, so its Equipment Summary instead shows
    # pump_line_ids directly (ungrouped, read-only) in the view.
    check_sheet_summary_line_ids = fields.One2many(
        "bs.fsm.order.check_sheet_summary.line",
        "order_id",
        string="Equipment Summary",
        compute="_compute_check_sheet_summary_line_ids",
        store=True,
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

    @api.depends(
        "equipment_line_ids.status",
        "equipment_line_ids.qty_total",
        "equipment_line_ids.qty_withdrawn",
        "equipment_line_ids.qty_returned",
    )
    def _compute_equipment_counts(self):
        for order in self:
            lines = order.equipment_line_ids
            order.equipment_total_count = sum(lines.mapped("qty_total"))
            order.equipment_withdrawn_count = sum(
                line.qty_withdrawn - line.qty_returned for line in lines
            )
            order.equipment_returned_count = sum(lines.mapped("qty_returned"))
            order.equipment_overdue_count = sum(
                line.qty_withdrawn - line.qty_returned
                for line in lines.filtered(lambda ln: ln.status == "overdue")
            )

    @api.onchange("technician_profile")
    def _onchange_technician_profile(self):
        self.phe_line_ids = [(5, 0, 0)]
        self.pump_line_ids = [(5, 0, 0)]
        self.assigned_team_ids = [(5, 0, 0)]
        # Supervisor's Comment is still PHE-only - once the profile changes
        # (in either direction), its data no longer applies, so wipe it
        # clean. Cleaning/PT Test Results/Re-gasket are shown for both
        # profiles now, so their data is kept across a profile switch.
        if self.sr_supervisor_comment:
            self.sr_supervisor_comment = False
        self._sync_check_sheet_lines()

    @api.onchange("phe_line_ids", "pump_line_ids")
    def _onchange_equipment_lines_sync_check_sheet(self):
        self._sync_check_sheet_lines()

    def _sync_check_sheet_lines(self):
        """Keep check_sheet_line_ids 1:1 with the Assigned Worker equipment
        table (phe_line_ids for PHE orders; Check Sheet doesn't apply to
        Pump). Only adds/removes lines at the margin so existing check
        sheet data is never overwritten by an unrelated equipment edit."""
        self.ensure_one()
        if self.technician_profile != "phe":
            if self.check_sheet_line_ids:
                self.check_sheet_line_ids = [(5, 0, 0)]
            return
        target_count = len(self.phe_line_ids)
        current = self.check_sheet_line_ids
        current_count = len(current)
        if current_count < target_count:
            partner_id = self.location_id.partner_id.id if self.location_id else False
            place = self.location_id.name if self.location_id else False
            self.check_sheet_line_ids = [
                (
                    0,
                    0,
                    {
                        "phe_line_id": line.id,
                        "customer_id": partner_id,
                        "place": place,
                    },
                )
                for line in self.phe_line_ids[current_count:]
            ]
        elif current_count > target_count:
            # Never auto-remove a confirmed check sheet: only trim draft
            # lines from the tail, so removing an unrelated equipment row
            # can't silently wipe out already-confirmed inspection data.
            removable = current[target_count:].filtered(
                lambda rec: rec.state != "confirmed"
            )
            if removable:
                self.check_sheet_line_ids = [(2, rec.id, 0) for rec in removable]
        # model_id/no_plate are related="phe_line_id.xxx", which the web
        # client doesn't reliably re-render live across two sibling
        # one2manys during onchange (it's only guaranteed correct after
        # save/reload). Force-refresh them here so the Check Sheet tab
        # reflects an Assigned Worker change immediately, without a save.
        for cs_line in self.check_sheet_line_ids:
            if not cs_line.phe_line_id:
                continue
            source_model_id = cs_line.phe_line_id.model_id
            if cs_line.model_id != source_model_id:
                cs_line.model_id = source_model_id
            source_no_plate = cs_line.phe_line_id.no_plate
            if cs_line.no_plate != source_no_plate:
                cs_line.no_plate = source_no_plate

    @api.depends(
        "technician_profile",
        "check_sheet_line_ids.model_id",
        "check_sheet_line_ids.maker",
        "check_sheet_line_ids.state",
    )
    def _compute_check_sheet_summary_line_ids(self):
        """Service Report's Equipment Summary (PHE only): one row per
        distinct Model found in check_sheet_line_ids, with a count of how
        many share it and Result reflecting Confirm status. Fully derived -
        never manually added/edited. Pump has no Check Sheet, so its
        Equipment Summary is shown directly from pump_line_ids in the view
        instead of going through this grouped model."""
        for order in self:
            if order.technician_profile != "phe":
                if order.check_sheet_summary_line_ids:
                    order.check_sheet_summary_line_ids = [(5, 0, 0)]
                continue
            groups = {}
            for line in order.check_sheet_line_ids:
                groups.setdefault(line.model_id, []).append(line)
            commands = [(5, 0, 0)]
            for model, lines in groups.items():
                all_confirmed = all(line.state == "confirmed" for line in lines)
                commands.append(
                    (
                        0,
                        0,
                        {
                            "model_id": model.id,
                            "maker": lines[0].maker,
                            "check_sheet_count": len(lines),
                            "result": "pass" if all_confirmed else "pending",
                        },
                    )
                )
            order.check_sheet_summary_line_ids = commands

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

    @api.onchange("location_id")
    def _onchange_location_id_check_sheet(self):
        if self.location_id:
            self.sr_customer_id = self.location_id.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sr_report_no"):
                vals["sr_report_no"] = self.env["ir.sequence"].next_by_code(
                    "bs.fsm.order.service_report"
                )
        return super().create(vals_list)

    def _calc_scheduled_dates(self, vals):
        # Core recalculates scheduled_date_start from
        # (scheduled_date_end - duration) when only the end date is written.
        # Editing Scheduled End manually should never move Scheduled Start -
        # pin it to its current value so core just recomputes the duration.
        if (
            vals.get("scheduled_date_end")
            and not vals.get("scheduled_date_start")
            and len(self) == 1
            and self.scheduled_date_start
        ):
            vals["scheduled_date_start"] = self.scheduled_date_start
        return super()._calc_scheduled_dates(vals)

    @api.onchange("scheduled_date_end")
    def onchange_scheduled_date_end(self):
        # Core's onchange moves Scheduled Start to (End - duration) live in
        # the browser as soon as End is typed, before the record is even
        # saved. Editing End must never move Start - recompute the
        # duration instead, mirroring the server-side write() fix above.
        if self.scheduled_date_start and self.scheduled_date_end:
            delta = self.scheduled_date_end - self.scheduled_date_start
            self.scheduled_duration = delta.total_seconds() / 3600

    @api.constrains("scheduled_date_start", "scheduled_date_end")
    def _check_scheduled_dates_order(self):
        for order in self:
            if (
                order.scheduled_date_start
                and order.scheduled_date_end
                and order.scheduled_date_end < order.scheduled_date_start
            ):
                raise ValidationError(
                    _("Scheduled End must not be earlier than Scheduled Start.")
                )

    @api.depends(
        "person_id",
        "scheduled_date_start",
        "scheduled_date_end",
        "schedule_slot_ids.date_from",
        "schedule_slot_ids.date_to",
        "schedule_slot_ids.slot_type",
    )
    def _compute_worker_line_ids(self):
        for order in self:
            existing = order.worker_line_ids
            if not order.person_id:
                order.worker_line_ids = [(5, 0, 0)]
                continue
            new_status = order._get_worker_conflict_status(order.person_id)
            if existing and existing.person_id == order.person_id:
                # Same worker as before - update the existing row in place
                # (instead of delete+recreate) so a status flip can be
                # logged as an actual FROM -> TO transition.
                line = existing[0]
                if line.status != new_status:
                    order._log_worker_status_change(
                        order.person_id, line.status, new_status
                    )
                order.worker_line_ids = [(1, line.id, {"status": new_status})]
            else:
                order._log_worker_status_change(order.person_id, False, new_status)
                order.worker_line_ids = [
                    (5, 0, 0),
                    (0, 0, {"person_id": order.person_id.id, "status": new_status}),
                ]

    def _log_worker_status_change(self, person, status_from, status_to):
        self.ensure_one()
        if not isinstance(self.id, int):
            # New/unsaved order (NewId) - nothing persisted to log against yet.
            return
        self.env["bs.fsm.order.worker.status.log"].sudo().create(
            {
                "order_id": self.id,
                "person_id": person.id,
                "status_from": status_from,
                "status_to": status_to,
            }
        )

    def _order_covers_today(self):
        """Whether today falls within this order's own relevant window -
        either one of its schedule sub-slots (any type) or its scheduled
        start/end. An order that has nothing to do with today has no
        meaningful "is the worker free today" question to answer."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        for slot in self.schedule_slot_ids:
            if slot.date_from and slot.date_to and slot.date_from <= today <= slot.date_to:
                return True
        if self.scheduled_date_start and self.scheduled_date_end:
            return (
                self.scheduled_date_start.date()
                <= today
                <= self.scheduled_date_end.date()
            )
        return False

    def _get_worker_conflict_status(self, person):
        """Conflict if `person` has any active (non-idle) commitment - from
        ANY order, including this one - that covers TODAY. Available means
        the worker is free today (idle, or no active booking at all), so
        they could be picked up for another job.

        Only evaluated when THIS order's own window includes today - an
        order scheduled entirely in the past or future has no stake in
        today's occupancy, so it just shows available."""
        self.ensure_one()
        if not self._order_covers_today():
            return "available"
        today = fields.Date.context_today(self)

        busy_via_slot = self.env["bs.fsm.order.schedule.slot"].search_count(
            [
                ("person_id", "=", person.id),
                ("slot_type", "!=", "idle"),
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ]
        )
        if busy_via_slot:
            return "conflict"

        # Orders with no sub-slots at all fall back to their own scheduled
        # window - still counts as the worker being busy that day.
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        busy_via_order = self.env["fsm.order"].search_count(
            [
                ("person_id", "=", person.id),
                ("schedule_slot_ids", "=", False),
                ("scheduled_date_start", "<=", today_end),
                ("scheduled_date_end", ">=", today_start),
            ]
        )
        return "conflict" if busy_via_order else "available"

    @api.model
    def _cron_recompute_worker_status(self):
        """Runs hourly - Conflict/Available depends on today's date, which
        isn't a trackable ORM dependency, so a stored order can go stale
        (e.g. a past conflict clears at midnight) without anyone editing it.
        This forces a fresh recompute for all open orders with a worker."""
        orders = self.search(
            [("stage_id.is_closed", "=", False), ("person_id", "!=", False)]
        )
        if orders:
            orders._compute_worker_line_ids()

    @api.constrains("assigned_team_ids", "technician_profile")
    def _check_assigned_team_side(self):
        for order in self:
            mismatched = order.assigned_team_ids.filtered(
                lambda t: t.team_side and t.team_side != order.technician_profile
            )
            if mismatched:
                raise ValidationError(
                    _(
                        "Request Teams must match the order's Technician "
                        "Profile (%(profile)s). Invalid team(s): %(teams)s",
                        profile=order.technician_profile,
                        teams=", ".join(mismatched.mapped("name")),
                    )
                )

    @api.depends("schedule_slot_ids")
    def _compute_schedule_slot_count(self):
        for order in self:
            order.schedule_slot_count = len(order.schedule_slot_ids)

    @api.depends(
        "schedule_slot_ids.slot_type",
        "schedule_slot_ids.date_from",
        "schedule_slot_ids.date_to",
    )
    def _compute_actual_work_summary(self):
        for order in self:
            order.actual_work_summary = order._build_actual_work_summary()

    @api.depends("person_id")
    def _compute_worker_busy_dates_summary(self):
        # Not stored, and can't meaningfully @api.depends on OTHER orders'
        # schedule slots - this is a best-effort, read-time convenience
        # summary (see the calendar day-graying in schedule_slot_date_field.js
        # for the real-time equivalent, and _check_no_overlap for the
        # authoritative server-side check), not a hard data-integrity field.
        for order in self:
            if not order.person_id:
                order.worker_busy_dates_summary = False
                continue
            current_id = order._origin.id if order._origin else order.id
            other_slots = self.env["bs.fsm.order.schedule.slot"].search(
                [
                    ("person_id", "=", order.person_id.id),
                    (
                        "order_id",
                        "!=",
                        current_id if isinstance(current_id, int) else 0,
                    ),
                    ("slot_type", "!=", "idle"),
                ]
            )
            if not other_slots:
                order.worker_busy_dates_summary = False
                continue
            parts = []
            # date_from can be unset on a still-incomplete slot (e.g. a row
            # just added elsewhere, no date picked yet) - sorted() would
            # otherwise crash comparing False to a real date.
            for slot in other_slots.sorted(lambda s: s.date_from or date.min):
                date_label = (
                    slot.date_from.strftime("%d/%m/%Y") if slot.date_from else "?"
                )
                if slot.date_to and slot.date_to != slot.date_from:
                    date_label += " - %s" % slot.date_to.strftime("%d/%m/%Y")
                time_label = "%s-%s" % (
                    self._format_float_time(slot.time_from),
                    self._format_float_time(slot.time_to),
                )
                parts.append(
                    "%s (%s %s)" % (slot.order_id.name, date_label, time_label)
                )
            order.worker_busy_dates_summary = ", ".join(parts)

    @api.model
    def _format_float_time(self, value):
        hours = int(value or 0.0)
        minutes = round((value or 0.0) % 1 * 60)
        if minutes == 60:
            hours += 1
            minutes = 0
        return "%02d:%02d" % (hours, minutes)

    def _build_actual_work_summary(self):
        self.ensure_one()
        active_slots = self.schedule_slot_ids.filtered(
            lambda s: s.slot_type != "idle"
        )
        idle_slots = self.schedule_slot_ids.filtered(lambda s: s.slot_type == "idle")
        dates = set()
        for slot in active_slots:
            if slot.date_from and slot.date_to:
                current = slot.date_from
                while current <= slot.date_to:
                    dates.add(current)
                    current += timedelta(days=1)
            elif slot.date_from:
                dates.add(slot.date_from)
        summary = _("%(count)d day(s)", count=len(dates))
        if dates:
            summary += " (%s)" % ", ".join(d.strftime("%d/%m") for d in sorted(dates))
        idle_labels = []
        for slot in idle_slots:
            if slot.date_from and slot.date_to:
                idle_labels.append(
                    "%s-%s"
                    % (slot.date_from.strftime("%d"), slot.date_to.strftime("%d"))
                )
            elif slot.date_from:
                idle_labels.append(slot.date_from.strftime("%d"))
        if idle_labels:
            summary += _(" - excluding idle %s") % ", ".join(idle_labels)
        return summary

    @api.depends(
        "street", "street2", "city", "state_name", "zip", "country_name"
    )
    def _compute_full_address(self):
        for order in self:
            parts = [
                order.street,
                order.street2,
                order.city,
                order.state_name,
                order.zip,
                order.country_name,
            ]
            order.full_address = ", ".join(p for p in parts if p)
