import textwrap

from odoo import models

# Characters that fit on one printed line of the footer's "other template"
# text at 22.5px AngsanaNew across the report's full content width
# (~190mm, i.e. A4 minus the 6mm side margins). First-pass estimate scaled
# from the article table's own 40%-wide Description column - NOT
# calibrated against a real print; re-check against an actual long-text
# quotation PDF and adjust if lines wrap noticeably short/long.
KUADY_OTHER_CHARS_PER_LINE = 112
# Total printed lines available in the footer per page, at 22.5px
# AngsanaNew over the report's 108mm bottom margin (see
# paper_format_bs_create_quotation_kuady_report). First-pass estimate;
# re-check against a real print.
KUADY_FOOTER_LINES_PER_PAGE = 22
# Lines reserved out of the first page's budget for the "Above price..."
# boilerplate line (rendered as ``.o_report_first_page`` in the footer
# template) - real other-template text only starts after it.
KUADY_FOOTER_INTRO_RESERVED_LINES = 2
# Lines reserved out of the last page's budget for the TOTAL PRICE row and
# the signature block (both rendered as ``.o_report_last_page``). If the
# first page also ends up being the last page, both reservations apply
# together.
KUADY_FOOTER_SIGNATURE_RESERVED_LINES = 8

# Characters that fit on one wrapped line of the article table's own
# Description column (~40% of the report's ~190mm content width) at
# 22.5px AngsanaNew - matches what's actually observed wrapping in that
# column.
KUADY_ARTICLE_DESC_CHARS_PER_LINE = 46
# How many of those wrapped Description lines fit on one physical page of
# the item table, over the report's ~84mm article canvas (297mm A4 minus
# the 105mm top / 108mm bottom margins). Empirically confirmed at 15 (real
# overflow test: 20 duplicated order lines, consistently 3 rows/page x 5
# slots each) - confirmed unchanged at both 0.75em and 0.9em Description
# line-height, so it isn't sensitive to that setting within this range.
KUADY_ARTICLE_LINE_SLOTS_PER_PAGE = 15


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "bs.report.paginated.text.mixin"]

    def _get_kuady_other_lines(self):
        """Wrapped lines of ``other_template_text`` (see
        ``bs_report_pagination_helper`` for the generic wrap/blank-line
        handling).
        """
        self.ensure_one()
        return self._report_wrap_html_lines(self.other_template_text, KUADY_OTHER_CHARS_PER_LINE)

    def _get_kuady_footer_page_budget(self, page_index, total_pages):
        """Real-text line budget for ``page_index`` (0-based) out of
        ``total_pages``: the full per-page budget, minus the intro
        reservation on page 0 and minus the signature reservation on the
        last page - both at once if page 0 is also the last page.
        """
        budget = KUADY_FOOTER_LINES_PER_PAGE
        if page_index == 0:
            budget -= KUADY_FOOTER_INTRO_RESERVED_LINES
        if page_index == total_pages - 1:
            budget -= KUADY_FOOTER_SIGNATURE_RESERVED_LINES
        return max(1, budget)

    def _get_kuady_footer_page_count(self):
        """How many physical pages the footer's other-template text alone
        needs, filling each page's real-text budget (see
        ``_get_kuady_footer_page_budget``) before overflowing onto the
        next.
        """
        self.ensure_one()
        lines = self._get_kuady_other_lines()
        pages = 1
        while True:
            capacity = sum(
                self._get_kuady_footer_page_budget(i, pages) for i in range(pages)
            )
            if len(lines) <= capacity:
                return pages
            pages += 1

    def _get_kuady_article_line_slots(self, line):
        """Estimated number of printed lines (line slots) the item row for
        ``line`` will take, based on how many lines its Description wraps
        to - the column most likely to wrap and grow the row taller than
        a single line. ``line.name`` is plain text (not HTML), so this
        wraps it directly rather than through ``_report_wrap_html_lines``.
        """
        text = (line.name or "").strip()
        lines = []
        for raw_line in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw_line, width=KUADY_ARTICLE_DESC_CHARS_PER_LINE) or [""])
        return max(1, len(lines))

    def _get_kuady_article_page_count(self):
        """How many physical pages the item table itself is expected to
        naturally need - the table isn't manually split (order lines just
        overflow onto further pages on their own), so this is only an
        estimate used to make sure the footer's own pagination (and its
        last-page reservation for the totals/signature block) lands on
        the report's true final page rather than assuming the footer's
        own, possibly shorter, text alone determines it (see
        ``report_main_content_kuady``'s extra-page loop).
        """
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)
        total_slots = sum(self._get_kuady_article_line_slots(line) for line in lines)
        if not total_slots:
            return 1
        return max(1, -(-total_slots // KUADY_ARTICLE_LINE_SLOTS_PER_PAGE))

    def _get_kuady_total_page_count(self):
        """Total physical pages the report needs: whichever is larger
        between what the item table naturally needs and what the footer's
        other-template text needs, so neither one runs out of pages to
        land its content on.
        """
        self.ensure_one()
        return max(
            self._get_kuady_footer_page_count(),
            self._get_kuady_article_page_count(),
        )

    def _get_kuady_other_page_lines(self, page_index):
        """Lines of the other-template text belonging on ``page_index``
        (0-based), padded to that page's own budget - render with one
        ``<br/>`` per line in the footer template. Padding on the last
        page is intentional: it keeps the signature/totals block
        (``.o_report_last_page``, which sits immediately below this text
        in the template's normal document flow) anchored at a consistent
        position near the bottom of the page instead of floating up right
        after however much real text happens to be there.
        """
        self.ensure_one()
        lines = self._get_kuady_other_lines()
        total_pages = self._get_kuady_total_page_count()
        start = sum(
            self._get_kuady_footer_page_budget(i, total_pages) for i in range(page_index)
        )
        budget = self._get_kuady_footer_page_budget(page_index, total_pages)
        page_lines = lines[start:start + budget]
        # A plain space collapses to nothing under some renderers - a
        # non-breaking space is needed so each padding line still reserves
        # a real line box.
        page_lines += ["\xa0"] * (budget - len(page_lines))
        return page_lines
