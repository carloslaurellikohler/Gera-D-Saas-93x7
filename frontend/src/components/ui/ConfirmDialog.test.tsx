import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConfirmDialog from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("does not render when closed", () => {
    render(
      <ConfirmDialog open={false} title="Excluir?" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the title and description when open", () => {
    render(
      <ConfirmDialog
        open
        title="Excluir o material?"
        description="Esta ação não pode ser desfeita."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Excluir o material?")).toBeInTheDocument();
    expect(screen.getByText("Esta ação não pode ser desfeita.")).toBeInTheDocument();
  });

  it("focuses the cancel button by default on a danger dialog", async () => {
    render(
      <ConfirmDialog open title="Excluir?" tone="danger" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );

    await screen.findByRole("dialog");
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
  });

  it("focuses the confirm button by default on a non-danger dialog", async () => {
    render(<ConfirmDialog open title="Publicar?" onConfirm={vi.fn()} onCancel={vi.fn()} />);

    await screen.findByRole("dialog");
    expect(screen.getByRole("button", { name: "Confirmar" })).toHaveFocus();
  });

  it("calls onConfirm when the confirm button is clicked", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog open title="Excluir?" confirmLabel="Excluir" onConfirm={onConfirm} onCancel={vi.fn()} />,
    );

    await user.click(screen.getByRole("button", { name: "Excluir" }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when the cancel button is clicked", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Excluir?" onConfirm={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when clicking the overlay", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Excluir?" onConfirm={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByRole("dialog").parentElement!);

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when pressing Escape", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Excluir?" onConfirm={vi.fn()} onCancel={onCancel} />);

    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
