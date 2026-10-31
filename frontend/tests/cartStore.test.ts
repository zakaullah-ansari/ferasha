import { describe, it, expect } from 'vitest';
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { useCartStore } from './useCartStore';

// Mocking local storage for persist middleware
const localStorageMock = (() => {
  let store: Record<string, any> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('useCartStore', () => {
  it('should add items to the cart', () => {
    const store = useCartStore.getState();
    store.addItem({ id: 'v1', name: 'Silk Saree', price: 12000, quantity: 1 });

    expect(store.items).toHaveLength(1);
    expect(store.items[0].id).toBe('v1');
  });

  it('should update quantity of existing items', () => {
    const store = useCartStore.getState();
    store.addItem({ id: 'v1', name: 'Silk Saree', price: 12000, quantity: 1 });
    store.updateQuantity('v1', 2);

    expect(store.items[0].quantity).toBe(2);
  });

  it('should calculate the total price correctly', () => {
    const store = useCartStore.getState();
    store.clearCart();
    store.addItem({ id: 'v1', name: 'Saree', price: 1000, quantity: 2 });
    store.addItem({ id: 'v2', name: 'Dupatta', price: 500, quantity: 1 });

    // Total = (1000*2) + (500*1) = 2500
    expect(store.getTotalPrice()).toBe(2500);
  });
});
