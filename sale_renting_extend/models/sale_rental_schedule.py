from odoo import api, fields, models, tools


class Base(models.AbstractModel):
    _inherit = "sale.rental.schedule"

    @api.model
    def get_gantt_data(
        self, domain, groupby, read_specification, limit=None, offset=0,
    ):
        """Super Call for Adding the Extra Data in Gantt View"""
        final_result = super().get_gantt_data(
            domain, groupby, read_specification, limit=limit, offset=offset
        )
        if "product_id" in groupby[0]:
            product_ids = []
            for rec in final_result["groups"]:
                product_ids.append(rec.get("product_id")[0])
            product_ids = (
                self.env["product.product"]
                .sudo()
                .search([("id", "not in", product_ids), ("rent_ok", "=", True)])
            )
            for pro in product_ids:
                final_result["groups"].append(
                    {
                        "product_id": tuple((pro.id, pro.name)),
                        "__record_ids": [],
                        "length": 0,
                        "records": [],
                    }
                )
        return final_result

    def init(self):
        # self._table = sale_rental_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """SELECT sol.id as id,
            t.name as product_name,
            sol.product_id as product_id,
            t.uom_id as product_uom,
            sol.name as description,
            s.name as name,
            
            sum(sol.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
            sum(sol.qty_delivered / u.factor * u2.factor) as qty_delivered,
            sum(sol.qty_returned / u.factor * u2.factor) as qty_returned
        ,
            s.date_order as order_date,
            s.rental_start_date as pickup_date,
            s.rental_return_date as return_date,
            s.state as state,
            s.rental_status as rental_status,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.company_id as company_id,
            extract(epoch from avg(date_trunc('day',s.rental_return_date)-date_trunc('day',s.rental_start_date)))/(24*60*60)::decimal(16,2) as delay,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.analytic_account_id as analytic_account_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.commercial_partner_id as commercial_partner_id,
            CONCAT(partner.name, ', ', s.name) as card_name,
            s.id as order_id,
            sol.id as order_line_id,
            
            CASE WHEN sol.qty_returned = sol.qty_delivered
                    AND sol.qty_delivered = sol.product_uom_qty THEN 'returned'
                WHEN sol.qty_delivered = sol.product_uom_qty THEN 'pickedup'
            ELSE 'reserved'
            END as report_line_status
        ,
            
            CASE WHEN sol.state != 'sale' THEN FALSE
                WHEN s.rental_start_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_delivered < sol.product_uom_qty THEN TRUE
                WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_returned < sol.qty_delivered THEN TRUE
            ELSE FALSE
            END as late
        ,
            
            CASE WHEN s.rental_start_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_delivered < sol.product_uom_qty THEN 4
                WHEN s.rental_return_date < NOW() AT TIME ZONE 'UTC' AND sol.qty_returned < sol.qty_delivered THEN 6
                WHEN sol.qty_returned = sol.qty_delivered AND sol.qty_delivered = sol.product_uom_qty THEN 7
                WHEN sol.qty_delivered = sol.product_uom_qty THEN 2
            ELSE 4
            END as color
        
        
                FROM 
            sale_order_line sol
                join sale_order s on (sol.order_id=s.id)
                join res_partner partner on s.partner_id = partner.id
                left join product_product p on (sol.product_id=p.id)
                left join product_template t on (p.product_tmpl_id=t.id)
                left join uom_uom u on (u.id=sol.product_uom)
                left join uom_uom u2 on (u2.id=t.uom_id)
        
                WHERE sol.product_id IS NOT NULL
                    AND sol.is_rental
                GROUP BY 
            sol.product_id,
            sol.order_id,
            t.uom_id,
            t.categ_id,
            t.name,
            s.name,
            s.date_order,
            s.rental_start_date,
            s.rental_return_date,
            s.partner_id,
            s.user_id,
            s.rental_status,
            s.company_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.commercial_partner_id,
            partner.name,
            s.id,
            sol.id
UNION ALL
SELECT 1000000 + ROW_NUMBER() OVER (ORDER BY sol.date_from) as id,
            t.name as product_name,
            sol.product_id as product_id,
            t.uom_id as product_uom,
            '' as description,
            '' as name,
            
            0 as product_uom_qty,
            0 as qty_delivered,
            0 as qty_returned
        ,
            sol.create_date as order_date,
            sol.date_from as pickup_date,
            sol.date_to as return_date,
            'sale' as state,
            'draft' as rental_status,
            null as partner_id,
            null as user_id,
            sol.company_id as company_id,
            null as delay,
            t.categ_id as categ_id,
            null as pricelist_id,
            null as analytic_account_id,
            null as team_id,
            p.product_tmpl_id,
            null as country_id,
            null as commercial_partner_id,
            out.reason as card_name,
            null as order_id,
            null as order_line_id,
            'reserved' as report_line_status,
			False as late,
            4 as color
        
        
                FROM 
            	service_records sol
				left join product_product p on (sol.product_id=p.id)
                left join out_of_service_reason out on (sol.reason_id=out.id)
                left join product_template t on (p.product_tmpl_id=t.id)
                left join uom_uom u2 on (u2.id=t.uom_id)
                WHERE sol.product_id IS NOT NULL
                GROUP BY 
	            sol.product_id,
	            t.uom_id,
	            t.categ_id,
	            t.name,
	            sol.create_date,
	            sol.date_from,
	            sol.date_to,
	            p.product_tmpl_id,
				sol.id,
                sol.company_id,
                out.reason
	            """
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query)
        )
