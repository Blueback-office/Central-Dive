from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RentalOutOfService(models.TransientModel):
    _name = "rental.out.of.service"
    _description = "Rental Out of Service"

    product_tmp_id = fields.Many2one("product.template", string="Name")
    reason_id = fields.Many2one("out.of.service.reason", string="Reason")
    date_from = fields.Datetime(string="Start Date")
    date_to = fields.Datetime(string="End Date")

    @api.constrains("date_from", "date_to")
    def check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise ValidationError(_("'Date To' must be greater than 'Date From' !"))

    @api.model
    def default_get(self, fields_list):
        res = super(RentalOutOfService, self).default_get(fields_list)
        product_template_id = self.env.context.get("default_product_template_id", False)
        if product_template_id:
            res["product_tmp_id"] = product_template_id
        return res

    def action_confirm(self):
        self.env["service.records"].create(
            {
                "product_tmp_id": self.product_tmp_id.id,
                "product_id": self.product_tmp_id.product_variant_id.id,
                "reason_id": self.reason_id.id,
                "date_from": self.date_from,
                "date_to": self.date_to,
            }
        )
        return True
