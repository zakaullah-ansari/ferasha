import { useEffect, useState } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * The bag, kept in the browser (localStorage) so guests can shop before
 * signing in. Prices here are for display only: checkout re-prices every line
 * on the server, and the server cart is replaced by this bag at that point.
 */
/** A made-to-measure piece: measurements in inches, and stitching preferences. */
export interface BespokeChoice {
  measurements: Record<string, number>;
  preferences: Record<string, string>;
}

export interface CartItem {
  /**
   * The line's own identity. A ready-made line is its variant (adding it
   * again adds to the quantity); every bespoke piece is a line of its own,
   * so two pieces cut to different measurements never merge.
   */
  lineId: string;
  variantId: string;
  quantity: number;
  name: string;
  /** One piece, including the stitching surcharge for a bespoke line. */
  price: number;
  image: string;
  colour: string;
  size: string;
  /** Present for a made-to-measure line, which is always one piece. */
  bespoke?: BespokeChoice;
}

export type NewCartItem = Omit<CartItem, "lineId">;

interface CartState {
  items: CartItem[];
  isOpen: boolean;

  // Actions
  toggleDrawer: () => void;
  setDrawerOpen: (open: boolean) => void;
  addItem: (item: NewCartItem) => void;
  removeItem: (lineId: string) => void;
  updateQuantity: (lineId: string, quantity: number) => void;
  clearCart: () => void;
  /** Drop every made-to-measure piece (and with it, its measurements). Used at sign-out. */
  forgetMeasurements: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      isOpen: false,

      toggleDrawer: () => set((state) => ({ isOpen: !state.isOpen })),
      setDrawerOpen: (open) => set({ isOpen: open }),

      addItem: (newItem) =>
        set((state) => {
          if (newItem.bespoke) {
            return { items: [...state.items, { ...newItem, quantity: 1, lineId: `bespoke-${crypto.randomUUID()}` }] };
          }
          const lineId = newItem.variantId;
          const existing = state.items.find((item) => item.lineId === lineId);
          if (existing) {
            return {
              items: state.items.map((item) =>
                item.lineId === lineId ? { ...item, quantity: item.quantity + newItem.quantity } : item,
              ),
            };
          }
          return { items: [...state.items, { ...newItem, lineId }] };
        }),

      removeItem: (lineId) => set((state) => ({ items: state.items.filter((item) => item.lineId !== lineId) })),

      updateQuantity: (lineId, quantity) =>
        set((state) => ({
          items: state.items.map((item) =>
            // A bespoke piece is always one: each is cut to its own measurements.
            item.lineId === lineId && !item.bespoke ? { ...item, quantity: Math.max(1, quantity) } : item,
          ),
        })),

      clearCart: () => set({ items: [] }),

      forgetMeasurements: () => set((state) => ({ items: state.items.filter((item) => !item.bespoke) })),
    }),
    {
      name: "ferasha-cart-storage",
      // Persist the lines only; an open drawer must not survive a reload.
      partialize: (state) => ({ items: state.items }),
      // v2 added lineId. A bag saved before it was all ready-made lines,
      // whose identity is their variant.
      version: 2,
      migrate: (persisted, version) => {
        const saved = (persisted ?? {}) as { items?: Omit<CartItem, "lineId">[] };
        if (version < 2) {
          return { items: (saved.items ?? []).map((item) => ({ ...item, lineId: item.variantId })) };
        }
        return saved as { items: CartItem[] };
      },
    },
  ),
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
