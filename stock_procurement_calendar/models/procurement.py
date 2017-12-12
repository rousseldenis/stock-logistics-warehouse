# -*- coding: utf-8 -*-
# Copyright 2017 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ProcurementOrder(models.Model):

    _inherit = 'procurement.order'

    procurement_location_calendar_id = fields.Many2one(
        'procurement.calendar',
        help="The calendar defined for the procurement location"
    )
    procurement_calendar_id = fields.Many2one(
        'procurement.calendar',
        help="The calendar defined for the procurement source"
    )
    procurement_location_attendance_id = fields.Many2one(
        'procurement.calendar.attendance',
        help="The attendance defined for the procurement location"
    )
    procurement_attendance_id = fields.Many2one(
        'procurement.calendar.attendance',
        help="The attendance defined for the procurement source"
    )
    aimed_attendance_ids = fields.Many2many(
        'procurement.calendar.attendance',
        compute='_compute_aimed_attendance_ids'
    )
    scheduled_next_attendance_id = fields.Many2one(
        'procurement.calendar.attendance',
        compute='_compute_scheduled_next_attendance_id',
        help="The next attendance scheduled for the procurement source. This "
        "is the one that will be used when procurement order will be run"
    )
    scheduled_next_attendance_date = fields.Datetime(
        compute='_compute_scheduled_next_attendance_id'
    )

    @api.multi
    def get_attendances_for_weekday(self, day_dt):
        """ Given a day datetime, return matching attendances """
        self.ensure_one()
        weekday = day_dt.weekday()
        attendances = self.env['procurement.calendar.attendance']

        for attendance in self.aimed_attendance_ids.filtered(
                lambda att: int(att.dayofweek) == weekday and
                not (att.date_from and fields.Date.from_string(
                    att.date_from) > day_dt.date()) and
                not (att.date_to and fields.Date.from_string(
                    att.date_to) < day_dt.date())):
            attendances |= attendance
        return attendances

    @api.multi
    @api.depends('aimed_attendance_ids')
    def _compute_scheduled_next_attendance_id(self, limit=100):
        """
        Compute the next attendance and the next scheduled date
        :param limit:
        :return:
        """
        for procurement in self.filtered(
                lambda p: p.aimed_attendance_ids):
            procurement_date = fields.Datetime.from_string(
                procurement.date_planned) or fields.Datetime.from_string(
                fields.Datetime.now())
            i = 0
            while i <= limit:

                attendances = procurement.get_attendances_for_weekday(
                    procurement_date)
                if attendances:
                    procurement.scheduled_next_attendance_id = attendances[0]
                    procurement.scheduled_next_attendance_date =\
                        procurement_date
                    break
                procurement_date = procurement_date + relativedelta(days=1)
                i += 1

    @api.multi
    def _compute_aimed_attendance_ids(self):
        """
        Helper field to compute the attendances for the weekday
        :return:
        """
        attendance_obj = self.env['procurement.calendar.attendance']
        for procurement in self.filtered(lambda p: p.procurement_calendar_id):
            attendances = attendance_obj.search(
                self._get_source_attendance_domain()
            )
            # Filtered product specific attendances
            product_attendances = attendances.filtered(
                lambda a: any(
                    product_id == procurement.product_id.id for product_id in
                    a.product_ids.ids))
            procurement.aimed_attendance_ids =\
                product_attendances or attendances

    @api.multi
    def _assign_calendar(self):
        """
        We search for calendar defined for the procurement location
        :return:
        """
        calendar_obj = self.env['procurement.calendar']
        for procurement in self:
            # 1 Search for calendars with location defined
            calendar = calendar_obj.search(
                procurement._get_calendar_location_domain(),
                limit=1
            )
            if not calendar:
                # 2 Search for calendars with warehouse defined
                calendar = calendar_obj.search(
                    procurement._get_calendar_location_warehouse_domain(),
                    limit=1
                )
            procurement.procurement_location_calendar_id = calendar

    @api.multi
    def _assign_attendance(self):
        for procurement in self.filtered(
                lambda p: p.procurement_location_calendar_id):
            # TODO: put procurement.date_planned ? # pylint: disable=W0511
            date_t = datetime.strptime(
                fields.Datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
            cal = procurement.procurement_location_calendar_id
            attendances = cal.get_attendances_for_weekday(date_t)
            if attendances:
                procurement.procurement_location_attendance_id = attendances[0]

    @api.multi
    def _get_source_attendance_domain(self, forward=True):
        self.ensure_one()
        domain = []
        if self.procurement_calendar_id:
            domain = expression.AND([
                [('procurement_calendar_id',
                  '=',
                  self.procurement_calendar_id.id)],
                domain
            ])
        else:
            return domain
        # Filter product dependant attendances
        product_domain = expression.OR([
            [('product_dependant', '=', False)],
            [('product_ids', 'in', self.product_id.ids)]
        ])
        domain = expression.AND([
            product_domain, domain
        ])
        return domain

    @api.multi
    def _assign_source_attendance(self):
        """
        We check here the attendance set on procurement and find the right
        one for the source
        :return:
        """
        for procurement in self.filtered(
                lambda p: p.procurement_calendar_id):
            # TODO: Replace with procurement.date_planned pylint: disable=W0511
            procurement.procurement_attendance_id =\
                procurement.scheduled_next_attendance_id

    @api.multi
    def _assign_source_calendar(self):
        """
        We search for calendar defined for the procurement source
        :return:
        """
        calendar_obj = self.env['procurement.calendar']
        not_assigned_procurements = self.filtered(
            lambda p: not p.procurement_calendar_id)
        for procurement in not_assigned_procurements:
            # 1 Search for calendars with location defined
            calendar = calendar_obj.search(
                procurement._get_calendar_location_domain(
                    location=procurement.rule_id.location_src_id),
                limit=1
            )
            # 2 Search for calendars with warehouse defined
            if not calendar:
                calendar = calendar_obj.search(
                    procurement._get_calendar_location_warehouse_domain(
                        location=procurement.rule_id.location_src_id
                    ),
                    limit=1
                )
            if calendar:
                procurement.procurement_calendar_id = calendar

    @api.multi
    def _get_calendar_location_domain(self, location=False):
        if not location:
            location = self.mapped('location_id')
        domain = [('location_id', 'in', location.ids)]
        return domain

    @api.multi
    def _get_calendar_location_warehouse_domain(self, location=False):
        self.ensure_one()
        if not location:
            location = self.location_id
        domain = [(
            'warehouse_id.view_location_id',
            'parent_of',
            location.id
        )]
        return domain

    @api.multi
    def _get_calendar_domain(self):
        # TODO
        self.ensure_one()
        domain = []

        if self.orderpoint_id:
            seller = self.product_id._select_seller()
            domain_seller = expression.OR([
                [('partner_id', '=', seller.id)],
                [('partner_id', '=', False)]
            ])
            domain = expression.AND([
                domain_seller,
                domain
            ])
        return domain

    def _get_stock_move_values(self):
        res = super(ProcurementOrder, self)._get_stock_move_values()
        # scheduled_date = self._get_procurement_scheduled_date()
        return res

    def run(self, autocommit=False):
        self._assign_calendar()
        self._assign_attendance()
        res = super(ProcurementOrder, self).run(autocommit=autocommit)

        return res

    def _assign(self):
        """
        We catch the rule assignement to update calendar procurement
        :return:
        """
        res = super(ProcurementOrder, self)._assign()
        if res and self.rule_id:
            self._assign_source_calendar()
            self._assign_source_attendance()
        return res
