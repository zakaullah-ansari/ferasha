import React from 'react';
import { cn } from '@/lib/cn';
import { useCartStore } from '@/store/useCartStore';
import { X, Plus, Minus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button'; // Assuming shadcn base

export function CartDrawer({ className }: { className?: string }) {
  const { items, isOpen, toggleDrawer, updateQuantity, removeItem } = useCartStore();

  if (!isOpen) return null;

  const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
  const totalPrice = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
        onClick={toggleDrawer}
      />

      {/* Drawer Content */}
      <div className={cn(
        "relative w-full max-w-md h-full bg-background border-l shadow-2xl transition-transform duration-300 ease-in-out",
        className
      )}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="font-display text-xl tracking-tight">Your Selection</h2>
            <Button variant="ghost" size="icon" onClick={toggleDrawer}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Items List */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                <p className="text-muted-foreground italic">Your cart is currently empty.</p>
                <Button onClick={toggleDrawer} variant="outline">Continue Shopping</Button>
              </div>
            ) : (
              items.map((item) => (
                <div key={item.variantId} className="flex gap-4 group">
                  <div className="h-20 w-20 rounded-lg overflow-hidden bg-muted shrink-0">
                    <img src={item.image} alt={item.name} className="h-full w-full object-cover" />
                  </div>
                  <div className="flex-1 flex flex-col justify-between py-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-sm font-medium leading-none">{item.name}</h3>
                        <p className="text-xs text-muted-foreground mt-1">{item.colour} • {item.size}</p>
                      </div>
                      <p className="text-sm font-medium tabular-nums">{item.price} INR</p>
                    </div>

                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center border rounded-full px-1">
                        <button
                          onClick={() => updateQuantity(item.variantId, item.quantity - 1)}
                          className="p-1 hover:bg-muted rounded-full transition-colors"
                        >
                          <Minus className="h-3 w-3" />
                        </button>
                        <span className="text-xs w-8 text-center font-medium tabular-nums">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => updateQuantity(item.variantId, item.quantity + 1)}
                          className="p-1 hover:bg-muted rounded-full transition-colors"
                        >
                          <Plus className="h-3 w-3" />
                        </button>
                      </div>
                      <button
                        onClick={() => removeItem(item.variantId)}
                        className="text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t bg-muted/30 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Subtotal ({totalItems} items)</span>
              <span className="text-lg font-display font-medium tabular-nums">
                {totalPrice.toLocaleString('en-IN')} INR
              </span>
            </div>
            <Button className="w-full py-6 text-md font-medium tracking-wide" size="lg">
              Proceed to Checkout
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
