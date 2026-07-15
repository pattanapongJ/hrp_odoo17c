/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Per-day status for one technician (fsm.person), sourced entirely from
// bs.fsm.order.schedule.slot.slot_type - there's no separate "day status"
// model, this widget buckets each slot's date_from-date_to range by ISO
// date and colors the day by its EXACT slot_type value (not a grouped
// busy/available/pending simplification), so the Legend can just mirror
// the model's own Selection one-for-one. A day with no slot at all shows
// no entry. When more than one slot covers the same day (shouldn't
// normally happen given the overlap constraint, but a day can still
// legitimately be split across back-to-back slots of different types),
// SLOT_TYPE_PRIORITY decides which one "wins" the cell.
const SLOT_TYPE_COLORS = {
    travel_disassemble: "#8ecae6",
    idle: "#a8e6cf",
    travel_assemble: "#cdb4db",
    pending_delivery: "#ffe08a",
    other: "#f4a688",
};
const DEFAULT_COLOR = "#ced4da";
const SLOT_TYPE_PRIORITY = {
    pending_delivery: 3,
    travel_disassemble: 2,
    travel_assemble: 2,
    other: 2,
    idle: 1,
};

export class WorkerCalendar extends Component {
    static template = "bs_fieldservice.WorkerCalendar";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            persons: [],
            personId: false,
            month: luxon.DateTime.local().startOf("month"),
            daysByDate: {},
            legend: [],
        });
        onWillStart(async () => {
            const [persons, slotTypeField] = await Promise.all([
                this.orm.searchRead("fsm.person", [], ["id", "name"]),
                this.orm.call("bs.fsm.order.schedule.slot", "fields_get", [], {
                    allfields: ["slot_type"],
                    attributes: ["selection"],
                }),
            ]);
            this.state.persons = persons;
            if (persons.length) {
                this.state.personId = persons[0].id;
            }
            // Built straight from the model's own Selection, in the same
            // order - the Legend always matches slot_type exactly, even if
            // its options change later.
            this.state.legend = slotTypeField.slot_type.selection.map(
                ([value, label]) => ({
                    value,
                    label,
                    color: SLOT_TYPE_COLORS[value] || DEFAULT_COLOR,
                })
            );
            await this.loadMonth();
        });
    }

    get monthLabel() {
        return this.state.month.setLocale("th").toFormat("LLLL yyyy");
    }

    get weeks() {
        const firstOfMonth = this.state.month;
        // luxon weekday: Mon=1..Sun=7 - shift so the grid starts on Sunday.
        const gridStart = firstOfMonth.minus({ days: firstOfMonth.weekday % 7 });
        const days = [];
        for (let i = 0; i < 42; i++) {
            const date = gridStart.plus({ days: i });
            const iso = date.toISODate();
            days.push({
                iso,
                day: date.day,
                inMonth: date.month === firstOfMonth.month,
                isToday: areSameDay(date, luxon.DateTime.local()),
                entry: this.state.daysByDate[iso] || null,
            });
        }
        const weeks = [];
        for (let i = 0; i < days.length; i += 7) {
            weeks.push(days.slice(i, i + 7));
        }
        // Trailing weeks that are entirely outside the current month add
        // nothing useful - drop them so short months don't show a blank row.
        while (weeks.length && weeks[weeks.length - 1].every((d) => !d.inMonth)) {
            weeks.pop();
        }
        return weeks;
    }

    async onPersonChange(ev) {
        this.state.personId = Number(ev.target.value) || false;
        await this.loadMonth();
    }

    async goToday() {
        this.state.month = luxon.DateTime.local().startOf("month");
        await this.loadMonth();
    }

    async prevMonth() {
        this.state.month = this.state.month.minus({ months: 1 });
        await this.loadMonth();
    }

    async nextMonth() {
        this.state.month = this.state.month.plus({ months: 1 });
        await this.loadMonth();
    }

    openOrder(orderId) {
        if (!orderId) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "fsm.order",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async loadMonth() {
        if (!this.state.personId) {
            this.state.daysByDate = {};
            return;
        }
        const monthStart = this.state.month;
        const monthEnd = monthStart.endOf("month");
        const slots = await this.orm.searchRead(
            "bs.fsm.order.schedule.slot",
            [
                ["person_id", "=", this.state.personId],
                ["date_from", "<=", monthEnd.toISODate()],
                ["date_to", ">=", monthStart.toISODate()],
            ],
            ["date_from", "date_to", "slot_type", "duration_type", "order_id"]
        );
        const legendByValue = Object.fromEntries(
            this.state.legend.map((entry) => [entry.value, entry])
        );
        const daysByDate = {};
        for (const slot of slots) {
            if (!slot.date_from) {
                continue;
            }
            const legendEntry = legendByValue[slot.slot_type];
            const orderId = slot.order_id ? slot.order_id[0] : false;
            const orderName = slot.order_id ? slot.order_id[1] : "";
            const label = legendEntry ? legendEntry.label : slot.slot_type;
            const isFullDay = slot.duration_type === "full_day";
            let current = luxon.DateTime.fromISO(slot.date_from);
            const end = slot.date_to ? luxon.DateTime.fromISO(slot.date_to) : current;
            while (current <= end) {
                const iso = current.toISODate();
                const existing = daysByDate[iso];
                const priority = SLOT_TYPE_PRIORITY[slot.slot_type] || 2;
                if (!existing || priority > existing.priority) {
                    daysByDate[iso] = {
                        color: legendEntry ? legendEntry.color : DEFAULT_COLOR,
                        label: orderName ? `${orderName} - ${label}` : label,
                        orderId,
                        priority,
                        // Duration=Full day means this slot occupies the
                        // whole day - shown with a distinct border so it
                        // reads as "unavailable all day" at a glance,
                        // versus a slot only covering part of the day.
                        fullDay: isFullDay,
                    };
                }
                current = current.plus({ days: 1 });
            }
        }
        this.state.daysByDate = daysByDate;
    }
}

function areSameDay(a, b) {
    return a.hasSame(b, "day") && a.hasSame(b, "month") && a.hasSame(b, "year");
}

registry.category("actions").add("bs_fieldservice.worker_calendar", WorkerCalendar);
