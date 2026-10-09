from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        """sale_order_type renumbers a draft order when its type changes, but
        base_revision keeps the old unrevisioned_name, so the next revision would
        reuse the prefix of the original type. Re-base the revision reference on
        the new number so revisions always follow the current Sale Order Type."""
        if not vals.get("type_id") or "name" in vals:
            return super().write(vals)
        old_names = {order.id: order.name for order in self}
        res = super().write(vals)
        for order in self:
            if order.name == old_names[order.id]:
                continue
            new_vals = {"unrevisioned_name": order.name}
            if order.revision_number:
                new_vals["name"] = "%s-%02d" % (order.name, order.revision_number)
            order.write(new_vals)
        return res
