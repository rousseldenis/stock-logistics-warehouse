# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProcurementOrder(models.Model):

    _inherit = 'procurement.order'

    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(
            orderpoint_ids[0])
        res_groups = []
        date_groups = orderpoint._get_group()
        for date, group in date_groups:
            if orderpoint.procurement_calendar_id and\
                    orderpoint.scheduled_attendance_date:
                res_groups += [{
                    'to_date': fields.Datetime.from_string(
                        orderpoint.scheduled_attendance_date),
                    'procurement_values': {
                        'group': group,
                        'date': fields.Datetime.from_string(
                            orderpoint.scheduled_attendance_date),
                    }
                }]
            else:
                res_groups += [{
                    'to_date': False,
                    'procurement_values': {
                        'group': group,
                        'date': date,
                    }
                }]
        return res_groups

    def _assign_procurement_source_calendar(self):
        assigned_procurements = self.env['procurement.order']
        for procurement in self.filtered(lambda p: p.orderpoint_id):
            calendar = procurement.orderpoint_id.procurement_calendar_id
            if calendar:
                procurement.procurement_calendar_id = calendar
                assigned_procurements += procurement
        return super(ProcurementOrder, self - assigned_procurements).\
            _assign_procurement_source_calendar()

    @api.multi
    def _prepare_purchase_order(self, partner):
        res = super(ProcurementOrder, self)._prepare_purchase_order(
            partner=partner)
        if self.procurement_attendance_id:
            res.update({
                'date_order': self.scheduled_next_attendance_date,
                'procurement_attendance_id': self.procurement_attendance_id.id,
            })
        return res

    @api.multi
    def _make_po_get_domain(self, partner):
        domain = super(ProcurementOrder, self)._make_po_get_domain(
            partner=partner)
        if self.procurement_attendance_id:
            domain += (('procurement_attendance_id',
                        '=',
                        self.procurement_attendance_id.id
                        )),
        return domain

    def _make_po_select_supplier(self, suppliers):
        suppliers_in_calendars = suppliers.filtered(
            lambda s: s.name == self.procurement_calendar_id.partner_id)
        if suppliers_in_calendars:
            return suppliers_in_calendars[0]
        else:
            return super(ProcurementOrder, self)._make_po_select_supplier(
                suppliers)

    @api.model
    def _procurement_from_orderpoint_get_grouping_key(self, orderpoint_ids):
        orderpoint = self.env['stock.warehouse.orderpoint'].browse(
            orderpoint_ids[0])
        return (
            orderpoint.location_id.id,
            orderpoint.procurement_attendance_id.id
        )
