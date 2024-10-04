from odoo import api, fields, models


class OutOfServiceReason(models.Model):
    _name = "out.of.service.reason"
    _description = "Out Of Service Reason"
    _rec_name = "reason"

    reason = fields.Char(string="Reason")
