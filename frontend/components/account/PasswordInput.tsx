"use client";

import { ArrowBigUpDash, Eye, EyeOff } from "lucide-react";
import { type ComponentProps, type KeyboardEvent, useEffect, useRef, useState } from "react";

import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from "@/components/ui/input-group";

/**
 * A password input with a show/hide toggle (shadcn InputGroup).
 *
 * The toggle is a real button (aria-pressed, keyboard reachable) that never
 * submits the form. The password hides again whenever its form is submitted,
 * so it is never left on screen behind a loading state or an error. A quiet
 * "Caps Lock is on" note appears while it is (a classic cause of "wrong password").
 */
export function PasswordInput({
  onKeyDown,
  onKeyUp,
  onBlur,
  ...props
}: Omit<ComponentProps<typeof InputGroupInput>, "type">) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const readCapsLock = (event: KeyboardEvent<HTMLInputElement>) =>
    setCapsLock(event.getModifierState?.("CapsLock") ?? false);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const form = ref.current?.form;
    if (!form) return;
    const hide = () => setVisible(false);
    form.addEventListener("submit", hide);
    return () => form.removeEventListener("submit", hide);
  }, []);

  return (
    <>
    <InputGroup>
      <InputGroupInput
        ref={ref}
        type={visible ? "text" : "password"}
        // Keep mobile keyboards from capitalising or "correcting" a visible password.
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        onKeyDown={(event) => {
          readCapsLock(event);
          onKeyDown?.(event);
        }}
        onKeyUp={(event) => {
          readCapsLock(event);
          onKeyUp?.(event);
        }}
        onBlur={(event) => {
          setCapsLock(false);
          onBlur?.(event);
        }}
        {...props}
      />
      <InputGroupAddon align="inline-end">
        <InputGroupButton
          size="icon-xs"
          aria-label="Show password"
          aria-pressed={visible}
          aria-controls={props.id}
          onClick={() => setVisible((shown) => !shown)}
        >
          {visible ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
        </InputGroupButton>
      </InputGroupAddon>
    </InputGroup>
    {capsLock && (
      <p role="status" className="inline-flex items-center gap-1 text-xs text-gold-800 dark:text-gold-300">
        <ArrowBigUpDash aria-hidden className="size-3.5" />
        Caps Lock is on
      </p>
    )}
    </>
  );
}
