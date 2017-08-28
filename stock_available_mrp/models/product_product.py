# -*- coding: utf-8 -*-
# © 2014 Numérigraphe SARL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from collections import Counter

from odoo import models, fields, api

from odoo.exceptions import AccessError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Needed for fields dependencies
    # When self.potential_qty is compute, we want to force the ORM
    # to compute all the components potential_qty too.
    component_ids = fields.Many2many(
        comodel_name='product.product',
        compute='_get_component_ids',
    )

    @api.depends('virtual_available', 'component_ids.potential_qty')
    def _compute_available_quantities(self):
        super(ProductProduct, self)._compute_available_quantities()

    @api.multi
    def _compute_available_quantities_dict(self):
        res = super(ProductProduct, self)._compute_available_quantities_dict()

        # avoid to make one query per product to find if it has a bom or not
        domain = [('product_id', 'in', self.ids)]
        product_tmpl_ids = []
        product_ids = self.env['mrp.bom'].search(domain).mapped('product_id')
        for product in self:
            if product.id not in product_ids.ids:
                product_tmpl_ids.append(product.product_tmpl_id.id)
        domain = [('product_id', '=', False),
                  ('product_tmpl_id', 'in', product_tmpl_ids)]
        bom_template = self.env['mrp.bom'].search(domain)
        product_ids = product_ids.ids
        template_ids = bom_template.mapped('product_tmpl_id.id')

        if not template_ids and not product_ids:
            return res

        for product in self:
            if product.id not in product_ids and product.product_tmpl_id.id \
                    not in template_ids:
                continue
            bom = self.env['mrp.bom']._bom_find(product=product)
            if not bom:
                res[product.id]['potential_qty'] = 0.0
                continue

            # Need by product (same product can be in many BOM lines/levels)
            try:
                component_needs = self._get_components_needs(product, bom)
            except AccessError:
                # If user doesn't have access to BOM
                # he can't see potential_qty
                component_needs = None

            if not component_needs:
                # The BoM has no line we can use
                potential_qty = 0.0

            else:
                # Find the lowest quantity we can make with the stock at hand
                components_potential_qty = min(
                    [self._get_component_qty(component) // need
                     for component, need in component_needs.items()]
                )

                potential_qty = bom.product_qty * components_potential_qty

            res[product.id]['potential_qty'] = potential_qty
            res[product.id]['immediately_usable_qty'] += potential_qty
        return res

    def _get_component_qty(self, component):
        """ Return the component qty to use based en company settings.

        :type component: product_product
        :rtype: float
        """
        icp = self.env['ir.config_parameter']
        stock_available_mrp_based_on = icp.get_param(
            'stock_available_mrp_based_on', 'qty_available'
        )

        return component[stock_available_mrp_based_on]

    def _get_components_needs(self, product, bom):
        """ Return the needed qty of each compoments in the *bom* of *product*.

        :type product: product_product
        :type bom: mrp_bom
        :rtype: collections.Counter
        """
        needs = Counter()
        for bom_component in bom.explode(product, 1.0)[1]:
            component = bom_component[0].product_id
            needs += Counter({component: bom_component[1]['qty']})

        return needs

    def _get_component_ids(self):
        """ Compute component_ids by getting all the components for
        this product.
        """
        bom = self.env['mrp.bom']._bom_find(product_id=self.id)
        if bom:
            for bom_component in bom.explode(self, 1.0)[1]:
                self.component_ids |= bom_component[0].product_id
