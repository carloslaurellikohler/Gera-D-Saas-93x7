import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import StatusBadge from "./StatusBadge";
import type { AnalysisStatus } from "../../types/analysis";

const SPINNING_STATUSES: AnalysisStatus[] = ["TRANSCRIBING", "ANALYZING", "GENERATING_REPORTS"];
const STATIC_STATUSES: AnalysisStatus[] = ["CREATED", "UPLOADED", "TRANSCRIBED", "COMPLETED", "FAILED"];

describe("StatusBadge", () => {
  it.each(SPINNING_STATUSES)("spins the icon while status is %s", (status) => {
    const { container } = render(<StatusBadge status={status} />);
    expect(container.querySelector(".ui-icon-spin")).not.toBeNull();
  });

  it.each(STATIC_STATUSES)("does not spin the icon when status is %s", (status) => {
    const { container } = render(<StatusBadge status={status} />);
    expect(container.querySelector(".ui-icon-spin")).toBeNull();
  });
});
