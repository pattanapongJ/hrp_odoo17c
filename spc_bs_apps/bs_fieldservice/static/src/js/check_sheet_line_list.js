/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { useRef, useState, onMounted, onPatched } from "@odoo/owl";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

// The third-party ks_list_view_manager module patches ListRenderer to add a
// per-column "advance search" row to every table, including one2many lists
// embedded in a form like this one. Its Ks_update_advance_search_controller
// assumes this.props.list.records always exists, which isn't true in this
// list's rendering context, and throws when searching. Rather than edit
// that vendor file, guard it defensively from here instead: applied lazily
// on first mount, so it's guaranteed to run after ks_list_view_manager's
// own patch regardless of asset load order, and it's a no-op if that
// module isn't installed at all.
let ksAdvanceSearchGuarded = false;
function guardKsAdvanceSearch() {
    if (ksAdvanceSearchGuarded) {
        return;
    }
    ksAdvanceSearchGuarded = true;
    if (typeof ListRenderer.prototype.Ks_update_advance_search_controller !== "function") {
        return;
    }
    patch(ListRenderer.prototype, {
        Ks_update_advance_search_controller(ksOptions) {
            if (!this.props.list || !this.props.list.records) {
                return;
            }
            return super.Ks_update_advance_search_controller(ksOptions);
        },
    });
}

// A search row built into the Check Sheet tab's own table header (Report
// No./No.Plate/Model/Status), one <th> per real column, so it's sized and
// aligned exactly like the data below it instead of a floating bar with
// its own widths. Replaces ks_list_view_manager's per-column search for
// this list only (see bs_line_table.scss), so this tab's search doesn't
// depend on that third-party module at all. Filtering hides/shows already-
// rendered <tr> rows by their cell text - a client-side quick-filter, not
// a server search.
export class CheckSheetListRenderer extends ListRenderer {
    static template = "bs_fieldservice.CheckSheetListRenderer";

    setup() {
        super.setup();
        guardKsAdvanceSearch();
        this.csSearch = useState({ reportNo: "", noPlate: "", modelCode: "", state: "" });
        this.csSearchRowRef = useRef("csSearchRow");
        onMounted(() => this.applyCsFilter());
        onPatched(() => this.applyCsFilter());
    }

    get csColumnIndex() {
        const offset = this.hasSelectors ? 1 : 0;
        const index = {};
        this.state.columns.forEach((column, i) => {
            if (column.type === "field") {
                index[column.name] = i + offset;
            }
        });
        return index;
    }

    applyCsFilter() {
        const searchRow = this.csSearchRowRef.el;
        const table = searchRow ? searchRow.closest("table") : null;
        if (!table) {
            return;
        }
        const { reportNo, noPlate, modelCode, state } = this.csSearch;
        const columnIndex = this.csColumnIndex;
        const cellText = (row, name) => {
            const index = columnIndex[name];
            const cell = index === undefined ? null : row.cells[index];
            return cell ? cell.textContent.trim().toLowerCase() : "";
        };
        table.querySelectorAll("tbody > tr.o_data_row").forEach((dataRow) => {
            const matches =
                (!reportNo || cellText(dataRow, "report_no").includes(reportNo.toLowerCase())) &&
                (!noPlate || cellText(dataRow, "no_plate").includes(noPlate.toLowerCase())) &&
                (!modelCode ||
                    cellText(dataRow, "model_id").includes(modelCode.toLowerCase())) &&
                (!state || cellText(dataRow, "state") === state);
            dataRow.style.display = matches ? "" : "none";
        });
    }
}

// Once a Check Sheet line is Confirmed, its popup should open read-only
// (just a "Close" button) instead of the usual Save/Discard - editing is
// only allowed again after a manager clicks "Reset to Draft". Odoo's
// X2ManyField decides Save/Discard vs Close per-field, not per-row, so this
// overrides openRecord() to force readonly mode for confirmed rows only.
export class CheckSheetLineList extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: CheckSheetListRenderer };

    async openRecord(record) {
        if (!this.canOpenRecord) {
            return;
        }
        const isConfirmed = record.data.state === "confirmed";
        return this._openRecord({
            record,
            context: this.props.context,
            mode: isConfirmed || this.props.readonly ? "readonly" : "edit",
        });
    }
}

export const checkSheetLineList = {
    ...x2ManyField,
    component: CheckSheetLineList,
};

registry.category("fields").add("bs_check_sheet_line_list", checkSheetLineList);
