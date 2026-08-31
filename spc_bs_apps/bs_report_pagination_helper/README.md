# BS Report Pagination Helper

Reusable building blocks for Odoo QWeb PDF reports (wkhtmltopdf) that need to:

1. **Split a long text field across several printed pages** inside a report's header or footer (e.g. a "Remarks" / "Terms" rich-text field that doesn't fit in the space reserved for it on one page), and/or
2. **Show or hide a block of content depending on which physical page is currently being rendered** (first page only, last page only, or "page N of the extra-text pages") — the standard wkhtmltopdf trick of re-rendering the header/footer HTML once per page with `page`/`topage` query-string arguments.

This module has **no models, no views, no security rules** — it's a pure toolkit that other report modules depend on and call into. It was extracted after the exact same ~90 lines of Python and ~30 lines of JavaScript were found copy-pasted (with only the numbers and class names changed) across 5 different quotation report modules.

This README is a step-by-step walkthrough. It builds one running example — pagination a `sale.order` "Remarks" field into a report footer — from an empty report module to a working, tested PDF. Follow it in order the first time; use **Quick reference** further down once you already know the shapes.

---

## Step 1 — Add the dependency

In your report module's `__manifest__.py`:

```python
"depends": [
    "sale",
    ...
    "bs_report_pagination_helper",
],
```

## Step 2 — Decide your report's numbers

Three numbers drive everything, and they are specific to *your* report's font and paperformat — there's no way to compute them, only to measure them against a real printed PDF:

- **chars per line** — how many characters fit on one printed line at your footer's font/width. Start with a guess (e.g. `110`), print a long test text, and adjust if lines wrap noticeably short or overflow.
- **lines per page** — how many lines fit in the vertical space your footer reserves for this text (depends on `paperformat.margin_bottom`).
- **reserved lines** — how many of those lines are already taken by *other* static content sharing the same page (e.g. boilerplate text above it on page 1, or a totals table below it on the last page).

Write them as plain constants in your module — don't try to make them configurable, they're a one-time calibration, not a setting:

```python
REMARK_CHARS_PER_LINE = 110
REMARK_LINES_PER_PAGE = 20
REMARK_INTRO_RESERVED_LINES = 2   # boilerplate text that sits above the remark on page 1
```

## Step 3 — Add the mixin to your model

Add `bs.report.paginated.text.mixin` to your model's `_inherit`, then write three small wrapper methods around it. Keep the field name (`my_remark_field` below) and the constants from Step 2 local to your module — the mixin itself never sees them.

```python
# models/sale_order.py
from odoo import models

REMARK_CHARS_PER_LINE = 110
REMARK_LINES_PER_PAGE = 20
REMARK_INTRO_RESERVED_LINES = 2


class SaleOrder(models.Model):
    _name = "sale.order"                                          # required, see "Common pitfalls"
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]

    def _get_remark_splitter(self):
        self.ensure_one()
        lines = self._report_wrap_html_lines(self.my_remark_field, REMARK_CHARS_PER_LINE)
        return self._report_paginate_lines(
            lines, REMARK_LINES_PER_PAGE, first_page_reserved=REMARK_INTRO_RESERVED_LINES,
        )

    def _get_remark_total_page_count(self):
        self.ensure_one()
        return self._get_remark_splitter().page_count

    def _get_remark_page_lines(self, page_index):
        self.ensure_one()
        return self._get_remark_splitter().page_lines(page_index)
```

What each call does:
- `_report_wrap_html_lines(html_value, chars_per_line)` strips HTML tags (via `html2plaintext`) and wraps the plain text into a `list[str]` of at most `chars_per_line` characters each.
- `_report_paginate_lines(lines, lines_per_page, first_page_reserved=..., last_page_reserved=...)` returns a `ReportPageSplitter` that slices those lines across as many pages as needed.
- `.page_count` and `.page_lines(page_index)` are what your XML template will call in Step 4.

## Step 4 — Render the paginated lines in your footer XML

Loop over the pages, and inside each page loop over `page_lines(...)` emitting one `<br/>` per line. This needs **no `white-space: pre-line`** at all — see "Common pitfalls" for why that CSS property is worth avoiding here.

```xml
<div class="row">
    <div class="col-12">
        <t t-foreach="range(o.sudo()._get_remark_total_page_count())" t-as="page_index">
            <div class="o_report_page_item" t-att-data-report-page="page_index + 1" style="display: none; width: 100%;">
                <t t-foreach="o.sudo()._get_remark_page_lines(page_index)" t-as="line">
                    <span t-esc="line"/><t t-if="not line_last"><br/></t>
                </t>
            </div>
        </t>
    </div>
</div>
```

`o_report_page_item` + `data-report-page="N"` is a fixed class/attribute convention — the visibility script in Step 6 looks for exactly this, so use it as-is.

## Step 5 — Add first-page-only / last-page-only blocks (if you need them)

Same convention, two more fixed classes — for content that shares the footer but isn't part of the paginated text itself (boilerplate above it, totals below it):

```xml
<!-- shown only on page 1 -->
<div class="row o_report_first_page" style="display: none;">
    <div class="col-12">
        <span>Cancellation of order is subject to a 25% charge...</span>
    </div>
</div>

<!-- shown only on the last page -->
<table class="o_report_last_page" style="display: none;">
    <tr><td>Total</td><td t-esc="'%.2f' % o.amount_total"/></tr>
</table>
```

| CSS class / attribute | Shown when |
|---|---|
| `o_report_first_page` | the current page is page 1 |
| `o_report_last_page` | the current page is the last page (`page === topage`) |
| `o_report_page_item` with `data-report-page="N"` | the current page number equals `N` |

Every matching element must start with `style="display: none;"` — the script only ever adds `display: block`, it never hides.

## Step 6 — Wire up the visibility script

At the end of your footer template (or header), `t-call` the shared script instead of writing your own:

```xml
<t t-call="bs_report_pagination_helper.page_visibility_script"/>
```

That's the JavaScript that reads wkhtmltopdf's `page`/`topage` query-string arguments on each per-page render and reveals whichever block belongs on that page.

## Putting it together

The full footer template after Steps 4–6:

```xml
<template id="report_footer_my_report">
    <div class="row">
        <div class="col-12">
            <div class="row o_report_first_page" style="display: none;">
                <div class="col-12">
                    <span>Cancellation of order is subject to a 25% charge...</span>
                </div>
            </div>

            <div class="row">
                <div class="col-12">
                    <t t-foreach="range(o.sudo()._get_remark_total_page_count())" t-as="page_index">
                        <div class="o_report_page_item" t-att-data-report-page="page_index + 1" style="display: none; width: 100%;">
                            <t t-foreach="o.sudo()._get_remark_page_lines(page_index)" t-as="line">
                                <span t-esc="line"/><t t-if="not line_last"><br/></t>
                            </t>
                        </div>
                    </t>
                </div>
            </div>

            <table class="o_report_last_page" style="display: none;">
                <tr><td>Total</td><td t-esc="'%.2f' % o.amount_total"/></tr>
            </table>
        </div>
    </div>

    <t t-call="bs_report_pagination_helper.page_visibility_script"/>
</template>
```

Nothing here is specific to footers — the same template and classes work in a report's header too (e.g. a `Page X / Y` display, or a header block that should only render on page 1).

## Step 7 — Install and test

1. Add the module to `depends` (Step 1) and upgrade your report module (Apps → your module → Upgrade). A plain file edit to a QWeb `<template>` does **not** take effect until the module is upgraded, even in `--dev=xml` mode — see "Common pitfalls".
2. Open (or create) a record with enough text in the paginated field to overflow one page.
3. Print the report and check, page by page:
   - Page 1 shows the `o_report_first_page` boilerplate, then the first chunk of paginated text.
   - Middle pages show only their own chunk of paginated text, no boilerplate, no totals.
   - The last page shows the tail of the paginated text plus the `o_report_last_page` block.
4. If the pagination boundaries look off (a page cuts off short, or overflows), the numbers from Step 2 need adjusting — this is expected on the first pass and is not a bug in the mixin.

---

## Quick reference

### Python (`bs.report.paginated.text.mixin`)

```python
self._report_wrap_html_lines(html_value, chars_per_line) -> list[str]
self._report_paginate_lines(lines, lines_per_page,
                             first_page_reserved=0,
                             last_page_reserved=0) -> ReportPageSplitter
```

`ReportPageSplitter`:
| Member | Description |
|---|---|
| `.page_count` | Total number of pages needed |
| `.page_lines(page_index, pad_char="\xa0")` | `list[str]` for `page_index` (0-based), padded up to that page's budget — render with one `<br/>` per line (Step 4) |
| `.page_text(page_index, pad_char="\xa0")` | `.page_lines(...)` joined with `\n` — only for callers who render with `white-space: pre-line` instead of `<br/>` (see "Common pitfalls") |

`_report_wrap_html_lines` is also useful standalone (without pagination) to estimate how many lines a piece of text will take, e.g. to size a table row.

### QWeb (`bs_report_pagination_helper.page_visibility_script`)

| CSS class / attribute | Shown when |
|---|---|
| `o_report_first_page` | the current page is page 1 |
| `o_report_last_page` | the current page is the last page |
| `o_report_page_item` + `data-report-page="N"` | the current page number equals `N` |

---

## Common pitfalls

**`_inherit` as a list requires an explicit `_name`.** When adding this mixin to an *existing* model (like `sale.order`), you must write:

```python
class SaleOrder(models.Model):
    _name = "sale.order"                                    # required!
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]
```

If you omit `_name`, Odoo's metaclass (`odoo/models.py`, `MetaModel.__new__`) only defaults `_name` to `_inherit[0]` when `_inherit` has **exactly one** element. With two or more elements it falls back to the **Python class name** instead (`"SaleOrder"`), silently creating a brand-new phantom model instead of extending `sale.order`. Any field the phantom model copies unchanged from the original (e.g. an explicit `Many2many` with a hardcoded `relation=`) will then collide with the real one:

```
TypeError: Many2many fields SaleOrder.transaction_ids and sale.order.transaction_ids use the same table and columns
```

If you ever see that error after adding this mixin (or any other multi-item `_inherit` list) to a model, this is almost certainly the cause — add the missing `_name`.

**Editing a QWeb `<template>` file doesn't take effect until the module is upgraded.** Even with `--dev=xml`, the compiled render used by `ir.actions.report` (the actual PDF pipeline) is not reliably invalidated just because the view's `arch` field would recompute fresh from disk — a real module upgrade (or server restart) is what makes the DB's stored template match your file. If a change "doesn't show up" in a test print, upgrade first before assuming the fix is wrong.

**This is why `white-space: pre-line` should be avoided for the paginated block — use `page_lines()` + one `<br/>` per line instead (Step 4).** An earlier version of this guide recommended joining the lines with `\n` (`page_text()`) and rendering with `white-space: pre-line`:

```xml
<!-- avoid this -->
<div class="o_report_page_item" style="white-space: pre-line; ...">
    <span t-esc="o.sudo()._get_remark_text(page_index)"/>
</div>
```

This renders with a phantom blank line *before* the real text in the actual PDF, even though nothing in the field content or in `ReportPageSplitter` produces one. The cause: QWeb preserves the indentation newline between `<div ...>` and `<span>` as a real text node, and because `white-space: pre-line` doesn't distinguish "insignificant formatting whitespace" from real content, that lone `\n` renders as an actual forced line break — pushing the first visible line down by roughly one line-height. The same happens in reverse for the newline before `</div>`, silently costing one line of that page's budget at the bottom. This was verified by rendering the exact HTML Odoo hands to wkhtmltopdf (via `ir.actions.report._prepare_html`) locally and bisecting cause by cause: removing `white-space: pre-line` closes the gap (but breaks the multi-line rendering); removing only the whitespace around the `<span>` *also* closes the gap while keeping pagination intact — proving it's a whitespace/pre-line interaction, nothing to do with Bootstrap `.row`/`.col-*` margins or padding, despite that being the obvious first suspect.

The `<br/>`-based approach from Step 4 sidesteps this whole class of bug: there's no CSS property reinterpreting incidental template whitespace as content, so how the XML is indented can never affect the printed output. `page_text()` / `white-space: pre-line` still work and remain available (some existing reports already use them), but if you do reach for that combination, keep the div and its span flush against each other with no whitespace in between:

```xml
<div class="o_report_page_item" style="white-space: pre-line; ..."><span t-esc="o.sudo()._get_remark_text(page_index)"/></div>
```

## Design notes

- No configuration model or `ir.actions.report` settings are provided on purpose — the pagination numbers are a font/paperformat calibration concern for each report, not something meant to be tuned from Settings UI. Each report module keeps its own constants and passes them explicitly.
- Only "reserve N lines on the first page" and "reserve N lines on the last page" are supported, since that covers every case observed so far. If a future report needs reservations on arbitrary pages, extend `ReportPageSplitter` rather than bolting a workaround onto a specific report module.
