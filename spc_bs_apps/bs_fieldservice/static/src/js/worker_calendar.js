/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Per-day status for one or more technicians (fsm.person), sourced from
// fsm.order's own request_early/request_late (Earliest/Latest Request
// Date) directly - NOT from bs.fsm.order.schedule.slot (that per-slot-type
// breakdown was removed: this widget no longer touches Schedule Sub-slot
// data at all). Any number of technicians can be shown at once (Technician
// sidebar is multi-select, with an "All" master checkbox) - each gets its
// own stable color (assigned once from the full technician list, so a
// given technician always renders the same color regardless of who else
// is currently selected), so overlapping bookings from different
// technicians stay visually distinguishable.
const PERSON_COLOR_PALETTE = [
    "#f4a688", "#a8d8e6", "#c9e4a8", "#f4d688", "#d8a8e6",
    "#e6a8c0", "#a8e6c9", "#e6c8a8", "#a8b8e6", "#e6e0a8",
];
const DEFAULT_COLOR = "#adb5bd";
//: pixels per hour in the Day/Week views' time grid - a block's top/height
//: are computed straight from request_early/request_late's time-of-day.
const HOUR_HEIGHT = 48;

export class WorkerCalendar extends Component {
    static template = "bs_fieldservice.WorkerCalendar";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            persons: [],
            personSearch: "",
            selectedPersonIds: {},
            allSelected: false,
            personColorById: {},
            viewMode: "month",
            month: luxon.DateTime.local().startOf("month"),
            day: luxon.DateTime.local().startOf("day"),
            week: startOfWeekSunday(luxon.DateTime.local().startOf("day")),
            // Mini date-picker shown next to the Day/Week view - browsable
            // on its own (prev/next month) independently of the selected
            // day/week, exactly like the stock Calendar app's sidebar picker.
            miniMonth: luxon.DateTime.local().startOf("month"),
            daysByDate: {},
            daySlots: [],
            weekSlotsByDay: {},
        });
        onWillStart(async () => {
            this.state.persons = await this.orm.searchRead(
                "fsm.person",
                [],
                ["id", "name"]
            );
            const colorById = {};
            this.state.persons.forEach((person, index) => {
                colorById[person.id] = PERSON_COLOR_PALETTE[index % PERSON_COLOR_PALETTE.length];
            });
            this.state.personColorById = colorById;
            // Default: everyone shown ("All" checked) on first load.
            this.selectAllPersons();
            await this.refresh();
        });
    }

    get monthLabel() {
        return this.state.month.setLocale("th").toFormat("LLLL yyyy");
    }

    get dayLabel() {
        return this.state.day.setLocale("th").toFormat("d LLLL yyyy");
    }

    get isToday() {
        return areSameDay(this.state.day, luxon.DateTime.local());
    }

    get weekLabel() {
        const start = this.state.week;
        const end = start.plus({ days: 6 });
        const sameMonth = start.month === end.month && start.year === end.year;
        const startFmt = start.setLocale("th").toFormat(sameMonth ? "d" : "d LLL");
        const endFmt = end.setLocale("th").toFormat("d LLL yyyy");
        return `${startFmt} - ${endFmt}`;
    }

    //: Column headers for the Week view - one per day, Sunday-start.
    get weekDays() {
        const start = this.state.week;
        return Array.from({ length: 7 }, (_, i) => {
            const date = start.plus({ days: i });
            const iso = date.toISODate();
            return {
                iso,
                day: date.day,
                weekday: date.setLocale("th").toFormat("ccc"),
                isToday: areSameDay(date, luxon.DateTime.local()),
                slots: this.state.weekSlotsByDay[iso] || [],
            };
        });
    }

    //: 00:00-23:00 row labels for the Day/Week views' time grid.
    get hours() {
        return Array.from({ length: 24 }, (_, h) => ({
            hour: h,
            label: String(h).padStart(2, "0") + ":00",
        }));
    }

    get dayGridHeight() {
        return 24 * HOUR_HEIGHT;
    }

    get weeks() {
        return buildMonthWeeks(this.state.month, (iso) => this.state.daysByDate[iso] || []);
    }

    //: Same 6-week Sunday-start grid, but for the small picker next to the
    //: Day view - no per-day status entries, just the days themselves.
    get miniWeeks() {
        return buildMonthWeeks(this.state.miniMonth, () => []);
    }

    get miniMonthLabel() {
        return this.state.miniMonth.setLocale("th").toFormat("LLLL yyyy");
    }

    //: Technician sidebar list, filtered by the search box - only affects
    //: which rows are shown, never the underlying selection itself.
    get filteredPersons() {
        const search = (this.state.personSearch || "").trim().toLowerCase();
        if (!search) {
            return this.state.persons;
        }
        return this.state.persons.filter((person) => person.name.toLowerCase().includes(search));
    }

    //: Legend mirrors whichever technicians are CURRENTLY selected (not the
    //: full master list), so it always explains exactly what's on screen.
    get legend() {
        return this.state.persons
            .filter((person) => this.state.selectedPersonIds[person.id])
            .map((person) => ({
                label: person.name,
                color: this.state.personColorById[person.id] || DEFAULT_COLOR,
            }));
    }

    get selectedPersonIdList() {
        return this.state.persons
            .map((person) => person.id)
            .filter((id) => this.state.selectedPersonIds[id]);
    }

    isPersonSelected(personId) {
        return !!this.state.selectedPersonIds[personId];
    }

    onPersonSearchInput(ev) {
        this.state.personSearch = ev.target.value;
    }

    async togglePerson(personId) {
        const selected = { ...this.state.selectedPersonIds };
        if (selected[personId]) {
            delete selected[personId];
        } else {
            selected[personId] = true;
        }
        this.state.selectedPersonIds = selected;
        this.state.allSelected = this.state.persons.every((person) => selected[person.id]);
        await this.refresh();
    }

    //: The "All" master checkbox - checking it selects every technician,
    //: unchecking it clears the selection entirely (a plain two-state
    //: switch; individual toggles are what nudge it on/off automatically
    //: as the selection happens to become complete/incomplete - see
    //: togglePerson above).
    async onToggleAllSelected(ev) {
        if (ev.target.checked) {
            this.selectAllPersons();
        } else {
            this.clearAllPersons();
        }
        await this.refresh();
    }

    selectAllPersons() {
        const selected = {};
        for (const person of this.state.persons) {
            selected[person.id] = true;
        }
        this.state.selectedPersonIds = selected;
        this.state.allSelected = true;
    }

    clearAllPersons() {
        this.state.selectedPersonIds = {};
        this.state.allSelected = false;
    }

    async onSelectAllClick() {
        this.selectAllPersons();
        await this.refresh();
    }

    async onClearClick() {
        this.clearAllPersons();
        await this.refresh();
    }

    async onViewModeChange(ev) {
        this.state.viewMode = ev.target.value;
        await this.refresh();
    }

    refresh() {
        if (this.state.viewMode === "day") {
            return this.loadDay();
        }
        if (this.state.viewMode === "week") {
            return this.loadWeek();
        }
        return this.loadMonth();
    }

    async goToday() {
        this.state.month = luxon.DateTime.local().startOf("month");
        this.state.day = luxon.DateTime.local().startOf("day");
        this.state.week = startOfWeekSunday(this.state.day);
        this.state.miniMonth = this.state.day.startOf("month");
        await this.refresh();
    }

    async prev() {
        if (this.state.viewMode === "day") {
            this.state.day = this.state.day.minus({ days: 1 });
            this.state.miniMonth = this.state.day.startOf("month");
        } else if (this.state.viewMode === "week") {
            this.state.week = this.state.week.minus({ days: 7 });
            this.state.miniMonth = this.state.week.startOf("month");
        } else {
            this.state.month = this.state.month.minus({ months: 1 });
        }
        await this.refresh();
    }

    async next() {
        if (this.state.viewMode === "day") {
            this.state.day = this.state.day.plus({ days: 1 });
            this.state.miniMonth = this.state.day.startOf("month");
        } else if (this.state.viewMode === "week") {
            this.state.week = this.state.week.plus({ days: 7 });
            this.state.miniMonth = this.state.week.startOf("month");
        } else {
            this.state.month = this.state.month.plus({ months: 1 });
        }
        await this.refresh();
    }

    // Browsing the mini picker itself (prev/next month, or picking a day)
    // never touches the main Month view's own `month` state.
    prevMiniMonth() {
        this.state.miniMonth = this.state.miniMonth.minus({ months: 1 });
    }

    nextMiniMonth() {
        this.state.miniMonth = this.state.miniMonth.plus({ months: 1 });
    }

    async selectMiniDay(iso) {
        const picked = luxon.DateTime.fromISO(iso);
        if (this.state.viewMode === "week") {
            this.state.week = startOfWeekSunday(picked);
        } else {
            this.state.day = picked;
        }
        this.state.miniMonth = picked.startOf("month");
        await this.refresh();
    }

    //: In Day mode, only the single selected day highlights; in Week mode,
    //: the whole selected week's range highlights instead.
    isMiniDaySelected(iso) {
        if (this.state.viewMode === "week") {
            const weekEndIso = this.state.week.plus({ days: 6 }).toISODate();
            return iso >= this.state.week.toISODate() && iso <= weekEndIso;
        }
        return iso === this.state.day.toISODate();
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

    //: fsm.order records for any of the currently selected technicians
    //: whose request_early-request_late window overlaps [rangeStart,
    //: rangeEnd] (both local DateTime). A missing request_late is treated
    //: as open-ended. Nothing selected -> nothing to show, no RPC needed.
    async searchOrders(rangeStart, rangeEnd) {
        const personIds = this.selectedPersonIdList;
        if (!personIds.length) {
            return [];
        }
        return this.orm.searchRead(
            "fsm.order",
            [
                ["person_id", "in", personIds],
                ["request_early", "<=", toOdooDatetime(rangeEnd)],
                "|",
                ["request_late", ">=", toOdooDatetime(rangeStart)],
                ["request_late", "=", false],
            ],
            ["request_early", "request_late", "name", "person_id"]
        );
    }

    //: This technician's stable color (assigned once from the full
    //: sidebar list, see setup()) - falls back to a neutral grey for the
    //: rare case a color wasn't pre-assigned (e.g. persons list changed).
    colorForPerson(personId) {
        return this.state.personColorById[personId] || DEFAULT_COLOR;
    }

    //: "ว่าง" (idle) Schedule Sub-slots for the given orders - these mark
    //: time the technician is actually FREE within the order's overall
    //: request_early-request_late window, so that stretch must be cut out
    //: of what the Calendar renders as busy for this order (see
    //: getOrderSegments). date_from/date_to are Date fields (no tz) and
    //: time_from/time_to are plain hour floats - both entered as local
    //: wall-clock directly, no UTC conversion (unlike request_early/
    //: request_late, which parseOdooDatetime already converts to local).
    //: Returns a map of order id -> array of [start, end] local DateTimes.
    async searchIdleSlots(orderIds) {
        if (!orderIds.length) {
            return {};
        }
        const slots = await this.orm.searchRead(
            "bs.fsm.order.schedule.slot",
            [
                ["order_id", "in", orderIds],
                ["slot_type", "=", "idle"],
            ],
            ["order_id", "date_from", "date_to", "time_from", "time_to"]
        );
        const byOrder = {};
        for (const slot of slots) {
            if (!slot.date_from) {
                continue;
            }
            const [orderId] = slot.order_id || [];
            const start = luxon.DateTime.fromISO(slot.date_from).plus({
                hours: slot.time_from || 0,
            });
            const end = luxon.DateTime.fromISO(slot.date_to || slot.date_from).plus({
                hours: slot.time_to || 0,
            });
            if (!byOrder[orderId]) {
                byOrder[orderId] = [];
            }
            byOrder[orderId].push([start, end]);
        }
        return byOrder;
    }

    //: This order's request_early-request_late window, cut into one or
    //: more remaining [start, end] segments after removing every idle
    //: sub-slot's range - an idle slot in the middle of the window splits
    //: it into a "before" and "after" segment; one covering the whole
    //: window empties it out entirely (order shows nothing on the
    //: Calendar). Returns [] if the order has no request_early at all.
    getOrderSegments(order, idleByOrder) {
        if (!order.request_early) {
            return [];
        }
        const early = parseOdooDatetime(order.request_early);
        const late = order.request_late ? parseOdooDatetime(order.request_late) : early;
        let segments = [[early, late]];
        for (const [exStart, exEnd] of idleByOrder[order.id] || []) {
            segments = segments.flatMap(([segStart, segEnd]) =>
                subtractInterval(segStart, segEnd, exStart, exEnd)
            );
        }
        return segments;
    }

    async loadMonth() {
        const monthStart = this.state.month;
        const monthEnd = monthStart.endOf("month");
        const orders = await this.searchOrders(monthStart, monthEnd);
        const idleByOrder = await this.searchIdleSlots(orders.map((order) => order.id));
        const daysByDate = {};
        for (const order of orders) {
            const [personId] = order.person_id || [];
            for (const [segStart, segEnd] of this.getOrderSegments(order, idleByOrder)) {
                let current = segStart.startOf("day");
                let lastDay = segEnd.startOf("day");
                // A segment that ends exactly at a day's midnight (e.g. an
                // idle cut) doesn't actually extend into that day - don't
                // count it, or an idle-excluded day would still show busy.
                if (segEnd.equals(lastDay) && lastDay > current) {
                    lastDay = lastDay.minus({ days: 1 });
                }
                while (current <= lastDay) {
                    const iso = current.toISODate();
                    if (!daysByDate[iso]) {
                        daysByDate[iso] = [];
                    }
                    // Same order can contribute more than one segment to
                    // the same day (e.g. idle splits it mid-day) - only one
                    // entry per order per day, not a visual duplicate.
                    if (!daysByDate[iso].some((entry) => entry.orderId === order.id)) {
                        daysByDate[iso].push({
                            color: this.colorForPerson(personId),
                            label: order.name,
                            orderId: order.id,
                        });
                    }
                    current = current.plus({ days: 1 });
                }
            }
        }
        this.state.daysByDate = daysByDate;
    }

    async loadDay() {
        const dayStart = this.state.day;
        const dayEnd = dayStart.endOf("day");
        const orders = await this.searchOrders(dayStart, dayEnd);
        const idleByOrder = await this.searchIdleSlots(orders.map((order) => order.id));
        const daySlots = [];
        for (const order of orders) {
            for (const [segStart, segEnd] of this.getOrderSegments(order, idleByOrder)) {
                if (segEnd <= dayStart || segStart >= dayEnd) {
                    continue;
                }
                daySlots.push(this.buildBlock(order, segStart, segEnd, dayStart, dayEnd));
            }
        }
        this.state.daySlots = daySlots;
    }

    async loadWeek() {
        const weekStart = this.state.week;
        const weekEnd = weekStart.plus({ days: 6 }).endOf("day");
        const orders = await this.searchOrders(weekStart, weekEnd);
        const idleByOrder = await this.searchIdleSlots(orders.map((order) => order.id));
        const weekSlotsByDay = {};
        for (let i = 0; i < 7; i++) {
            weekSlotsByDay[weekStart.plus({ days: i }).toISODate()] = [];
        }
        for (const order of orders) {
            for (const [segStart, segEnd] of this.getOrderSegments(order, idleByOrder)) {
                let current = segStart.startOf("day");
                const lastDay = segEnd.equals(segEnd.startOf("day"))
                    ? segEnd.minus({ days: 1 }).startOf("day")
                    : segEnd.startOf("day");
                while (current <= lastDay) {
                    const iso = current.toISODate();
                    if (iso in weekSlotsByDay) {
                        const dayStart = current;
                        const dayEnd = current.endOf("day");
                        const clippedStart = segStart > dayStart ? segStart : dayStart;
                        const clippedEnd = segEnd < dayEnd ? segEnd : dayEnd;
                        weekSlotsByDay[iso].push(
                            this.buildBlock(order, clippedStart, clippedEnd, dayStart, dayEnd)
                        );
                    }
                    current = current.plus({ days: 1 });
                }
            }
        }
        this.state.weekSlotsByDay = weekSlotsByDay;
    }

    //: One order segment's positioned block for a single day's time grid -
    //: clips [segStart, segEnd] to [dayStart, dayEnd] so a multi-day segment
    //: still renders sensibly on each day it touches (full-height on days
    //: strictly in between its start/end day). The technician's name is
    //: prefixed onto the label (Day/Week have room for it, unlike the
    //: compact Month cells) since several technicians' colors can appear
    //: side by side here.
    buildBlock(order, segStart, segEnd, dayStart, dayEnd) {
        const from = segStart < dayStart ? 0 : segStart.hour + segStart.minute / 60;
        const to = segEnd > dayEnd ? 24 : segEnd.hour + segEnd.minute / 60;
        const [personId, personName] = order.person_id || [];
        return {
            orderId: order.id,
            label: personName ? `${personName} - ${order.name}` : order.name,
            color: this.colorForPerson(personId),
            timeLabel: `${segStart.toFormat("HH:mm")}-${segEnd.toFormat("HH:mm")}`,
            top: from * HOUR_HEIGHT,
            height: Math.max((to - from) * HOUR_HEIGHT, 18),
        };
    }
}

function areSameDay(a, b) {
    return a.hasSame(b, "day") && a.hasSame(b, "month") && a.hasSame(b, "year");
}

//: luxon weekday: Mon=1..Sun=7 - shift back to the Sunday on/before `dt`,
//: since every grid in this widget (Month, mini picker, Week) starts on
//: Sunday, not luxon's own Monday-first default.
function startOfWeekSunday(dt) {
    return dt.minus({ days: dt.weekday % 7 });
}

//: Shared 6-week, Sunday-start grid builder for both the main Month view
//: and the small Day-view date picker - entryFn(iso) supplies each day's
//: list of status entries (empty array for the picker, which doesn't need
//: any).
function buildMonthWeeks(month, entryFn) {
    const gridStart = startOfWeekSunday(month);
    const days = [];
    for (let i = 0; i < 42; i++) {
        const date = gridStart.plus({ days: i });
        const iso = date.toISODate();
        days.push({
            iso,
            day: date.day,
            inMonth: date.month === month.month,
            isToday: areSameDay(date, luxon.DateTime.local()),
            entries: entryFn(iso),
        });
    }
    const weeks = [];
    for (let i = 0; i < days.length; i += 7) {
        weeks.push(days.slice(i, i + 7));
    }
    // Trailing weeks entirely outside the month add nothing useful - drop
    // them so short months don't show a blank row.
    while (weeks.length && weeks[weeks.length - 1].every((d) => !d.inMonth)) {
        weeks.pop();
    }
    return weeks;
}

//: request_early/request_late come back from searchRead as Odoo's own
//: "yyyy-MM-dd HH:mm:ss" UTC string (Datetime field) - parse it as UTC,
//: then convert to the browser's local zone for display/positioning.
function parseOdooDatetime(value) {
    return luxon.DateTime.fromFormat(value, "yyyy-LL-dd HH:mm:ss", { zone: "utc" }).toLocal();
}

//: The reverse of parseOdooDatetime - a local DateTime back to the UTC
//: string format Odoo's ORM expects in a domain filter.
function toOdooDatetime(dt) {
    return dt.toUTC().toFormat("yyyy-LL-dd HH:mm:ss");
}

//: [rangeStart, rangeEnd] minus [excludeStart, excludeEnd) as an array of
//: 0, 1, or 2 remaining [start, end] segments - an exclusion in the middle
//: splits the range in two; one covering the whole range empties it out
//: (returns []); no overlap returns the original range unchanged.
function subtractInterval(rangeStart, rangeEnd, excludeStart, excludeEnd) {
    if (excludeEnd <= rangeStart || excludeStart >= rangeEnd) {
        return [[rangeStart, rangeEnd]];
    }
    const segments = [];
    if (excludeStart > rangeStart) {
        segments.push([rangeStart, excludeStart]);
    }
    if (excludeEnd < rangeEnd) {
        segments.push([excludeEnd, rangeEnd]);
    }
    return segments;
}

registry.category("actions").add("bs_fieldservice.worker_calendar", WorkerCalendar);
