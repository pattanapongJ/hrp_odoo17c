/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class ServiceReportTable extends Component {
    static template = "bs_fieldservice.ServiceReportTable";
    static props = { ...standardFieldProps };

    get list() {
        return this.props.record.data[this.props.name];
    }

    get profile() {
        return this.props.record.data.technician_profile;
    }

    async addLine() {
        await this.list.addNewRecord({ position: "bottom" });
    }

    async removeLine(record) {
        await this.list.delete(record);
    }

    onTextChange(record, fieldName, ev) {
        record.update({ [fieldName]: ev.target.value });
    }

    onCheckChange(record, fieldName, ev) {
        record.update({ [fieldName]: ev.target.checked });
    }

    onSelectChange(record, fieldName, ev) {
        record.update({ [fieldName]: ev.target.value || false });
    }
}

export const serviceReportTable = {
    component: ServiceReportTable,
    supportedTypes: ["one2many"],
};

registry.category("fields").add("bs_service_report_table", serviceReportTable);
