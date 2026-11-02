import { useEffect, useState } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * The bag, kept in the browser (localStorage) so guests can shop before
 * signing in. Prices here are for display only: checkout re-prices every line
 * on the server, and the server cart is replaced by this bag at that point.
 */
export interface CartItem {
  variantId: string;
  quantity: number;
  name: string;
  price: number;
  image: string;
  colour: string;
  size: string;
}

interface CartState {
  items: CartItem[];
  isOpen: boolean;

  // Actions
  toggleDrawer: () => void;
  setDrawerOpen: (open: boolean) => void;
  addItem: (item: CartItem) => void;
  removeItem: (variantId: string) => void;
  updateQuantity: (variantId: string, quantity: number) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],
      isOpen: false,

      toggleDrawer: () => set((state) => ({ isOpen: !state.isOpen })),
      setDrawerOpen: (open) => set({ isOpen: open }),

      addItem: (newItem) => set((state) => {
        const existingItem = state.items.find(i => i.variantId === newItem.variantId);
        if (existingItem) {
          return {
            items: state.items.map(i =>
              i.variantId === newItem.variantId
                ? { ...i, quantity: i.quantity + newItem.quantity }
                : i
            )
          };
        }
        return { items: [...state.items, newItem] };
      }),

      removeItem: (variantId) => set((state) => ({
        items: state.items.filter(i => i.variantId !== variantId)
      })),

      updateQuantity: (variantId, quantity) => set((state) => ({
        items: state.items.map(i =>
          i.variantId === variantId
            ? { ...i, quantity: Math.max(1, quantity) }
            : i
        )
      })),

      clearCart: () => set({ items: [] }),
    }),
    {
      name: 'ferasha-cart-storage',
      // Persist the lines only; an open drawer must not survive a reload.
      partialize: (state) => ({ items: state.items }),
    }
  )
);

/**
 * True once the persisted bag has loaded in the browser. The server always
 * renders an empty bag, so anything derived from it (the header count) must
 * wait for this to avoid a hydration mismatch.
 */
export function useBagHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}

export const selectItemCount = (state: { items: CartItem[] }) =>
  state.items.reduce((sum, item) => sum + item.quantity, 0);
