import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import TrailStatusBadge from "./TrailStatusBadge";

describe("TrailStatusBadge", () => {
  it("spins the icon while in progress", () => {
    const { container } = render(<TrailStatusBadge status="IN_PROGRESS" />);
    expect(container.querySelector(".ui-icon-spin")).not.toBeNull();
  });

  it.each(["NOT_STARTED", "COMPLETED"] as const)("does not spin the icon when status is %s", (status) => {
    const { container } = render(<TrailStatusBadge status={status} />);
    expect(container.querySelector(".ui-icon-spin")).toBeNull();
  });
});
