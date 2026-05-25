import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import type {
  AddressResponse,
  ListMessagesResponse,
  MessageRow,
} from "../src/types";

const mocks = vi.hoisted(() => ({
  createAddress: vi.fn() as ReturnType<typeof vi.fn<() => Promise<AddressResponse>>>,
  listMessages: vi.fn() as ReturnType<
    typeof vi.fn<(addr: string, after?: string) => Promise<ListMessagesResponse>>
  >,
  deleteAddress: vi.fn(),
}));

vi.mock("../src/api", () => ({
  api: {
    createAddress: mocks.createAddress,
    listMessages: mocks.listMessages,
    deleteAddress: mocks.deleteAddress,
    presignAttachment: vi.fn(),
  },
}));

const msg = (over: Partial<MessageRow> = {}): MessageRow => ({
  id: "0000000001#abc",
  from: "alice@example.com",
  subject: "Hello",
  received_at: 1779000000,
  body_text: "plain body",
  body_html_safe: "",
  attachments: [],
  ...over,
});

beforeEach(() => {
  mocks.createAddress.mockReset();
  mocks.listMessages.mockReset();
  mocks.deleteAddress.mockReset();
  // navigator.clipboard polyfill
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("<App />", () => {
  it("acquires an address on mount and renders it", async () => {
    mocks.createAddress.mockResolvedValue({
      address: "xyz@dev-temp-mail.com",
      expires_at: "2026-05-25T00:00:00Z",
    });
    mocks.listMessages.mockResolvedValue({ items: [], next_after: null });

    render(<App />);

    expect(await screen.findByTestId("current-address")).toHaveTextContent(
      "xyz@dev-temp-mail.com"
    );
    expect(mocks.createAddress).toHaveBeenCalledTimes(1);
  });

  it("polls list-messages every 5s and appends new items", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocks.createAddress.mockResolvedValue({
      address: "poll@dev-temp-mail.com",
      expires_at: "x",
    });
    mocks.listMessages
      .mockResolvedValueOnce({ items: [], next_after: null })
      .mockResolvedValueOnce({ items: [msg({ id: "001#a" })], next_after: "001#a" })
      .mockResolvedValue({ items: [], next_after: "001#a" });

    render(<App />);

    await screen.findByTestId("current-address");
    // First interval tick fetches the new item and updates the cursor.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5100);
    });
    await screen.findByText("Hello");
    // Second tick must carry the cursor from the previous response.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5100);
    });

    expect(mocks.listMessages.mock.calls.at(-1)).toEqual([
      "poll@dev-temp-mail.com",
      "001#a",
    ]);
  });

  it("renders the body inside a sandbox=\"\" iframe with no-referrer", async () => {
    mocks.createAddress.mockResolvedValue({
      address: "iframe@dev-temp-mail.com",
      expires_at: "x",
    });
    mocks.listMessages.mockResolvedValueOnce({
      items: [
        msg({
          id: "010#b",
          body_html_safe: "<p>safe</p>",
          subject: "click me",
        }),
      ],
      next_after: "010#b",
    });

    render(<App />);
    await screen.findByText("click me");
    fireEvent.click(screen.getByText("click me"));

    const iframe = await screen.findByTestId("message-iframe");
    expect(iframe).toHaveAttribute("sandbox", "");
    expect(iframe).toHaveAttribute("referrerpolicy", "no-referrer");
    const doc = (iframe as HTMLIFrameElement).getAttribute("srcdoc") ?? "";
    expect(doc).toContain("Content-Security-Policy");
    expect(doc).toContain("<p>safe</p>");
  });

  it("clicking '새 주소' clears inbox and requests a fresh address", async () => {
    mocks.createAddress
      .mockResolvedValueOnce({
        address: "first@dev-temp-mail.com",
        expires_at: "x",
      })
      .mockResolvedValueOnce({
        address: "second@dev-temp-mail.com",
        expires_at: "x",
      });
    mocks.listMessages
      .mockResolvedValueOnce({ items: [msg({ id: "1" })], next_after: "1" })
      .mockResolvedValue({ items: [], next_after: null });

    render(<App />);
    await screen.findByText("Hello");

    fireEvent.click(screen.getByRole("button", { name: /새 주소 발급/ }));

    await waitFor(() =>
      expect(screen.getByTestId("current-address")).toHaveTextContent(
        "second@dev-temp-mail.com"
      )
    );
    // Inbox was cleared at the moment of refresh.
    expect(screen.queryByText("Hello")).toBeNull();
    expect(mocks.createAddress).toHaveBeenCalledTimes(2);
  });

  it("copy button writes the address to clipboard", async () => {
    mocks.createAddress.mockResolvedValue({
      address: "clip@dev-temp-mail.com",
      expires_at: "x",
    });
    mocks.listMessages.mockResolvedValue({ items: [], next_after: null });

    render(<App />);
    await screen.findByTestId("current-address");
    fireEvent.click(screen.getByRole("button", { name: /주소 복사/ }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "clip@dev-temp-mail.com"
    );
  });
});
