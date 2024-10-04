from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_tmp_id = fields.Many2one("product.template", string="Name")
    reason_id = fields.Many2one("out.of.service.reason", string="Reason")
    date_from = fields.Datetime(string="Start Date")
    date_to = fields.Datetime(string="End Date")
    use_custom_rental_price = fields.Boolean()
    custom_pricelist_ids = fields.One2many(
        comodel_name="custom.pricelist",
        inverse_name="product_template_id",
        string="Custom PriceList",
        auto_join=True,
        copy=True,
    )

    def action_out_of_service(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Rental Out of Service",
            "res_model": "rental.out.of.service",
            "view_mode": "form",
            "target": "new",
        }

    def action_out_of_service_records(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Service Records"),
            "res_model": "service.records",
            "domain": [["product_tmp_id", "=", self.id]],
            "view_mode": "tree,form",
        }


class CustomPriceList(models.Model):
    _name = "custom.pricelist"
    _description = "Custom Price List"

    product_template_id = fields.Many2one(
        comodel_name="product.template",
        ondelete="cascade",
        help="Select products on which this pricing will be applied.",
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    price = fields.Float()

    @api.constrains("date_from", "date_to")
    def check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_("'Date To' must be greater than 'Date From' !"))
