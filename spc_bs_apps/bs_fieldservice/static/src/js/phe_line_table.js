/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class PheLineTable extends Component {
    static template = "bs_fieldservice.PheLineTable";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ modelOptions: [] });
        onWillStart(async () => {
            this.state.modelOptions = await this.orm.searchRead(
                "bs.equipment.model",
                [],
                ["id", "code", "brand"]
            );
        });
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    // The Check Sheet tab shows one line per Assigned Worker (phe_line_ids)
    // row, matched 1:1 by position.
    getSiblingCheckSheetRecord(pheRecord) {
        const csField = this.props.record.data.check_sheet_line_ids;
        if (!csField) {
            return undefined;
        }
        const idx = this.list.records.findIndex((r) => r.id === pheRecord.id);
        return csField.records[idx];
    }

    // model_id/no_plate there are related="phe_line_id.xxx", which the web
    // client doesn't reliably re-render live across two sibling one2manys
    // during onchange - so push model_id/no_plate edits straight into the
    // sibling check_sheet_line record here for instant feedback, instead of
    // waiting on an onchange round-trip.
    async syncCheckSheetSibling(pheRecord, fieldName, value) {
        const csRecord = this.getSiblingCheckSheetRecord(pheRecord);
        if (csRecord) {
            await csRecord.update({ [fieldName]: value });
        }
    }

    async onModelChange(record, ev) {
        const id = ev.target.value ? Number(ev.target.value) : false;
        let modelValue = false;
        let opt;
        if (id) {
            opt = this.state.modelOptions.find((o) => o.id === id);
            modelValue = [id, opt.code];
        }
        const updates = { model_id: modelValue };
        // Auto-fill Brand from the selected Model's master data, when set.
        if (opt && opt.brand) {
            updates.brand = opt.brand;
        }
        await record.update(updates);
        await this.syncCheckSheetSibling(record, "model_id", modelValue);
    }

    async addLine() {
        await this.list.addNewRecord({ position: "bottom" });
    }

    async removeLine(record) {
        const csRecord = this.getSiblingCheckSheetRecord(record);
        if (csRecord && csRecord.data.state === "confirmed") {
            this.notification.add(
                "Cannot remove this line: its Check Sheet has already been " +
                    "confirmed. Ask a manager to Reset to Draft first.",
                { type: "danger" }
            );
            return;
        }
        await this.list.delete(record);
    }

    async updateField(record, fieldName, value) {
        await record.update({ [fieldName]: value });
        if (fieldName === "no_plate") {
            await this.syncCheckSheetSibling(record, "no_plate", value);
        }
    }

    onTextChange(record, fieldName, ev) {
        this.updateField(record, fieldName, ev.target.value);
    }

    onCheckboxChange(record, fieldName, ev) {
        this.updateField(record, fieldName, ev.target.checked);
    }

    onNumberChange(record, fieldName, ev) {
        const value = ev.target.value === "" ? 0 : Number(ev.target.value);
        this.updateField(record, fieldName, value);
    }
}

export const pheLineTable = {
    component: PheLineTable,
    supportedTypes: ["one2many"],
};

registry.category("fields").add("bs_phe_line_table", pheLineTable);
