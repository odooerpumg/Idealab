from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta

CASH_TYPE = [
    ('pay', 'Cash Payment'),
    ('receive', 'Cash Recieved'),
    ]


class AccountMove(models.Model):
    _inherit = "account.move"

    cashbook_id = fields.Many2one('account.cashbook', string='Cash Book')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    narration = fields.Text(related='move_id.narration', string='Narration', store=True)

class AccountCashBook(models.Model):
	_name = 'account.cashbook'
	_inherit = 'mail.thread'

	name = fields.Char('No', copy=False,track_visibility='onchange')
	date = fields.Date(string='Date', required=True,track_visibility='onchange', default=datetime.today())
	ref_no = fields.Char('Ref No', copy=False, required=True,track_visibility='onchange')
	cash_type = fields.Selection(CASH_TYPE, string='Type', required=True)
	account_id = fields.Many2one('account.account',string='Chart of Account', required=True)
	currency_id = fields.Many2one('res.currency', related='account_id.currency_id', string="Currency",store=True)
	move_ids = fields.One2many('account.move', 'cashbook_id', string='Journal Entries')
	line_ids = fields.One2many('account.cashbook.line', 'cashbook',string='Cashbook Line')
	journal_id = fields.Many2one('account.journal', string='Journal', required=True)
	note = fields.Text(string='Note')
	state = fields.Selection([('draft', 'Draft'),('done', 'Done'),], string='Status', default='draft',track_visibility='onchange')

	@api.onchange('journal_id')
	def get_account_id_with_journal(self):
		if self.cash_type and self.journal_id:
			if self.cash_type == 'pay':
				self.account_id = self.journal_id.default_credit_account_id
			else:
				self.account_id = self.journal_id.default_debit_account_id

	# @api.model
	def validate_cashbook(self):
		print ("Validate----------------")
		
		for line in self.line_ids:
			res = []
			move_line = {
				# 'type': 'dest',
				'name': self.name,
				'account_id': line.account_id.id,
				'date_maturity': self.date,
				#'amount_currency': diff_currency and total_currency,
				'currency_id': line.currency_id.id,
				'debit': 0.0,
				'credit': 0.0,
				'narration': line.name,
			}
			# print (".........1............")
			if self.cash_type == 'pay':
				move_line['debit'] = line.amount
				# print (".........2............")
			else:
				move_line['credit'] = line.amount
				# print (".........3............")
			res.append(move_line)
			# print move_line

			move_line = {
				# 'type': 'dest',
				'name': self.name,
				'account_id': self.account_id.id,
				'date_maturity': self.date,
				#'amount_currency': diff_currency and total_currency,
				'currency_id': line.currency_id.id,
				'credit': 0.0,
				'debit': 0.0,
			}
			# print (".........4............")
			if self.cash_type == 'pay':
				move_line['credit'] = line.amount
			else:
				move_line['debit'] = line.amount
			res.append(move_line)
			line = [(0, 0, l) for l in res]
			move_vals = {
				'journal_id': self.journal_id.id,
				'ref': self.ref_no,
				'date': self.date,
				'line_ids': line,
				'cashbook_id': self.id,
			}
			move_id = self.env['account.move'].create(move_vals)
			print (move_id)
			move_id.post()

		body = "Journal Entries are already created for cashbook line. Please check in 'Journal Entries' tab."
		self.state='done'
		self.message_post(body=body, subtype='notification')

	@api.model
	def create(self, vals):
		# print "------create------------"
		if vals.get('name','') == False:
			type_name = vals['cash_type']
			# print type_name

			sequence = self.env['ir.sequence'].search([('code','=',type_name)])
			# print sequence
			if not sequence:
				raise ValidationError('Sequence cannot be found.')
			vals['name'] = sequence.next_by_code(type_name)
			# print vals['name']
		return super(AccountCashBook, self).create(vals)


	@api.model
	def unlink(self):
		for result in self:
			if result.state == 'done':
				raise ValidationError('Done records cannot be deleted.')
			for line in result.line_ids:
				line.unlink()
		res = super(AccountCashBook, self).unlink()
		return res



class AccountCashBookLine(models.Model):
	_name = 'account.cashbook.line'
	_inherit = 'mail.thread'

	name = fields.Char('Description', copy=False)
	date = fields.Date(string='Date', required=False)
	debit = fields.Monetary(default=0.0, currency_field='currency_id')
	credit = fields.Monetary(default=0.0, currency_field='currency_id')
	amount = fields.Monetary(string='Amount', default=0.0, currency_field='currency_id')
	cashbook = fields.Many2one('account.cashbook', string='Cash Book')
	account_id = fields.Many2one('account.account',string='Account', required=True)
	currency_id = fields.Many2one('res.currency', string="Company Currency", store=True)

	# @api.onchange('account_id')
	# def get_currency(self):
	# 	if self.account_id:
	# 		self.currency_id = self.account_id.currency_id

	# @api.model
	# def create(self, vals):
	# 	record = super(AccountCashBookLine, self).create(vals)

	# @api.model
	# def default_get(self, fields):
	# 	print "Default-----------------------------"
	# 	print fields
	# 	print self.cashbook_id.date, self.cashbook_id.currency_id.name
	# 	rec = super(AccountCashBookLine, self).default_get(fields)
	# 	rec['date'] = self.cashbook_id.date
	# 	rec['currency_id'] = self.cashbook_id.currency_id.id
	# 	print rec
	# 	return rec