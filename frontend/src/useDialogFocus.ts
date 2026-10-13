import { useEffect, useRef } from "react";

export function useDialogFocus(open: boolean, close: () => void) {
  const dialog = useRef<HTMLDivElement>(null);
  const closeRef = useRef(close);
  useEffect(() => {
    closeRef.current = close;
  }, [close]);
  useEffect(() => {
    if (!open || !dialog.current) return;
    const previous = document.activeElement;
    const node = dialog.current;
    const controls = () =>
      Array.from(
        node.querySelectorAll<HTMLElement>(
          'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), summary, [tabindex="0"]',
        ),
      ).filter((element) => element.getClientRects().length > 0);
    (controls()[0] || node).focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeRef.current();
      }
      if (event.key === "Tab") {
        const items = controls();
        const first = items[0],
          last = items[items.length - 1];
        if (!first) {
          event.preventDefault();
          node.focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    node.addEventListener("keydown", keydown);
    return () => {
      node.removeEventListener("keydown", keydown);
      if (previous instanceof HTMLElement && previous.isConnected)
        previous.focus();
    };
  }, [open]);
  return dialog;
}
