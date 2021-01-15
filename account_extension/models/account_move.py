# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
# from datetime imsort datetime, time, timedelta
# from pytz imsort timezone, UTC


class SaleCommission(models.Model):
	_inherit = 'account.move'

	product_uom_id = fields.Many2one('uom.uom', string='UOM')