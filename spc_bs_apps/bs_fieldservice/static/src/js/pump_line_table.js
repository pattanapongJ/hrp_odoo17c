/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class PumpLineTable extends Component {
    static template = "bs_fieldservice.PumpLineTable";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ modelOptions: [] });
        onWillStart(async () => {
            this.state.modelOptions = await this.orm.searchRead(
                "bs.equipment.model",
                [],
                ["id", "code"]
            );
        });
    }

    get list() {
        return this.props.record.data[this.props.name];
    }

    async onModelChange(record, ev) {
        const id = ev.target.value ? Number(ev.target.value) : false;
        if (!id) {
            await record.update({ model_id: false });
            return;
        }
        const opt = this.state.modelOptions.find((o) => o.id === id);
        await record.update({ model_id: [id, opt.code] });
    }

    async addLine() {
        await this.list.addNewRecord({ position: "bottom" });
    }

    async removeLine(record) {
        await this.list.delete(record);
    }

    async updateField(record, fieldName, value) {
        await record.update({ [fieldName]: value });
    }

    onTextChange(record, fieldName, ev) {
        this.updateField(record, fieldName, ev.target.value);
    }

    onNumberChange(record, fieldName, ev) {
        const value = ev.target.value === "" ? 0 : Number(ev.target.value);
        this.updateField(record, fieldName, value);
    }
}

export const pumpLineTable = {
    component: PumpLineTable,
    supportedTypes: ["one2many"],
};

registry.category("fields").add("bs_pump_line_table", pumpLineTable);
