{
    "name": "BS Sale Order HRP",
    "version": "17.0.0.2",
    "summary": "Add Delivery Time and Brand Logo fields on the sales quotation",
    "author": "Basic Solution Co.,Ltd.",
    "website": "http://www.basic-solution.com",
    "category": "Sales",
    "depends": ["sale", "sales_team"],
    "data": [
        "security/ir.model.access.csv",
        "views/bs_brand_logo_views.xml",
        "views/sale_order_views.xml",
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
