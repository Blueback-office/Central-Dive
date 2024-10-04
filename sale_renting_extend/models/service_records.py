from odoo import api, fields, models


class ServiceRecords(models.Model):
    _name = "service.records"
    _description = "Service Records"

    product_tmp_id = fields.Many2one("product.template", string="Product Template")
    product_id = fields.Many2one("product.product", string="Product Template")
    company_id = fields.Many2one(
        "res.company", string="company", default=lambda line: line.env.company.id
    )
    reason_id = fields.Many2one("out.of.service.reason", string="Reason")
    date_from = fields.Datetime(string="Start Date")
    date_to = fields.Datetime(string="End Date")
