from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSaleOrderTypeRevision(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})
        cls.product = cls.env["product.product"].create({"name": "Test product"})
        cls.type_1 = cls._create_sale_type("TYPE1-")
        cls.type_2 = cls._create_sale_type("TYPE2-")

    @classmethod
    def _create_sale_type(cls, prefix):
        sequence = cls.env["ir.sequence"].create(
            {"name": prefix, "code": "sale.order", "prefix": prefix, "padding": 4}
        )
        return cls.env["sale.order.type"].create(
            {"name": prefix, "sequence_id": sequence.id}
        )

    def _create_order(self, sale_type):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "type_id": sale_type.id,
                "order_line": [(0, 0, {"product_id": self.product.id})],
            }
        )

    @staticmethod
    def _new_revision(order):
        order.create_revision()
        return order.current_revision_id

    def test_revision_same_type(self):
        order = self._create_order(self.type_1)
        self.assertTrue(order.name.startswith("TYPE1-"))
        revision = self._new_revision(order)
        self.assertEqual(revision.name, "%s-01" % order.name)

    def test_revision_after_type_change(self):
        order = self._create_order(self.type_1)
        order.type_id = self.type_2
        self.assertTrue(order.name.startswith("TYPE2-"))
        self.assertEqual(order.unrevisioned_name, order.name)
        revision = self._new_revision(order)
        self.assertEqual(revision.name, "%s-01" % order.name)
        self.assertEqual(revision.type_id, self.type_2)

    def test_type_change_on_revision(self):
        order = self._create_order(self.type_1)
        revision = self._new_revision(order)
        revision.type_id = self.type_2
        self.assertTrue(revision.name.startswith("TYPE2-"))
        self.assertEqual(revision.name, "%s-01" % revision.unrevisioned_name)
        self.assertEqual(revision.old_revision_ids, order)
        revision_2 = self._new_revision(revision)
        self.assertEqual(revision_2.name, "%s-02" % revision.unrevisioned_name)
        self.assertEqual(revision_2.revision_number, 2)
