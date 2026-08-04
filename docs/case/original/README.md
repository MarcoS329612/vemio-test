## Grano

Cada fila representa una transacción a nivel:
- Día
- Cliente
- Producto
- Transacción individual (ticket)
- Promoción dentro de la que se vendió ese producto

## Diccionario de datos

| Columna | Descripción |
|---|---|
| `year`| Año ISO |
| `month` | Mes ISO |
| `date` | Fecha calendario de la transacción (grano diario). |
| `warehouse` | Bodega que despachó el pedido. |
| `route`| Ruta que hizo la venta |
| `product_code` | Identificador numérico del SKU. |
| `product_name` | Descripción comercial del SKU. |
| `client_code` | Identificador del cliente. |
| `client_name` | Nombre del cliente. |
| `category` | Categoría de producto |
| `subcategory` | Subcategoría de producto. |
| `brand` | Marca del SKU. |
| `basket`| Canasto. |
| `ticket_code` | Identificador de la transacción única |
| `sell_in_quantity` | Cantidad de unidades vendidas. |
| `sell_in_amount` | Cantidad monetaria en que se vendieron las unidades vendidas. |
| `id_combo` | Identificador del combo que se aplicó en la transacción, `None` si fue venta orgánica. |
| `combo` | NOmbre del combo que se aplicó en la transacción, `None` si fue venta orgánica. |
| `bruto` | La cantidad monetaria que se debió haber pagado a precio de lista. |
| `discount` | Descuento que implicó la venta en promoción. Calculado como bundle. |
| `product_cost`| Cantidad monetaria que implicó adquirir ese mismo número de productos vendidos. Si
la cantidad vendida es mayor a cero, entonces es costo de adquisión * cantidad vendida. |
| `product_margin` | Margen de ganancia del producto. |