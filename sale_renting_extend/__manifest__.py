{
    "name": "sale_renting_extend",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "https://www.serpentcs.com",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "depends": ["sale_renting", "sale", "product"],
    "description": """
        Sale Renting Extend 
    """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/rental_out_of_service_view.xml",
        "views/out_of_service_reason_view.xml",
        "views/product_template_view.xml",
        "views/service_records_view.xml",
    ],
    "installable": True,
}
