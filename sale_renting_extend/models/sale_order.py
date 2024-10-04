from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_multi_line_booking = fields.Boolean(copy=False, string="Multi Line Booking?")

    @api.constrains("order_line")
    def check_out_of_service_records(self):
        service_records_obj = self.env["service.records"]
        for line in self.order_line:
            service_records = service_records_obj.search(
                [("product_id", "=", line.product_id.id)]
            )
            for service_record in service_records:
                if (
                    service_record.date_from.date()
                    == line.order_id.rental_start_date.date()
                ):
                    raise UserError(
                        (
                            "{} is out of service on {} kindly select any other date or change Product.".format(
                                line.product_id.name,
                                line.order_id.rental_start_date.date(),
                            )
                        )
                    )
