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

    expect(items()).toEqual([{ ...saree, lineId: saree.variantId }]);
  });

  it("accumulates quantity when the same variant is added again", () => {
    useCartStore.getState().addItem(saree);
    useCartStore.getState().addItem({ ...saree, quantity: 2 });

    expect(items()).toHaveLength(1);
    expect(items()[0]?.quantity).toBe(3);
  });

  it("never lets quantity fall below one", () => {
    useCartStore.getState().addItem(saree);
    useCartStore.getState().updateQuantity(saree.variantId, 0); // a ready-made line's id is its variant

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
    expect(stored.state.items).toEqual([{ ...saree, lineId: saree.variantId }]);
  });
});

describe("made-to-measure lines", () => {
  const bespoke = {
    ...saree,
    variantId: "v-custom",
    size: "Made to measure",
    price: 15000,
    bespoke: { measurements: { bust: 36 }, preferences: {} },
  };

  beforeEach(() => {
    useCartStore.getState().clearCart();
  });

  it("keeps every piece its own line, however alike", () => {
    useCartStore.getState().addItem(bespoke);
    useCartStore.getState().addItem({ ...bespoke, bespoke: { measurements: { bust: 34 }, preferences: {} } });

    expect(items()).toHaveLength(2);
    expect(new Set(items().map((item) => item.lineId)).size).toBe(2);
  });

  it("is always one piece", () => {
    useCartStore.getState().addItem({ ...bespoke, quantity: 3 });
    const [line] = items();
    useCartStore.getState().updateQuantity(line!.lineId, 4);

    expect(items()[0]?.quantity).toBe(1);
  });

  it("removes only the piece asked for", () => {
    useCartStore.getState().addItem(bespoke);
    useCartStore.getState().addItem(bespoke);
    useCartStore.getState().removeItem(items()[0]!.lineId);

    expect(items()).toHaveLength(1);
  });

  it("upgrades a bag saved before lines had their own identity", async () => {
    const migrate = useCartStore.persist.getOptions().migrate!;
    const old = { items: [{ ...saree }] };

    const upgraded = (await migrate(old, 0)) as { items: { lineId: string }[] };

    expect(upgraded.items[0]?.lineId).toBe(saree.variantId);
  });
});
