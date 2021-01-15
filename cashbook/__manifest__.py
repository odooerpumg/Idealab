##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Cash Book',
    'version' : '10.0.0.5',
    'summary':'Accounting',
    'author': 'Myat Min Hein(M2h)',
    'depends':['account','mail'],
    'category': '',
    'description': """

Cash Book Form
===========================

Alter debit & Credit for COA.

    """,
    'application':True,
    'data':['views/cashbook_view.xml','security/ir.model.access.csv'],
    
}
