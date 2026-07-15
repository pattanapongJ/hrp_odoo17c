/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STATUS_LABELS = {
    not_withdrawn: "ยังไม่เบิก",
    in_use: "ใช้อยู่",
    partial: "บางส่วน",
    overdue: "ค้างคืน",
    returned: "คืนแล้ว",
};

const RETURN_STATUS_LABELS = {
    not_withdrawn: "ยังไม่เบิก",
    not_returned: "ยังไม่คืน",
    partial: "บางส่วน",
    overdue: "ค้างคืน",
    complete: "ครบ",
};

function datetimeToInputValue(value) {
    // record.data holds Datetime fields as Luxon DateTime objects already
    // deserialized to the local zone - just format for the HTML input.
    return value ? value.toFormat("yyyy-MM-dd'T'HH:mm") : "";
}

function inputValueToDatetime(value) {
    // record.update() re-serializes Datetime fields by calling
    // value.setZone("utc"), so it must be given back a Luxon DateTime
    // object, not a plain string.
    return value ? luxon.DateTime.fromISO(value) : false;
}

export class EquipmentLineTable extends Component {
    static template = "bs_fieldservice.EquipmentLineTable";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ equipmentOptions: [] });
        onWillStart(async () => {
            this.state.equipmentOptions = await this.orm.searchRead(
                "fsm.equipment",
                [],
                ["id", "name"]
            );
        });
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    get overdueLines() {
        return this.list.records.filter((r) => r.data.status === "overdue");
    }

    statusLabel(status) {
        return STATUS_LABELS[status] || status;
    }

    returnStatusLabel(status) {
        return RETURN_STATUS_LABELS[status] || status;
    }

    progressPct(record) {
        const total = record.data.qty_total;
        if (!total) {
            return 0;
        }
        return Math.min(100, (record.data.qty_withdrawn / total) * 100);
    }

    formatDateInput(record, fieldName) {
        return datetimeToInputValue(record.data[fieldName]);
    }

    async addLine() {
        await this.list.addNewRecord({ position: "bottom" });
    }

    async removeLine(record) {
        await this.list.delete(record);
    }

    async onEquipmentChange(record, ev) {
        const id = ev.target.value ? Number(ev.target.value) : false;
        if (!id) {
            await record.update({ equipment_id: false });
            return;
        }
        const opt = this.state.equipmentOptions.find((o) => o.id === id);
        await record.update({ equipment_id: [id, opt.name] });
    }

    onDateChange(record, fieldName, ev) {
        record.update({ [fieldName]: inputValueToDatetime(ev.target.value) });
    }

    onTextChange(record, fieldName, ev) {
        record.update({ [fieldName]: ev.target.value });
    }

    onNumberChange(record, fieldName, ev) {
        const value = ev.target.value === "" ? 0 : Number(ev.target.value);
        record.update({ [fieldName]: value });
    }
}

export const equipmentLineTable = {
    component: EquipmentLineTable,
    supportedTypes: ["one2many"],
};

registry.category("fields").add("bs_equipment_line_table", equipmentLineTable);
