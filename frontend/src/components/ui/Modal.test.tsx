import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modal from "./Modal";

describe("Modal", () => {
  it("does not render when closed", () => {
    render(
      <Modal open={false} title="Novo item" onClose={vi.fn()}>
        <input aria-label="Campo" />
      </Modal>,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the title and children when open", () => {
    render(
      <Modal open title="Novo item" onClose={vi.fn()}>
        <input aria-label="Campo" />
      </Modal>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Novo item")).toBeInTheDocument();
    expect(screen.getByLabelText("Campo")).toBeInTheDocument();
  });

  it("focuses the first focusable field in the body on open, not the close button", async () => {
    render(
      <Modal open title="Novo item" onClose={vi.fn()}>
        <input aria-label="Campo" />
      </Modal>,
    );

    await screen.findByRole("dialog");
    expect(screen.getByLabelText("Campo")).toHaveFocus();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open title="Novo item" onClose={onClose}>
        <input aria-label="Campo" />
      </Modal>,
    );

    await user.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open title="Novo item" onClose={onClose}>
        <input aria-label="Campo" />
      </Modal>,
    );

    await user.click(screen.getByRole("dialog").parentElement!);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <Modal open title="Novo item" onClose={onClose}>
        <input aria-label="Campo" />
      </Modal>,
    );

    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("traps Tab focus between the close button and the last field", async () => {
    const user = userEvent.setup();
    render(
      <Modal open title="Novo item" onClose={vi.fn()}>
        <input aria-label="Primeiro campo" />
        <button type="button">Salvar</button>
      </Modal>,
    );

    await screen.findByRole("dialog");
    expect(screen.getByLabelText("Primeiro campo")).toHaveFocus();

    screen.getByRole("button", { name: "Salvar" }).focus();
    await user.tab();

    expect(screen.getByRole("button", { name: "Fechar" })).toHaveFocus();
  });

  it("toggles document.body overflow while open", () => {
    const { unmount } = render(
      <Modal open title="Novo item" onClose={vi.fn()}>
        <input aria-label="Campo" />
      </Modal>,
    );

    expect(document.body.style.overflow).toBe("hidden");

    unmount();

    expect(document.body.style.overflow).not.toBe("hidden");
  });
  it("renders the footer and the header actions when given", () => {
    render(
      <Modal
        open
        title="Novo item"
        onClose={vi.fn()}
        headerActions={<span>Rascunho</span>}
        footer={<button type="button">Publicar</button>}
      >
        <input aria-label="Campo" />
      </Modal>,
    );

    expect(screen.getByText("Rascunho")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar" })).toBeInTheDocument();
  });

  it("keeps the initial focus in the body even with a footer present", async () => {
    render(
      <Modal open title="Novo item" onClose={vi.fn()} footer={<button type="button">Publicar</button>}>
        <input aria-label="Campo" />
      </Modal>,
    );

    await screen.findByRole("dialog");
    expect(screen.getByLabelText("Campo")).toHaveFocus();
  });

  it("includes the footer buttons in the focus trap", async () => {
    const user = userEvent.setup();
    render(
      <Modal open title="Novo item" onClose={vi.fn()} footer={<button type="button">Publicar</button>}>
        <input aria-label="Campo" />
      </Modal>,
    );

    // O rodapé é o último focável do painel: daí o Tab volta para o Fechar, o primeiro.
    screen.getByRole("button", { name: "Publicar" }).focus();
    await user.tab();

    expect(screen.getByRole("button", { name: "Fechar" })).toHaveFocus();
  });

  it("applies the full size class", () => {
    render(
      <Modal open title="Novo item" onClose={vi.fn()} size="full">
        <input aria-label="Campo" />
      </Modal>,
    );

    expect(screen.getByRole("dialog")).toHaveClass("ui-modal-panel-full");
  });
});
