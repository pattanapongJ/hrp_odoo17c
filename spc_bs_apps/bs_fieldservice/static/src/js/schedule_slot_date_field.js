/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { areDatesEqual } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {
    DateTimeField,
    dateField,
} from "@web/views/fields/datetime/datetime_field";

// Schedule Sub-slot's date_from/date_to, for the SAME worker (person_id)
// on ANOTHER order:
// - A "Full day" sub-slot occupies the entire day (00:00-24:00), so ANY
//   other booking that date is guaranteed to conflict - those dates are
//   hard-blocked (isDateValid) and shown in red.
// - A "Custom" (partial-time) sub-slot only occupies part of the day (e.g.
//   order 1 books 08:00-12:00, order 2 can still pick the same date for
//   13:00-18:00) - those dates are only soft-highlighted, not blocked;
//   only the actual chosen time can tell whether it truly conflicts, which
//   is what the model's _check_no_overlap constraint decides for real
//   (see fsm_order_schedule_slot.py).
//
// DateTimeField's own setup() computes picker props in a closure that
// isn't otherwise overridable, so this re-implements it with isDateValid/
// dayCellClass added - keep this in sync if core's datetime_field.js
// setup() changes.
export class ScheduleSlotDateField extends DateTimeField {
    setup() {
        this.orm = useService("orm");
        this.fullyBookedDates = new Set();
        this.partiallyBookedDates = new Set();

        const getPickerProps = () => {
            const value = this.getRecordValue();
            const pickerProps = {
                value,
                type: this.field.type,
                range: this.isRange(value),
                isDateValid: (day) => !this.fullyBookedDates.has(day.toISODate()),
                dayCellClass: (day) => {
                    const iso = day.toISODate();
                    if (this.fullyBookedDates.has(iso)) {
                        return "o_bs_slot_busy_day_full";
                    }
                    return this.partiallyBookedDates.has(iso) ? "o_bs_slot_busy_day" : "";
                },
            };
            if (this.props.maxDate) {
                pickerProps.maxDate = this.parseLimitDate(this.props.maxDate);
            }
            if (this.props.minDate) {
                pickerProps.minDate = this.parseLimitDate(this.props.minDate);
            }
            if (!isNaN(this.props.rounding)) {
                pickerProps.rounding = this.props.rounding;
            }
            return pickerProps;
        };

        const dateTimePicker = useDateTimePicker({
            target: "root",
            get pickerProps() {
                return getPickerProps();
            },
            onChange: () => {
                this.state.range = this.isRange(this.state.value);
            },
            onApply: () => {
                const toUpdate = {};
                if (Array.isArray(this.state.value)) {
                    [toUpdate[this.startDateField], toUpdate[this.endDateField]] =
                        this.state.value;
                } else {
                    toUpdate[this.props.name] = this.state.value;
                }
                if (!this.startDateField || !this.endDateField) {
                    for (const fieldName in toUpdate) {
                        if (
                            areDatesEqual(
                                toUpdate[fieldName],
                                this.props.record.data[fieldName]
                            )
                        ) {
                            delete toUpdate[fieldName];
                        }
                    }
                } else if (
                    areDatesEqual(
                        toUpdate[this.startDateField],
                        this.props.record.data[this.startDateField]
                    ) &&
                    areDatesEqual(
                        toUpdate[this.endDateField],
                        this.props.record.data[this.endDateField]
                    )
                ) {
                    delete toUpdate[this.startDateField];
                    delete toUpdate[this.endDateField];
                }
                if (Object.keys(toUpdate).length) {
                    this.props.record.update(toUpdate);
                }
            },
        });
        this.state = useState(dateTimePicker.state);
        this.openPicker = dateTimePicker.open;

        onWillStart(() => this.loadBusyDates());
        onWillUpdateProps(() => this.loadBusyDates());
    }

    get currentPersonId() {
        const value = this.props.record.data.person_id;
        return Array.isArray(value) ? value[0] : value && value.id;
    }

    async loadBusyDates() {
        const personId = this.currentPersonId;
        if (!personId) {
            this.fullyBookedDates = new Set();
            this.partiallyBookedDates = new Set();
            return;
        }
        const domain = [
            ["person_id", "=", personId],
            ["order_id", "!=", this.props.record.data.order_id?.[0] || false],
            // idle ("ว่าง") means the worker is free during that slot - it
            // never blocks another order from booking the same date/time.
            ["slot_type", "!=", "idle"],
        ];
        const slots = await this.orm.searchRead(
            "bs.fsm.order.schedule.slot",
            domain,
            ["date_from", "date_to", "duration_type"]
        );
        const fullyBooked = new Set();
        const partiallyBooked = new Set();
        for (const slot of slots) {
            if (!slot.date_from) {
                continue;
            }
            const target = slot.duration_type === "full_day" ? fullyBooked : partiallyBooked;
            let current = luxon.DateTime.fromISO(slot.date_from);
            const end = slot.date_to ? luxon.DateTime.fromISO(slot.date_to) : current;
            while (current <= end) {
                target.add(current.toISODate());
                current = current.plus({ days: 1 });
            }
        }
        this.fullyBookedDates = fullyBooked;
        this.partiallyBookedDates = partiallyBooked;
    }
}

export const scheduleSlotDateField = {
    ...dateField,
    component: ScheduleSlotDateField,
    displayName: _t("Schedule Slot Date"),
};

registry.category("fields").add("bs_schedule_slot_date", scheduleSlotDateField);
