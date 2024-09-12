from odoo import _, api, fields, models


class PriceList(models.Model):
    _inherit = "product.pricelist"

    def _compute_price_rule(
        self,
        products,
        quantity,
        currency=None,
        date=False,
        start_date=None,
        end_date=None,
        **kwargs
    ):
        """ Override to handle the rental product price

        Note that this implementation can be done deeper in the base price method of pricelist item
        or the product price compute method.
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        results = {}
        if self._enable_rental_price(start_date, end_date):
            rental_products = products.filtered("rent_ok")
            Pricing = self.env["product.pricing"]
            for product in rental_products:
                if start_date and end_date:
                    pricing = product._get_best_pricing_rule(
                        start_date=start_date,
                        end_date=end_date,
                        pricelist=self,
                        currency=currency,
                    )
                    duration_vals = Pricing._compute_duration_vals(start_date, end_date)
                    duration = (
                        pricing
                        and duration_vals[pricing.recurrence_id.unit or "day"]
                        or 0
                    )
                else:
                    pricing = Pricing._get_first_suitable_pricing(product, self)
                    duration = pricing.recurrence_id.duration

                if product.use_custom_rental_price and start_date and end_date:
                    st_duration = abs((end_date - start_date).days)
                    st_date = product.custom_pricelist_ids.filtered(
                        lambda x: x.date_to >= start_date.date() >= x.date_from
                    )
                    ed_date = product.custom_pricelist_ids.filtered(
                        lambda x: x.date_to >= end_date.date() >= x.date_from
                    )
                    if st_date and ed_date and st_date[0].id == ed_date[0].id:
                        price = st_duration * st_date[0].price
                    elif st_date and ed_date and st_date[0].id != ed_date[0].id:
                        rem_duration = (st_date[0].date_to - start_date.date()).days
                        price = rem_duration * st_date[0].price
                        price = (st_duration - rem_duration) * ed_date[0].price + price
                    elif pricing:
                        price = pricing._compute_price(
                            duration, pricing.recurrence_id.unit
                        )
                    elif product._name == "product.product":
                        price = product.lst_price
                    else:
                        price = product.list_price

                elif pricing:
                    price = pricing._compute_price(duration, pricing.recurrence_id.unit)
                elif product._name == "product.product":
                    price = product.lst_price
                else:
                    price = product.list_price
                results[product.id] = (
                    pricing.currency_id._convert(
                        price, currency, self.env.company, date
                    ),
                    False,
                )

        price_computed_products = self.env[products._name].browse(results.keys())
        return {
            **results,
            **super()._compute_price_rule(
                products - price_computed_products,
                quantity,
                currency=currency,
                date=date,
                **kwargs
            ),
        }
