import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Modesty } from '@/lib/api/types';

interface CartItem {
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
  isLoading: boolean;

  // Actions
  toggleDrawer: () => void;
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
      isLoading: false,

      toggleDrawer: () => set((state) => ({ isOpen: !state.isOpen })),

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
    }
  )
);
