import { beforeEach, describe, expect, it } from "vitest";

import { useCartStore } from "@/store/useCartStore";

const saree = {
  variantId: "v-saree",
  name: "Silk Saree",
  price: 12000,
  quantity: 1,
  image: "/saree.jpg",
  colour: "Ivory",
  size: "M",
};

// getState() returns a snapshot; read it again after every action rather than
// holding one reference across mutations.
const items = () => useCartStore.getState().items;

describe("useCartStore", () => {
  beforeEach(() => {
    useCartStore.getState().clearCart();
  });

  it("adds a new line", () => {
    useCartStore.getState().addItem(saree);

    expect(items()).toEqual([saree]);
  });

  it("accumulates quantity when the same variant is added again", () => {
    useCartStore.getState().addItem(saree);
    useCartStore.getState().addItem({ ...saree, quantity: 2 });

    expect(items()).toHaveLength(1);
    expect(items()[0]?.quantity).toBe(3);
  });

  it("never lets quantity fall below one", () => {
    useCartStore.getState().addItem(saree);
    useCartStore.getState().updateQuantity(saree.variantId, 0);

    expect(items()[0]?.quantity).toBe(1);
  });

  it("removes a line", () => {
    useCartStore.getState().addItem(saree);
    useCartStore.getState().removeItem(saree.variantId);

    expect(items()).toEqual([]);
  });

  it("persists the bag to localStorage", () => {
    useCartStore.getState().addItem(saree);

    const stored = JSON.parse(window.localStorage.getItem("ferasha-cart-storage") ?? "{}");
    expect(stored.state.items).toEqual([saree]);
  });
});
