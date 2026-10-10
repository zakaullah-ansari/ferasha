/**
 * FitDrawer behaviour.
 *
 * This is the one component where a bug costs real money: these numbers are
 * cut into cloth. The suite covers the three things most likely to be broken
 * by a later refactor — the unit round trip, the shared validation, and the
 * modal accessibility contract.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FitDrawer, type FitSelection } from "@/components/FitDrawer";

function setup(overrides: Partial<Parameters<typeof FitDrawer>[0]> = {}) {
  const onClose = vi.fn();
  const onSubmit = vi.fn<(s: FitSelection) => void>();
  const utils = render(
    <>
      <button type="button">outside trigger</button>
      <FitDrawer
        open
        onClose={onClose}
        onSubmit={onSubmit}
        garment="suit_set"
        productName="Karachi Lawn Chikankari Suit"
        supportsBespoke
        {...overrides}
      />
    </>,
  );
  return { onClose, onSubmit, ...utils };
}

async function switchToBespoke(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("tab", { name: /bespoke/i }));
}

/** Fill every required suit_set measurement with plausible inches. */
async function fillValidSuit(user: ReturnType<typeof userEvent.setup>) {
  const values: Record<string, string> = {
    Bust: "36",
    Waist: "30",
    Hip: "38",
    Shoulder: "15",
    "Kameez length": "42",
    "Sleeve length": "22",
  };
  for (const [label, value] of Object.entries(values)) {
    const field = screen.getByLabelText(new RegExp(`^${label}`, "i"));
    await user.clear(field);
    await user.type(field, value);
  }
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("dialog accessibility contract", () => {
  it("exposes itself as a modal dialog with an accessible name", () => {
    setup();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName(/select your fit/i);
  });

  it("moves focus into the drawer when opened", async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toContainElement(
        document.activeElement as HTMLElement,
      );
    });
  });

  it("closes on Escape", async () => {
    const user = userEvent.setup();
    const { onClose } = setup();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("traps Tab inside the drawer", async () => {
    const user = userEvent.setup();
    setup();
    const dialog = screen.getByRole("dialog");

    // Tab around well past the number of focusable elements; focus must
    // never land on the trigger button rendered outside the dialog.
    for (let i = 0; i < 25; i += 1) {
      await user.tab();
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("traps Shift+Tab at the start boundary", async () => {
    const user = userEvent.setup();
    setup();
    const dialog = screen.getByRole("dialog");
    for (let i = 0; i < 10; i += 1) {
      await user.tab({ shift: true });
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    }
  });

  it("locks body scroll while open and restores it on close", () => {
    const { unmount } = setup();
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });

  it("renders nothing at all when closed", () => {
    render(
      <FitDrawer
        open={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        garment="suit_set"
        productName="x"
        supportsBespoke
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("standard sizing", () => {
  it("submits the chosen size", async () => {
    const user = userEvent.setup();
    const { onSubmit, onClose } = setup();

    await user.click(screen.getByRole("radio", { name: "L" }));
    await user.click(screen.getByRole("button", { name: /confirm size/i }));

    expect(onSubmit).toHaveBeenCalledWith({ mode: "standard", size: "L" });
    expect(onClose).toHaveBeenCalled();
  });

  it("disables bespoke when the product does not support it", () => {
    setup({ supportsBespoke: false });
    expect(screen.getByRole("tab", { name: /bespoke/i })).toBeDisabled();
  });
});

describe("bespoke measurements", () => {
  it("asks only for what this garment needs", async () => {
    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);

    // suit_set requires these six.
    for (const label of [
      "Bust",
      "Waist",
      "Hip",
      "Shoulder",
      "Kameez length",
      "Sleeve length",
    ]) {
      expect(screen.getByLabelText(new RegExp(`^${label}`, "i"))).toBeInTheDocument();
    }
    // A lehenga measurement has no business on a suit form.
    expect(screen.queryByLabelText(/lehenga length/i)).not.toBeInTheDocument();
  });

  it("submits canonical inches", async () => {
    const user = userEvent.setup();
    const { onSubmit } = setup();
    await switchToBespoke(user);
    await fillValidSuit(user);
    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        mode: "bespoke",
        measurements: expect.objectContaining({ bust: 36, waist: 30, hip: 38 }),
      }),
    );
  });

  it("blocks submission when a measurement is missing", async () => {
    const user = userEvent.setup();
    const { onSubmit, onClose } = setup();
    await switchToBespoke(user);

    await user.type(screen.getByLabelText(/^bust/i), "36");
    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("rejects a centimetre value typed into an inch field", async () => {
    const user = userEvent.setup();
    const { onSubmit } = setup();
    await switchToBespoke(user);
    await fillValidSuit(user);

    // 91 is a normal bust in cm and impossible in inches.
    const bust = screen.getByLabelText(/^bust/i);
    await user.clear(bust);
    await user.type(bust, "91");
    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    // Assert on the bust field's own message rather than whichever alert
    // happens to render first.
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.map((a) => a.textContent).join(" ")).toMatch(/centimetres/i);
  });

  it("associates the error with its input for screen readers", async () => {
    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);
    await fillValidSuit(user);

    const bust = screen.getByLabelText(/^bust/i);
    await user.clear(bust);
    await user.type(bust, "91");
    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    await waitFor(() => expect(bust).toHaveAttribute("aria-invalid", "true"));
    expect(bust).toHaveAccessibleDescription(/centimetres/i);
  });

  it("enforces the backend cross-field rule", async () => {
    const user = userEvent.setup();
    const { onSubmit } = setup({ garment: "blouse" });
    await switchToBespoke(user);

    const entries: Record<string, string> = {
      Bust: "34",
      Underbust: "40", // larger than bust — the serializer forbids this
      Shoulder: "14",
      "Blouse length": "15",
      "Sleeve length": "6",
      Armhole: "16",
    };
    for (const [label, value] of Object.entries(entries)) {
      await user.type(screen.getByLabelText(new RegExp(`^${label}`, "i")), value);
    }
    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(await screen.findAllByRole("alert")).not.toHaveLength(0);
  });
});

describe("unit toggle", () => {
  it("converts displayed values without changing the stored measurement", async () => {
    const user = userEvent.setup();
    const { onSubmit } = setup();
    await switchToBespoke(user);
    await fillValidSuit(user);

    const bust = screen.getByLabelText(/^bust/i) as HTMLInputElement;
    expect(bust.value).toBe("36");

    // Switch to centimetres: 36in is 91.44cm.
    await user.click(screen.getByRole("button", { name: /centimetres/i }));
    await waitFor(() => expect(bust.value).toBe("91.4"));

    // Back to inches, and the original is intact.
    await user.click(screen.getByRole("button", { name: /inches/i }));
    await waitFor(() => expect(bust.value).toBe("36"));

    await user.click(screen.getByRole("button", { name: /save measurements/i }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        measurements: expect.objectContaining({ bust: 36 }),
      }),
    );
  });

  it("accepts entry in centimetres and stores inches", async () => {
    const user = userEvent.setup();
    const { onSubmit } = setup();
    await switchToBespoke(user);
    await fillValidSuit(user);
    await user.click(screen.getByRole("button", { name: /centimetres/i }));

    const bust = screen.getByLabelText(/^bust/i);
    await user.clear(bust);
    await user.type(bust, "91.44");

    await user.click(screen.getByRole("button", { name: /save measurements/i }));

    const selection = onSubmit.mock.calls[0]?.[0] as FitSelection;
    expect(selection.measurements?.bust).toBeCloseTo(36, 4);
  });

  it("shows the range in the user's chosen unit", async () => {
    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);
    // The unit suffix next to each field must follow the toggle.
    expect(screen.getAllByText("in").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /centimetres/i }));
    await waitFor(() => expect(screen.getAllByText("cm").length).toBeGreaterThan(0));
  });
});

describe("draft persistence", () => {
  it("restores an in-progress draft", async () => {
    window.localStorage.setItem(
      "ferasha:fit-draft:v1",
      JSON.stringify({ values: { bust: 38 }, unit: "inch", fullLining: true }),
    );

    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);

    await waitFor(() =>
      expect(screen.getByLabelText(/^bust/i)).toHaveValue(38),
    );
    expect(screen.getByRole("checkbox", { name: /full lining/i })).toBeChecked();
  });

  it("survives a corrupt draft rather than failing to open", async () => {
    window.localStorage.setItem("ferasha:fit-draft:v1", "{{{not json");
    const user = userEvent.setup();
    setup();
    // The drawer still works.
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await switchToBespoke(user);
    expect(screen.getByLabelText(/^bust/i)).toHaveValue(null);
    // And the poison value is cleared out.
    expect(window.localStorage.getItem("ferasha:fit-draft:v1")).toBeNull();
  });

  it("clears the draft once measurements are submitted", async () => {
    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);
    await fillValidSuit(user);
    await user.click(screen.getByRole("button", { name: /save measurements/i }));
    await waitFor(() =>
      expect(window.localStorage.getItem("ferasha:fit-draft:v1")).toBeNull(),
    );
  });
});

describe("touch targets", () => {
  it("gives every control at least a 44px tap height class", async () => {
    const user = userEvent.setup();
    setup();
    await switchToBespoke(user);

    const dialog = screen.getByRole("dialog");
    const inputs = within(dialog).getAllByRole("spinbutton");
    for (const input of inputs) {
      // min-h-11 is 2.75rem = 44px.
      expect(input.className).toMatch(/min-h-(11|12)/);
    }
  });
});
