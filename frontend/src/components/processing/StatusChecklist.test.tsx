import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusChecklist from "./StatusChecklist";

describe("StatusChecklist", () => {
  it("spins the icon only on the active step", () => {
    render(<StatusChecklist currentStatus="ANALYZING" />);

    const list = screen.getByRole("list");
    const activeItem = list.querySelector(".ui-stepper-item-active");
    const doneItem = list.querySelector(".ui-stepper-item-done");
    const pendingItem = list.querySelector(".ui-stepper-item-pending");

    expect(activeItem?.querySelector(".ui-icon-spin")).not.toBeNull();
    expect(doneItem?.querySelector(".ui-icon-spin")).toBeNull();
    expect(pendingItem?.querySelector(".ui-icon-spin")).toBeNull();
  });

  it("does not spin any icon once completed", () => {
    render(<StatusChecklist currentStatus="COMPLETED" />);

    expect(screen.getByRole("list").querySelector(".ui-icon-spin")).toBeNull();
  });
});
