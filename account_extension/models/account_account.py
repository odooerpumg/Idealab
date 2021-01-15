from odoo import models, fields, api
from odoo.exceptions import UserError

class AccountAccount(models.Model):
	_inherit = 'account.account'

	bu_br_name = fields.Char('BU/BR Name')