from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_fsm_values(self, **kwargs):
        """fsm.order.team_id is required and no longer auto-derived from
        location_id when picked interactively in the browser (a user must
        pick it) - but this vals-builder feeds fsm.order.create() straight
        from Sale Order confirmation, with no user around to pick anything.
        Falls back to the Service Location's own default team, then to the
        company's first team, mirroring the same fallback already used by
        fsm.recurring/fsm.route.dayroute for the identical "no interactive
        user" situation."""
        vals = super()._prepare_fsm_values(**kwargs)
        if not vals.get("team_id"):
            team = self.fsm_location_id.team_id
            if not team:
                team = self.env["fsm.team"].search(
                    [("company_id", "in", (self.company_id.id, False))],
                    order="sequence",
                    limit=1,
                )
            vals["team_id"] = team.id
        return vals
