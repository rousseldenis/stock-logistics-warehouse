# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class ProcurementOrder(models.Model):

    _inherit = 'procurement.order'

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

    @api.multi
    def _assign_source_calendar(self):
        """
        We search for calendar defined for the procurement source
        :return:
        """

        calendar_obj = self.env['procurement.calendar']
        buy_procurements = self.filtered(lambda p: p.rule_id.action == 'buy')
        other_procurements = self - buy_procurements
        for procurement in buy_procurements:
            calendar = calendar_obj.search(
                procurement._get_calendar_supplier_domain(),
                limit=1
            )
            if calendar:
                procurement.procurement_calendar_id = calendar
        return super(
            ProcurementOrder, other_procurements)._assign_source_calendar()

    @api.multi
    def _get_calendar_supplier_domain(self):
        seller = self.product_id._select_seller(quantity=self.product_qty)
        domain = []
        if seller:
            domain = [('partner_id', '=', seller.name.id)]
        return domain
