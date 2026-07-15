from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_display_name_with_attribute(self):
        """Same as `display_name` but uses the template's Sales Description
        (`description_sale`) instead of its Name as the prefix, and prefixes
        each attribute value with its attribute name, e.g:
        "<description_sale> (Type Plate, Type End plate I, Size 4, Pattern HT)"
        """
        self.ensure_one()
        variant = self.product_template_attribute_value_ids._get_combination_name_with_attribute()
        name = self.product_tmpl_id.description_sale or self.name
        return "%s (%s)" % (name, variant) if variant else name

    def get_product_multiline_description_sale(self):
        """Override to use the attribute-name-prefixed variant name instead
        of the plain `display_name`."""
        self.ensure_one()
        return self._get_display_name_with_attribute()

    def _get_mako_tmpl_name(self):
        """When no Mako template is configured on the product template
        (`mako_tmpl_name`), the base method falls back to `display_name`,
        which is what `product.configurator.sale._get_order_line_vals()`
        uses to fill the sale order line description. Use the
        attribute-name-prefixed variant name for that fallback instead."""
        self.ensure_one()
        if self.mako_tmpl_name:
            return super()._get_mako_tmpl_name()
        return self._get_display_name_with_attribute()
