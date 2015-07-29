# -*- coding: utf-8 -*-
##############################################################################
#
#    Authors: Laetitia Gangloff
#    Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
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

from openerp.osv import osv, fields


class ModelTotalSaleSqlMatView(osv.Model):

    _name = 'total.sale.mat.view'
    _description = u"Total Sales"
    _auto = False
    _order = 'name'

    _inherit = [
        'abstract.materialized.sql.view',
    ]

    _columns = {
        'ref': fields.char('Reference'),
        'name': fields.char('Customer'),
        'lang': fields.char('Language'),
        'title': fields.char('Title'),
        'first_name': fields.char('First Name'),
        'last_name': fields.char('Last Name'),
        'zip': fields.char('zip'),
        'birthday': fields.date('Birthday'),
        'email': fields.char('Email'),
        'last_drive': fields.many2one('res.company', 'Last Drive'),
        'preferred_drive': fields.many2one('res.company', 'Preferred Drive'),
        'diff_drive': fields.boolean('Diff Drive'),
        'sale_order_count': fields.integer('# of sales order'),
        'promo_count': fields.integer('# of Promo code'),
        'average_basket': fields.float('Average Basket'),
        'company_id': fields.many2one('res.company', 'Drive'),
        'sale_order_count_drive': fields.integer('# of sales order Drive'),
        'promo_count_drive': fields.integer('# of Promo code Drive'),
        'average_basket_drive': fields.float('Average Basket Drive'),
        'total_product_diff': fields.float('Number of ordered reference Drive'),
        'total_qty_drive': fields.float('Quantity ordered Drive'),
        'total_ttc_drive': fields.float('Total TVAC Drive'),
        'last_order_date': fields.date('Date de la dernière commande Drive'),
        'first_order_date': fields.date('Date de la première commande Drive'),
        'carrier_id': fields.many2one('delivery.carrier', 'Delivery Methods')
    }

    _sql_view_definition = """
with partner_info as (
select p.id as partner_id,
p.ref as ref,
p.name as name,
p.lang as lang,
tit.name as title,
p.first_name as first_name,
p.last_name as last_name,
p.zip as zip,
p.birthday as birthday,
p.email as email

from res_partner p
left join res_partner_title tit on p.title = tit.id

where p.customer is True
),
sale_info as (
select so.partner_id as partner_id,

(select so_last.company_id from sale_order so_last
 where so.partner_id = so_last.partner_id
 and so_last.state = 'done'
 order by so_last.date_order desc limit 1) as last_drive,

(select so_pref.company_id from sale_order so_pref
 where so.partner_id = so_pref.partner_id
 and so_pref.state = 'done'
 group by so_pref.company_id
 order by count(so_pref.*) desc limit 1) as preferred_drive,

(select so_last.company_id from sale_order so_last
 where so_last.state = 'done'
 and so_last.partner_id = so.partner_id
 order by so_last.date_order desc limit 1)
 <> 
(select so_pref.company_id from sale_order so_pref
 where so_pref.state = 'done'
 and so_pref.partner_id = so.partner_id
 group by so_pref.company_id
 order by count(so_pref.*) desc limit 1) as diff_drive,

(select count(soc2.*) from sale_order soc2
where soc2.state = 'done'
and soc2.partner_id = so.partner_id) as sale_order_count,
(select count(soc3.*) from sale_order soc3
where soc3.state = 'done'
and soc3.discount_code is not null
and soc3.partner_id = so.partner_id) as promo_count,

(select sum(soc.amount_total)/count(soc.*) from sale_order soc
where soc.state = 'done'
and soc.partner_id = so.partner_id) as average_basket,

so.company_id as company_id,
count(so.id) as sale_order_count_drive,
(sum(so.amount_total)/count(so.id)) as average_basket_drive,

(select count(distinct sol.product_packaging)
 from sale_order_line sol
 where sol.order_id in (select so_for_line.id
            from sale_order so_for_line
            where so_for_line.company_id = so.company_id
            and so_for_line.partner_id = so.partner_id
            and so.carrier_id = so_for_line.carrier_id
            and so_for_line.state = 'done')) as total_product_diff,

(select sum(sol.product_uom_qty)
 from sale_order_line sol
 where sol.order_id in (select so_for_line.id
            from sale_order so_for_line
            where so_for_line.company_id = so.company_id
            and so_for_line.partner_id = so.partner_id
            and so.carrier_id = so_for_line.carrier_id
            and so_for_line.state = 'done')) as total_qty_drive,

sum(so.amount_total) as total_ttc_drive,
max(so.date_order) as last_order_date,
min(so.date_order) as first_order_date,
(select count(soc4.*) from sale_order soc4
where soc4.state = 'done'
and soc4.discount_code is not null
and soc4.company_id = so.company_id
and so.carrier_id = soc4.carrier_id
and soc4.partner_id = so.partner_id) as promo_count_drive,
so.carrier_id as carrier_id

from sale_order so

where so.state = 'done' and so.carrier_id is not null

group by so.partner_id, so.company_id, so.carrier_id

union all

select so.partner_id as partner_id,

(select so_last.company_id from sale_order so_last
 where so.partner_id = so_last.partner_id
 and so_last.state = 'done'
 order by so_last.date_order desc limit 1) as last_drive,

(select so_pref.company_id from sale_order so_pref
 where so.partner_id = so_pref.partner_id
 and so_pref.state = 'done'
 group by so_pref.company_id
 order by count(so_pref.*) desc limit 1) as preferred_drive,

(select so_last.company_id from sale_order so_last
 where so_last.state = 'done'
 and so_last.partner_id = so.partner_id
 order by so_last.date_order desc limit 1)
 <> 
(select so_pref.company_id from sale_order so_pref
 where so_pref.state = 'done'
 and so_pref.partner_id = so.partner_id
 group by so_pref.company_id
 order by count(so_pref.*) desc limit 1) as diff_drive,

(select count(soc2.*) from sale_order soc2
where soc2.state = 'done'
and soc2.partner_id = so.partner_id) as sale_order_count,
(select count(soc3.*) from sale_order soc3
where soc3.state = 'done'
and soc3.discount_code is not null
and soc3.partner_id = so.partner_id) as promo_count,

(select sum(soc.amount_total)/count(soc.*) from sale_order soc
where soc.state = 'done'
and soc.partner_id = so.partner_id) as average_basket,

so.company_id as company_id,
count(so.id) as sale_order_count_drive,
(sum(so.amount_total)/count(so.id)) as average_basket_drive,

(select count(distinct sol.product_packaging)
 from sale_order_line sol
 where sol.order_id in (select so_for_line.id
            from sale_order so_for_line
            where so_for_line.company_id = so.company_id
            and so_for_line.partner_id = so.partner_id
            and so_for_line.carrier_id is null
            and so_for_line.state = 'done')) as total_product_diff,

(select sum(sol.product_uom_qty)
 from sale_order_line sol
 where sol.order_id in (select so_for_line.id
            from sale_order so_for_line
            where so_for_line.company_id = so.company_id
            and so_for_line.partner_id = so.partner_id
            and so_for_line.carrier_id is null
            and so_for_line.state = 'done')) as total_qty_drive,

sum(so.amount_total) as total_ttc_drive,
max(so.date_order) as last_order_date,
min(so.date_order) as first_order_date,
(select count(soc4.*) from sale_order soc4
where soc4.state = 'done'
and soc4.discount_code is not null
and soc4.company_id = so.company_id
and soc4.carrier_id is null
and soc4.partner_id = so.partner_id) as promo_count_drive,
so.carrier_id as carrier_id

from sale_order so

where so.state = 'done' and so.carrier_id is null

group by so.partner_id, so.company_id, so.carrier_id)


select
    row_number() over () as id,
    partner_info.ref,
    partner_info.name,
    partner_info.lang,
    partner_info.title,
    partner_info.first_name,
    partner_info.last_name,
    partner_info.zip,
    partner_info.birthday,
    partner_info.email,
    sale_info.last_drive,
    sale_info.preferred_drive,
    coalesce(sale_info.diff_drive, False) as diff_drive,
    coalesce(sale_info.sale_order_count, 0) as sale_order_count,
    coalesce(sale_info.promo_count, 0) as promo_count,
    coalesce(sale_info.average_basket, 0) as average_basket,
    sale_info.company_id,
    coalesce(sale_info.sale_order_count_drive, 0) as sale_order_count_drive,
    coalesce(sale_info.promo_count_drive, 0) as promo_count_drive,
    coalesce(sale_info.average_basket_drive, 0) as average_basket_drive,
    coalesce(sale_info.total_product_diff, 0) as total_product_diff,
    coalesce(sale_info.total_qty_drive, 0) as total_qty_drive,
    coalesce(sale_info.total_ttc_drive, 0) as total_ttc_drive,
    sale_info.last_order_date,
    sale_info.first_order_date,
    sale_info.carrier_id

from partner_info
left outer join sale_info on (partner_info.partner_id = sale_info.partner_id)
"""
