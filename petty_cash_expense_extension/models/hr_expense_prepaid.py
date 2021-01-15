from odoo import models, fields, api
from datetime import date,timedelta,datetime
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp
import time
from odoo.tools.translate import _
import calendar
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth
import hashlib
import json
import requests
import locale


# class hr_expense_project(models.Model):
# 	_name = "hr.expense.prepaid.project"

# 	name = fields.Char('Name')

# class product_product(models.Model):
# 	_inherit = "product.product"

# 	parent_id = fields.Many2one('product.product', 'Parent Product',)
# 	is_parent = fields.Boolean('Is Parent',)
	
# class Expense_Prepaid_Group(models.Model):
# 	_name = 'expense.prepaid.group'
	
# 	group_name = fields.Char('Analytical Account', required = True)
# 	group_code = fields.Char('Analytical Code', required = True)
	
# 	# @api.multi
# 	def name_get(self):
# 		res = super(Expense_Prepaid_Group, self).name_get()
# 		data = []
# 		for expense in self:
# 			display_value = ''
# 			display_value += str(expense.group_name) or ""
# 			data.append((expense.id, display_value))
# 		return data

class Expense_Prepaid_Account(models.Model):
	_name = "expense.prepaid.account"
	
	account_code = fields.Char('Account Code')
	account_name = fields.Char('Account Name')

	# @api.multi
	def name_get(self):
		res = super(Expense_Prepaid_Account, self).name_get()
		data = []
		for expense in self:
			display_value = ''
			display_value += str(expense.account_name) or ""
			data.append((expense.id, display_value))
		return data

# class Expense_Approver_Limit(models.Model):
# 	_name = 'hr.expense.approver.limit'

# 	user_id = fields.Many2one('res.users', 'User Name')
# 	from_amount = fields.Float('From Amount Limit')
# 	to_amount = fields.Float('To Amount Limit')
# 	currency_id = fields.Many2one('res.currency', 'Currencies')

# class ProductProduct(models.Model):
# 	_name = "product.product"
# 	_inherit = "product.product"

# 	prepaid_id = fields.Many2many('expense.prepaid','prepaid_product_rel', 'product_id', 'prepaid_id', string='Prepaid Expense')
# 	expense_id = fields.Many2many('hr.expense','hrexpense_product_rel', 'product_id', 'expense_id', string='Expense')
	
class Expense_Prepaid(models.Model):
	_name = 'expense.prepaid'
	_description = 'Expense Prepaid'
	_order = "invoice_date desc, voucher_no desc"


	@api.model
	def get_today(self):
		my_date = fields.Datetime.context_timestamp(self, timestamp=datetime.now())
		return my_date

	def get_sequence(self):
	# 11-01-2021 by M2h ********************************************8
	  sequence = self.env['ir.sequence'].next_by_code('expense.prepaid')
	  year = datetime.now().year
	  month = datetime.now().month
	  seq_no = str(self.env.user.company_id.code)+'-'+'ADV-'+str(year)+'-'+str(month)+sequence
	  print('....................... sequence no is = ',str(seq_no))
	  return seq_no

	state = fields.Selection([
		('draft', 'Draft'),
		('confirm', 'Confirm'),
		('manager_approve','Manager Approved'),
		('approve', 'Finance Approved'),
		('cancel', 'Cancelled'),
		('paid', 'Paid'),
		('closed', 'Close'),
		],
		'Status',default="draft")

	def employee_get(self):        
		emp_id = self.env.context.get('default_employee_name', False)
		if emp_id:
			return emp_id
		ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
		if ids:
			print('.................. id ',ids)
			return ids[0]
		return False

	account_ids = fields.Many2one('account.account', 'Advanced Account Name')
	account_code = fields.Char(related = 'account_ids.code',string='Advanced Account Code')
	name_reference = fields.Char('Reference', required=True)
	voucher_no = fields.Char(string='Invoice No',states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}, copy=False)
	invoice_date = fields.Date('Date', default=get_today, required=True)
	employee_name = fields.Many2one('hr.employee', 'Employee', default=employee_get, domain="[('active','=',True)]", required=True)
	department_id = fields.Many2one('hr.department','Department')
	advance_amount = fields.Float('Advanced Amount')
	manager_approve_date = fields.Date('Manager Approve Date',default=fields.date.today() , states={'manager_approve':[('required', True)]})
	# finance_approve_date = fields.Date('Finance Approve Date')
	# next_approval_person = fields.Many2one('hr.employee','Next Approveal Person')
	expense_total = fields.Float('Expenses Total')
	chart_of_account = fields.Many2one('account.account','Chart of Account')
	currency_id = fields.Many2one('res.currency', 'Currency',required=True, default=119, readonly=True, states={'draft':[('readonly',False)],'cancelled':[('readonly',False)]})
	account_name = fields.Char(' ')
	state_type = fields.Many2one('account.journal', string='Journal')
	cash_account = fields.Many2one('account.account','Paid By',domain=[('user_type_id','=','Bank and Cash')])
	move_line_ids = fields.One2many('account.move.line', 'general_exp_id', string='Journal Advance', store=True)
	exp_move_line_ids = fields.One2many('account.move.line', 'exp_exp_id', string='Journal Expense', store=True)
	adj_move_line_ids = fields.One2many('account.move.line', 'adj_exp_id', string='Journal Adjustment', store=True)
	note = fields.Text('ADVANCE NOTE')
	can_reset = fields.Boolean(compute='_get_can_reset')
	can_approve = fields.Boolean(compute='_get_can_approve')
	paid_date = fields.Date('Cash Paid Date',default=fields.date.today() , states={'approve':[('required', True)], 'paid':[('readonly', True)], 'closed':[('readonly', True)]})
	paid_ref = fields.Char('Paid Ref', states={'paid':[('readonly', True)], 'closed':[('readonly', True)]})
	close_date = fields.Date('Cash Refund Date', states={'closed':[('readonly', True)]})
	close_ref = fields.Char('Close Ref', states={'closed':[('readonly', True)]})
	account_move_id = fields.Many2one('account.move', string='Advance Journal Entry', copy=False, track_visibility="onchange")
	advance_account_move_id = fields.Many2one('account.move', string='Expense Journal Entry', copy=False, track_visibility="onchange")
	adjustment_journal =  fields.Many2one('account.move', string='Adjustment Journal Entry', copy=False, track_visibility="onchange")
	diff_amount = fields.Float('Balance Amount', readonly=True, default=0.0)
	fst_aproval = fields.Many2one('hr.employee', string='First Aproval', domain="[('active','=',True)]")
	snd_aproval = fields.Many2one('hr.employee', string='Second Aproval', domain="[('active','=',True)]" )
	analytic_id = fields.Many2one('account.analytic.account','Analytic Account')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True)
	line_ids = fields.One2many('expense.prepaid.line', 'prepaid_id', 'Expense Lines')
	# TPS===================
	product_id = fields.Many2many('product.product', 'prepaid_product_rel', 'prepaid_id', 'product_id',string='Product')
	# TPS===================

		# product_id = fields.Many2one('product.product', 'Product', required=True, domain="[('can_be_expensed','=',False)]")
	# 20190524 by yma
	# prepaid_type = fields.Many2one('hr.prepaid.type',string='Type')
	currency_rate = fields.Float(string='Currency Rate')
	# md = fields.Boolean('Need MD Approved ?')
	approved_by_id = fields.Many2one('hr.employee',string='Approved By Manager', required=True)
	finance_approved_id = fields.Many2one('hr.employee',string='Finance Approved', domain="[('department_id','=','Finance&Account')]", required=True)
	is_approve = fields.Boolean('Is Approve Manager ?',compute='get_approve',default=False)
	is_approve_finance = fields.Boolean('Is Approve Finance ?',compute='get_approve',default=False)

	def get_approve(self):
		for approve in self:
			reason = False
			finance = False
			to_approve_id = self.env.uid
			print('.................. now id ',to_approve_id,' and approve id ',approve.approved_by_id.user_id)
			# to_approve_id= self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).id
			if to_approve_id == approve.approved_by_id.user_id.id:
				reason = True
			if to_approve_id == approve.finance_approved_id.user_id.id:
				finance = True
			print ('>>>>>>>>>>>>> approve ? >>>>>>>>>>>>>>>>> ', reason)
			approve.is_approve = reason
			approve.is_approve_finance = finance

	@api.onchange('employee_name')
	def onchange_employee(self):
		self.department_id = self.employee_name.department_id.id

	# @api.model
	# @api.onchange('currency_id')
	# def get_apiData(self):
	# 	locale.setlocale(locale.LC_ALL, '')
	# 	url = 'https://forex.cbm.gov.mm/api/latest'
	# 	resp = requests.get(url, verify=False)
	# 	response = json.loads(resp.text)
	# 	api_data = response['rates']
	# 	if self.currency_id:
	# 		if self.currency_id.name != 'MMK':
	# 			self.currency_rate = locale.atof(api_data[self.currency_id.name])
	# 		else:
	# 			self.currency_rate = 1.0

	   
	@api.onchange('line_ids')
	def compute_amount(self):
		if self.line_ids:
			total = 0.0
			print ('why no woking ----------------------------------------------->><<>><<>><<>>')
			for line in self.line_ids:
				total += line.amount
			self.advance_amount = total

	def prepaid_expense_paid(self):
		for expense in self:
			journal = expense.state_type
			expense.paid_date = date.today()
			if not journal:
				raise ValidationError('Define Journal')
			#create the move that will contain the accounting entries
			acc_date = date.today()
			move = self.env['account.move'].create({
				'journal_id': journal.id,
				'company_id': self.env.user.company_id.id,
				'date': acc_date,
				'ref': expense.voucher_no,
				'employee_id': self.employee_name.id,
				# force the name to the default value, to avoid an eventual 'default_name' in the context
				# to set it to '' which cause no number to be given to the account.move when posted.
				'name': '/',
			})
			company_currency = expense.company_id.currency_id
			diff_currency_p = expense.currency_id != company_currency
			#one account.move.line per expense (+taxes..)
			move_lines = expense._move_line_get()

			#create one more move line, a counterline for the total on payable account
			payment_id = False
			total, total_currency, move_lines = expense._compute_expense_totals(company_currency, move_lines, acc_date)
			emp_account = expense.cash_account.id
			if not emp_account:
				raise ValidationError('Define Paid By')

			aml_name = self.employee_name.name + ': ' + self.voucher_no.split('\n')[0][:64]
			move_lines.append({
					'type': 'dest',
					'name': aml_name,
					'analytic_account_id':expense.analytic_id.id,
					'price': total,
					'account_id': emp_account,
					'date_maturity': acc_date,
					'amount_currency': expense.advance_amount*-1,
					'currency_id': False,
					'payment_id': payment_id,
					})

			#convert eml into an osv-valid format
			lines = list(map(lambda x: (0, 0, expense._prepare_move_line(x)), move_lines))
			move.with_context(dont_create_taxes=True).write({'line_ids': lines})
			move.post()
		return self.write({'account_move_id': move.id,'state': 'paid'})

	#expense prepaid
	# @api.multi
	def _prepare_move_line_value(self):
		self.ensure_one()
		aml_name = self.employee_name.name + ': ' + self.voucher_no.split('\n')[0][:64]
		if not self.account_ids:
			raise ValidationError('Define Advance Account')
		move_line = {
			'type': 'src',
			'name': aml_name,
			'analytic_account_id':self.analytic_id.id,
			'price_unit': self.advance_amount,
			'quantity': 1,
			'price': self.advance_amount,
			'account_id': self.account_ids.id,
		}
		return move_line

	

	# @api.multi
	def _compute_expense_totals(self, company_currency, account_move_lines, move_date):
		#print "----------------cumpute expense total--------------------"
		self.ensure_one()
		total = 0.0
		total_currency = 0.0
		for line in account_move_lines:
			#print "line loop"
			line['currency_id'] = False
			line['amount_currency'] = False
			if self.currency_id != company_currency:
				line['currency_id'] = self.currency_id.id
				line['amount_currency'] = line['price']
				#line['price'] = self.currency_id.compute(line['price'], company_currency)
				line['price'] = line['price']
			total -= line['price']
			#print line['price'], line['amount_currency']
			total_currency -= line['amount_currency'] or line['price']
			#raise ValidationError('Emergenncy Stop')
		return total, total_currency, account_move_lines

	# @api.multi
	def _move_line_get(self):
		account_move = []
		for expense in self:
			move_line = expense._prepare_move_line_value()
			account_move.append(move_line)
		return account_move


	# @api.multi
	def unlink(self):
		for rec in self.browse(self.ids):
			if rec.state != 'draft':
				raise ValidationError ('You can only delete draft prepaid expense!')
			for rec_line in rec.line_ids:
				rec_line.unlink()
		return super(Expense_Prepaid, self).unlink()

	

	def _prepare_move_line(self, line):
		#partner_id = self.employee_name.address_home_id.commercial_partner_id.i
		if self.currency_id.id !=self.company_id.currency_id.id:
			print('woking here ---------------------------->><<>>><<>>>',line['price'])
			return {
				'date_maturity': line.get('date_maturity'),
				'general_exp_id': self.id,
				#'partner_id': partner_id,
				'name': line['name'][:64],
				'debit': line['price'] > 0 and line['price'],
				'credit': line['price'] < 0 and - line['price'],
				'account_id': line['account_id'],
				'analytic_line_ids': line.get('analytic_line_ids'),
				'amount_currency': line['price'] > 0 and abs(line.get('amount_currency')) or - abs(line.get('amount_currency')),
				# 'exchange_rate':self.currency_rate,
				'currency_id': self.currency_id.id,
				'tax_line_id': line.get('tax_line_id'),
				'tax_ids': line.get('tax_ids'),
				'quantity': line.get('quantity', 1.00),
				'product_id': line.get('product_id'),
				'product_uom_id': line.get('uom_id'),
				'analytic_account_id': line.get('analytic_account_id'),
				'payment_id': line.get('payment_id'),
			}
		else:
			print('not working here ----------------------->><<>><<>>')
			return {
				'date_maturity': line.get('date_maturity'),
				'general_exp_id': self.id,
				#'partner_id': partner_id,
				'name': line['name'][:64],
				'debit': line['price'] > 0 and line['price'],
				'credit': line['price'] < 0 and - line['price'],
				'account_id': line['account_id'],
				'analytic_line_ids': line.get('analytic_line_ids'),
				# 'exchange_rate':self.currency_rate,
				# 'amount_currency': line['price'] > 0 and abs(line.get('amount_currency')) or - abs(line.get('amount_currency')),
				# 'currency_id': line.get('currency_id'),
				'tax_line_id': line.get('tax_line_id'),
				'tax_ids': line.get('tax_ids'),
				'quantity': line.get('quantity', 1.00),
				'product_id': line.get('product_id'),
				'product_uom_id': line.get('uom_id'),
				'analytic_account_id': line.get('analytic_account_id'),
				'payment_id': line.get('payment_id'),
			}

	def _get_currency(self, cr, uid, context=None):
		user = self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0]
		return user.company_id.currency_id.id

	#@api.one
	def _get_can_reset(self):
		result = False
		is_financial_manager = False
		user = self.env['res.users'].browse()
		group_financial_manager_id = self.env['ir.model.data'].get_object_reference('account', 'group_account_manager')[1]
		if group_financial_manager_id in [g.id for g in user.groups_id]:
			is_financial_manager = True

		for expense in self.browse(self.id):
			if expense.state in ['confirm','cancel']:
				if is_financial_manager:
					result = False
				elif expense.employee_name and expense.employee_name.user_id and expense.employee_name.user_id.id == self.env.uid:
					result = True
		self.can_reset = result

	# @api.one
	def _get_can_approve(self):
		#print '--------------------GET CAN APPROVE-------------------------'
		# result = False
		# #print self.env.user , self.fst_aproval.user_id
		# if self.fst_aproval.user_id == self.env.user:
		#     #print "Correct User"
		#     self.can_approve = True
		self.can_approve = True

	@api.model
	def create(self, data):
		data['voucher_no'] = self.get_sequence()
		record_id = super(Expense_Prepaid, self).create(data)
		return record_id

	# @api.multi
	def name_get(self):
		res = super(Expense_Prepaid, self).name_get()
		data = []
		for expense in self:
			display_value = ''
			display_value += str(expense.voucher_no) or ""
			data.append((expense.id, display_value))
		return data

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		args = args or []
		recs = self.browse()
		if not recs:
			recs = self.search([('name_reference', operator, name)] + args, limit=limit)
		if not recs:
			recs = self.search([('voucher_no', operator, name)] + args, limit=limit)
		return recs.name_get()

	def prepaid_expense_confirm(self):
		return self.write({'state': 'confirm'})

	# def md_approved(self):
	# 	return self.write({'state': 'md'})

	def prepaid_expense_draft(self):
		return self.write({'state': 'draft'})

	######## Line Manager #########

	def prepaid_expense_manager_accept(self):
		return self.write({'state': 'manager_approve'})

	def approve(self):
		return self.write({'state': 'approve'})

	# @api.one
	# def prepaid_expense_manager_accept_snd(self):
	# 	return self.write({'state': 'manager_accepted_snd'})

	# @api.one
	def cancel(self):
		return self.write({'state': 'cancel'})

		

	def prepaid_expense_cashier_closed(self):
		date = self.get_today()
		close_ref = self.name_reference
		return self.write({'close_date': date,'state': 'closed','close_ref':close_ref})

	#for closed function
	# @api.multi
	def _move_line_get_closed(self):
		account_move = []
		for expense in self:
			move_line = expense._prepare_move_line_value_closed()
			account_move.append(move_line)
		return account_move

	# @api.multi
	def _prepare_move_line_value_closed(self):
		self.ensure_one()
		aml_name = self.employee_name.name + ': ' + self.voucher_no.split('\n')[0][:64]
		move_line = {
			'type': 'src',
			'name': aml_name,
			'price_unit': self.advance_amount,
			'quantity': 1,
			'price': self.advance_amount,
			'account_id': self.cahs.id,
		}
		return move_line

	def expense_accept(self, cr, uid, ids, context=None):
		for expense in self.browse(cr, uid, ids):
		  if not expense.manager_approve_date:
			  raise ValidationError('You must choose approve date!')
		return self.write(cr, uid, ids, {'state': 'accepted'}, context=context)
	  
	def expense_post(self, cr, uid, ids, context=None):
		for expense in self.browse(cr, uid, ids):
		  if not expense.post_date:
			  raise ValidationError('You must choose post date!')
		  if not expense.advance_amount > 0.0:
			  raise ValidationError('You must add advanced amount!')
		return self.write(cr, uid, ids, {'state': 'paid'}, context=context)
	  
	def expense_close(self, cr, uid, ids, context=None):
		for expense in self.browse(cr, uid, ids):
		  if not expense.close_date:
			  raise ValidationError('You must choose close date!')
		return self.write(cr, uid, ids, {'state': 'closed'}, context=context)

	def expense_canceled(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state': 'cancelled'}, context=context)

	def reset_to_draft(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {'state': 'draft'}, context=context)

	# reopen when error solve
		 
	# @api.one
	# @api.onchanage('employee_name')
	# def onchange_employee_name(self):
	#     emp_obj = self.env['hr.employee']
	#     # next_approval_person = False
	#     # company_id = False
	#     if self.employee_name:
	#         employee = emp_obj.search([('id','=',self.employee_name.id)])
	#         next_approval_person = employee.parent_id.id
	#         company_id = employee.company_id.id
	#         self.next_approval_person = next_approval_person
	#         self.company_id = company_id


class Expense_Prepaid_Line(models.Model):
	_name = 'expense.prepaid.line'
	_description = 'Expense Prepaid Line'    

	prepaid_id = fields.Many2one('expense.prepaid', 'Title', ondelete='cascade', select=True)    
	product_id = fields.Many2one('product.product', 'Product', domain="[('can_be_expensed','=',True)]")
	sequence = fields.Integer('Sequence', select=True, help="Gives the sequence order when displaying a list of expense lines.")
	date_value = fields.Date('Date',required=True,store=True)
	analytic_account = fields.Many2one('account.analytic.account','Analytic account',related="prepaid_id.analytic_id")
	account_ids = fields.Many2one('account.account', string='Account Name',store=True)
	account_code = fields.Char(string='Account Code',related='account_ids.code',store=True)
	amount = fields.Float(string='Total Amount',store=True)
	line_no = fields.Integer(compute='_get_line_numbers', string='Sr')
	ref = fields.Char('Description', required=True) 

	@api.model
	@api.onchange('product_id')
	def onchange_product_id(self):
		if self.product_id:
			product = self.env['product.product'].browse(self.product_id)
			product=product.id
			amount_unit = product.standard_price
			self.uom_id = product.uom_id.id
			self.date_value = self.prepaid_id.invoice_date
			self.account_ids = self.product_id.property_account_expense_id
			self.analytic_account = self.prepaid_id.analytic_id
			self.ref = self.prepaid_id.name_reference

	# @api.multi
	def _get_line_numbers(self):
		for expense in self.mapped('prepaid_id'):
			line_no = 1
			for line in expense.line_ids:
				line.line_no = line_no
				line_no += 1

	@api.model
	def default_get(self, fields_list):
		res = super(Expense_Prepaid_Line, self).default_get(fields_list)
		res.update({'line_no': len(self._context.get('line_ids', [])) + 1}) 
		return res


	@api.model
	def create(self,data):
		if data:
			#print data,"Data_______"
			prepaid_id = super(Expense_Prepaid_Line, self).create(data)
		return prepaid_id
	
	# @api.one
	def write(self,vals):
		flag = super(Expense_Prepaid_Line, self).write(vals)

		return flag


# class Expense_Prepaid_Advance_Account(models.Model):
# 	_name = "expense.prepaid.adv_account"
	
# 	account_code = fields.Char('Account Code')
# 	account_name = fields.Char('Account Name')

# 	def name_get(self):
# 		res = super(Expense_Prepaid_Advance_Account, self).name_get()
# 		data = []
# 		for expense in self:
# 			display_value = ''
# 			display_value += str(expense.account_name) or ""
# 			data.append((expense.id, display_value))
# 		return data

# class rescurrency_inherit(models.Model):

# 	_inherit = 'res.currency'

# 	base = fields.Boolean('Base')
# 	active = fields.Boolean('Active',default="True")
# 	line_id = fields.One2many('res.currency.line','res_id')

# class rescurrency_line(models.Model):

# 	_name = 'res.currency.line'

# 	res_id = fields.Many2one('res.currency','Currency Line')
# 	date=fields.Date('Date')
# 	rate = fields.Float('Rate')




		
		