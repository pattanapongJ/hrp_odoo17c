/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class PheLineTable extends Component {
    static template = "bs_fieldservice.PheLineTable";
    static props = { ...standardFieldProps };

    get list() {
        return this.props.record.data[this.props.name];
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
