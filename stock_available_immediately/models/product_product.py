# -*- coding: utf-8 -*-
# Copyright 2014 Camptocamp, Akretion, Numérigraphe
# Copyright 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    @api.depends('virtual_available', 'incoming_qty')
    def _compute_immediately_usable_qty(self):
        super(ProductProduct, self)._compute_immediately_usable_qty()
        for prod in self:
            prod.immediately_usable_qty -= prod.incoming_qty
