import textwrap

from odoo import models
from odoo.tools import html2plaintext

# Names of the terms_template_ids records that feed the three footer columns.
KUADY_TERMS_NAMES = ("Scope Of Supply", "Site Requirement", "Warranty")

# Approx characters that fit on one footer-column line, and how many such
# lines are printed per physical page before continuing onto the next one.
# The footer column div no longer has a fixed height/overflow:hidden (that
# was clipping lines away silently at 5), so this is now bounded only by
# the report's overall footer canvas (~105mm margin_bottom), not by this
# one box - re-check against a real print and raise further if there's
# still room before the footer content overflows.
KUADY_TERMS_CHARS_PER_LINE = 40
KUADY_TERMS_MAX_LINES_PER_PAGE = 6

# Approx characters that fit on one item-table Description-column line, and
# how many such line slots fit in the space left for the item table on one
# page. Estimated from the report's own paperformat (AngsanaNew 24px, ~69mm
# of article height per Letter page) rather than measured from a real print
# - re-check against an actual long quotation and adjust if rows overflow
# past the footer or leave too much blank space.
KUADY_DESC_CHARS_PER_LINE = 48
KUADY_LINE_SLOTS_PER_PAGE = 7


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_kuady_terms_template(self, name):
        """The terms_template_ids record whose name matches ``name``
        exactly, or an empty recordset if there is none.
        """
        self.ensure_one()
        return self.terms_template_ids.filtered(lambda t: t.name == name)[:1]

    def _get_kuady_terms_template_text(self, name):
        """Plain-text (HTML tags stripped) rendering of the template
        named ``name``, or an empty string if there is no such template.
        """
        self.ensure_one()
        template = self._get_kuady_terms_template(name)
        if not template:
            return ""
        return html2plaintext(template.get_value(self) or "")

    def _get_kuady_terms_lines(self, name):
        """Wrap the template named ``name`` into printed lines, so the
        per-page split can be sliced precisely.
        """
        self.ensure_one()
        text = self._get_kuady_terms_template_text(name).strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=KUADY_TERMS_CHARS_PER_LINE) or [""])
        return lines

    def _get_kuady_terms_page_count(self):
        """How many pages the three footer columns need, at
        ``KUADY_TERMS_MAX_LINES_PER_PAGE`` lines per page (every page has
        the same layout, so the space left for these columns is the same
        everywhere).
        """
        self.ensure_one()
        max_lines = max(
            (len(self._get_kuady_terms_lines(name)) for name in KUADY_TERMS_NAMES),
            default=0,
        )
        return max(1, -(-max_lines // KUADY_TERMS_MAX_LINES_PER_PAGE))

    def _get_kuady_terms_text(self, name, page_index):
        """Portion of the template named ``name`` that belongs on
        ``page_index`` (0-based): each page gets its own
        ``KUADY_TERMS_MAX_LINES_PER_PAGE``-line slice, so the text keeps
        flowing onto as many pages as it needs instead of being cut off.

        Padded with invisible (non-breaking space) lines up to the full
        ``KUADY_TERMS_MAX_LINES_PER_PAGE`` budget, so the block always
        reserves the same height regardless of how much real text there is.
        """
        self.ensure_one()
        lines = self._get_kuady_terms_lines(name)
        start = page_index * KUADY_TERMS_MAX_LINES_PER_PAGE
        page_lines = lines[start:start + KUADY_TERMS_MAX_LINES_PER_PAGE]
        page_lines += [" "] * (KUADY_TERMS_MAX_LINES_PER_PAGE - len(page_lines))
        return "\n".join(page_lines)

    def _get_kuady_order_line_slots(self, line):
        """Estimated number of printed lines (line slots) the item row
        for ``line`` will take, based on how many lines its Description
        wraps to - the column most likely to wrap and grow the row
        taller than a single line.
        """
        text = (line.name or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=KUADY_DESC_CHARS_PER_LINE) or [""])
        return max(1, len(lines))

    def _get_kuady_report_pages(self):
        """Split order lines into pages sized to ``KUADY_LINE_SLOTS_PER_PAGE``
        slots each - a row whose Description wraps to 2 lines uses 2 of the
        page's slots instead of 1, so the natural render height stays inside
        what wkhtmltopdf fits on one physical page. Each page is padded with
        ``(False, False)`` blank single-line rows up to its slot budget, so
        the printed table always shows a full set of ruled rows regardless
        of how much real data there is. ``row_number`` starts at 1 and only
        counts real lines.

        Extended with fully-blank pages if the Terms and Conditions footer
        needs more pages than the item table does, so that text always has
        somewhere to continue (the footer can't create new PDF pages by
        itself - only the body content can).
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        numbered_lines = list(enumerate(lines, start=1))

        pages = []
        current_page = []
        current_slots = 0
        for entry in numbered_lines:
            slots = self._get_kuady_order_line_slots(entry[1])
            if current_page and current_slots + slots > KUADY_LINE_SLOTS_PER_PAGE:
                pages.append((current_page, current_slots))
                current_page = []
                current_slots = 0
            current_page.append(entry)
            current_slots += slots
        pages.append((current_page, current_slots))

        while len(pages) < self._get_kuady_terms_page_count():
            pages.append(([], 0))

        return [
            page_lines + [(False, False)] * max(0, KUADY_LINE_SLOTS_PER_PAGE - slots)
            for page_lines, slots in pages
        ]

    def _get_kuady_total_page_count(self):
        """Total number of physical report pages - simply the length of
        ``_get_kuady_report_pages()``, so the footer's per-page terms
        blocks are always in sync with what the body actually renders
        (never a separately-estimated number that could drift out of sync).
        """
        self.ensure_one()
        return len(self._get_kuady_report_pages())

