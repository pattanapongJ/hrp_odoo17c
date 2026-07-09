from odoo import models


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def _get_combination_name_with_attribute(self):
        """Same as `_get_combination_name` but prefixes each value with its
        attribute name (e.g. "Type End plate I") instead of the bare value
        name, for use in the sale order line description."""
        ptavs = self._without_no_variant_attributes().with_prefetch(self._prefetch_ids)
        ptavs = ptavs._filter_single_value_lines().with_prefetch(self._prefetch_ids)
        return ", ".join(
            "%s %s" % (ptav.attribute_id.name, ptav.name) for ptav in ptavs
        )
