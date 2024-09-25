from odoo import _, api, fields, models
from pytz import timezone, UTC
from odoo.tools import format_datetime, format_time
from odoo.exceptions import UserError, ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_start_date = fields.Datetime(string="Start Date")
    line_end_date = fields.Datetime(string="End Date")
    duration = fields.Char("Duration(Days)", readonly="1", compute="_compute_duration")

    def _compute_duration(self):
        for line in self:
            line.duration = 0
            if (
                line.order_id.is_multi_line_booking
                and line.product_id.use_custom_rental_price
                and line.line_start_date
                and line.line_end_date
            ):
                line.duration = abs(
                    (line.line_end_date.date() - line.line_start_date.date()).days
                )

    @api.constrains("product_id", "line_start_date", "line_end_date")
    def check_out_of_service_records(self):
        service_records_obj = self.env["service.records"]
        env = self.with_context(use_babel=True).env
        tz = self._get_tz()
        for line in self:
            service_records = service_records_obj.search(
                [("product_id", "=", line.product_id.id)]
            )
            for service_record in service_records:
                if (
                    (
                        line.line_start_date.date() >= service_record.date_from.date()
                        and line.line_start_date.date() <= service_record.date_to.date()
                    )
                    or (
                        line.line_end_date.date() >= service_record.date_from.date()
                        and line.line_end_date.date() <= service_record.date_to.date()
                    )
                    or (
                        not line.line_start_date.date()
                        >= service_record.date_from.date()
                        and line.line_end_date.date() >= service_record.date_to.date()
                    )
                ):
                    date_from = format_datetime(
                        env, service_record.date_from, tz=tz, dt_format=False
                    )
                    date_to = format_datetime(
                        env, service_record.date_to, tz=tz, dt_format=False
                    )
                    raise UserError(
                        (
                            "{} is not available from {} to {} due to {}.".format(
                                line.product_id.name,
                                date_from,
                                date_to,
                                service_record.reason_id.reason,
                            )
                        )
                    )

            existing_sol = self.search(
                [
                    ("product_id", "=", line.product_id.id),
                    ("id", "!=", line.id),
                    ("line_start_date", ">=", line.line_start_date),
                    ("line_end_date", "<=", line.line_end_date),
                    ("state", "=", "sale"),
                ]
            )
            if existing_sol:
                line_start_date = format_datetime(
                    env, line.line_start_date, tz=tz, dt_format=False
                )
                line_end_date = format_datetime(
                    env, line.line_end_date, tz=tz, dt_format=False
                )
                raise UserError(
                    (
                        "{} is already booked from {} to {}.".format(
                            line.product_id.name, line_start_date, line_end_date,
                        )
                    )
                )

    @api.depends(
        "line_start_date",
        "line_end_date",
        "product_id",
        "product_uom",
        "product_uom_qty",
    )
    def _compute_price_unit(self):

        for line in self:
            if (
                line.order_id.is_multi_line_booking
                and line.product_id.use_custom_rental_price
                and line.line_start_date
                and line.line_end_date
            ):
                price = self.product_id.lst_price
                st_duration = abs(
                    (line.line_end_date.date() - line.line_start_date.date()).days
                )
                st_date = self.product_id.custom_pricelist_ids.filtered(
                    lambda x: x.date_to >= self.line_start_date.date() >= x.date_from
                )
                ed_date = self.product_id.custom_pricelist_ids.filtered(
                    lambda x: x.date_to >= self.line_end_date.date() >= x.date_from
                )
                if st_date and ed_date and st_date[0].id == ed_date[0].id:
                    price = st_duration * st_date[0].price
                line.price_unit = line.product_id._get_tax_included_unit_price_from_price(
                    price,
                    line.currency_id or line.order_id.currency_id,
                    product_taxes=line.product_id.taxes_id.filtered(
                        lambda tax: tax.company_id == line.env.company
                    ),
                    fiscal_position=line.order_id.fiscal_position_id,
                )
            else:
                return super()._compute_price_unit()

    @api.constrains("line_start_date", "line_end_date")
    def check_dates(self):
        for rec in self:
            if (
                rec.order_id.is_multi_line_booking
                and rec.line_start_date > rec.line_end_date
            ):
                raise ValidationError(_("End date must be Bigger than the Start date!"))

    @api.depends(
        "order_id.rental_start_date",
        "order_id.rental_return_date",
        "is_rental",
        "line_start_date",
        "line_end_date",
    )
    def _compute_name(self):
        """Override to add the compute dependency.

        The custom name logic can be found below in _get_sale_order_line_multiline_description_sale.
        """
        super()._compute_name()

    def _get_rental_order_line_description(self):
        if self.order_id.is_multi_line_booking:
            tz = self._get_tz()
            start_date = self.line_start_date
            return_date = self.line_end_date
            env = self.with_context(use_babel=True).env
            if (
                start_date
                and return_date
                and start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
                == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
            ):
                # If return day is the same as pickup day, don't display return_date Y/M/D in description.
                return_date_part = format_time(
                    env, return_date, tz=tz, time_format=False
                )
            else:
                return_date_part = format_datetime(
                    env, return_date, tz=tz, dt_format=False
                )
            start_date_part = format_datetime(env, start_date, tz=tz, dt_format=False)
            return _(
                "\n%(from_date)s to %(to_date)s",
                from_date=start_date_part,
                to_date=return_date_part,
            )
        else:
            return super()._get_rental_order_line_description()
