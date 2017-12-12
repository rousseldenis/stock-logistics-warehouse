# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_compare, float_round


class StockWarehouseOrderpoint(models.Model):

    _name = 'stock.warehouse.orderpoint'
    _inherit = ['stock.warehouse.orderpoint', 'procurement.calendar.mixin']

    _location_field = 'location_id'

    procurement_calendar_id = fields.Many2one(
        'procurement.calendar',
        compute='_compute_procure_recommended'
    )
    procurement_attendance_id = fields.Many2one(
        'procurement.calendar.attendance',
        compute='_compute_procure_recommended'
    )
    location_procurement_calendar_id = fields.Many2one(
        'procurement.calendar',
        _compute='_compute_location_procurement_calendar_id'
    )
    scheduled_attendance_date = fields.Datetime(
        compute='_compute_procure_recommended'
    )
    procure_recommended_qty = fields.Float(
        compute='_compute_procure_recommended'
    )
    expected_seller_id = fields.Many2one(
        'product.supplierinfo',
        string='Expected Supplier',
        compute='_compute_expected_seller_id',
        help="The computed seller at this moment and for the expected "
             "ordering quantities"
    )

    @api.model
    def _get_group(self):
        now_date = datetime.utcnow()
        return [(now_date, None)]

    @api.multi
    def _get_procure_recommended_qty(self, attendance=None):
        res = {}
        location_data = defaultdict(
            lambda: dict(products=self.env['product.product'],
                         orderpoints=self.env['stock.warehouse.orderpoint'],
                         groups=list()))
        for orderpoint in self:
            key = (orderpoint.location_id.id, attendance.id)
            location_data[key]['products'] += orderpoint.product_id
            location_data[key]['orderpoints'] += orderpoint
            res[orderpoint.id] = 0.0

        for location_id, location_data in location_data.iteritems():
            location_orderpoints = location_data['orderpoints']
            product_context = dict(self._context,
                                   location=location_orderpoints[
                                       0].location_id.id)
            substract_quantity = location_orderpoints and not isinstance(
                location_orderpoints.id,
                models.NewId) and location_orderpoints.\
                subtract_procurements_from_orderpoints() or 0.0

            product_quantity = location_data['products'].with_context(
                product_context)._product_available()
            for orderpoint in location_orderpoints:
                if not orderpoint.product_id:
                    continue
                op_product_virtual = \
                    product_quantity[orderpoint.product_id.id][
                        'virtual_available']
                if float_compare(
                        op_product_virtual,
                        orderpoint.product_min_qty,
                        precision_rounding=orderpoint.product_uom.rounding) \
                        <= 0:
                    qty = max(
                        orderpoint.product_min_qty,
                        orderpoint.product_max_qty) - op_product_virtual
                    remainder = orderpoint.qty_multiple > 0 and\
                        qty % orderpoint.qty_multiple or 0.0

                    if float_compare(
                            remainder,
                            0.0,
                            precision_rounding=orderpoint.product_uom.rounding
                    ) > 0:
                        qty += orderpoint.qty_multiple - remainder
                    qty -= substract_quantity[orderpoint.id]
                    res[orderpoint.id] = float_round(
                        qty,
                        precision_rounding=orderpoint.product_uom.rounding
                    )
        return res

    @api.multi
    @api.depends('product_id', 'procure_recommended_qty')
    def _compute_expected_seller_id(self):
        for orderpoint in self.filtered(lambda o: o.product_id):
            orderpoint.expected_seller_id = \
                orderpoint.product_id._select_seller(
                    quantity=orderpoint.procure_recommended_qty)

    @api.multi
    @api.depends('product_id', 'location_id', 'product_min_qty',
                 'product_max_qty')
    def _compute_procure_recommended(self, with_calendar=False, limit=100):
        '''
        if not with_calendar:
            return super(
                StockWarehouseOrderpoint, self)._compute_procure_recommended()
        '''
        for orderpoint in self:
            vals = {
                'location_id': orderpoint.location_id,
                'product_id': orderpoint.product_id
            }
            virtual_procurement = self.env['procurement.order'].new(vals)
            virtual_rule = virtual_procurement._find_suitable_rule()
            calendars = self.env['procurement.calendar']
            if virtual_rule and virtual_rule.action == 'buy':
                calendars = self.env['procurement.calendar'].search(
                    orderpoint._get_calendar_supplier_domain())
            procurement_date = fields.Datetime.from_string(
                fields.Datetime.now())
            i = 0
            while i <= limit:
                attendances = orderpoint.get_attendances_for_weekday(
                    procurement_date,
                    calendars)
                attendances_with_partner = attendances.filtered(
                    lambda a: a.procurement_calendar_id.partner_id)
                context_date = fields.Datetime.to_string(procurement_date)
                for attendance in attendances_with_partner:
                    # The case we have a partner defined
                    # We don't force partner in _select_seller method as
                    # in procurement, it will select automatically the good
                    # one depending on quantities
                    partner = attendance.procurement_calendar_id.partner_id
                    seller = orderpoint.product_id._select_seller(
                        quantity=orderpoint.procure_recommended_qty,
                        date=procurement_date,
                        uom_id=orderpoint.product_id.uom_id)
                    if seller.name == partner:
                        orderpoint.procurement_attendance_id = attendance
                        orderpoint.procurement_calendar_id = \
                            attendance.procurement_calendar_id
                        orderpoint.scheduled_attendance_date = \
                            procurement_date
                        # Get expected quantity
                        procure_recommended_qty = orderpoint.with_context(
                            from_date=context_date).\
                            _get_procure_recommended_qty(attendance)
                        orderpoint.procure_recommended_qty = \
                            procure_recommended_qty[orderpoint.id]
                        i = limit + 1
                        break
                attendances_without_partner = attendances -\
                    attendances_with_partner
                for attendance in attendances_without_partner:
                    procure_recommended_qty = orderpoint.with_context(
                        from_date=context_date)._get_procure_recommended_qty(
                        attendance)
                    orderpoint.procure_recommended_qty =\
                        procure_recommended_qty[orderpoint.id]
                    i = limit + 1
                    break

                procurement_date = procurement_date + relativedelta(days=1)
                i += 1

    @api.multi
    def get_attendances_for_weekday(self, day_dt, calendars):
        """ Given a day datetime, return matching attendances """
        self.ensure_one()
        weekday = day_dt.weekday()
        attendances = self.env['procurement.calendar.attendance']

        domain = self._get_attendances_domain()
        domain = expression.OR([
            [('procurement_calendar_id', 'in', calendars.ids)],
            domain
        ])
        attendances = attendances.search(domain)

        product_attendances = attendances.filtered(
            lambda a: any(
                product_id == self.product_id.id for product_id in
                a.product_ids.ids))
        filtered_attendances = product_attendances or attendances

        result_attendances = self.env['procurement.calendar.attendance']

        for attendance in filtered_attendances.filtered(
                lambda att: int(att.dayofweek) == weekday and not (
                    att.date_from and
                    fields.Date.from_string(att.date_from) > day_dt.date()
                ) and not (
                    att.date_to and fields.Date.from_string(att.date_to) <
                    day_dt.date()
                )):
            result_attendances |= attendance
        return result_attendances

    def _get_attendances_domain(self):
        domain = []
        product_domain = expression.OR([
            [('product_dependant', '=', False)],
            [('product_ids', 'in', self.product_id.ids)]
        ])
        domain = expression.AND([
            product_domain, domain
        ])
        return domain

    @api.multi
    def _get_calendar_supplier_domain(self):
        sellers = self.product_id.seller_ids.mapped('name')
        domain = []
        if sellers:
            domain = [('partner_id', 'in', sellers.ids)]
        return domain
