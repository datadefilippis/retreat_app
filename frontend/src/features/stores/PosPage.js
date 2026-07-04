/**
 * PosPage — simplified point-of-sale interface for in-person sales.
 *
 * Accessed via /pos/:storeId. Shows a product grid with quick add,
 * a cart summary, and a single "Complete order" button that creates
 * + confirms the order in one step.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  ShoppingCart, Plus, Minus, Loader2, Trash2, CheckCircle2, ArrowLeft,
} from 'lucide-react';
import { productsAPI, ordersAPI, storesAPI } from '../../api';
import { toast } from 'sonner';
import { useCurrency } from '../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../lib/utils';

// CH compliance v1: pos prices flow through the shared currency-aware
// formatter. The closure form below is replaced by an org-bound helper
// inside the component (see ``fmtPrice`` near the top of PosPage).

export default function PosPage() {
  const { storeId } = useParams();
  const { t } = useTranslation('pos');
  const navigate = useNavigate();
  const orgCurrency = useCurrency();
  const fmtPrice = (v) => v != null ? fmtCurrency(Number(v), orgCurrency) : '-';

  const [store, setStore] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Cart: { productId: { product, quantity } }
  const [cart, setCart] = useState({});
  const [customerName, setCustomerName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [orderDone, setOrderDone] = useState(null); // order object after completion

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [storeRes, productsRes] = await Promise.all([
        storesAPI.get(storeId),
        productsAPI.list(true, 500),
      ]);
      setStore(storeRes.data);
      // Filter products for this store
      const all = productsRes.data || [];
      const filtered = all.filter(p =>
        (p.store_ids?.includes(storeId) || !p.store_ids?.length) && p.is_active
      );
      setProducts(filtered);
    } catch {
      toast.error(t('error.load'));
    } finally { setLoading(false); }
  }, [storeId]);

  useEffect(() => { load(); }, [load]);

  const addToCart = (product) => {
    setCart(prev => {
      const existing = prev[product.id];
      if (existing) {
        return { ...prev, [product.id]: { ...existing, quantity: existing.quantity + 1 } };
      }
      return { ...prev, [product.id]: { product, quantity: 1 } };
    });
  };

  const updateQty = (productId, delta) => {
    setCart(prev => {
      const item = prev[productId];
      if (!item) return prev;
      const newQty = item.quantity + delta;
      if (newQty <= 0) {
        const next = { ...prev };
        delete next[productId];
        return next;
      }
      return { ...prev, [productId]: { ...item, quantity: newQty } };
    });
  };

  const removeFromCart = (productId) => {
    setCart(prev => {
      const next = { ...prev };
      delete next[productId];
      return next;
    });
  };

  const cartItems = Object.values(cart);
  const cartTotal = cartItems.reduce((sum, { product, quantity }) => sum + (product.unit_price || 0) * quantity, 0);

  const handleSubmit = async () => {
    if (cartItems.length === 0 || !customerName.trim()) return;
    setSubmitting(true);
    try {
      const res = await ordersAPI.pos({
        customer_name: customerName.trim(),
        store_id: storeId,
        items: cartItems.map(({ product, quantity }) => ({
          product_id: product.id,
          quantity,
          unit_price: product.unit_price || 0,
        })),
      });
      setOrderDone(res.data);
      setCart({});
      setCustomerName('');
      toast.success(t('toast.completed'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    } finally { setSubmitting(false); }
  };

  if (loading) {
    return (
      <AppLayout>
        <Header title="POS" />
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <Header title={store?.name || 'POS'} subtitle={t('subtitle')}>
        <Button variant="outline" size="sm" onClick={() => navigate('/stores')} className="gap-1">
          <ArrowLeft className="h-3.5 w-3.5" /> {t('back')}
        </Button>
      </Header>

      <div className="p-4 md:p-6">
        <div className="flex gap-6">
          {/* Product grid */}
          <div className="flex-1">
            {orderDone && (
              <Card className="border-emerald-200 bg-emerald-50/30 mb-4">
                <CardContent className="py-3 px-4 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-emerald-800">
                    <CheckCircle2 className="h-4 w-4" />
                    {t('order_done', { number: orderDone.order_number || orderDone.id?.slice(0, 8) })}
                  </div>
                  <Button variant="outline" size="sm" onClick={() => setOrderDone(null)}>{t('new_order')}</Button>
                </CardContent>
              </Card>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {products.map(p => {
                const inCart = cart[p.id]?.quantity || 0;
                return (
                  <button
                    key={p.id}
                    onClick={() => addToCart(p)}
                    className={`rounded-xl border p-3 text-left hover:shadow-md transition-shadow ${inCart > 0 ? 'border-primary bg-primary/5' : ''}`}
                  >
                    <p className="text-sm font-medium truncate">{p.name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{p.category || ''}</p>
                    <p className="text-sm font-bold mt-2">{fmtPrice(p.unit_price)}</p>
                    {inCart > 0 && (
                      <span className="mt-1 inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary text-white text-[10px] font-bold">
                        {inCart}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Cart sidebar */}
          <div className="w-80 shrink-0">
            <Card className="sticky top-20">
              <CardContent className="py-4 px-4 space-y-3">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4" />
                  <h3 className="text-sm font-semibold">{t('cart.title')}</h3>
                  <span className="text-xs text-muted-foreground">({cartItems.length})</span>
                </div>

                {cartItems.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">{t('cart.empty')}</p>
                ) : (
                  <div className="space-y-2">
                    {cartItems.map(({ product, quantity }) => (
                      <div key={product.id} className="flex items-center justify-between text-sm">
                        <div className="flex-1 min-w-0">
                          <p className="truncate font-medium">{product.name}</p>
                          <p className="text-xs text-muted-foreground">{fmtPrice(product.unit_price)}</p>
                        </div>
                        <div className="flex items-center gap-1 ml-2">
                          <button onClick={() => updateQty(product.id, -1)} className="h-6 w-6 rounded border flex items-center justify-center hover:bg-muted">
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="text-sm font-bold w-6 text-center">{quantity}</span>
                          <button onClick={() => updateQty(product.id, 1)} className="h-6 w-6 rounded border flex items-center justify-center hover:bg-muted">
                            <Plus className="h-3 w-3" />
                          </button>
                          <button onClick={() => removeFromCart(product.id)} className="h-6 w-6 rounded flex items-center justify-center text-red-400 hover:text-red-600">
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Total */}
                <div className="border-t pt-2 flex justify-between items-center">
                  <span className="text-sm font-semibold">{t('cart.total')}</span>
                  <span className="text-lg font-bold">{fmtPrice(cartTotal)}</span>
                </div>

                {/* Customer name */}
                <Input
                  placeholder={t('cart.customer_placeholder')}
                  value={customerName}
                  onChange={e => setCustomerName(e.target.value)}
                />

                {/* Submit */}
                <Button
                  className="w-full gap-1.5"
                  disabled={submitting || cartItems.length === 0 || !customerName.trim()}
                  onClick={handleSubmit}
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  {t('cart.complete')}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
