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
                    custom_pricelist_ids = product.custom_pricelist_ids.filtered(
                        lambda line: start_date.date() <= line.date_to
                        and end_date.date() >= line.date_from
                    )
                    falling_days_total = 0
                    total_days_user = (end_date.date() - start_date.date()).days + 1
                    overlapping_ranges = []
                    price = product.lst_price
                    for price_list in product.custom_pricelist_ids:
                        overlap_start = max(start_date.date(), price_list.date_from)
                        overlap_end = min(end_date.date(), price_list.date_to)
                        if overlap_end >= overlap_start:
                            falling_days = (overlap_end - overlap_start).days + 1
                            falling_days_total += falling_days
                            overlapping_ranges.append(
                                {"range": price_list, "falling_days": falling_days}
                            )
                    non_falling_days_total = total_days_user - falling_days_total
                    if non_falling_days_total <= 6 and product.per_day_price:
                        price = non_falling_days_total * product.per_day_price
                    elif non_falling_days_total > 6 and product.morethan_6day_price:
                        price = non_falling_days_total * product.morethan_6day_price

                    for value in overlapping_ranges:
                        price += value.get("range").price * value.get("falling_days")

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
